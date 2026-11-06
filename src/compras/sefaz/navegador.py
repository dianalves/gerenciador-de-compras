"""Abre a consulta da SEFAZ num navegador de verdade para o usuário resolver o captcha."""
from __future__ import annotations

# A página de resultado tem os itens (classe txtTit) ou o texto "Valor a pagar".
_NOTA_CARREGADA = """() => !!document.querySelector('.txtTit')
    || /valor a pagar/i.test(document.body ? document.body.innerText : '')"""


def baixar_html_da_nota(link: str, tempo_limite_s: int = 300) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            navegador = p.chromium.launch(channel="chrome", headless=False)  # Chrome instalado
        except Exception:
            navegador = p.chromium.launch(headless=False)  # Chromium do Playwright
        pagina = navegador.new_page()
        pagina.goto(link)
        pagina.wait_for_function(_NOTA_CARREGADA, timeout=tempo_limite_s * 1000)
        pagina.wait_for_timeout(1000)  # dá tempo de terminar de desenhar
        html = pagina.content()
        navegador.close()
    return html
