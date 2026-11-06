"""Extrai a NotaFiscal do HTML da consulta pública da NFC-e.

O layout (classes txtTit, Rqtd, RUN, RvlUnit, valor, RCod, totalNumb) é o mais comum
nos portais estaduais. Se algo não bater, `importar_html` usa o modelo sobre o TEXTO
da página como plano B.
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from bs4 import BeautifulSoup

from compras.nota.esquema import ItemNota, NotaFiscal


class LayoutDesconhecido(Exception):
    pass


def numero_br(texto: str) -> Decimal:
    """'1.234,56' -> Decimal('1234.56'); aceita lixo em volta ('Vl. Unit.: 3,59')."""
    achado = re.search(r"\d[\d.]*(?:,\d+)?", texto or "")
    if not achado:
        raise LayoutDesconhecido(f"Número não encontrado em {texto!r}")
    try:
        return Decimal(achado.group(0).replace(".", "").replace(",", "."))
    except InvalidOperation as erro:
        raise LayoutDesconhecido(str(erro)) from erro


def _texto(no, seletor: str) -> str:
    achado = no.select_one(seletor)
    return achado.get_text(" ", strip=True) if achado else ""


def _total(soup: BeautifulSoup, rotulo: str) -> Optional[Decimal]:
    """Procura no rodapé linhas tipo 'Valor a pagar R$: 580,00'."""
    for linha in soup.select("#totalNota div, #totalNota tr, .linhaTotal, .linhaShade"):
        texto = linha.get_text(" ", strip=True)
        if re.search(rotulo, texto, re.I):
            valor = linha.select_one(".totalNumb")
            return numero_br(valor.get_text() if valor else texto.split(":")[-1])
    texto = soup.get_text(" ", strip=True)
    achado = re.search(rotulo + r"[^\d]{0,20}(\d[\d.]*,\d{2})", texto, re.I)
    return numero_br(achado.group(1)) if achado else None


def ler_html(html: str, chave: Optional[str] = None) -> NotaFiscal:
    soup = BeautifulSoup(html, "html.parser")

    itens = []
    # a célula "Vl. Total" também usa a classe txtTit; o nome do produto é o <span>
    for n, titulo in enumerate(soup.select("span.txtTit"), start=1):
        linha = titulo.find_parent("tr") or titulo.parent
        codigo = re.search(r"\d+", _texto(linha, ".RCod"))
        itens.append(ItemNota(
            numero_item=n,
            codigo=codigo.group(0) if codigo else None,
            descricao=titulo.get_text(" ", strip=True),
            quantidade=numero_br(_texto(linha, ".Rqtd")),
            unidade=(_texto(linha, ".RUN").split(":")[-1].strip() or "UN").upper(),
            valor_unitario=numero_br(_texto(linha, ".RvlUnit")),
            valor_total=numero_br(_texto(linha, ".valor")),
        ))
    if not itens:
        raise LayoutDesconhecido("Nenhum item (span.txtTit) encontrado na página")

    texto = soup.get_text(" ", strip=True)
    nome = _texto(soup, "#u20") or _texto(soup, ".txtTopo") or "Desconhecido"
    cnpj = re.search(r"CNPJ:?\s*([\d./-]{14,18})", texto)
    emissao = re.search(r"Emiss[ãa]o:?\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)", texto)
    if not chave:
        chave_html = re.sub(r"\D", "", _texto(soup, ".chave"))
        chave = chave_html if len(chave_html) == 44 else None

    valor_pagar = _total(soup, r"valor a pagar")
    if valor_pagar is None:
        raise LayoutDesconhecido("Total da nota não encontrado")

    data = None
    if emissao:
        formato = "%d/%m/%Y %H:%M:%S" if emissao.group(1).count(":") == 2 else "%d/%m/%Y %H:%M"
        data = datetime.strptime(re.sub(r"\s+", " ", emissao.group(1)), formato)

    return NotaFiscal(
        estabelecimento_nome=nome,
        estabelecimento_cnpj=re.sub(r"\D", "", cnpj.group(1)) if cnpj else None,
        data_emissao=data,
        chave_acesso=chave,
        valor_total=valor_pagar,
        desconto=_total(soup, r"descontos?") or Decimal("0"),
        quantidade_itens=len(itens),
        itens=itens,
    )


def texto_da_pagina(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for lixo in soup(["script", "style", "noscript"]):
        lixo.decompose()
    return re.sub(r"\n\s*\n+", "\n", soup.get_text("\n", strip=True))
