"""Esquema (Pydantic) do que o modelo de visão deve extrair de uma NFC-e."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

import difflib

from pydantic import BaseModel, Field, PrivateAttr, field_validator

CATEGORIAS = [
    "hortifruti", "carnes", "frios_laticinios", "padaria", "mercearia",
    "bebidas", "limpeza", "higiene", "pet", "congelados", "outros",
]


class ItemNota(BaseModel):
    numero_item: Optional[int] = Field(None, description="Número sequencial da linha no cupom (coluna #)")
    codigo: Optional[str] = Field(None, description="Código do produto, SEM o número do item")
    descricao: str = Field(..., description="Descrição do item como aparece na nota")
    quantidade: Decimal = Field(..., description="Quantidade comprada")
    unidade: str = Field("UN", description="UN, KG, L, etc.")
    valor_unitario: Decimal
    valor_total: Decimal
    categoria: str = Field("outros", description=f"Uma de: {', '.join(CATEGORIAS)}")

    @field_validator("categoria", mode="before")
    @classmethod
    def _normalizar_categoria(cls, valor):
        valor = str(valor or "outros").strip().lower().replace(" ", "_")
        if valor in CATEGORIAS:
            return valor
        parecida = difflib.get_close_matches(valor, CATEGORIAS, n=1, cutoff=0.6)
        return parecida[0] if parecida else "outros"

    def confere(self, tolerancia: Decimal = Decimal("0.02")) -> bool:
        """quantidade x valor_unitario deve dar valor_total."""
        return abs(self.quantidade * self.valor_unitario - self.valor_total) <= tolerancia


class NotaFiscal(BaseModel):
    estabelecimento_nome: str
    estabelecimento_cnpj: Optional[str] = None
    data_emissao: Optional[datetime] = None
    chave_acesso: Optional[str] = Field(None, description="44 dígitos, sem espaços")
    valor_total: Decimal = Field(..., description="Valor final pago (VALOR A PAGAR / VALOR TOTAL)")
    desconto: Decimal = Field(
        Decimal("0"),
        description="Só se houver uma linha DESCONTO que reduz o total; senão 0")
    economia: Optional[Decimal] = Field(
        None,
        description='Valor informativo de economia ("você economizou"); NÃO entra na conta')
    forma_pagamento: Optional[str] = None
    quantidade_itens: Optional[int] = Field(
        None, description='Total de itens impresso no rodapé ("QTD. TOTAL DE ITENS")')
    itens: list[ItemNota]

    # Itens em que leituras diferentes discordaram (preenchido pelo leitor, não vai no JSON)
    _duvidas: list = PrivateAttr(default_factory=list)

    @property
    def duvidas(self) -> list:
        return self._duvidas

    def soma_itens(self) -> Decimal:
        return sum((i.valor_total for i in self.itens), Decimal("0"))

    def diferenca(self) -> Decimal:
        """Quanto a soma dos itens (menos desconto) passa do total da nota."""
        return self.soma_itens() - self.desconto - self.valor_total

    def itens_inconsistentes(self) -> list[ItemNota]:
        return [i for i in self.itens if not i.confere()]

    def itens_faltando(self) -> list[int]:
        """Números de item que pularam na sequência (ex.: leu 1,2,4 -> falta 3)."""
        numeros = {i.numero_item for i in self.itens if i.numero_item}
        if not numeros:
            return []
        ultimo = max(max(numeros), self.quantidade_itens or 0)
        return [n for n in range(1, ultimo + 1) if n not in numeros]

    def confere_total(self, tolerancia: Decimal = Decimal("0.05")) -> bool:
        """Checa se a soma dos itens menos desconto bate com o total da nota."""
        return abs(self.soma_itens() - self.desconto - self.valor_total) <= tolerancia
