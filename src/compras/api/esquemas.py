"""Formatos de entrada e saída da API (aparecem documentados em /docs)."""
from datetime import date, datetime
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


class ItemEstoqueSaida(BaseModel):
    produto_id: int
    nome: str
    categoria: str
    unidade: str
    quantidade: Decimal
    ultima_entrada: Optional[datetime] = None


class EntradaQuantidade(BaseModel):
    quantidade: Decimal = Field(..., description="Quantidade (un ou kg)")


class MensagemConversa(BaseModel):
    papel: str = Field(..., description="usuario | assistente")
    texto: str


class EntradaPergunta(BaseModel):
    pergunta: str = Field(..., min_length=2, max_length=500)
    historico: List[MensagemConversa] = Field(default_factory=list,
                                              description="Conversa anterior (opcional)")


class FerramentaUsada(BaseModel):
    nome: str
    argumentos: dict


class RespostaPergunta(BaseModel):
    resposta: str
    ferramentas: List[FerramentaUsada]


class CasaSaida(BaseModel):
    adultos: int
    criancas: int
    pets: int


class CasaEntrada(BaseModel):
    adultos: int = Field(..., ge=1, le=20)
    criancas: int = Field(0, ge=0, le=20)
    pets: int = Field(0, ge=0, le=20)


class ProdutoResumo(BaseModel):
    id: int
    nome: str


class EssencialSaida(BaseModel):
    id: int
    nome: str
    unidade: str
    consumo_pessoa_mes: Decimal
    ativo: bool
    quantidade_pacote: Optional[Decimal] = None
    dura_pacote_dias: Optional[float] = None  # "1 pacote dura ~N dias nesta casa"
    produtos: List[ProdutoResumo] = []


class EssencialNovo(BaseModel):
    nome: str = Field(..., min_length=1, max_length=60)
    produto_ids: List[int] = Field(default_factory=list,
                                   description="Produtos já comprados que contam para ele")
    duracao_dias: int = Field(..., ge=1, le=365, description="Quanto essa quantidade dura")
    quantidade: Optional[Decimal] = Field(None, gt=0, description="Quanto costuma comprar")
    unidade: Optional[str] = Field(None, description="UN, KG ou L")


class EssencialEntrada(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=60)
    ativo: Optional[bool] = None
    duracao_dias: Optional[int] = Field(None, ge=1, le=365)
    produto_ids: Optional[List[int]] = None
    consumo_pessoa_mes: Optional[Decimal] = Field(None, gt=0)
    quantidade: Optional[Decimal] = Field(None, gt=0)
    unidade: Optional[str] = None


class PrevisaoSaida(BaseModel):
    essencial_id: int
    nome: str
    unidade: str
    estoque: Decimal
    consumo_diario: Decimal
    dias_restantes: Optional[float] = None
    acaba_em: Optional[date] = None
    situacao: str
    produtos: List[str]
    sem_tamanho: List[str]
    fonte: str
    registrado: Decimal
    desde: Optional[date] = None


class PreviaEssencialSaida(BaseModel):
    nome: str
    encontrados: int
    unidade: str
    quantidade_pacote: Decimal
    em_estoque: Decimal


class EntradaManual(BaseModel):
    nome: str = Field("", max_length=120, description="Nome do item (se não escolher produto)")
    produto_id: Optional[int] = Field(None, description="Produto já comprado (opcional)")
    quantidade: Decimal = Field(..., gt=0)
    unidade: str = Field("UN", description="UN, KG ou L")
