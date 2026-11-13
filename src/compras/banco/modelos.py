"""Tabelas do banco: estabelecimentos, compras, itens, produtos, estoque, casa e essenciais."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Table, func
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


class MovimentoEstoque(Base):
    """Entrada (compra) ou saída (consumo, acabou) de um produto. Saldo = soma das quantidades."""
    __tablename__ = "movimentos_estoque"

    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), index=True)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3))  # positiva entra, negativa sai
    unidade: Mapped[str] = mapped_column(String(10), default="UN")
    tipo: Mapped[str] = mapped_column(String(20))  # compra | manual | consumo | acabou | ajuste
    compra_id: Mapped[Optional[int]] = mapped_column(ForeignKey("compras.id", ondelete="CASCADE"))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    produto: Mapped[Produto] = relationship()


class Casa(Base):
    """Quem mora na casa (só o essencial para estimar consumo). Uma linha só."""
    __tablename__ = "casa"

    id: Mapped[int] = mapped_column(primary_key=True)
    adultos: Mapped[int] = mapped_column(Integer, default=1)
    criancas: Mapped[int] = mapped_column(Integer, default=0)
    pets: Mapped[int] = mapped_column(Integer, default=0)
    padroes_criados: Mapped[bool] = mapped_column(Boolean, default=False)  # sugestões já criadas
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now(),
                                                    onupdate=func.now())


essencial_produtos = Table(
    "essencial_produtos", Base.metadata,
    Column("essencial_id", ForeignKey("essenciais.id", ondelete="CASCADE"), primary_key=True),
    Column("produto_id", ForeignKey("produtos.id", ondelete="CASCADE"), primary_key=True),
)


class Essencial(Base):
    """Tipo de produto que não pode faltar (ex.: Arroz), agrupando marcas e tamanhos.

    Conta para ele: os produtos que o usuário escolheu (essencial_produtos) e qualquer
    produto cujo nome tenha as palavras de `palavras` (grupos separados por vírgula; dentro
    de um grupo, todas as palavras precisam aparecer).
    """
    __tablename__ = "essenciais"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    palavras: Mapped[str] = mapped_column(String(200))  # "ARROZ" -> casa no nome do produto
    excluir: Mapped[str] = mapped_column(String(200), default="")  # "CREME,CONDENSADO"
    unidade: Mapped[str] = mapped_column(String(5))  # kg | L | un
    consumo_pessoa_mes: Mapped[Decimal] = mapped_column(Numeric(10, 3))  # na unidade acima
    ativo: Mapped[bool] = mapped_column(Boolean, default=False)  # o usuário escolhe
    quantidade_pacote: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))  # "1 pacote"

    produtos: Mapped[list[Produto]] = relationship(secondary=essencial_produtos)
