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
    data: Optional[datetime]
    mercado: str
    valor_unitario: Decimal
    unidade: str
    quantidade: Decimal


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
    """Cada compra do produto, da mais antiga para a mais recente."""
    linhas = sessao.execute(
        select(Compra.data_emissao, Estabelecimento.nome, ItemCompra.valor_unitario,
               ItemCompra.unidade, ItemCompra.quantidade)
        .join(Compra, ItemCompra.compra_id == Compra.id)
        .join(Estabelecimento, Compra.estabelecimento_id == Estabelecimento.id)
        .where(ItemCompra.produto_id == produto_id)
        .order_by(Compra.data_emissao)
    ).all()
    return [Preco(*linha) for linha in linhas]


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
