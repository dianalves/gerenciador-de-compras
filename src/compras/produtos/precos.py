"""Preço do mesmo produto ao longo do tempo e entre mercados."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from compras.banco.modelos import Compra, Estabelecimento, ItemCompra, Produto


@dataclass
class Preco:
    """Uma compra do produto (várias linhas iguais no mesmo cupom viram uma só)."""
    data: Optional[datetime]
    mercado: str
    valor_unitario: Decimal  # por un ou por kg: é o que dá para comparar entre compras
    unidade: str
    quantidade: Decimal
    valor_total: Decimal


@dataclass
class Comparacao:
    produto_id: int
    produto: str
    unidade: str
    mais_barato: str
    preco_mais_barato: Decimal
    mais_caro: str
    preco_mais_caro: Decimal

    @property
    def diferenca(self) -> Decimal:
        return self.preco_mais_caro - self.preco_mais_barato

    @property
    def percentual(self) -> float:
        return float(100 * self.diferenca / self.preco_mais_barato) if self.preco_mais_barato else 0.0


def historico(sessao: Session, produto_id: int) -> list[Preco]:
    """Cada compra do produto, da mais antiga para a mais recente, com quantidade e total."""
    linhas = sessao.execute(
        select(Compra.id, Compra.data_emissao, Estabelecimento.nome, ItemCompra.unidade,
               func.sum(ItemCompra.quantidade), func.sum(ItemCompra.valor_total))
        .join(Compra, ItemCompra.compra_id == Compra.id)
        .join(Estabelecimento, Compra.estabelecimento_id == Estabelecimento.id)
        .where(ItemCompra.produto_id == produto_id)
        .group_by(Compra.id, Compra.data_emissao, Estabelecimento.nome, ItemCompra.unidade)
        .order_by(Compra.data_emissao)
    ).all()
    precos = []
    for _id, data, mercado, unidade, quantidade, total in linhas:
        quantidade, total = Decimal(str(quantidade)), Decimal(str(total))
        unitario = (total / quantidade).quantize(Decimal("0.01")) if quantidade else total
        precos.append(Preco(data, mercado, unitario, unidade, quantidade, total))
    return precos


def comparar_mercados(sessao: Session) -> list[Comparacao]:
    """Produtos comprados em 2+ mercados: preço médio pago em cada um, do maior gap ao menor.

    Compara preço UNITÁRIO (por unidade ou por kg), então só faz sentido dentro da mesma
    unidade — por isso agrupa por produto E unidade.
    """
    linhas = sessao.execute(
        select(Produto.id, Produto.nome, ItemCompra.unidade, Estabelecimento.nome,
               func.avg(ItemCompra.valor_unitario))
        .join(ItemCompra, ItemCompra.produto_id == Produto.id)
        .join(Compra, ItemCompra.compra_id == Compra.id)
        .join(Estabelecimento, Compra.estabelecimento_id == Estabelecimento.id)
        .group_by(Produto.id, Produto.nome, ItemCompra.unidade, Estabelecimento.nome)
    ).all()

    por_produto: dict[tuple, list[tuple[str, Decimal]]] = {}
    for produto_id, nome, unidade, mercado, media in linhas:
        por_produto.setdefault((produto_id, nome, unidade), []).append(
            (mercado, Decimal(str(media)).quantize(Decimal("0.01"))))

    comparacoes = []
    for (produto_id, nome, unidade), mercados in por_produto.items():
        if len(mercados) < 2:
            continue
        barato = min(mercados, key=lambda m: m[1])
        caro = max(mercados, key=lambda m: m[1])
        comparacoes.append(Comparacao(produto_id, nome, unidade, barato[0], barato[1],
                                      caro[0], caro[1]))
    return sorted(comparacoes, key=lambda c: -c.diferenca)


@dataclass
class Variacao:
    produto_id: int
    produto: str
    unidade: str
    data_antes: Optional[datetime]
    preco_antes: Decimal
    data_depois: Optional[datetime]
    preco_depois: Decimal

    @property
    def percentual(self) -> float:
        return float(100 * (self.preco_depois - self.preco_antes) / self.preco_antes)


def variacao_de_precos(sessao: Session) -> list[Variacao]:
    """Primeira x última compra de cada produto (mesma unidade), da maior alta à maior queda."""
    repetidos = sessao.execute(
        select(ItemCompra.produto_id)
        .where(ItemCompra.produto_id.is_not(None))
        .group_by(ItemCompra.produto_id)
        .having(func.count(func.distinct(ItemCompra.compra_id)) > 1)
    ).scalars().all()

    variacoes = []
    for produto_id in repetidos:
        precos = historico(sessao, produto_id)
        unidade = precos[-1].unidade
        mesmos = [p for p in precos if p.unidade == unidade]
        antes, depois = mesmos[0], mesmos[-1]
        if len(mesmos) < 2 or antes.valor_unitario == depois.valor_unitario or not antes.valor_unitario:
            continue
        nome = sessao.get(Produto, produto_id).nome
        variacoes.append(Variacao(produto_id, nome, unidade, antes.data, antes.valor_unitario,
                                  depois.data, depois.valor_unitario))
    return sorted(variacoes, key=lambda v: -abs(v.percentual))
