"""Lista de compras editável (com sugestões dos essenciais acabando)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from compras.api.dependencias import obter_sessao
from compras.api.esquemas import ItemListaEdicao, ItemListaNovo, ItemListaSaida
from compras.reposicao import lista

roteador = APIRouter(prefix="/lista", tags=["lista de compras"])


def _saida(i, previsoes: Optional[dict] = None) -> ItemListaSaida:
    previsao = (previsoes or {}).get(i.essencial_id)
    return ItemListaSaida(id=i.id, texto=i.texto, quantidade=i.quantidade, unidade=i.unidade,
                          origem=i.origem, status=i.status, essencial_id=i.essencial_id,
                          situacao=previsao.situacao if previsao else None,
                          dias_restantes=previsao.dias_restantes if previsao else None)


def _tratar(acao):
    try:
        return acao()
    except LookupError as erro:
        raise HTTPException(404, str(erro))
    except ValueError as erro:
        raise HTTPException(422, str(erro))


@roteador.get("", response_model=List[ItemListaSaida],
              summary="A lista (já inclui sugestões dos essenciais acabando)")
def ver(sessao: Session = Depends(obter_sessao)):
    from compras.reposicao.servico import prever

    lista.sugerir(sessao)
    # situação atual de cada essencial (ex.: "acabou" x "acaba em ~3 dias")
    previsoes = {p.essencial_id: p for p in prever(sessao)}
    return [_saida(i, previsoes) for i in lista.listar(sessao)]


@roteador.post("", response_model=ItemListaSaida, status_code=201, summary="Acrescenta um item")
def adicionar(entrada: ItemListaNovo, sessao: Session = Depends(obter_sessao)):
    return _saida(_tratar(lambda: lista.adicionar(sessao, entrada.texto, entrada.quantidade,
                                                  entrada.unidade)))


@roteador.patch("/{item_id}", response_model=ItemListaSaida,
                summary="Edita o item ou marca como comprado/pendente")
def editar(item_id: int, entrada: ItemListaEdicao, sessao: Session = Depends(obter_sessao)):
    return _saida(_tratar(lambda: lista.editar(
        sessao, item_id, texto=entrada.texto, quantidade=entrada.quantidade,
        unidade=entrada.unidade, status=entrada.status)))


@roteador.delete("/{item_id}", status_code=204, summary="Tira o item da lista")
def remover(item_id: int, sessao: Session = Depends(obter_sessao)):
    _tratar(lambda: lista.remover(sessao, item_id))


@roteador.post("/limpar-comprados", summary="Tira da lista o que já foi comprado")
def limpar(sessao: Session = Depends(obter_sessao)):
    return {"removidos": lista.limpar_comprados(sessao)}
