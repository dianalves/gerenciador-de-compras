"""Orquestra: link/foto -> navegador (captcha) -> HTML -> NotaFiscal categorizada."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from compras.nota.categorizar import categorizar_detalhado
from compras.nota.esquema import NotaFiscal
from compras.nota.prompt import PROMPT_LEITURA
from compras.sefaz.navegador import baixar_html_da_nota
from compras.sefaz.parser import LayoutDesconhecido, ler_html, texto_da_pagina
from compras.sefaz.qrcode import chave_do_link, ler_qrcode
from compras.visao.fabrica import obter_provedor

PASTA_HTML = Path("notas/sefaz")

PROMPT_TEXTO = PROMPT_LEITURA.replace(
    "Você recebe a foto de um cupom fiscal brasileiro (NFC-e) de supermercado.",
    "Você recebe o TEXTO da consulta pública de uma NFC-e na SEFAZ.",
) + "\nTexto da página:\n{texto}\n"


def obter_link(entrada: str) -> str:
    return entrada if entrada.startswith("http") else ler_qrcode(entrada)


def importar_da_sefaz(entrada: str, provedor: Optional[str] = None,
                      avisar: Callable[[str], None] = print,
                      usar_modelo: bool = True) -> tuple[NotaFiscal, Path]:
    if entrada.lower().endswith((".html", ".htm")):
        # Página já baixada antes: não precisa abrir a SEFAZ nem resolver captcha.
        arquivo = Path(entrada)
        html = arquivo.read_text(encoding="utf-8")
        chave = chave_do_link(arquivo.stem)
        avisar(f"Lendo a página já salva {arquivo.name} (sem acessar a SEFAZ)...")
    else:
        link = obter_link(entrada)
        chave = chave_do_link(link)

        avisar("Abrindo a SEFAZ no navegador. Resolva o captcha na janela que abriu...")
        html = baixar_html_da_nota(link)

        PASTA_HTML.mkdir(parents=True, exist_ok=True)
        arquivo = PASTA_HTML / f"{chave or 'nota'}.html"
        arquivo.write_text(html, encoding="utf-8")  # guarda a página para conferência

    modelo = obter_provedor(provedor) if usar_modelo else None
    try:
        nota = ler_html(html, chave)
    except LayoutDesconhecido as erro:
        if modelo is None:
            raise LayoutDesconhecido(
                f"{erro}. Página salva em {arquivo}; rode sem --sem-modelo para usar o plano B."
            ) from erro
        avisar(f"Layout da página diferente do esperado ({erro}); extraindo pelo modelo...")
        from compras.nota.leitor import _extrair_json
        resposta = modelo.analisar_texto(PROMPT_TEXTO.replace("{texto}", texto_da_pagina(html)))
        nota = NotaFiscal.model_validate(_extrair_json(resposta))
        if chave and not nota.chave_acesso:
            nota.chave_acesso = chave

    avisar("Classificando os produtos por categoria"
           + ("..." if modelo else " (palavras-chave)..."))
    categorias = categorizar_detalhado(nota.itens, modelo)
    avisar(categorias.resumo())
    nota = nota.model_copy(update={"itens": categorias.itens})
    return nota, arquivo
