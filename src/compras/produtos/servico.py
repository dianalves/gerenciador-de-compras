"""Liga itens de compra a produtos, sugere e executa junções."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from compras.banco.modelos import ApelidoProduto, ItemCompra, Produto
from compras.produtos.normalizar import normalizar, parecidos


def _limpa(descricao: str) -> str:
    return " ".join(descricao.upper().split())


def produto_para(sessao: Session, descricao: str, categoria: str = "mercearia") -> Produto:
    """Acha (ou cria) o produto de uma descrição de cupom e lembra a descrição como apelido."""
    descricao = _limpa(descricao)
    apelido = sessao.scalar(select(ApelidoProduto).where(ApelidoProduto.descricao == descricao))
    if apelido:
        return apelido.produto

    norm = normalizar(descricao)
    produto = sessao.scalar(select(Produto).where(Produto.chave == norm.chave))
    if produto is None:
        produto = Produto(nome=norm.nome or descricao, chave=norm.chave or descricao,
                          categoria=categoria, tamanho=norm.tamanho,
                          unidade_tamanho=norm.unidade)
        sessao.add(produto)
    sessao.add(ApelidoProduto(descricao=descricao, produto=produto))
    sessao.flush()
    return produto


def vincular_pendentes(sessao: Session) -> int:
    """Liga ao produto todo item que ainda não tem um (itens importados antes desta etapa)."""
    itens = sessao.scalars(select(ItemCompra).where(ItemCompra.produto_id.is_(None))).all()
    for item in itens:
        item.produto = produto_para(sessao, item.descricao, item.categoria)
    sessao.commit()
    return len(itens)


@dataclass
class Sugestao:
    origem: Produto
    destino: Produto
    semelhanca: float


def sugerir_juncoes(sessao: Session, minimo: float = 0.85) -> list[Sugestao]:
    """Pares de produtos que parecem ser o mesmo. Destino = o de nome mais completo."""
    produtos = sessao.scalars(select(Produto)).all()
    normais = {p.id: normalizar(p.nome) for p in produtos}
    sugestoes = []
    for a, b in combinations(produtos, 2):
        if a.categoria != b.categoria:
            continue
        nota = parecidos(normais[a.id], normais[b.id])
        if nota >= minimo:
            origem, destino = sorted((a, b), key=lambda p: (p.tamanho is not None, len(p.nome)))
            sugestoes.append(Sugestao(origem, destino, nota))
    return sorted(sugestoes, key=lambda s: -s.semelhanca)


def juntar(sessao: Session, origem_id: int, destino_id: int) -> Produto:
    """Move itens e apelidos da origem para o destino e apaga a origem."""
    if origem_id == destino_id:
        raise ValueError("Origem e destino são o mesmo produto")
    origem, destino = sessao.get(Produto, origem_id), sessao.get(Produto, destino_id)
    if origem is None or destino is None:
        raise ValueError("Produto não encontrado")
    for item in list(origem.itens):
        item.produto = destino
    for apelido in list(origem.apelidos):
        apelido.produto = destino
    sessao.flush()
    sessao.delete(origem)
    sessao.commit()
    return destino


def buscar(sessao: Session, texto: Optional[str] = None) -> list[Produto]:
    consulta = select(Produto).order_by(Produto.categoria, Produto.nome)
    if texto:
        consulta = consulta.where(Produto.nome.ilike(f"%{texto.upper()}%"))
    return list(sessao.scalars(consulta).all())
