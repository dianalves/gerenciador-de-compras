"""Estoque: compras somam, consumo subtrai, nunca fica negativo."""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from compras.banco.modelos import Base
from compras.estoque import servico
from compras.nota.esquema import ItemNota, NotaFiscal
from compras.servicos.importar import salvar_nota


def _nota(chave, data, *itens):
    total = sum(Decimal(str(v)) for _, _, _, v in itens)
    return NotaFiscal(
        estabelecimento_nome="MERCADO", estabelecimento_cnpj="11111111000111",
        data_emissao=data, chave_acesso=chave, valor_total=total,
        itens=[ItemNota(descricao=d, quantidade=Decimal(str(q)), unidade=u,
                        valor_unitario=Decimal(str(v)) / Decimal(str(q)),
                        valor_total=Decimal(str(v)), categoria="mercearia")
               for d, q, u, v in itens])


@pytest.fixture
def sessao():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as s:
        yield s


def _tem(sessao, nome_parcial):
    return {i.nome: i.quantidade for i in servico.saldo(sessao) if nome_parcial in i.nome}


def test_compras_somam_e_consumo_subtrai(sessao):
    salvar_nota(sessao, _nota("1" * 44, "2026-11-01T10:00", ("REFR.COCA COLA 2L", 2, "UN", 21.98)))
    salvar_nota(sessao, _nota("2" * 44, "2026-11-08T10:00", ("REFRI.COCA COLA 2LT", 1, "UN", 12.39)))
    assert _tem(sessao, "COCA") == {"REFRIGERANTE COCA COLA 2 L": Decimal("3")}

    coca = servico.saldo(sessao)[0].produto_id
    assert servico.consumir(sessao, coca).quantidade == Decimal("2")
    assert servico.consumir(sessao, coca, Decimal("5")).quantidade == 0  # não fica negativo
    assert _tem(sessao, "COCA") == {}  # zerado some da lista


def test_acabou_e_ajuste(sessao):
    salvar_nota(sessao, _nota("1" * 44, "2026-11-01T10:00", ("FLV ALHO A GRANEL Kg", 0.5, "KG", 24.95),
                              ("ARROZ CAMIL 5KG", 1, "UN", 29.90)))
    alho = next(i.produto_id for i in servico.saldo(sessao) if i.nome == "ALHO")
    assert servico.ajustar(sessao, alho, Decimal("0.2")).quantidade == Decimal("0.2")
    servico.acabou(sessao, alho)
    assert [i.nome for i in servico.saldo(sessao)] == ["ARROZ CAMIL 5 kg"]


def test_iniciar_usa_so_a_compra_mais_recente(sessao):
    from sqlalchemy import delete

    from compras.banco.modelos import MovimentoEstoque

    salvar_nota(sessao, _nota("1" * 44, "2026-04-03T10:00", ("UVA ARRA 500G", 1, "UN", 9.99)))
    salvar_nota(sessao, _nota("2" * 44, "2026-11-02T10:00", ("ARROZ CAMIL 5KG", 1, "UN", 29.90)))
    # simula o banco de antes do estoque existir: compras sem movimentos
    sessao.execute(delete(MovimentoEstoque))
    sessao.commit()

    assert servico.iniciar(sessao) == 1
    assert [i.nome for i in servico.saldo(sessao)] == ["ARROZ CAMIL 5 kg"]  # uva de abril não
    assert servico.iniciar(sessao) == 0  # não roda de novo


def test_item_que_ja_tinha_em_casa_entra_sem_preco(sessao):
    from sqlalchemy import func, select

    from compras.banco.modelos import Compra, ItemCompra

    item = servico.adicionar_manual(sessao, "Arroz", Decimal("2"), "KG")
    assert item.nome == "ARROZ" and item.quantidade == Decimal("2") and item.unidade == "KG"
    # não vira compra: gastos e preços continuam vazios
    assert sessao.scalar(select(func.count()).select_from(Compra)) == 0
    assert sessao.scalar(select(func.count()).select_from(ItemCompra)) == 0

    # consumo e "acabou" funcionam igual
    assert servico.consumir(sessao, item.produto_id, Decimal("0.5")).quantidade == Decimal("1.5")


def test_manual_escolhendo_produto_ja_comprado_soma_no_mesmo(sessao):
    salvar_nota(sessao, _nota("1" * 44, "2026-11-01T10:00", ("REFR.COCA COLA 2L", 1, "UN", 10.99)))
    coca = servico.saldo(sessao)[0].produto_id
    item = servico.adicionar_manual(sessao, "", Decimal("2"), "UN", produto_id=coca)
    assert item.produto_id == coca and item.quantidade == Decimal("3")


def test_manual_valida_entrada(sessao):
    with pytest.raises(ValueError):
        servico.adicionar_manual(sessao, "Arroz", Decimal("0"), "KG")
    with pytest.raises(ValueError):
        servico.adicionar_manual(sessao, "Arroz", Decimal("1"), "CAIXA")
    with pytest.raises(ValueError):
        servico.adicionar_manual(sessao, "  ", Decimal("1"), "UN")
