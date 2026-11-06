from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from compras.api.dependencias import obter_sessao
from compras.api.esquemas import CompraDetalhe, CompraResumo, ItemSaida
from compras.banco.modelos import Compra

roteador = APIRouter(prefix="/compras", tags=["compras"])


def _resumo(compra: Compra) -> dict:
    return dict(id=compra.id, estabelecimento=compra.estabelecimento.nome,
                data_emissao=compra.data_emissao, valor_total=compra.valor_total,
                quantidade_itens=len(compra.itens), origem=compra.origem)


@roteador.get("", response_model=List[CompraResumo], summary="Lista as compras, mais recentes primeiro")
def listar(limite: int = Query(50, le=500), sessao: Session = Depends(obter_sessao)):
    compras = sessao.scalars(
        select(Compra).options(selectinload(Compra.itens), selectinload(Compra.estabelecimento))
        .order_by(Compra.data_emissao.desc()).limit(limite)
    ).all()
    return [CompraResumo(**_resumo(c)) for c in compras]


@roteador.get("/chave/{chave}", response_model=CompraResumo,
              summary="Procura a compra pela chave de acesso (44 dígitos) da NFC-e")
def por_chave(chave: str, sessao: Session = Depends(obter_sessao)):
    """O app chama isto logo depois de ler o QR: se a nota já existe, nem abre a SEFAZ."""
    compra = sessao.scalar(select(Compra).where(Compra.chave_acesso == chave))
    if compra is None:
        raise HTTPException(404, "Nota ainda não cadastrada")
    return CompraResumo(**_resumo(compra))


@roteador.get("/{compra_id}", response_model=CompraDetalhe, summary="Uma compra com seus itens")
def detalhar(compra_id: int, sessao: Session = Depends(obter_sessao)):
    compra = sessao.get(Compra, compra_id)
    if compra is None:
        raise HTTPException(404, "Compra não encontrada")
    return CompraDetalhe(**_resumo(compra), chave_acesso=compra.chave_acesso,
                         desconto=compra.desconto, economia=compra.economia,
                         itens=[ItemSaida.model_validate(i) for i in compra.itens])


@roteador.delete("/{compra_id}", status_code=204, summary="Apaga uma compra (e seus itens)")
def apagar(compra_id: int, sessao: Session = Depends(obter_sessao)):
    compra = sessao.get(Compra, compra_id)
    if compra is None:
        raise HTTPException(404, "Compra não encontrada")
    sessao.delete(compra)
    sessao.commit()
