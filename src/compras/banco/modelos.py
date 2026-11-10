"""Tabelas do banco: estabelecimentos, compras, itens e produtos."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Estabelecimento(Base):
    __tablename__ = "estabelecimentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    cnpj: Mapped[Optional[str]] = mapped_column(String(14), unique=True)

    compras: Mapped[list["Compra"]] = relationship(back_populates="estabelecimento")


class Compra(Base):
    __tablename__ = "compras"

    id: Mapped[int] = mapped_column(primary_key=True)
    estabelecimento_id: Mapped[int] = mapped_column(ForeignKey("estabelecimentos.id"))
    chave_acesso: Mapped[Optional[str]] = mapped_column(String(44), unique=True)
    data_emissao: Mapped[Optional[datetime]]
    valor_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    desconto: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    economia: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    forma_pagamento: Mapped[Optional[str]] = mapped_column(String(50))
    origem: Mapped[str] = mapped_column(String(20), default="foto")  # foto | sefaz
    provedor_visao: Mapped[Optional[str]] = mapped_column(String(20))
    imagem: Mapped[Optional[str]] = mapped_column(String(500))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    estabelecimento: Mapped[Estabelecimento] = relationship(back_populates="compras")
    itens: Mapped[list["ItemCompra"]] = relationship(
        back_populates="compra", cascade="all, delete-orphan"
    )


class ItemCompra(Base):
    __tablename__ = "itens_compra"

    id: Mapped[int] = mapped_column(primary_key=True)
    compra_id: Mapped[int] = mapped_column(ForeignKey("compras.id"))
    codigo: Mapped[Optional[str]] = mapped_column(String(50))
    descricao: Mapped[str] = mapped_column(String(300))
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unidade: Mapped[str] = mapped_column(String(10), default="UN")
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    categoria: Mapped[str] = mapped_column(String(30), default="outros")
    produto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("produtos.id"), index=True)

    compra: Mapped[Compra] = relationship(back_populates="itens")
    produto: Mapped[Optional["Produto"]] = relationship(back_populates="itens")


class Produto(Base):
    """O produto "de verdade", independente de como cada mercado escreve no cupom."""
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))  # ex.: REFRIGERANTE COCA COLA 2 L
    chave: Mapped[str] = mapped_column(String(200), unique=True)  # forma normalizada
    categoria: Mapped[str] = mapped_column(String(30), default="mercearia")
    tamanho: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))  # em g, ml ou un
    unidade_tamanho: Mapped[Optional[str]] = mapped_column(String(5))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    apelidos: Mapped[list["ApelidoProduto"]] = relationship(
        back_populates="produto", cascade="all, delete-orphan")
    itens: Mapped[list[ItemCompra]] = relationship(back_populates="produto")


class ApelidoProduto(Base):
    """Cada forma como o produto já apareceu num cupom (ex.: REFR.COCA COLA 2L)."""
    __tablename__ = "apelidos_produto"

    id: Mapped[int] = mapped_column(primary_key=True)
    descricao: Mapped[str] = mapped_column(String(300), unique=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), index=True)

    produto: Mapped[Produto] = relationship(back_populates="apelidos")
