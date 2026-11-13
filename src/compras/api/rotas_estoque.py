from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from compras.api.dependencias import obter_sessao
from compras.api.esquemas import EntradaManual, EntradaQuantidade, ItemEstoqueSaida
from compras.estoque import servico
from compras.estoque.servico import ProdutoForaDoEstoque

roteador = APIRouter(prefix="/estoque", tags=["estoque"])


def _executar(acao):
    try:
        return ItemEstoqueSaida(**vars(acao()))
    except ProdutoForaDoEstoque as erro:
        raise HTTPException(404, str(erro))
    except ValueError as erro:
        raise HTTPException(422, str(erro))


@roteador.get("", response_model=List[ItemEstoqueSaida], summary="O que tem em casa agora")
def listar(sessao: Session = Depends(obter_sessao)):
    return [ItemEstoqueSaida(**vars(i)) for i in servico.saldo(sessao)]


@roteador.post("/manual", response_model=ItemEstoqueSaida, status_code=201,
               summary="Item que já tinha em casa (sem nota, sem preço)")
def adicionar_manual(entrada: EntradaManual, sessao: Session = Depends(obter_sessao)):
    return _executar(lambda: servico.adicionar_manual(
        sessao, entrada.nome, entrada.quantidade, entrada.unidade, entrada.produto_id))


@roteador.post("/{produto_id}/consumir", response_model=ItemEstoqueSaida,
               summary="Usei uma parte (padrão: 1)")
def consumir(produto_id: int, entrada: EntradaQuantidade = EntradaQuantidade(quantidade=Decimal("1")),
             sessao: Session = Depends(obter_sessao)):
    return _executar(lambda: servico.consumir(sessao, produto_id, entrada.quantidade))


@roteador.post("/{produto_id}/acabou", response_model=ItemEstoqueSaida, summary="Acabou")
def acabou(produto_id: int, sessao: Session = Depends(obter_sessao)):
    return _executar(lambda: servico.acabou(sessao, produto_id))


@roteador.put("/{produto_id}", response_model=ItemEstoqueSaida,
              summary="Corrige a quantidade (contei e tem X)")
def ajustar(produto_id: int, entrada: EntradaQuantidade, sessao: Session = Depends(obter_sessao)):
    return _executar(lambda: servico.ajustar(sessao, produto_id, entrada.quantidade))
