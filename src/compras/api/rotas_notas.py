"""Entrada de notas: pela página da SEFAZ (principal) ou pela foto (alternativa)."""
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from compras.api.dependencias import obter_modelo, obter_sessao
from compras.api.esquemas import Duvida, EntradaSefaz, ResultadoImportacao
from compras.nota.esquema import NotaFiscal
from compras.sefaz.importar import arquivar_html, nota_de_html
from compras.sefaz.parser import LayoutDesconhecido
from compras.sefaz.qrcode import chave_do_link
from compras.servicos.importar import NotaJaImportada, salvar_nota

roteador = APIRouter(prefix="/notas", tags=["notas"])

PASTA_FOTOS = Path("notas/fotos")


def _finalizar(nota: NotaFiscal, sessao: Session, *, salvar: bool, forcar: bool,
               origem: str, provedor: Optional[str] = None, imagem: Optional[str] = None,
               categorias: Optional[str] = None) -> ResultadoImportacao:
    """Salva só se a conta fechar (ou se o usuário forçar depois de conferir)."""
    duvidas = [Duvida(**vars(d)) for d in getattr(nota, "duvidas", [])]
    base = dict(confere_total=nota.confere_total(), diferenca=nota.diferenca(),
                categorias=categorias, duvidas=duvidas, nota=nota)

    if not salvar:
        return ResultadoImportacao(salva=False, mensagem="Prévia: nota lida, não salva.", **base)
    if not nota.confere_total() and not forcar:
        return ResultadoImportacao(
            salva=False,
            mensagem=(f"A soma dos itens difere do total em R$ {nota.diferenca():.2f}. "
                      "Confira os itens duvidosos e reenvie com forcar=true para salvar."),
            **base)
    try:
        compra = salvar_nota(sessao, nota, origem=origem, provedor=provedor, imagem=imagem)
    except NotaJaImportada:
        raise HTTPException(409, f"Essa nota já foi importada (chave {nota.chave_acesso}).")
    return ResultadoImportacao(salva=True, compra_id=compra.id,
                               mensagem=f"Compra #{compra.id} salva.", **base)


@roteador.post("/sefaz", response_model=ResultadoImportacao,
               summary="Importa a nota a partir do HTML da consulta na SEFAZ")
def importar_sefaz(entrada: EntradaSefaz,
                   salvar: bool = Query(True, description="false = só prévia"),
                   forcar: bool = Query(False, description="salva mesmo se a conta não fechar"),
                   sessao: Session = Depends(obter_sessao),
                   modelo=Depends(obter_modelo)):
    chave = chave_do_link(entrada.link) if entrada.link else None
    arquivar_html(entrada.html, chave)
    try:
        nota, categorias = nota_de_html(entrada.html, chave, modelo)
    except LayoutDesconhecido as erro:
        raise HTTPException(422, f"Não reconheci a página da SEFAZ: {erro}")
    return _finalizar(nota, sessao, salvar=salvar, forcar=forcar, origem="sefaz",
                      categorias=categorias.resumo())


@roteador.post("/foto", response_model=ResultadoImportacao,
               summary="Lê a foto do cupom com o modelo de visão (alternativa ao QR)")
def importar_foto(foto: UploadFile = File(..., description="Foto do cupom (jpg/png)"),
                  salvar: bool = Query(True),
                  forcar: bool = Query(False),
                  provedor: Optional[str] = Query(None, description="claude|gemini|openai|lmstudio"),
                  sessao: Session = Depends(obter_sessao)):
    from compras.nota.leitor import ler_nota

    PASTA_FOTOS.mkdir(parents=True, exist_ok=True)
    nome = f"{datetime.now():%Y%m%d_%H%M%S}_{Path(foto.filename or 'foto.jpg').name}"
    caminho = PASTA_FOTOS / nome
    caminho.write_bytes(foto.file.read())
    try:
        nota = ler_nota(caminho, provedor)
    except ValueError as erro:
        raise HTTPException(502, f"O modelo não devolveu uma nota válida: {erro}")
    return _finalizar(nota, sessao, salvar=salvar, forcar=forcar, origem="foto",
                      provedor=provedor, imagem=str(caminho))
