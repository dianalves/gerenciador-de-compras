"""Lista de compras editável.

- Sugestões: essenciais que acabaram ou estão acabando entram sozinhos, com a quantidade que
  a casa costuma comprar. Uma sugestão removida não volta antes de DIAS_SEM_REPETIR.
- O usuário acrescenta, edita, marca como comprado e remove o que quiser.
- Ao importar uma nota, o que estava na lista e foi comprado é marcado sozinho.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from compras.banco.modelos import Compra, Essencial, ItemLista
from compras.reposicao.servico import _nome_casa, _palavras_do_nome, alertas, produto_e_do_essencial

DIAS_SEM_REPETIR = 7
UNIDADES = {"UN": "un", "KG": "kg", "L": "L", "un": "un", "kg": "kg"}


def _agora() -> datetime:
    return datetime.now()


def sugerir(sessao: Session, hoje: Optional[date] = None) -> int:
    """Põe na lista os essenciais acabando que ainda não estão lá. Devolve quantos entraram."""
    limite = (hoje or date.today()) - timedelta(days=DIAS_SEM_REPETIR)
    novos = 0
    for previsao in alertas(sessao, hoje):
        recentes = sessao.scalars(select(ItemLista).where(
            ItemLista.essencial_id == previsao.essencial_id)).all()
        if any(i.status == "pendente" for i in recentes):
            continue  # já está na lista
        if any(i.criado_em and i.criado_em.date() > limite for i in recentes):
            continue  # removido ou comprado há pouco: não insistir
        essencial = sessao.get(Essencial, previsao.essencial_id)
        sessao.add(ItemLista(texto=essencial.nome, quantidade=essencial.quantidade_pacote,
                             unidade=essencial.unidade, essencial_id=essencial.id,
                             origem="sugestao", status="pendente"))
        novos += 1
    sessao.commit()
    return novos


def listar(sessao: Session, incluir_comprados: bool = True) -> list[ItemLista]:
    """Pendentes primeiro (sugestões no topo), depois os comprados nas últimas 24 h."""
    itens = sessao.scalars(select(ItemLista).where(ItemLista.status != "removido")).all()
    ontem = _agora() - timedelta(days=1)
    visiveis = [i for i in itens if i.status == "pendente" or (
        incluir_comprados and i.status == "comprado" and (i.atualizado_em or _agora()) >= ontem)]
    return sorted(visiveis, key=lambda i: (i.status != "pendente", i.origem != "sugestao",
                                           i.texto.lower()))


def _validar(texto: Optional[str], quantidade: Optional[Decimal], unidade: Optional[str]):
    if texto is not None and not texto.strip():
        raise ValueError("Digite o item")
    if quantidade is not None and quantidade <= 0:
        raise ValueError("A quantidade tem que ser maior que zero")
    if unidade is not None and unidade not in UNIDADES:
        raise ValueError("Unidade deve ser unidades, kg ou litros")


def adicionar(sessao: Session, texto: str, quantidade: Optional[Decimal] = None,
              unidade: Optional[str] = None) -> ItemLista:
    _validar(texto, quantidade, unidade)
    item = ItemLista(texto=texto.strip()[:120], quantidade=quantidade,
                     unidade=UNIDADES.get(unidade) if unidade else None,
                     origem="manual", status="pendente")
    sessao.add(item)
    sessao.commit()
    return item


def editar(sessao: Session, item_id: int, *, texto: Optional[str] = None,
           quantidade: Optional[Decimal] = None, unidade: Optional[str] = None,
           status: Optional[str] = None) -> ItemLista:
    item = sessao.get(ItemLista, item_id)
    if item is None:
        raise LookupError("Item não encontrado na lista")
    _validar(texto, quantidade, unidade)
    if status is not None and status not in ("pendente", "comprado", "removido"):
        raise ValueError("Status deve ser pendente, comprado ou removido")
    if texto is not None:
        item.texto = texto.strip()[:120]
    if quantidade is not None:
        item.quantidade = quantidade
    if unidade is not None:
        item.unidade = UNIDADES[unidade]
    if status is not None:
        item.status = status
    item.atualizado_em = _agora()
    sessao.commit()
    return item


def remover(sessao: Session, item_id: int) -> None:
    """Some da lista. Fica registrado como removido para a sugestão não voltar logo."""
    editar(sessao, item_id, status="removido")


def limpar_comprados(sessao: Session) -> int:
    itens = sessao.scalars(select(ItemLista).where(ItemLista.status == "comprado")).all()
    for item in itens:
        item.status = "removido"
    sessao.commit()
    return len(itens)


def marcar_comprados_da_nota(sessao: Session, compra: Compra) -> list[str]:
    """Chamado ao salvar uma nota: o que estava pendente na lista e veio no cupom vira
    comprado. Sugestões casam pelo essencial; itens digitados, pelo nome."""
    pendentes = sessao.scalars(select(ItemLista).where(ItemLista.status == "pendente")).all()
    produtos = [i.produto for i in compra.itens if i.produto is not None]
    marcados = []
    for item in pendentes:
        if item.essencial is not None:
            comprado = any(produto_e_do_essencial(p, item.essencial) for p in produtos)
        else:
            grupo = _palavras_do_nome(item.texto)
            comprado = any(_nome_casa(grupo, p.nome) for p in produtos)
        if comprado:
            item.status = "comprado"
            item.atualizado_em = _agora()
            marcados.append(item.texto)
    return marcados
