from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from compras.api.dependencias import obter_sessao
from compras.api.esquemas import GastoCategoria, GastoMensal, GastoProduto
from compras.servicos import consultas

roteador = APIRouter(prefix="/relatorios", tags=["relatórios"])


@roteador.get("/gastos-mensais", response_model=List[GastoMensal])
def gastos_mensais(sessao: Session = Depends(obter_sessao)):
    return [GastoMensal(ano=int(a), mes=int(m), total=t)
            for a, m, t in consultas.gasto_por_mes(sessao)]


@roteador.get("/categorias", response_model=List[GastoCategoria])
def categorias(ano: int, mes: int = Query(..., ge=1, le=12),
               sessao: Session = Depends(obter_sessao)):
    linhas = consultas.gasto_por_categoria(sessao, ano, mes)
    total = sum(t for _, t in linhas) or 1
    return [GastoCategoria(categoria=c, total=t, percentual=round(float(100 * t / total), 1))
            for c, t in linhas]


@roteador.get("/produtos", response_model=List[GastoProduto],
              summary="Produtos com que mais se gasta")
def produtos(limite: int = Query(10, le=100), sessao: Session = Depends(obter_sessao)):
    return [GastoProduto(descricao=d, unidade=u, quantidade=q, total=t)
            for d, u, q, t in consultas.produtos_que_mais_gasto(sessao, limite)]
