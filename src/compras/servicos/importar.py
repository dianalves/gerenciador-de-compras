"""Grava no banco uma NotaFiscal já extraída."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from compras.banco.modelos import Compra, Estabelecimento, ItemCompra
from compras.nota.esquema import NotaFiscal


class NotaJaImportada(Exception):
    pass


def salvar_nota(sessao: Session, nota: NotaFiscal, *, origem: str = "foto",
                provedor: str | None = None, imagem: str | None = None) -> Compra:
    if nota.chave_acesso and sessao.scalar(
        select(Compra).where(Compra.chave_acesso == nota.chave_acesso)
    ):
        raise NotaJaImportada(nota.chave_acesso)

    estab = None
    if nota.estabelecimento_cnpj:
        estab = sessao.scalar(
            select(Estabelecimento).where(Estabelecimento.cnpj == nota.estabelecimento_cnpj)
        )
    if estab is None:
        estab = Estabelecimento(nome=nota.estabelecimento_nome, cnpj=nota.estabelecimento_cnpj)
        sessao.add(estab)

    compra = Compra(
        estabelecimento=estab,
        chave_acesso=nota.chave_acesso,
        data_emissao=nota.data_emissao,
        valor_total=nota.valor_total,
        desconto=nota.desconto,
        economia=nota.economia,
        forma_pagamento=nota.forma_pagamento,
        origem=origem,
        provedor_visao=provedor,
        imagem=imagem,
        itens=[ItemCompra(**item.model_dump(exclude={"numero_item"})) for item in nota.itens],
    )
    sessao.add(compra)
    sessao.commit()
    return compra
