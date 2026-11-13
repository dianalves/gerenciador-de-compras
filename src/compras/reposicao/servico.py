"""Previsão de quando cada essencial acaba (fase 1: estimativa pelo perfil da casa).

    O estoque registrado vale para a data do último movimento (compra, consumo ou ajuste).
    Desde então a casa continuou consumindo, então:
    estoque estimado hoje = registrado - consumo diário x dias desde o último movimento
    acaba em = data do último movimento + registrado / consumo diário
    consumo diário = consumo por pessoa por mês x pessoas equivalentes / 30
    pessoas equivalentes = adultos + 0,5 x crianças

Na fase 2 o consumo por pessoa passa a ser aprendido do histórico (compras e "Acabou").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from compras.banco.modelos import Casa, Compra, Essencial, MovimentoEstoque, Produto
from compras.estoque.servico import saldo
from compras.produtos.normalizar import sem_acento

PESO_CRIANCA = Decimal("0.5")
DIAS_AVISO = 7  # "está acabando" quando faltam até 7 dias

@dataclass
class Previsao:
    essencial_id: int
    nome: str
    unidade: str
    estoque: Decimal  # estimado HOJE (registrado menos o consumo estimado desde a referência)
    consumo_diario: Decimal
    dias_restantes: Optional[float]
    acaba_em: Optional[date]
    situacao: str  # acabou | acabando | ok | sem_tamanho
    produtos: list[str] = field(default_factory=list)  # o que no estoque conta para ele
    sem_tamanho: list[str] = field(default_factory=list)  # produtos que não sei converter
    fonte: str = "perfil"  # perfil (fase 1) | historico (fase 2)
    registrado: Decimal = Decimal("0")  # o que o estoque mostra (compras - marcações)
    desde: Optional[date] = None  # data do último movimento: referência do registrado


def garantir_padroes(sessao: Session) -> None:
    """Garante que a casa existe. Não há essenciais prontos: cada casa define os seus."""
    if sessao.get(Casa, 1) is None:
        sessao.add(Casa(id=1, adultos=1, criancas=0, pets=0, padroes_criados=True))
        sessao.commit()


def casa(sessao: Session) -> Casa:
    garantir_padroes(sessao)
    return sessao.get(Casa, 1)


def configurar_casa(sessao: Session, adultos: int, criancas: int = 0, pets: int = 0) -> Casa:
    if adultos < 1 or criancas < 0 or pets < 0:
        raise ValueError("A casa precisa de pelo menos 1 adulto; crianças e pets não negativos")
    c = casa(sessao)
    c.adultos, c.criancas, c.pets = adultos, criancas, pets
    sessao.commit()
    return c


def pessoas_equivalentes(c: Casa) -> Decimal:
    return Decimal(c.adultos) + PESO_CRIANCA * Decimal(c.criancas)


def _lista(texto: str) -> list[str]:
    return [sem_acento(p).strip() for p in (texto or "").split(",") if p.strip()]


def _palavra_casa(palavra_nome: str, palavra_produto: str) -> bool:
    """HIGIENICO (nome) casa com HIG (cupom abreviou); SAL (nome) NÃO casa com SALGADINHO."""
    return palavra_nome == palavra_produto or (
        len(palavra_produto) >= 3 and palavra_nome.startswith(palavra_produto))


def _nome_casa(grupo: str, nome_produto: str) -> bool:
    """No cupom o tipo do produto vem primeiro: a 1ª palavra do essencial tem que ser a 1ª do
    produto ("LEITE INTEGRAL" é Leite; "CREME LEITE" e "CHOCOLATE AO LEITE" não). As demais
    palavras podem estar em qualquer posição. Abreviações do cupom valem (HIG = HIGIENICO)."""
    palavras_grupo = grupo.split()
    palavras_produto = sem_acento(nome_produto).split()
    if not palavras_grupo or not palavras_produto:
        return False
    if not _palavra_casa(palavras_grupo[0], palavras_produto[0]):
        return False
    return all(any(_palavra_casa(w, p) for p in palavras_produto) for w in palavras_grupo[1:])


def produto_e_do_essencial(produto: Produto, essencial: Essencial) -> bool:
    """Escolhido pelo usuário, ou o nome tem as palavras de algum grupo.
    ARROZ CAMIL 5 kg é Arroz; CREME DE LEITE não é Leite (palavra excluída)."""
    if any(p.id == produto.id for p in essencial.produtos):
        return True
    palavras_produto = set(sem_acento(produto.nome).split())
    if any(p in palavras_produto for p in _lista(essencial.excluir)):
        return False
    return any(_nome_casa(grupo, produto.nome) for grupo in _lista(essencial.palavras))


def na_unidade(quantidade: Decimal, unidade_item: str, produto: Produto,
               unidade_alvo: str) -> Optional[Decimal]:
    """Converte o que tem no estoque para kg/L do essencial. None = não sei o tamanho."""
    unidade_item = (unidade_item or "UN").upper()
    if unidade_alvo == "un":
        return quantidade
    if unidade_alvo == "kg":
        if unidade_item == "KG":
            return quantidade
        if produto.unidade_tamanho == "g" and produto.tamanho:
            return quantidade * produto.tamanho / 1000
    if unidade_alvo == "L":
        if unidade_item in ("L", "LT"):
            return quantidade
        if produto.unidade_tamanho == "ml" and produto.tamanho:
            return quantidade * produto.tamanho / 1000
    return None


def ultimo_movimento(sessao: Session, produto_id: int) -> Optional[date]:
    """Data do último movimento do produto. Para compras vale a data do CUPOM (o estoque
    inicial é criado depois, mas o arroz foi comprado no dia da nota)."""
    mov = sessao.scalars(select(MovimentoEstoque)
                         .where(MovimentoEstoque.produto_id == produto_id)
                         .order_by(MovimentoEstoque.id.desc()).limit(1)).first()
    if mov is None:
        return None
    if mov.tipo == "compra" and mov.compra_id:
        compra = sessao.get(Compra, mov.compra_id)
        if compra is not None and compra.data_emissao is not None:
            return compra.data_emissao.date()
    return mov.criado_em.date() if mov.criado_em else None


def prever(sessao: Session, hoje: Optional[date] = None, so_ativos: bool = True) -> list[Previsao]:
    hoje = hoje or date.today()
    c = casa(sessao)
    pessoas = pessoas_equivalentes(c)
    consulta = select(Essencial).order_by(Essencial.nome)
    if so_ativos:
        consulta = consulta.where(Essencial.ativo.is_(True))
    essenciais = sessao.scalars(consulta).all()

    em_casa = [(i, sessao.get(Produto, i.produto_id)) for i in saldo(sessao)]
    previsoes = []
    for e in essenciais:
        estoque, produtos, sem_tamanho = Decimal("0"), [], []
        for item, produto in em_casa:
            if not produto_e_do_essencial(produto, e):
                continue
            convertido = na_unidade(item.quantidade, item.unidade, produto, e.unidade)
            if convertido is None:
                sem_tamanho.append(produto.nome)
            else:
                estoque += convertido
                produtos.append(produto.nome)

        consumo_diario = (e.consumo_pessoa_mes * pessoas / 30).quantize(Decimal("0.0001"))
        datas = [d for d in (ultimo_movimento(sessao, item.produto_id) for item, produto in em_casa
                             if produto.nome in produtos) if d]
        desde = max(datas) if datas else hoje
        desde = min(desde, hoje)
        registrado = estoque

        if registrado <= 0 and not sem_tamanho:
            estimado, dias, acaba, situacao = Decimal("0"), 0.0, hoje, "acabou"
        elif registrado <= 0:  # tem em casa, mas não sei quanto (embalagem sem tamanho)
            estimado, dias, acaba, situacao = Decimal("0"), None, None, "sem_tamanho"
        elif consumo_diario > 0:
            duracao_total = float(registrado / consumo_diario)  # a partir de `desde`
            acaba = desde + timedelta(days=round(duracao_total))
            dias = max(0.0, duracao_total - (hoje - desde).days)
            estimado = max(Decimal("0"), registrado - consumo_diario * (hoje - desde).days)
            situacao = "acabou" if dias <= 0 else "acabando" if dias <= DIAS_AVISO else "ok"
        else:
            estimado, dias, acaba, situacao = registrado, None, None, "ok"
        previsoes.append(Previsao(
            e.id, e.nome, e.unidade, estimado.quantize(Decimal("0.001")), consumo_diario, dias,
            acaba, situacao, produtos, sem_tamanho,
            registrado=registrado.quantize(Decimal("0.001")), desde=desde))
    return previsoes


def alertas(sessao: Session, hoje: Optional[date] = None) -> list[Previsao]:
    """Essenciais ativos que acabaram ou estão acabando (os mais urgentes primeiro)."""
    return sorted((p for p in prever(sessao, hoje) if p.situacao in ("acabou", "acabando")),
                  key=lambda p: p.dias_restantes or 0)


def atualizar_essencial(sessao: Session, essencial_id: int, ativo: Optional[bool] = None,
                        consumo_pessoa_mes: Optional[Decimal] = None) -> Essencial:
    e = sessao.get(Essencial, essencial_id)
    if e is None:
        raise LookupError("Essencial não encontrado")
    if ativo is not None:
        e.ativo = ativo
    if consumo_pessoa_mes is not None:
        if consumo_pessoa_mes <= 0:
            raise ValueError("O consumo tem que ser maior que zero")
        e.consumo_pessoa_mes = consumo_pessoa_mes
    sessao.commit()
    return e


def essencial_por_nome(sessao: Session, nome: str) -> Optional[Essencial]:
    garantir_padroes(sessao)
    alvo = sem_acento(nome).strip()
    return next((e for e in sessao.scalars(select(Essencial)).all()
                 if sem_acento(e.nome) == alvo), None)


# ---- essenciais criados e editados pelo usuário ----

def dura_um_pacote(essencial: Essencial, c: Casa) -> Optional[float]:
    """Quantos dias "1 pacote" dura nesta casa, pelo consumo atual."""
    consumo_dia = essencial.consumo_pessoa_mes * pessoas_equivalentes(c) / 30
    if not essencial.quantidade_pacote or consumo_dia <= 0:
        return None
    return float(essencial.quantidade_pacote / consumo_dia)


def _pacote_dos_produtos(sessao: Session, produtos: list[Produto]) -> tuple[str, Decimal]:
    """Unidade e tamanho de "1 pacote" a partir do primeiro produto escolhido.
    Com tamanho no nome (5 kg, 900 ml) usa kg/L; vendido por peso usa a quantidade média
    comprada; sem nenhuma pista, conta embalagens (un)."""
    from sqlalchemy import func

    from compras.banco.modelos import ItemCompra

    for produto in produtos:
        if produto.unidade_tamanho == "g" and produto.tamanho:
            return "kg", produto.tamanho / 1000
        if produto.unidade_tamanho == "ml" and produto.tamanho:
            return "L", produto.tamanho / 1000
        media_kg = sessao.scalar(select(func.avg(ItemCompra.quantidade)).where(
            ItemCompra.produto_id == produto.id, ItemCompra.unidade == "KG"))
        if media_kg:
            return "kg", Decimal(str(media_kg)).quantize(Decimal("0.001"))
    return "un", Decimal("1")


def produtos_do_nome(sessao: Session, nome: str) -> list[Produto]:
    """Produtos já comprados que contam para um essencial com esse nome (mais recente 1º)."""
    from sqlalchemy import func

    from compras.banco.modelos import ItemCompra

    grupo = _palavras_do_nome(nome)
    if not grupo:
        return []
    ultima_compra = (select(ItemCompra.produto_id, func.max(Compra.data_emissao).label("ultima"))
                     .join(Compra).group_by(ItemCompra.produto_id).subquery())
    produtos = sessao.execute(
        select(Produto).join(ultima_compra, ultima_compra.c.produto_id == Produto.id)
        .order_by(ultima_compra.c.ultima.desc())).scalars().all()
    return [p for p in produtos if _nome_casa(grupo, p.nome)]


@dataclass
class PreviaEssencial:
    nome: str
    encontrados: int
    unidade: str
    quantidade_pacote: Decimal
    em_estoque: Decimal = Decimal("0")  # o que já está no estoque, na unidade acima


def previa(sessao: Session, nome: str) -> PreviaEssencial:
    """O que o app mostra enquanto você digita: quantos itens combinam e o tamanho do pacote."""
    produtos = produtos_do_nome(sessao, nome)
    unidade, pacote = _pacote_dos_produtos(sessao, produtos)
    texto = nome.strip()

    # quanto já tem: mesma regra de "o que conta" do essencial, sem salvar nada
    provisorio = Essencial(nome=texto, palavras=_palavras_do_nome(texto), excluir="",
                           unidade=unidade, consumo_pessoa_mes=Decimal("1"))
    em_estoque = Decimal("0")
    for item in saldo(sessao):
        produto = sessao.get(Produto, item.produto_id)
        if produto_e_do_essencial(produto, provisorio):
            convertido = na_unidade(item.quantidade, item.unidade, produto, unidade)
            em_estoque += convertido or Decimal("0")
    return PreviaEssencial(texto[:1].upper() + texto[1:], len(produtos), unidade, pacote,
                           em_estoque.quantize(Decimal("0.001")))


def _consumo_por_duracao(pacote: Decimal, duracao_dias: int, c: Casa) -> Decimal:
    """"1 pacote dura N dias nesta casa" -> consumo por pessoa por mês."""
    if duracao_dias < 1:
        raise ValueError("A duração precisa ser de pelo menos 1 dia")
    return (pacote / Decimal(duracao_dias) * 30 / pessoas_equivalentes(c)).quantize(Decimal("0.001"))


def _palavras_do_nome(nome: str) -> str:
    from compras.produtos.normalizar import normalizar

    return " ".join(normalizar(nome).palavras)


def _produtos(sessao: Session, produto_ids: list[int]) -> list[Produto]:
    produtos = [sessao.get(Produto, i) for i in dict.fromkeys(produto_ids)]
    if any(p is None for p in produtos):
        raise LookupError("Algum produto escolhido não existe")
    return produtos


UNIDADES_ESSENCIAL = {"UN": "un", "KG": "kg", "L": "L", "un": "un", "kg": "kg"}


def _quantidade_comprada(quantidade: Optional[Decimal],
                         unidade: Optional[str]) -> Optional[tuple[str, Decimal]]:
    """"Quantidade que você geralmente compra": 2 unidades, 5 kg, 3 L."""
    if quantidade is None and unidade is None:
        return None
    if quantidade is None or quantidade <= 0:
        raise ValueError("A quantidade que você compra tem que ser maior que zero")
    if unidade not in UNIDADES_ESSENCIAL:
        raise ValueError("Unidade deve ser unidades, kg ou litros")
    return UNIDADES_ESSENCIAL[unidade], Decimal(quantidade)


def criar_essencial(sessao: Session, nome: str, produto_ids: list[int], duracao_dias: int,
                    quantidade: Optional[Decimal] = None,
                    unidade: Optional[str] = None) -> Essencial:
    """`quantidade` + `unidade` = quanto a casa costuma comprar; `duracao_dias` = quanto isso
    dura. Sem quantidade, usa o tamanho do item comprado mais recente com esse nome."""
    nome = nome.strip()
    if not nome:
        raise ValueError("Dê um nome ao essencial")
    existente = essencial_por_nome(sessao, nome)
    if existente is not None:
        if existente.ativo:
            raise FileExistsError(f"Você já acompanha '{existente.nome}'")
        # estava desativado (sugestão ou desligado antes): reativa com a nova duração
        return editar_essencial(sessao, existente.id, ativo=True, duracao_dias=duracao_dias,
                                produto_ids=produto_ids or None, quantidade=quantidade,
                                unidade=unidade)
    produtos = _produtos(sessao, produto_ids)
    comprada = _quantidade_comprada(quantidade, unidade)
    if comprada:
        unidade, pacote = comprada
    else:  # sem quantidade informada, vem do item mais recente que combina com o nome
        unidade, pacote = _pacote_dos_produtos(sessao, produtos or produtos_do_nome(sessao, nome))
    e = Essencial(nome=nome, palavras=_palavras_do_nome(nome), excluir="", unidade=unidade,
                  quantidade_pacote=pacote, ativo=True,
                  consumo_pessoa_mes=_consumo_por_duracao(pacote, duracao_dias, casa(sessao)))
    e.produtos = produtos
    sessao.add(e)
    sessao.commit()
    return e


def editar_essencial(sessao: Session, essencial_id: int, *, nome: Optional[str] = None,
                     ativo: Optional[bool] = None, duracao_dias: Optional[int] = None,
                     produto_ids: Optional[list[int]] = None,
                     consumo_pessoa_mes: Optional[Decimal] = None,
                     quantidade: Optional[Decimal] = None,
                     unidade: Optional[str] = None) -> Essencial:
    e = sessao.get(Essencial, essencial_id)
    if e is None:
        raise LookupError("Essencial não encontrado")
    dias_antes = dura_um_pacote(e, casa(sessao))
    comprada = _quantidade_comprada(quantidade, unidade)
    if comprada:
        e.unidade, e.quantidade_pacote = comprada
        if duracao_dias is None and dias_antes:  # mudou só a quantidade: mantém a duração
            duracao_dias = max(1, round(dias_antes))
    if nome is not None and nome.strip() and nome.strip() != e.nome:
        if essencial_por_nome(sessao, nome) is not None:
            raise FileExistsError(f"Já existe o essencial '{nome.strip()}'")
        e.nome = nome.strip()
        e.palavras = _palavras_do_nome(e.nome)  # o nome é o que define o que conta
        if not e.produtos and not comprada:
            e.unidade, e.quantidade_pacote = _pacote_dos_produtos(
                sessao, produtos_do_nome(sessao, e.nome))
    if produto_ids is not None:
        e.produtos = _produtos(sessao, produto_ids)
        if e.produtos and not comprada:  # o "pacote" passa a ser o do produto escolhido
            e.unidade, e.quantidade_pacote = _pacote_dos_produtos(sessao, e.produtos)
    if duracao_dias is not None:
        e.consumo_pessoa_mes = _consumo_por_duracao(e.quantidade_pacote or Decimal("1"),
                                                    duracao_dias, casa(sessao))
    sessao.commit()
    return atualizar_essencial(sessao, essencial_id, ativo=ativo,
                               consumo_pessoa_mes=consumo_pessoa_mes)


def apagar_essencial(sessao: Session, essencial_id: int) -> None:
    e = sessao.get(Essencial, essencial_id)
    if e is None:
        raise LookupError("Essencial não encontrado")
    sessao.delete(e)
    sessao.commit()


# ---- correção pelo usuário: "ainda tenho" ----

def _para_unidade_do_produto(quantidade: Decimal, unidade_essencial: str, produto: Produto,
                             unidade_item: str) -> tuple[Decimal, str]:
    """Inverso de na_unidade: X kg do essencial -> quantas embalagens desse produto."""
    unidade_item = (unidade_item or "UN").upper()
    if unidade_essencial == "un" or unidade_item in ("KG", "L", "LT"):
        return quantidade, unidade_item
    if unidade_essencial == "kg" and produto.unidade_tamanho == "g" and produto.tamanho:
        return (quantidade * 1000 / produto.tamanho).quantize(Decimal("0.001")), "UN"
    if unidade_essencial == "L" and produto.unidade_tamanho == "ml" and produto.tamanho:
        return (quantidade * 1000 / produto.tamanho).quantize(Decimal("0.001")), "UN"
    return quantidade, {"kg": "KG", "L": "L"}.get(unidade_essencial, "UN")


def ainda_tenho(sessao: Session, essencial_id: int, quantidade: Decimal,
                hoje: Optional[date] = None) -> Previsao:
    """O usuário corrige a estimativa: "ainda tenho X" (na unidade do essencial).

    Zera os outros produtos do essencial e deixa X no mais recente; vira ajuste com a data de
    hoje (nova referência da previsão) e tira a sugestão da lista de compras.
    """
    from compras.banco.modelos import ItemLista, MovimentoEstoque
    from compras.estoque.servico import ajustar

    if quantidade < 0:
        raise ValueError("A quantidade não pode ser negativa")
    e = sessao.get(Essencial, essencial_id)
    if e is None:
        raise LookupError("Essencial não encontrado")

    em_casa = [(i, sessao.get(Produto, i.produto_id)) for i in saldo(sessao)]
    do_essencial = [(i, p) for i, p in em_casa if produto_e_do_essencial(p, e)]

    if do_essencial:
        alvo_item, alvo = do_essencial[0]
        recentes = [d for d in (ultimo_movimento(sessao, i.produto_id) for i, _ in do_essencial)]
        alvo_item, alvo = max(zip(do_essencial, recentes),
                              key=lambda par: par[1] or date.min)[0]
        unidade_item = alvo_item.unidade
    else:  # nada no estoque: usa o último comprado com esse nome, ou cria pelo nome
        from compras.produtos.servico import produto_para

        comprados = produtos_do_nome(sessao, e.nome)
        alvo = comprados[0] if comprados else produto_para(sessao, e.nome)
        unidade_item = "KG" if e.unidade == "kg" and not alvo.tamanho else "UN"

    for item, produto in do_essencial:
        if produto.id != alvo.id:
            ajustar(sessao, produto.id, Decimal("0"))

    qtd_produto, unidade_produto = _para_unidade_do_produto(quantidade, e.unidade, alvo, unidade_item)
    tem = next((i for i, p in do_essencial if p.id == alvo.id and i.unidade == unidade_produto), None)
    atual = tem.quantidade if tem is not None else Decimal("0")
    # grava SEMPRE, mesmo sem diferença: a data da confirmação vira a nova referência
    sessao.add(MovimentoEstoque(produto_id=alvo.id, quantidade=qtd_produto - atual,
                                unidade=unidade_produto, tipo="ajuste"))

    for item in sessao.scalars(select(ItemLista).where(
            ItemLista.essencial_id == e.id, ItemLista.status == "pendente")):
        item.status = "removido"
    sessao.commit()
    return next(p for p in prever(sessao, hoje) if p.essencial_id == e.id)
