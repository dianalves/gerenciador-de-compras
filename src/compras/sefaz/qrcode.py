"""Encontra o link da SEFAZ no QR code de uma foto de cupom."""
from __future__ import annotations

import re
from pathlib import Path


class QRCodeNaoEncontrado(ValueError):
    pass


def _candidatas(cinza):
    """Gera versões da imagem para tentar: inteira, ampliada, binarizada e em janelas."""
    import cv2

    yield cinza
    yield cv2.adaptiveThreshold(cinza, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 51, 10)
    for fator in (0.5, 2):
        yield cv2.resize(cinza, None, fx=fator, fy=fator, interpolation=cv2.INTER_AREA
                         if fator < 1 else cv2.INTER_CUBIC)

    # Varre o cupom em janelas quadradas sobrepostas, de baixo pra cima (o QR fica no fim).
    altura, largura = cinza.shape
    lado = min(largura, altura)
    passo = max(lado // 3, 1)
    for y in range(max(altura - lado, 0), -1, -passo):
        janela = cinza[y:y + lado, 0:largura]
        for fator in (1, 2):
            yield cv2.resize(janela, None, fx=fator, fy=fator, interpolation=cv2.INTER_CUBIC)


def ler_qrcode(caminho_imagem: str | Path) -> str:
    import cv2

    img = cv2.imread(str(caminho_imagem))
    if img is None:
        raise QRCodeNaoEncontrado(f"Não consegui abrir a imagem {caminho_imagem}")
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if max(cinza.shape) > 4000:  # fotos enormes deixam a varredura lenta
        fator = 4000 / max(cinza.shape)
        cinza = cv2.resize(cinza, None, fx=fator, fy=fator, interpolation=cv2.INTER_AREA)

    detector = cv2.QRCodeDetector()
    for imagem in _candidatas(cinza):
        texto, _, _ = detector.detectAndDecode(imagem)
        if texto:
            return texto.strip()
    raise QRCodeNaoEncontrado(
        "QR code não encontrado na foto. Tire uma foto só do QR (de perto, reto e sem "
        "reflexo) ou escaneie com a câmera do celular e passe o link entre aspas.")


def chave_do_link(link: str) -> str | None:
    """A chave de acesso (44 dígitos) vem no parâmetro p= do link do QR code."""
    achado = re.search(r"\d{44}", link)
    return achado.group(0) if achado else None
