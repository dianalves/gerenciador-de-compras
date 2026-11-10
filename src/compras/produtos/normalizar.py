"""Transforma a descrição do cupom numa forma padrão (regras, sem IA).

"REFR.COCA COLA 2L" e "REFRI.COCA COLA 2LT" -> chave "REFRIGERANTE COCA COLA|2000ml"
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

# Trechos trocados ANTES de separar as palavras (envolvem ponto ou mais de uma palavra).
EXPRESSOES = {
    "C.LEITE": "CREME DE LEITE",
    "CR.LEITE": "CREME DE LEITE",
    "CR LEITE": "CREME DE LEITE",
    "LEITE COND.": "LEITE CONDENSADO ",
    "SOBRE COXA": "SOBRECOXA",
}

# Abreviações comuns nos cupons, palavra por palavra.
ABREVIACOES = {
    "REFR": "REFRIGERANTE", "REFRI": "REFRIGERANTE", "REFRIG": "REFRIGERANTE",
    "BISC": "BISCOITO", "CHOC": "CHOCOLATE", "SABO": "SABONETE", "SAB": "SABONETE",
    "BEB": "BEBIDA", "CAPS": "CAPSULA", "MIST": "MISTURA", "COND": "CONDENSADO",
    "CONDENS": "CONDENSADO", "ENERG": "ENERGETICO", "SALG": "SALGADINHO",
    "DESOSS": "DESOSSADA", "DESOSSAD": "DESOSSADA", "MUSS": "MUSSARELA",
    "PARM": "PARMESAO", "QJO": "QUEIJO", "LTE": "LEITE", "AZEIT": "AZEITONA",
    "MIGN": "MIGNON", "SUINA": "SUINO", "REFINAD": "REFINADO",
    "ESC": "ESCOVA", "ESP": "ESPONJA", "NAT": "NATURAL",
}

# Palavras que não ajudam a identificar o produto (prefixos de seção, unidades soltas...).
IGNORAR = {
    "DE", "DA", "DO", "DOS", "DAS", "E", "COM", "C", "P", "KG", "KGS", "UN", "UND", "UNID",
    "UNIDADE", "GRANEL", "FLV", "AC", "FR", "BAND", "BND", "PCT", "PC", "CX",
}

_UNIDADES = {
    "KG": ("g", 1000), "KGS": ("g", 1000), "G": ("g", 1), "GR": ("g", 1), "GRS": ("g", 1),
    "L": ("ml", 1000), "LT": ("ml", 1000), "LTS": ("ml", 1000), "LITRO": ("ml", 1000),
    "LITROS": ("ml", 1000), "ML": ("ml", 1), "M": ("ml", 1),  # "250M": ML cortado no cupom
}
_TAMANHO = re.compile(r"(?<!\d)(?<!\d[.,])(\d+(?:[.,]\d+)?)\s*(" + "|".join(
    sorted(_UNIDADES, key=len, reverse=True)) + r")(?![A-Z])")


@dataclass(frozen=True)
class DescricaoNormalizada:
    palavras: tuple[str, ...]
    tamanho: Optional[Decimal] = None  # em g ou ml
    unidade: Optional[str] = None  # "g" | "ml"

    @property
    def chave(self) -> str:
        base = " ".join(self.palavras)
        return f"{base}|{self.tamanho.normalize():f}{self.unidade}" if self.tamanho else base

    @property
    def nome(self) -> str:
        return " ".join(self.palavras) + (f" {formatar_tamanho(self.tamanho, self.unidade)}"
                                          if self.tamanho else "")


def formatar_tamanho(tamanho: Decimal, unidade: Optional[str]) -> str:
    if unidade == "g" and tamanho >= 1000:
        valor, sigla = tamanho / 1000, "kg"
    elif unidade == "ml" and tamanho >= 1000:
        valor, sigla = tamanho / 1000, "L"
    else:
        valor, sigla = tamanho, unidade or ""
    texto = f"{valor.normalize():f}".replace(".", ",")
    return f"{texto} {sigla}".strip()


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.upper())
                   if unicodedata.category(c) != "Mn")


def normalizar(descricao: str) -> DescricaoNormalizada:
    texto = sem_acento(descricao).strip()
    for de, para in EXPRESSOES.items():
        texto = texto.replace(de, para)

    tamanho = unidade = None
    achado = _TAMANHO.search(texto)
    if achado:
        numero = Decimal(achado.group(1).replace(",", "."))
        unidade, fator = _UNIDADES[achado.group(2)]
        tamanho = numero * fator
        texto = texto[:achado.start()] + " " + texto[achado.end():]

    palavras: list[str] = []
    for palavra in re.split(r"[^A-Z0-9]+", texto):
        palavra = ABREVIACOES.get(palavra, palavra)
        for parte in palavra.split():  # abreviação pode virar mais de uma palavra
            if len(parte) > 1 and parte not in IGNORAR and parte not in palavras:
                palavras.append(parte)
    return DescricaoNormalizada(tuple(palavras), tamanho, unidade)


def parecidos(a: DescricaoNormalizada, b: DescricaoNormalizada) -> float:
    """0 a 1: quão parecidos são dois produtos (para SUGERIR junções, nunca juntar sozinho)."""
    from difflib import SequenceMatcher

    if a.tamanho and b.tamanho and a.tamanho != b.tamanho:
        return 0.0  # tamanhos diferentes = produtos diferentes (2 L x 600 ml)
    if not a.palavras or not b.palavras:
        return 0.0
    if a.palavras == b.palavras:
        return 0.95  # mesmas palavras, só um dos dois sem tamanho ("ENERGETICO MONSTER 4")
    if (len(a.palavras) == len(b.palavras) and a.palavras[:-1] == b.palavras[:-1]
            and (a.palavras[-1].startswith(b.palavras[-1])
                 or b.palavras[-1].startswith(a.palavras[-1]))):
        return 0.9  # última palavra cortada pelo caixa ("SURPRES" x "SURPRESA")
    return SequenceMatcher(None, " ".join(a.palavras), " ".join(b.palavras)).ratio()
