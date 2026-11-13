"""Casa, essenciais e alertas de reposição."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from compras.api.dependencias import obter_sessao
from compras.api.esquemas import (CasaEntrada, CasaSaida, EntradaQuantidade, EssencialEntrada,
                                  EssencialNovo,
                                  EssencialSaida, PreviaEssencialSaida, PrevisaoSaida,
                                  ProdutoResumo)
from compras.banco.modelos import Essencial
from compras.reposicao import servico

roteador = APIRouter(tags=["reposição"])


def _casa(c) -> CasaSaida:
    return CasaSaida(adultos=c.adultos, criancas=c.criancas, pets=c.pets)


def _essencial(e, sessao: Session) -> EssencialSaida:
    dura = servico.dura_um_pacote(e, servico.casa(sessao))
    return EssencialSaida(id=e.id, nome=e.nome, unidade=e.unidade,
                          consumo_pessoa_mes=e.consumo_pessoa_mes, ativo=e.ativo,
                          quantidade_pacote=e.quantidade_pacote,
                          dura_pacote_dias=round(dura, 1) if dura else None,
                          produtos=[ProdutoResumo(id=p.id, nome=p.nome) for p in e.produtos])


def _tratar(acao):
    try:
        return acao()
    except LookupError as erro:
        raise HTTPException(404, str(erro))
    except FileExistsError as erro:
        raise HTTPException(409, str(erro))
    except ValueError as erro:
        raise HTTPException(422, str(erro))


@roteador.get("/casa", response_model=CasaSaida, summary="Quem mora na casa")
def ver_casa(sessao: Session = Depends(obter_sessao)):
    return _casa(servico.casa(sessao))


@roteador.put("/casa", response_model=CasaSaida, summary="Atualiza quem mora na casa")
def salvar_casa(entrada: CasaEntrada, sessao: Session = Depends(obter_sessao)):
    return _casa(servico.configurar_casa(sessao, entrada.adultos, entrada.criancas, entrada.pets))


@roteador.get("/essenciais", response_model=List[EssencialSaida],
              summary="Todos os essenciais (ativos e sugeridos)")
def listar_essenciais(sessao: Session = Depends(obter_sessao)):
    servico.garantir_padroes(sessao)
    return [_essencial(e, sessao)
            for e in sessao.scalars(select(Essencial).order_by(Essencial.nome)).all()]


@roteador.get("/essenciais/previa", response_model=PreviaEssencialSaida,
              summary="Enquanto digita: quantos itens comprados combinam e o tamanho do pacote")
def previa_essencial(nome: str, sessao: Session = Depends(obter_sessao)):
    return PreviaEssencialSaida(**vars(servico.previa(sessao, nome)))


@roteador.post("/essenciais", response_model=EssencialSaida, status_code=201,
               summary="Cria um essencial: nome, produtos que contam e quanto 1 pacote dura")
def criar_essencial(entrada: EssencialNovo, sessao: Session = Depends(obter_sessao)):
    e = _tratar(lambda: servico.criar_essencial(sessao, entrada.nome, entrada.produto_ids,
                                                 entrada.duracao_dias, entrada.quantidade,
                                                 entrada.unidade))
    return _essencial(e, sessao)


@roteador.delete("/essenciais/{essencial_id}", status_code=204, summary="Apaga um essencial")
def apagar_essencial(essencial_id: int, sessao: Session = Depends(obter_sessao)):
    _tratar(lambda: servico.apagar_essencial(sessao, essencial_id))


@roteador.patch("/essenciais/{essencial_id}", response_model=EssencialSaida,
                summary="Edita nome, ativo, quanto 1 pacote dura ou os produtos que contam")
def editar_essencial(essencial_id: int, entrada: EssencialEntrada,
                     sessao: Session = Depends(obter_sessao)):
    e = _tratar(lambda: servico.editar_essencial(
        sessao, essencial_id, nome=entrada.nome, ativo=entrada.ativo,
        duracao_dias=entrada.duracao_dias, produto_ids=entrada.produto_ids,
        consumo_pessoa_mes=entrada.consumo_pessoa_mes, quantidade=entrada.quantidade,
        unidade=entrada.unidade))
    return _essencial(e, sessao)


@roteador.get("/essenciais/previsao", response_model=List[PrevisaoSaida],
              summary="Quanto cada essencial ativo ainda dura")
def previsao(sessao: Session = Depends(obter_sessao)):
    return [PrevisaoSaida(**vars(p)) for p in servico.prever(sessao)]


@roteador.post("/essenciais/{essencial_id}/ainda-tenho", response_model=PrevisaoSaida,
               summary="Corrige a estimativa: 'ainda tenho X' (na unidade do essencial)")
def ainda_tenho(essencial_id: int, entrada: EntradaQuantidade,
                sessao: Session = Depends(obter_sessao)):
    return PrevisaoSaida(**vars(_tratar(
        lambda: servico.ainda_tenho(sessao, essencial_id, entrada.quantidade))))


@roteador.get("/essenciais/alertas", response_model=List[PrevisaoSaida],
              summary="Essenciais que acabaram ou estão acabando")
def alertas(sessao: Session = Depends(obter_sessao)):
    return [PrevisaoSaida(**vars(p)) for p in servico.alertas(sessao)]
