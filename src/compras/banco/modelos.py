"""Tabelas do banco: estabelecimentos, compras e itens."""
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

    compra: Mapped[Compra] = relationship(back_populates="itens")
