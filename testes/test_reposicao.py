"""Casa, essenciais definidos pelo usuário e previsão de quando acabam (fase 1: perfil)."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from compras.banco.modelos import Base, Essencial
from compras.estoque import servico as estoque
from compras.nota.esquema import ItemNota, NotaFiscal
from compras.reposicao import servico as reposicao
from compras.servicos.importar import salvar_nota

HOJE = date(2026, 11, 12)


def _nota(chave, *itens, data="2026-11-12T10:00"):
    return NotaFiscal(
        estabelecimento_nome="MERCADO", estabelecimento_cnpj="11111111000111",
        data_emissao=data, chave_acesso=chave,
        valor_total=sum(Decimal(str(t)) for *_, t in itens),
        itens=[ItemNota(descricao=d, quantidade=Decimal(str(q)), unidade=u, categoria="mercearia",
                        valor_unitario=Decimal(str(t)) / Decimal(str(q)), valor_total=Decimal(str(t)))
               for d, q, u, t in itens])


def _essencial(s, nome, palavras, unidade, consumo, pacote, ativo=True):
    """Essencial com consumo por pessoa/mês conhecido (para as contas dos testes)."""
    e = Essencial(nome=nome, palavras=palavras, excluir="", unidade=unidade, ativo=ativo,
                  consumo_pessoa_mes=Decimal(consumo), quantidade_pacote=Decimal(pacote))
    s.add(e)
    s.commit()
    return e


@pytest.fixture
def sessao():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as s:
        reposicao.configurar_casa(s, adultos=2)
        _essencial(s, "Arroz", "ARROZ", "kg", "2.5", "5")
        _essencial(s, "Leite", "LEITE", "L", "4", "1")
        _essencial(s, "Feijão", "FEIJAO", "kg", "1.2", "1")
        _essencial(s, "Café", "CAFE", "kg", "0.4", "0.5")
        yield s


def _por_nome(sessao):
    return {p.nome: p for p in reposicao.prever(sessao, HOJE)}


def _id_produto(sessao, parte):
    return next(i.produto_id for i in estoque.saldo(sessao) if parte in i.nome)


# ---------- previsão ----------

def test_arroz_5kg_para_duas_pessoas_dura_um_mes(sessao):
    salvar_nota(sessao, _nota("1" * 44, ("ARROZ CAMIL 5KG", 1, "UN", 29.90)))
    arroz = _por_nome(sessao)["Arroz"]
    assert arroz.estoque == Decimal("5.000")
    assert arroz.dias_restantes == pytest.approx(30, abs=0.5)  # 5 kg / (2,5 kg x 2 pessoas)
    assert arroz.situacao == "ok" and arroz.acaba_em == date(2026, 12, 12)


def test_crianca_conta_meia_pessoa(sessao):
    reposicao.configurar_casa(sessao, adultos=2, criancas=2)  # 3 pessoas equivalentes
    salvar_nota(sessao, _nota("1" * 44, ("ARROZ CAMIL 5KG", 1, "UN", 29.90)))
    assert _por_nome(sessao)["Arroz"].dias_restantes == pytest.approx(20, abs=0.5)


def test_soma_marcas_e_tamanhos_e_ignora_o_que_nao_e_o_item(sessao):
    salvar_nota(sessao, _nota("1" * 44,
                              ("ARROZ CAMIL 5KG", 1, "UN", 29.90),
                              ("ARROZ TIO JOAO 1KG", 2, "UN", 15.00),
                              ("LEITE INTEGRAL ITALAC 1L", 3, "UN", 15.00),
                              ("C.LEITE PIRACANJUBA 200G", 2, "UN", 5.58),  # creme de leite
                              ("CHOC.LACTA 145G AO LEITE", 1, "UN", 11.99)))  # chocolate
    previsoes = _por_nome(sessao)
    assert previsoes["Arroz"].estoque == Decimal("7.000")
    assert previsoes["Leite"].estoque == Decimal("3.000")
    assert previsoes["Leite"].produtos == ["LEITE INTEGRAL ITALAC 1 L"]


def test_alertas_acabando_e_acabou(sessao):
    salvar_nota(sessao, _nota("1" * 44, ("FEIJAO CAMIL 1KG CARIOCA", 1, "UN", 8.99),
                              ("CAFE PILAO 250G", 1, "UN", 18.90)))
    alertas = {p.nome: p.situacao for p in reposicao.alertas(sessao, HOJE)}
    assert alertas.get("Arroz") == "acabou"  # acompanhado e sem estoque
    assert "Feijão" not in alertas and "Café" not in alertas

    estoque.ajustar(sessao, _id_produto(sessao, "CAFE"), Decimal("0.5"))  # 125 g = ~4 dias
    assert {p.nome: p.situacao for p in reposicao.alertas(sessao, HOJE)}["Café"] == "acabando"


def test_produto_sem_tamanho_nao_vira_alerta_falso(sessao):
    _essencial(sessao, "Açúcar", "ACUCAR", "kg", "1.5", "1")
    salvar_nota(sessao, _nota("1" * 44, ("ACUCAR REFINADO CARA", 1, "UN", 5.49)))
    p = _por_nome(sessao)["Açúcar"]
    assert p.situacao == "sem_tamanho" and p.sem_tamanho == ["ACUCAR REFINADO CARA"]
    assert "Açúcar" not in {a.nome for a in reposicao.alertas(sessao, HOJE)}


def test_conta_o_consumo_desde_a_data_da_compra(sessao):
    """Arroz de 5 kg comprado há 10 dias: já foi ~1/3, acaba 30 dias depois da COMPRA."""
    salvar_nota(sessao, _nota("1" * 44, ("ARROZ CAMIL 5KG", 1, "UN", 29.90),
                              data="2026-11-02T10:00"))
    arroz = _por_nome(sessao)["Arroz"]
    assert arroz.registrado == Decimal("5.000") and arroz.desde == date(2026, 11, 2)
    assert arroz.estoque == pytest.approx(Decimal("3.333"), abs=Decimal("0.01"))
    assert arroz.acaba_em == date(2026, 12, 2)
    assert arroz.dias_restantes == pytest.approx(20, abs=0.5)


def test_ajuste_vira_nova_referencia(sessao):
    salvar_nota(sessao, _nota("1" * 44, ("ARROZ CAMIL 5KG", 1, "UN", 29.90),
                              data="2026-10-01T10:00"))
    assert _por_nome(sessao)["Arroz"].situacao == "acabou"  # pela estimativa, já teria acabado
    estoque.ajustar(sessao, _id_produto(sessao, "ARROZ"), Decimal("0.4"))  # 40% de 5 kg = 2 kg
    arroz = _por_nome(sessao)["Arroz"]
    assert arroz.registrado == Decimal("2.000") and arroz.situacao == "ok"
    assert arroz.dias_restantes == pytest.approx(12, abs=0.5)


# ---------- essenciais definidos pelo usuário ----------

def test_casa_nova_comeca_sem_essenciais():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as s:
        reposicao.garantir_padroes(s)
        assert s.scalars(select(Essencial)).all() == []
        assert reposicao.casa(s).adultos == 1


def test_essencial_por_embalagem(sessao):
    """Papel higiênico: sem peso no nome, conta por embalagem. 1 pacote dura 14 dias."""
    salvar_nota(sessao, _nota("1" * 44, ("PAPEL HIG NEVE 12 ROLOS", 2, "UN", 39.80)))
    papel = reposicao.criar_essencial(sessao, "Papel higiênico", [], duracao_dias=14)
    assert papel.unidade == "un" and papel.ativo
    assert reposicao.dura_um_pacote(papel, reposicao.casa(sessao)) == pytest.approx(14, abs=0.1)
    p = _por_nome(sessao)["Papel higiênico"]
    assert p.estoque == 2 and p.dias_restantes == pytest.approx(28, abs=0.5)


def test_so_o_nome_sem_marca_acha_os_itens_e_o_pacote(sessao):
    salvar_nota(sessao, _nota("1" * 44, ("PAPEL HIG NEVE 12 ROLOS", 1, "UN", 19.90),
                              ("SALG.MILHO FABITOS 8", 1, "UN", 4.50),
                              ("RACAO GOLDEN GATO 10KG", 1, "UN", 199.90)))
    assert reposicao.previa(sessao, "papel higiênico").encontrados == 1  # cupom abreviou HIG
    assert reposicao.previa(sessao, "sal").encontrados == 0  # SALGADINHO não é sal
    previa = reposicao.previa(sessao, "ração")
    assert previa.nome == "Ração" and previa.unidade == "kg" and previa.quantidade_pacote == 10

    racao = reposicao.criar_essencial(sessao, "Ração", [], duracao_dias=30)
    assert racao.quantidade_pacote == 10
    assert _por_nome(sessao)["Ração"].dias_restantes == pytest.approx(30, abs=0.5)


def test_tipo_do_produto_e_a_primeira_palavra(sessao):
    salvar_nota(sessao, _nota("1" * 44, ("PAO FORMA PULLMAN 500G", 1, "UN", 9.90),
                              ("PAO FRANCES KG", 0.5, "KG", 7.45),
                              ("C.LEITE PIRACANJUBA 200G", 1, "UN", 2.79)))
    reposicao.criar_essencial(sessao, "Pão de forma", [], duracao_dias=7)
    assert _por_nome(sessao)["Pão de forma"].produtos == ["PAO FORMA PULLMAN 500 g"]
    assert reposicao.previa(sessao, "leite").encontrados == 0  # creme de leite não conta


def test_editar_e_apagar(sessao):
    arroz = reposicao.essencial_por_nome(sessao, "Arroz")
    reposicao.editar_essencial(sessao, arroz.id, duracao_dias=40)  # 5 kg duram 40 dias
    assert reposicao.dura_um_pacote(arroz, reposicao.casa(sessao)) == pytest.approx(40, abs=0.1)

    cafe = reposicao.essencial_por_nome(sessao, "Café")
    reposicao.apagar_essencial(sessao, cafe.id)
    assert reposicao.essencial_por_nome(sessao, "Café") is None

    with pytest.raises(FileExistsError):
        reposicao.criar_essencial(sessao, "arroz", [], duracao_dias=10)  # já acompanha


def test_adicionar_um_desativado_reativa_em_vez_de_dar_erro(sessao):
    acucar = _essencial(sessao, "Açúcar", "ACUCAR", "kg", "1.5", "1", ativo=False)
    reativado = reposicao.criar_essencial(sessao, "açúcar", [], duracao_dias=20)
    assert reativado.id == acucar.id and reativado.ativo
    assert reposicao.dura_um_pacote(reativado, reposicao.casa(sessao)) == pytest.approx(20, abs=0.1)


def test_casa_precisa_de_um_adulto(sessao):
    with pytest.raises(ValueError):
        reposicao.configurar_casa(sessao, adultos=0)


def test_previa_mostra_o_que_ja_tem_no_estoque(sessao):
    assert reposicao.previa(sessao, "arroz").em_estoque == 0
    salvar_nota(sessao, _nota("1" * 44, ("ARROZ CAMIL 5KG", 1, "UN", 29.90)))
    previa = reposicao.previa(sessao, "arroz")
    assert previa.em_estoque == Decimal("5.000") and previa.unidade == "kg"


def test_essencial_novo_com_o_que_ja_tinha_em_casa(sessao):
    """Fluxo do app: cria o essencial e informa quanto tem (vira entrada manual)."""
    reposicao.criar_essencial(sessao, "Detergente", [], duracao_dias=15)
    estoque.adicionar_manual(sessao, "Detergente", Decimal("2"), "UN")
    p = _por_nome(sessao)["Detergente"]
    assert p.estoque == 2 and p.dias_restantes == pytest.approx(30, abs=0.5)


def test_quantidade_que_geralmente_compra_e_quanto_dura(sessao):
    """"Compro 2 unidades de detergente e duram 1 mês": 1 unidade a cada 15 dias."""
    detergente = reposicao.criar_essencial(sessao, "Detergente", [], duracao_dias=30,
                                           quantidade=Decimal("2"), unidade="UN")
    assert detergente.unidade == "un" and detergente.quantidade_pacote == 2
    assert reposicao.dura_um_pacote(detergente, reposicao.casa(sessao)) == pytest.approx(30, abs=0.1)
    estoque.adicionar_manual(sessao, "Detergente", Decimal("1"), "UN")
    assert _por_nome(sessao)["Detergente"].dias_restantes == pytest.approx(15, abs=0.5)


def test_informar_kg_vale_mais_que_o_tamanho_do_cupom(sessao):
    salvar_nota(sessao, _nota("1" * 44, ("CAFE PILAO 250G", 1, "UN", 18.90)))
    cafe = reposicao.essencial_por_nome(sessao, "Café")
    reposicao.editar_essencial(sessao, cafe.id, quantidade=Decimal("1"), unidade="KG")
    assert cafe.unidade == "kg" and cafe.quantidade_pacote == 1


def test_mudar_so_a_quantidade_mantem_a_duracao(sessao):
    arroz = reposicao.essencial_por_nome(sessao, "Arroz")
    reposicao.editar_essencial(sessao, arroz.id, duracao_dias=30)
    reposicao.editar_essencial(sessao, arroz.id, quantidade=Decimal("10"), unidade="KG")
    assert arroz.quantidade_pacote == 10
    assert reposicao.dura_um_pacote(arroz, reposicao.casa(sessao)) == pytest.approx(30, abs=0.5)


def test_quantidade_ou_unidade_invalida(sessao):
    with pytest.raises(ValueError):
        reposicao.criar_essencial(sessao, "Sabão", [], 30, quantidade=Decimal("0"), unidade="UN")
    with pytest.raises(ValueError):
        reposicao.criar_essencial(sessao, "Sabão", [], 30, quantidade=Decimal("1"), unidade="CX")


def test_ainda_tenho_corrige_a_previsao_e_tira_da_lista(sessao):
    """Feijão de 1 kg comprado há 10 dias: a estimativa diz ~2 dias, mas há um pacote fechado."""
    from compras.reposicao import lista

    salvar_nota(sessao, _nota("1" * 44, ("FEIJAO CAMIL 1KG CARIOCA", 1, "UN", 8.99),
                              data="2026-11-02T10:00"))
    assert _por_nome(sessao)["Feijão"].situacao == "acabando"
    lista.sugerir(sessao, HOJE)
    assert any(i.texto == "Feijão" for i in lista.listar(sessao))

    feijao = reposicao.essencial_por_nome(sessao, "Feijão")
    p = reposicao.ainda_tenho(sessao, feijao.id, Decimal("1"), hoje=HOJE)  # "tenho 1 kg"
    assert p.situacao == "ok" and p.registrado == Decimal("1.000")
    assert p.dias_restantes == pytest.approx(12.5, abs=0.6)  # 1 kg / (1,2 x 2 / 30)
    assert not any(i.texto == "Feijão" for i in lista.listar(sessao))
    assert "Feijão" not in {a.nome for a in reposicao.alertas(sessao, HOJE)}


def test_ainda_tenho_converte_kg_para_embalagens(sessao):
    salvar_nota(sessao, _nota("1" * 44, ("ARROZ CAMIL 5KG", 1, "UN", 29.90)))
    arroz = reposicao.essencial_por_nome(sessao, "Arroz")
    reposicao.ainda_tenho(sessao, arroz.id, Decimal("2.5"), hoje=HOJE)  # meio pacote
    assert estoque.saldo(sessao)[0].quantidade == Decimal("0.5")
    assert _por_nome(sessao)["Arroz"].registrado == Decimal("2.500")


def test_ainda_tenho_sem_nada_no_estoque(sessao):
    cafe = reposicao.essencial_por_nome(sessao, "Café")
    p = reposicao.ainda_tenho(sessao, cafe.id, Decimal("0.5"), hoje=HOJE)
    assert p.registrado == Decimal("0.500") and p.situacao == "ok"
