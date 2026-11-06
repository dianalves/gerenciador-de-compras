"""Consultas prontas: gasto por mês, por categoria e produtos mais caros."""
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from compras.banco.modelos import Compra, ItemCompra


def gasto_por_mes(sessao: Session):
    ano = extract("year", Compra.data_emissao).label("ano")
    mes = extract("month", Compra.data_emissao).label("mes")
    return sessao.execute(
        select(ano, mes, func.sum(Compra.valor_total).label("total"))
        .group_by(ano, mes).order_by(ano, mes)
    ).all()


def gasto_por_categoria(sessao: Session, ano: int, mes: int):
    return sessao.execute(
        select(ItemCompra.categoria, func.sum(ItemCompra.valor_total).label("total"))
        .join(Compra)
        .where(extract("year", Compra.data_emissao) == ano,
               extract("month", Compra.data_emissao) == mes)
        .group_by(ItemCompra.categoria)
        .order_by(func.sum(ItemCompra.valor_total).desc())
    ).all()


def produtos_que_mais_gasto(sessao: Session, limite: int = 10):
    return sessao.execute(
        select(ItemCompra.descricao, ItemCompra.unidade,
               func.sum(ItemCompra.quantidade).label("quantidade"),
               func.sum(ItemCompra.valor_total).label("total"))
        .group_by(ItemCompra.descricao, ItemCompra.unidade)
        .order_by(func.sum(ItemCompra.valor_total).desc())
        .limit(limite)
    ).all()
