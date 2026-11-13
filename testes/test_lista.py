"""Lista de compras: sugestões, edição e a nota marcando o que foi comprado."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from compras.banco.modelos import Base
from compras.nota.esquema import ItemNota, NotaFiscal
from compras.reposicao import lista
from compras.reposicao import servico as reposicao
from compras.servicos.importar import salvar_nota


def _nota(chave, *itens):
    return NotaFiscal(
        estabelecimento_nome="MERCADO", estabelecimento_cnpj="11111111000111",
        data_emissao=f"{date.today():%Y-%m-%d}T10:00", chave_acesso=chave,
        valor_total=sum(Decimal(str(t)) for *_, t in itens),
        itens=[ItemNota(descricao=d, quantidade=Decimal(str(q)), unidade="UN", categoria="mercearia",
                        valor_unitario=Decimal(str(t)) / Decimal(str(q)), valor_total=Decimal(str(t)))
               for d, q, t in itens])


@pytest.fixture
def sessao():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as s:
        reposicao.configurar_casa(s, adultos=2)
        # sem estoque nenhum: os dois "acabaram"
        reposicao.criar_essencial(s, "Arroz", [], 30, quantidade=Decimal("5"), unidade="KG")
        reposicao.criar_essencial(s, "Detergente", [], 15, quantidade=Decimal("2"), unidade="UN")
        yield s


def _textos(sessao, status="pendente"):
    return sorted(i.texto for i in lista.listar(sessao) if i.status == status)


def test_essenciais_acabando_viram_sugestao_com_a_quantidade_de_costume(sessao):
    assert lista.sugerir(sessao) == 2
    arroz = next(i for i in lista.listar(sessao) if i.texto == "Arroz")
    assert arroz.origem == "sugestao" and arroz.quantidade == 5 and arroz.unidade == "kg"
    assert lista.sugerir(sessao) == 0  # não duplica


def test_sugestao_removida_nao_volta_na_mesma_semana(sessao):
    lista.sugerir(sessao)
    detergente = next(i for i in lista.listar(sessao) if i.texto == "Detergente")
    lista.remover(sessao, detergente.id)
    assert lista.sugerir(sessao) == 0
    assert _textos(sessao) == ["Arroz"]


def test_usuario_acrescenta_edita_e_marca(sessao):
    pilhas = lista.adicionar(sessao, "Pilhas AA", Decimal("4"), "UN")
    lista.editar(sessao, pilhas.id, quantidade=Decimal("8"))
    assert pilhas.quantidade == 8 and pilhas.origem == "manual"
    lista.editar(sessao, pilhas.id, status="comprado")
    assert "Pilhas AA" in _textos(sessao, "comprado")
    assert lista.limpar_comprados(sessao) == 1 and "Pilhas AA" not in _textos(sessao, "comprado")
    with pytest.raises(ValueError):
        lista.adicionar(sessao, "  ")


def test_nota_marca_como_comprado_o_que_estava_na_lista(sessao):
    lista.sugerir(sessao)
    lista.adicionar(sessao, "Papel higiênico")
    lista.adicionar(sessao, "Pilhas")
    salvar_nota(sessao, _nota("1" * 44, ("ARROZ CAMIL 5KG", 1, 29.90),
                              ("PAPEL HIG NEVE 12 ROLOS", 1, 19.90)))
    assert _textos(sessao, "comprado") == ["Arroz", "Papel higiênico"]
    assert _textos(sessao) == ["Detergente", "Pilhas"]
