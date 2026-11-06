"""Orquestra: link/foto -> navegador (captcha) -> HTML -> NotaFiscal categorizada.

`nota_de_html` é o coração, usado tanto pelo terminal quanto pela API (o app envia o HTML).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from compras.nota.categorizar import ResultadoCategorias, categorizar_detalhado
from compras.nota.esquema import NotaFiscal
from compras.nota.prompt import PROMPT_LEITURA
from compras.sefaz.parser import LayoutDesconhecido, ler_html, texto_da_pagina
from compras.sefaz.qrcode import chave_do_link, ler_qrcode
from compras.visao.base import ProvedorVisao
from compras.visao.fabrica import obter_provedor

PASTA_HTML = Path("notas/sefaz")

PROMPT_TEXTO = PROMPT_LEITURA.replace(
    "Você recebe a foto de um cupom fiscal brasileiro (NFC-e) de supermercado.",
    "Você recebe o TEXTO da consulta pública de uma NFC-e na SEFAZ.",
) + "\nTexto da página:\n{texto}\n"


def _nada(_mensagem: str) -> None:
    pass


def obter_link(entrada: str) -> str:
    return entrada if entrada.startswith("http") else ler_qrcode(entrada)


def arquivar_html(html: str, chave: Optional[str]) -> Path:
    """Guarda a página da SEFAZ: é o "original" da nota, reimportável sem captcha."""
    PASTA_HTML.mkdir(parents=True, exist_ok=True)
    arquivo = PASTA_HTML / f"{chave or 'nota'}.html"
    arquivo.write_text(html, encoding="utf-8")
    return arquivo


def nota_de_html(html: str, chave: Optional[str], modelo: Optional[ProvedorVisao],
                 avisar: Callable[[str], None] = _nada
                 ) -> tuple[NotaFiscal, ResultadoCategorias]:
    try:
        nota = ler_html(html, chave)
    except LayoutDesconhecido as erro:
        if modelo is None:
            raise
        avisar(f"Layout da página diferente do esperado ({erro}); extraindo pelo modelo...")
        from compras.nota.leitor import _extrair_json
        resposta = modelo.analisar_texto(PROMPT_TEXTO.replace("{texto}", texto_da_pagina(html)))
        nota = NotaFiscal.model_validate(_extrair_json(resposta))
        if chave and not nota.chave_acesso:
            nota.chave_acesso = chave

    avisar("Classificando os produtos por categoria...")
    categorias = categorizar_detalhado(nota.itens, modelo)
    avisar(categorias.resumo())
    return nota.model_copy(update={"itens": categorias.itens}), categorias


def importar_da_sefaz(entrada: str, provedor: Optional[str] = None,
                      avisar: Callable[[str], None] = print,
                      usar_modelo: bool = True) -> tuple[NotaFiscal, Path]:
    """Usado pelo terminal: aceita foto do QR, link do QR ou página .html já salva."""
    if entrada.lower().endswith((".html", ".htm")):
        arquivo = Path(entrada)
        html = arquivo.read_text(encoding="utf-8")
        chave = chave_do_link(arquivo.stem)
        avisar(f"Lendo a página já salva {arquivo.name} (sem acessar a SEFAZ)...")
    else:
        from compras.sefaz.navegador import baixar_html_da_nota

        link = obter_link(entrada)
        chave = chave_do_link(link)
        avisar("Abrindo a SEFAZ no navegador. Resolva o captcha na janela que abriu...")
        html = baixar_html_da_nota(link)
        arquivo = arquivar_html(html, chave)

    modelo = obter_provedor(provedor) if usar_modelo else None
    try:
        nota, _ = nota_de_html(html, chave, modelo, avisar)
    except LayoutDesconhecido as erro:
        raise LayoutDesconhecido(
            f"{erro}. Página salva em {arquivo}; rode sem --sem-modelo para usar o plano B."
        ) from erro
    return nota, arquivo
