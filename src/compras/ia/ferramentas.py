"""Ferramentas que o agente pode chamar. São as ÚNICAS portas do modelo para os dados:
consultas prontas, somente leitura, com parâmetros validados (nada de SQL livre).

Cada ferramenta devolve texto curto e direto, fácil para um modelo pequeno ler.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Callable, Optional

from langchain_core.tools import BaseTool, tool
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from compras.banco.modelos import Compra, Estabelecimento, ItemCompra, Produto
from compras.nota.esquema import CATEGORIAS


def _reais(valor) -> str:
    texto = f"{Decimal(str(valor or 0)):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _periodo(data_inicio: str, data_fim: str) -> tuple[datetime, datetime]:
    """Datas 'AAAA-MM-DD' -> intervalo [início 00:00, dia seguinte ao fim 00:00)."""
    inicio = datetime.fromisoformat(data_inicio[:10])
    fim = datetime.fromisoformat(data_fim[:10]) + timedelta(days=1)
    if fim <= inicio:
        raise ValueError("data_fim precisa ser igual ou depois de data_inicio")
    return inicio, fim


def _categoria_valida(categoria: Optional[str]) -> Optional[str]:
    if not categoria:
        return None
    categoria = categoria.strip().lower().replace(" ", "_")
    if categoria not in CATEGORIAS:
        raise ValueError(f"Categoria inválida. Use uma de: {', '.join(CATEGORIAS)}")
    return categoria


def criar_ferramentas(abrir_sessao: Callable[[], Session]) -> list[BaseTool]:
    """Monta as ferramentas ligadas ao banco. `abrir_sessao` cria uma sessão por chamada."""

    @tool
    def gasto_total(data_inicio: str, data_fim: str, categoria: Optional[str] = None) -> str:
        """Quanto foi gasto no período (datas AAAA-MM-DD, inclusive), opcionalmente só
        numa categoria (mercearia, carnes, bebidas, hortifruti, frios_laticinios, padaria,
        limpeza, higiene, pet, congelados)."""
        inicio, fim = _periodo(data_inicio, data_fim)
        categoria = _categoria_valida(categoria)
        with abrir_sessao() as s:
            if categoria:
                total = s.scalar(
                    select(func.sum(ItemCompra.valor_total)).join(Compra)
                    .where(Compra.data_emissao >= inicio, Compra.data_emissao < fim,
                           ItemCompra.categoria == categoria))
            else:
                total = s.scalar(select(func.sum(Compra.valor_total))
                                 .where(Compra.data_emissao >= inicio, Compra.data_emissao < fim))
            compras = s.scalar(select(func.count(Compra.id))
                               .where(Compra.data_emissao >= inicio, Compra.data_emissao < fim))
        alvo = f" em {categoria}" if categoria else ""
        return (f"Gasto{alvo} de {data_inicio} a {data_fim}: {_reais(total)} "
                f"({compras} compra(s) no período).")

    @tool
    def gasto_por_categoria(data_inicio: str, data_fim: str) -> str:
        """Gasto de cada categoria no período (datas AAAA-MM-DD), do maior para o menor."""
        inicio, fim = _periodo(data_inicio, data_fim)
        with abrir_sessao() as s:
            linhas = s.execute(
                select(ItemCompra.categoria, func.sum(ItemCompra.valor_total)).join(Compra)
                .where(Compra.data_emissao >= inicio, Compra.data_emissao < fim)
                .group_by(ItemCompra.categoria)
                .order_by(func.sum(ItemCompra.valor_total).desc())).all()
        if not linhas:
            return f"Nenhuma compra de {data_inicio} a {data_fim}."
        return "\n".join(f"{c}: {_reais(t)}" for c, t in linhas)

    @tool
    def produtos_mais_gastos(data_inicio: str, data_fim: str, limite: int = 10) -> str:
        """Produtos com que mais se gastou no período (datas AAAA-MM-DD)."""
        inicio, fim = _periodo(data_inicio, data_fim)
        with abrir_sessao() as s:
            linhas = s.execute(
                select(Produto.nome, func.sum(ItemCompra.quantidade), ItemCompra.unidade,
                       func.sum(ItemCompra.valor_total))
                .join(ItemCompra, ItemCompra.produto_id == Produto.id).join(Compra)
                .where(Compra.data_emissao >= inicio, Compra.data_emissao < fim)
                .group_by(Produto.nome, ItemCompra.unidade)
                .order_by(func.sum(ItemCompra.valor_total).desc())
                .limit(max(1, min(limite, 30)))).all()
        if not linhas:
            return f"Nenhuma compra de {data_inicio} a {data_fim}."
        return "\n".join(f"{n}: {_reais(t)} ({Decimal(str(q)).normalize():f} {u.lower()})"
                         for n, q, u, t in linhas)

    @tool
    def compras_no_periodo(data_inicio: str, data_fim: str) -> str:
        """Lista as compras (data, mercado, total) no período (datas AAAA-MM-DD)."""
        inicio, fim = _periodo(data_inicio, data_fim)
        with abrir_sessao() as s:
            linhas = s.execute(
                select(Compra.data_emissao, Estabelecimento.nome, Compra.valor_total).join(Estabelecimento)
                .where(Compra.data_emissao >= inicio, Compra.data_emissao < fim)
                .order_by(Compra.data_emissao)).all()
        if not linhas:
            return f"Nenhuma compra de {data_inicio} a {data_fim}."
        return "\n".join(f"{d:%Y-%m-%d} {m}: {_reais(t)}" for d, m, t in linhas)

    @tool
    def buscar_produtos(texto: str) -> str:
        """Procura produtos pelo nome (ex.: 'coca', 'arroz'). Devolve id e nome; use o id
        nas ferramentas historico_preco."""
        from compras.produtos.servico import buscar

        with abrir_sessao() as s:
            achados = buscar(s, texto)[:15]
            if not achados:
                return f"Nenhum produto com '{texto}': esse produto nunca foi comprado."
            return "\n".join(f"id {p.id}: {p.nome} ({p.categoria})" for p in achados)

    @tool
    def historico_preco(produto_id: int) -> str:
        """Cada compra de um produto: data, mercado, quantidade, preço unitário e total."""
        from compras.produtos.precos import historico

        with abrir_sessao() as s:
            produto = s.get(Produto, produto_id)
            if produto is None:
                return f"Produto {produto_id} não existe. Use buscar_produtos."
            precos = historico(s, produto_id)
        linhas = [f"{p.data:%Y-%m-%d} {p.mercado}: {Decimal(p.quantidade).normalize():f} "
                  f"{p.unidade.lower()} x {_reais(p.valor_unitario)} = {_reais(p.valor_total)}"
                  for p in precos]
        return f"{produto.nome}:\n" + "\n".join(linhas)

    @tool
    def comparar_mercados() -> str:
        """Produtos comprados em mais de um mercado e onde saíram mais baratos."""
        from compras.produtos.precos import comparar_mercados as comparar

        with abrir_sessao() as s:
            comparacoes = comparar(s)
        if not comparacoes:
            return "Nenhum produto foi comprado em mais de um mercado."
        return "\n".join(
            f"{c.produto}: mais barato no {c.mais_barato} ({_reais(c.preco_mais_barato)}/"
            f"{c.unidade.lower()}), mais caro no {c.mais_caro} ({_reais(c.preco_mais_caro)}), "
            f"diferença {c.percentual:.0f}%" for c in comparacoes[:15])

    @tool
    def produtos_que_mudaram_de_preco(limite: int = 10) -> str:
        """Produtos cujo preço unitário mais mudou entre a primeira e a última compra
        (responde 'o que ficou mais caro/mais barato')."""
        from compras.produtos.precos import variacao_de_precos

        with abrir_sessao() as s:
            variacoes = variacao_de_precos(s)[:max(1, min(limite, 30))]
        if not variacoes:
            return "Nenhum produto foi comprado mais de uma vez com preços diferentes."
        return "\n".join(
            f"{v.produto}: {_reais(v.preco_antes)} ({v.data_antes:%Y-%m-%d}) -> "
            f"{_reais(v.preco_depois)} ({v.data_depois:%Y-%m-%d}), {v.percentual:+.0f}%"
            for v in variacoes)

    @tool
    def estoque_atual(categoria: Optional[str] = None, nome: Optional[str] = None) -> str:
        """O que tem em casa agora, com quantidades e categoria de cada item.
        Use `categoria` para tipos de produto ("tem bebida?" -> bebidas; "tem carne?" ->
        carnes; frutas/verduras -> hortifruti). Use `nome` para um produto ("tem arroz?").
        Sem nada: lista todo o estoque."""
        import re

        from compras.estoque.servico import saldo
        from compras.produtos.normalizar import sem_acento

        categoria = _categoria_valida(categoria)
        with abrir_sessao() as s:
            itens = saldo(s)
        if categoria:
            itens = [i for i in itens if i.categoria == categoria]
        if nome:
            palavras = [p for p in re.split(r"[^A-Z0-9]+", sem_acento(nome)) if p]
            itens = [i for i in itens if all(p in i.nome for p in palavras)]
        if not itens:
            alvo = " ".join(x for x in (categoria, nome and f"'{nome}'") if x)
            return f"Nada no estoque{' de ' + alvo if alvo else ''}."
        return "\n".join(f"{i.nome} ({i.categoria}): {Decimal(i.quantidade).normalize():f} "
                         f"{i.unidade.lower()}" for i in itens)

    return [gasto_total, gasto_por_categoria, produtos_mais_gastos, compras_no_periodo,
            buscar_produtos, historico_preco, comparar_mercados, produtos_que_mudaram_de_preco,
            estoque_atual]
