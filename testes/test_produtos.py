"""Normalização de produtos com descrições reais dos cupons."""
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from compras.banco.modelos import Base, Produto
from compras.produtos.normalizar import normalizar, parecidos


def chave(descricao):
    return normalizar(descricao).chave


def test_mesmo_produto_escrito_diferente():
    assert chave("REFR.COCA COLA 2L") == chave("REFRI.COCA COLA 2LT")
    assert chave("REFR.COCA COLA 2L") == "REFRIGERANTE COCA COLA|2000ml"
    assert chave("FLV ALHO A GRANEL Kg") == chave("ALHO Kg") == chave("FLV ALHO A GRANEL kg")
    assert chave("FLV CEBOLA GRANEL Kg") == chave("CEBOLA Kg")
    assert chave("SOBRE COXA BAND. Kg") == chave("SOBRECOXA")


def test_produtos_diferentes_continuam_diferentes():
    assert chave("CEBOLA ROXA Kg") != chave("CEBOLA Kg")
    assert chave("CAPS.CAFE D.GUSTO 80G") != chave("CAPS.CAFE D.GUSTO 175G N")
    assert chave("REFR.COCA COLA 2L") != chave("REFR.COCA COLA 600ML")


def test_tamanhos():
    n = normalizar("C.LEITE PIRACANJUBA 200G")
    assert n.palavras == ("CREME", "LEITE", "PIRACANJUBA") and n.tamanho == 200
    assert normalizar("ABACAXI PEROLA 1,2KG").tamanho == Decimal("1200.0")
    assert normalizar("H2OH 1.5LT CITRUS").tamanho == Decimal("1500.0")
    assert normalizar("CHOC.NESTLE 41,5G KIT KA").nome == "CHOCOLATE NESTLE KIT KA 41,5 g"
    assert normalizar("REFR.COCA COLA 2L").nome == "REFRIGERANTE COCA COLA 2 L"
    assert normalizar("LEITE COND.PIRACANJ.395G").nome == "LEITE CONDENSADO PIRACANJ 395 g"


def test_nome_cortado_pelo_caixa_vira_sugestao():
    a, b = normalizar("ENERGETICO MONSTER 473ML"), normalizar("ENERGETICO MONSTER 4")
    assert a.chave != b.chave  # não junta sozinho...
    assert parecidos(a, b) >= 0.85  # ...mas sugere
    assert parecidos(normalizar("REFR.COCA COLA 2L"), normalizar("REFR.COCA COLA 600ML")) == 0
    # falsos positivos encontrados nas notas reais: não podem virar sugestão
    assert parecidos(normalizar("CEBOLA Kg"), normalizar("CEBOLA ROXA Kg")) < 0.85
    assert parecidos(normalizar("FLV BATATA GRANEL Kg"), normalizar("BATATA PRINGLES 100G")) < 0.85
    assert parecidos(normalizar("BISC.NESTLE SURPRES 130G"),
                     normalizar("BISC.NESTLE SURPRESA 130G")) >= 0.85


def _sessao():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    return sessionmaker(bind=motor)()


def test_vincula_cria_apelido_e_reaproveita():
    from compras.produtos.servico import produto_para

    s = _sessao()
    p1 = produto_para(s, "REFR.COCA COLA 2L", "bebidas")
    p2 = produto_para(s, "REFRI.COCA COLA 2LT", "bebidas")  # outro mercado
    p3 = produto_para(s, "refr.coca  cola 2l", "bebidas")  # mesma descrição, outra grafia
    assert p1.id == p2.id == p3.id
    assert sorted(a.descricao for a in p1.apelidos) == ["REFR.COCA COLA 2L", "REFRI.COCA COLA 2LT"]


def test_sugerir_e_juntar():
    from compras.banco.modelos import ApelidoProduto
    from compras.produtos.servico import juntar, produto_para, sugerir_juncoes

    s = _sessao()
    cheio = produto_para(s, "ENERGETICO MONSTER 473ML", "bebidas")
    cortado = produto_para(s, "ENERGETICO MONSTER 4", "bebidas")
    produto_para(s, "ALHO Kg", "hortifruti")
    s.commit()

    sugestoes = sugerir_juncoes(s)
    assert len(sugestoes) == 1
    assert (sugestoes[0].origem.id, sugestoes[0].destino.id) == (cortado.id, cheio.id)

    juntar(s, cortado.id, cheio.id)
    assert s.get(Produto, cortado.id) is None
    apelidos = s.query(ApelidoProduto).filter_by(produto_id=cheio.id).count()
    assert apelidos == 2
    # depois de juntar, a descrição cortada já cai no produto certo
    assert produto_para(s, "ENERGETICO MONSTER 4", "bebidas").id == cheio.id
