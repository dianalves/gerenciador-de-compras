"""Regras do estoque. Nada é apagado: cada mudança vira um movimento (dá para auditar)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from compras.banco.modelos import Compra, ItemCompra, MovimentoEstoque, Produto

ZERO = Decimal("0")


@dataclass
class ItemEstoque:
    produto_id: int
    nome: str
    categoria: str
    unidade: str
    quantidade: Decimal
    ultima_entrada: Optional[datetime]


class ProdutoForaDoEstoque(ValueError):
    pass


def registrar_compra(sessao: Session, compra: Compra) -> None:
    """Cada item comprado entra no estoque (chamado ao salvar a nota)."""
    for item in compra.itens:
        if item.produto is None:
            continue
        sessao.add(MovimentoEstoque(produto=item.produto, quantidade=item.quantidade,
                                    unidade=item.unidade, tipo="compra", compra_id=compra.id))


def iniciar(sessao: Session) -> int:
    """Estoque inicial = itens da compra mais recente. Só roda com o estoque vazio."""
    if sessao.scalar(select(func.count()).select_from(MovimentoEstoque)):
        return 0
    compra = sessao.scalar(select(Compra).order_by(Compra.data_emissao.desc()).limit(1))
    if compra is None:
        return 0
    registrar_compra(sessao, compra)
    sessao.commit()
    return len(compra.itens)


def _consulta_saldos():
    return (
        select(MovimentoEstoque.produto_id, Produto.nome, Produto.categoria,
               MovimentoEstoque.unidade, func.sum(MovimentoEstoque.quantidade),
               func.max(MovimentoEstoque.criado_em).filter(MovimentoEstoque.tipo == "compra"))
        .join(Produto, MovimentoEstoque.produto_id == Produto.id)
        .group_by(MovimentoEstoque.produto_id, Produto.nome, Produto.categoria,
                  MovimentoEstoque.unidade)
    )


def _item(linha) -> ItemEstoque:
    produto_id, nome, categoria, unidade, total, ultima = linha
    return ItemEstoque(produto_id, nome, categoria, unidade, Decimal(str(total or 0)), ultima)


def saldo(sessao: Session) -> list[ItemEstoque]:
    """O que tem em casa agora (só quantidades positivas), por categoria e nome."""
    itens = [_item(l) for l in sessao.execute(_consulta_saldos()).all()]
    return sorted((i for i in itens if i.quantidade > ZERO), key=lambda i: (i.categoria, i.nome))


def saldo_do_produto(sessao: Session, produto_id: int) -> ItemEstoque:
    linha = sessao.execute(
        _consulta_saldos().where(MovimentoEstoque.produto_id == produto_id)).first()
    if linha is None:
        raise ProdutoForaDoEstoque("Esse produto não está no estoque")
    return _item(linha)


def _movimentar(sessao: Session, produto_id: int, delta: Decimal, tipo: str) -> ItemEstoque:
    atual = saldo_do_produto(sessao, produto_id)
    delta = max(delta, -atual.quantidade)  # nunca deixa o estoque negativo
    if delta != ZERO:
        sessao.add(MovimentoEstoque(produto_id=produto_id, quantidade=delta,
                                    unidade=atual.unidade, tipo=tipo))
        sessao.commit()
    return saldo_do_produto(sessao, produto_id)


def consumir(sessao: Session, produto_id: int, quantidade: Decimal = Decimal("1")) -> ItemEstoque:
    if quantidade <= ZERO:
        raise ValueError("A quantidade consumida tem que ser maior que zero")
    return _movimentar(sessao, produto_id, -quantidade, "consumo")


def acabou(sessao: Session, produto_id: int) -> ItemEstoque:
    atual = saldo_do_produto(sessao, produto_id)
    return _movimentar(sessao, produto_id, -atual.quantidade, "acabou")


def ajustar(sessao: Session, produto_id: int, nova_quantidade: Decimal) -> ItemEstoque:
    """Corrige o saldo para um valor contado na mão."""
    if nova_quantidade < ZERO:
        raise ValueError("A quantidade não pode ser negativa")
    atual = saldo_do_produto(sessao, produto_id)
    return _movimentar(sessao, produto_id, nova_quantidade - atual.quantidade, "ajuste")
