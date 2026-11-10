"""Aplicação FastAPI. Rode com `compras api` e abra http://localhost:8000/docs"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from compras.api import (rotas_compras, rotas_estoque, rotas_notas, rotas_produtos,
                         rotas_relatorios)
from compras.api.dependencias import obter_sessao

app = FastAPI(
    title="Gerenciador de Compras",
    description="Importa NFC-e (pela SEFAZ ou por foto) e mostra para onde vai o dinheiro "
                "do mercado.",
    version="0.1.0",
)

# Em desenvolvimento o app no celular acessa de outro endereço; liberado geral por enquanto.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

app.include_router(rotas_notas.roteador)
app.include_router(rotas_compras.roteador)
app.include_router(rotas_relatorios.roteador)
app.include_router(rotas_produtos.roteador)
app.include_router(rotas_estoque.roteador)


@app.get("/saude", tags=["sistema"], summary="Verifica se a API e o banco estão no ar")
def saude(sessao: Session = Depends(obter_sessao)):
    try:
        sessao.execute(text("select 1"))
        banco = True
    except Exception:
        banco = False
    return {"api": True, "banco": banco}
