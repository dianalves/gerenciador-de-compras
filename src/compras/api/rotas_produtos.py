from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from compras.api.dependencias import obter_sessao
from compras.api.esquemas import ComparacaoSaida, PrecoSaida, ProdutoSaida
from compras.banco.modelos import Produto
from compras.produtos.precos import comparar_mercados, historico
from compras.produtos.servico import buscar

roteador = APIRouter(prefix="/produtos", tags=["produtos"])


def _saida(p: Produto) -> ProdutoSaida:
    return ProdutoSaida(id=p.id, nome=p.nome, categoria=p.categoria,
                        descricoes=[a.descricao for a in p.apelidos], compras=len(p.itens))


@roteador.get("", response_model=List[ProdutoSaida], summary="Lista/busca produtos")
def listar(busca: Optional[str] = Query(None, description="Parte do nome, ex.: COCA"),
           sessao: Session = Depends(obter_sessao)):
    return [_saida(p) for p in buscar(sessao, busca)]


@roteador.get("/comparar-mercados", response_model=List[ComparacaoSaida],
              summary="Produtos comprados em 2+ mercados: onde saiu mais barato")
def comparar(sessao: Session = Depends(obter_sessao)):
    return [ComparacaoSaida(**vars(c), diferenca=c.diferenca, percentual=round(c.percentual, 1))
            for c in comparar_mercados(sessao)]


@roteador.get("/{produto_id}/precos", response_model=List[PrecoSaida],
              summary="Histórico de preço de um produto")
def precos(produto_id: int, sessao: Session = Depends(obter_sessao)):
    if sessao.get(Produto, produto_id) is None:
        raise HTTPException(404, "Produto não encontrado")
    return [PrecoSaida(**vars(p)) for p in historico(sessao, produto_id)]
