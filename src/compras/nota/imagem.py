"""Tratamento da foto do cupom: melhora a legibilidade e corta em fatias (o "zoom")."""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageFilter, ImageOps

LARGURA_MINIMA = 1200
LARGURA_MAXIMA = 2000


def _para_jpeg(img: Image.Image) -> bytes:
    saida = BytesIO()
    img.save(saida, format="JPEG", quality=95)
    return saida.getvalue()


def preparar_imagem(imagem: bytes) -> bytes:
    """Corrige rotação, passa para cinza, aumenta contraste e nitidez."""
    img = Image.open(BytesIO(imagem))
    img = ImageOps.exif_transpose(img)  # foto de celular costuma vir "deitada"
    img = img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)

    largura = img.width
    if largura < LARGURA_MINIMA or largura > LARGURA_MAXIMA:
        alvo = min(max(largura, LARGURA_MINIMA), LARGURA_MAXIMA)
        fator = alvo / largura
        img = img.resize((alvo, int(img.height * fator)), Image.LANCZOS)

    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    return _para_jpeg(img)


def fatiar(imagem: bytes, proporcao: float = 0.8, sobreposicao: float = 0.2) -> list[bytes]:
    """Corta o cupom em fatias horizontais com sobreposição (nenhuma linha se perde)."""
    img = Image.open(BytesIO(imagem))
    altura_fatia = max(int(img.width * proporcao), 400)
    passo = int(altura_fatia * (1 - sobreposicao))

    fatias, y = [], 0
    while True:
        fim = min(y + altura_fatia, img.height)
        fatias.append(_para_jpeg(img.crop((0, y, img.width, fim))))
        if fim >= img.height:
            break
        y += passo
    return fatias
