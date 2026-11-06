from decimal import Decimal

from compras.nota.esquema import NotaFiscal
from compras.nota.leitor import _extrair_json

RESPOSTA = """```json
{"estabelecimento_nome": "Mercado Exemplo", "estabelecimento_cnpj": "12345678000199",
 "data_emissao": "2026-11-01T10:30:00", "valor_total": 25.40, "desconto": 0,
 "itens": [
   {"descricao": "BANANA PRATA KG", "quantidade": 1.2, "unidade": "KG",
    "valor_unitario": 6.50, "valor_total": 7.80, "categoria": "hortifruti"},
   {"descricao": "LEITE INTEGRAL 1L", "quantidade": 4, "unidade": "UN",
    "valor_unitario": 4.40, "valor_total": 17.60, "categoria": "frios_laticinios"}
 ]}
```"""


def test_extrai_e_valida_nota():
    nota = NotaFiscal.model_validate(_extrair_json(RESPOSTA))
    assert len(nota.itens) == 2
    assert nota.soma_itens() == Decimal("25.40")
    assert nota.confere_total()


def test_detecta_item_pesado_lido_errado():
    dados = _extrair_json(RESPOSTA)
    dados["itens"].append({"descricao": "FILE SALMAO FRESCO", "quantidade": 1,
                           "unidade": "KG", "valor_unitario": 109.90,
                           "valor_total": 90.56, "categoria": "carnes"})
    dados["valor_total"] = 115.96
    nota = NotaFiscal.model_validate(dados)
    assert nota.confere_total()
    assert [i.descricao for i in nota.itens_inconsistentes()] == ["FILE SALMAO FRESCO"]


def _item(n, valor):
    from compras.nota.esquema import ItemNota
    return ItemNota(numero_item=n, descricao=f"ITEM {n}", quantidade=1,
                    valor_unitario=valor, valor_total=valor)


def test_conciliar_aplica_troca_que_fecha_a_conta():
    from compras.nota.leitor import conciliar
    nota = NotaFiscal(estabelecimento_nome="X", valor_total=Decimal("28.98"),
                      itens=[_item(1, Decimal("9.99")), _item(2, Decimal("16.99"))])
    corrigida, duvidas = conciliar(nota, {1: _item(1, Decimal("9.79")),
                                          2: _item(2, Decimal("18.99"))})
    assert [i.valor_total for i in corrigida.itens] == [Decimal("9.99"), Decimal("18.99")]
    assert corrigida.confere_total()
    assert [d.numero_item for d in duvidas] == [1]


def test_conciliar_nao_deixa_erro_compensar_erro():
    """Caso real: biscoito certo (3,59) lido 3,99 no zoom; cream cheese errado nas duas."""
    from compras.nota.leitor import conciliar
    nota = NotaFiscal(estabelecimento_nome="X", valor_total=Decimal("25.17"),
                      itens=[_item(12, Decimal("16.99")),
                             _item(21, Decimal("3.59")), _item(22, Decimal("3.59"))])
    resultado, duvidas = conciliar(nota, {21: _item(21, Decimal("3.99")),
                                          22: _item(22, Decimal("3.99"))})
    assert resultado is nota  # nada fecha a conta -> mantém leitura original
    assert {d.numero_item for d in duvidas} == {21, 22}


def test_categorias_casos_reais():
    from compras.nota.categorizar import categoria_por_palavras as cat
    esperado = {
        "CERVEJA SPATEN ONE W": "bebidas",        # "VEJA" não pode virar limpeza
        "CAPELETTI MASSA LEVE": "mercearia",
        "CHOC.LACTA 145G AO LEITE": "mercearia",  # chocolate, não laticínio
        "BBS MUPY 1L MACA": "bebidas",            # bebida de soja, não fruta
        "BISTECA SUINA AC kg": "carnes",
        "FLV BATATA GRANEL Kg": "hortifruti",
        "BATATA PRINGLES 100G": "mercearia",
        "SABO.FRANCIS LUXO 90": "higiene",
        "ESP.D.FACE S.BRITE L": "limpeza",
        "CREAM CHEESE POLENGHI 30": "frios_laticinios",
    }
    for descricao, categoria in esperado.items():
        assert cat(descricao) == categoria, descricao


class _ModeloFalso:
    """Simula o LM Studio nos testes de categorização."""

    def __init__(self, respostas=None, erro=None):
        self.respostas, self.erro, self.chamadas = list(respostas or []), erro, 0

    def analisar_texto(self, prompt):
        self.chamadas += 1
        if self.erro:
            raise self.erro
        return self.respostas.pop(0)


def _itens(*descricoes):
    from compras.nota.esquema import ItemNota
    return [ItemNota(descricao=d, quantidade=1, valor_unitario=1, valor_total=1)
            for d in descricoes]


def test_categorias_modelo_desligado_usa_palavras():
    from compras.nota.categorizar import categorizar_detalhado
    modelo = _ModeloFalso(erro=ConnectionError("recusado"))
    r = categorizar_detalhado(_itens("CERVEJA SPATEN", "ALHO Kg", "PRODUTO DESCONHECIDO XYZ"), modelo)
    assert [i.categoria for i in r.itens] == ["bebidas", "hortifruti", "mercearia"]
    assert r.origens == ["palavras", "palavras", "padrao"]
    assert r.erro_modelo == "ConnectionError"


def test_modelo_nao_altera_o_que_as_palavras_reconhecem():
    """O LM classificou alho como mercearia e bala como padaria: não pode mais acontecer."""
    from compras.nota.categorizar import categorizar_detalhado
    modelo = _ModeloFalso(['{"categorias": {"1": "frios_laticinios"}}'])
    r = categorizar_detalhado(_itens("FLV ALHO A GRANEL Kg", "BALA FINI 80G", "PRODUTO DESCONHECIDO XYZ"),
                              modelo)
    assert [i.categoria for i in r.itens] == ["hortifruti", "mercearia", "frios_laticinios"]
    assert r.origens == ["palavras", "palavras", "modelo"]
    assert modelo.chamadas == 1  # só o desconhecido foi perguntado ao modelo


def test_modelo_nem_e_chamado_se_tudo_foi_reconhecido():
    from compras.nota.categorizar import categorizar_detalhado
    modelo = _ModeloFalso()
    categorizar_detalhado(_itens("CERVEJA SPATEN", "ALHO Kg"), modelo)
    assert modelo.chamadas == 0


def test_resposta_invalida_do_modelo_cai_no_padrao():
    from compras.nota.categorizar import categorizar_detalhado
    r = categorizar_detalhado(_itens("PRODUTO DESCONHECIDO XYZ", "XPTO 123"),
                              _ModeloFalso(['{"categorias": {"1": "inventada"}}']))
    assert [i.categoria for i in r.itens] == ["mercearia", "mercearia"]
    assert r.origens == ["padrao", "padrao"]


def test_categorias_em_lotes():
    from compras.nota.categorizar import TAMANHO_LOTE, categorizar_detalhado
    modelo = _ModeloFalso(['{"categorias": {}}', '{"categorias": {"1": "carnes"}}'])
    r = categorizar_detalhado(_itens(*[f"XPTO {n}" for n in range(TAMANHO_LOTE + 1)]), modelo)
    assert modelo.chamadas == 2
    assert r.itens[-1].categoria == "carnes" and r.origens[-1] == "modelo"
