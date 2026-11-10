"""Formatos de entrada e saída da API (aparecem documentados em /docs)."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from compras.nota.esquema import NotaFiscal


class EntradaSefaz(BaseModel):
    html: str = Field(..., description="HTML da página de resultado da consulta na SEFAZ")
    link: Optional[str] = Field(None, description="Link do QR code (de onde sai a chave)")


class Duvida(BaseModel):
    numero_item: int
    descricao: str
    leitura_inteira: Optional[Decimal] = None
    leitura_zoom: Decimal


class ResultadoImportacao(BaseModel):
    salva: bool
    compra_id: Optional[int] = None
    mensagem: str
    confere_total: bool
    diferenca: Decimal
    categorias: Optional[str] = None
    duvidas: List[Duvida] = []
    nota: NotaFiscal


class ItemSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: Optional[str] = None
    descricao: str
    quantidade: Decimal
    unidade: str
    valor_unitario: Decimal
    valor_total: Decimal
    categoria: str


class CompraResumo(BaseModel):
    id: int
    estabelecimento: str
    data_emissao: Optional[datetime] = None
    valor_total: Decimal
    quantidade_itens: int
    origem: str


class CompraDetalhe(CompraResumo):
    chave_acesso: Optional[str] = None
    desconto: Decimal
    economia: Optional[Decimal] = None
    itens: List[ItemSaida]


class GastoMensal(BaseModel):
    ano: int
    mes: int
    total: Decimal


class GastoCategoria(BaseModel):
    categoria: str
    total: Decimal
    percentual: float


class GastoProduto(BaseModel):
    descricao: str
    unidade: str
    quantidade: Decimal
    total: Decimal


class ProdutoSaida(BaseModel):
    id: int
    nome: str
    categoria: str
    descricoes: List[str]
    compras: int


class PrecoSaida(BaseModel):
    data: Optional[datetime] = None
    mercado: str
    valor_unitario: Decimal
    unidade: str
    quantidade: Decimal
    valor_total: Decimal


class ComparacaoSaida(BaseModel):
    produto_id: int
    produto: str
    unidade: str
    mais_barato: str
    preco_mais_barato: Decimal
    mais_caro: str
    preco_mais_caro: Decimal
    diferenca: Decimal
    percentual: float
