"""Agente de perguntas: ferramentas (números do banco) e o grafo LangGraph com modelo falso."""
from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("langgraph")

from langchain_core.messages import AIMessage  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from compras.banco.modelos import Base  # noqa: E402
from compras.ia.agente import criar_agente, responder  # noqa: E402
from compras.ia.ferramentas import criar_ferramentas  # noqa: E402
from compras.nota.esquema import ItemNota, NotaFiscal  # noqa: E402
from compras.servicos.importar import salvar_nota  # noqa: E402


def _nota(chave, cnpj, data, *itens):
    return NotaFiscal(
        estabelecimento_nome=f"MERCADO {cnpj[:2]}", estabelecimento_cnpj=cnpj,
        data_emissao=data, chave_acesso=chave,
        valor_total=sum(Decimal(str(t)) for *_, t in itens),
        itens=[ItemNota(descricao=d, quantidade=Decimal(str(q)), unidade=u, categoria=c,
                        valor_unitario=Decimal(str(t)) / Decimal(str(q)), valor_total=Decimal(str(t)))
               for d, q, u, c, t in itens])


@pytest.fixture
def abrir_sessao():
    # StaticPool: o ToolNode pode rodar a ferramenta em outra thread; todas veem o mesmo banco
    motor = create_engine("sqlite://", poolclass=StaticPool,
                          connect_args={"check_same_thread": False})
    Base.metadata.create_all(motor)
    fabrica = sessionmaker(bind=motor)
    with fabrica() as s:
        salvar_nota(s, _nota("1" * 44, "11111111000111", "2026-10-02T10:00",
                             ("SOBRE COXA BAND. Kg", 0.768, "KG", "carnes", 15.35),
                             ("REFR.COCA COLA 2L", 1, "UN", "bebidas", 10.99)))
        salvar_nota(s, _nota("2" * 44, "22222222000122", "2026-11-02T10:00",
                             ("AC MUSCULO BOVINO Kg", 1.094, "KG", "carnes", 43.75),
                             ("REFRI.COCA COLA 2LT", 1, "UN", "bebidas", 12.39)))
    return fabrica


def _ferramenta(abrir_sessao, nome):
    return next(f for f in criar_ferramentas(abrir_sessao) if f.name == nome)


def test_gasto_total_por_categoria_e_mes(abrir_sessao):
    texto = _ferramenta(abrir_sessao, "gasto_total").invoke(
        {"data_inicio": "2026-10-01", "data_fim": "2026-10-31", "categoria": "carnes"})
    assert "R$ 15,35" in texto


def test_categoria_invalida_e_recusada(abrir_sessao):
    with pytest.raises(Exception, match="Categoria inválida"):
        _ferramenta(abrir_sessao, "gasto_total").invoke(
            {"data_inicio": "2026-10-01", "data_fim": "2026-10-31", "categoria": "doces"})


def test_o_que_ficou_mais_caro(abrir_sessao):
    texto = _ferramenta(abrir_sessao, "produtos_que_mudaram_de_preco").invoke({})
    assert "REFRIGERANTE COCA COLA 2 L" in texto and "R$ 10,99" in texto and "R$ 12,39" in texto
    assert "+13%" in texto


def test_estoque_e_busca(abrir_sessao):
    assert "REFRIGERANTE COCA COLA 2 L (bebidas): 2" in _ferramenta(abrir_sessao, "estoque_atual").invoke({})
    assert "id " in _ferramenta(abrir_sessao, "buscar_produtos").invoke({"texto": "coca"})


class ModeloFalso:
    """Faz o papel do LLM: devolve respostas prontas e registra o que recebeu."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.recebido = []

    def bind_tools(self, ferramentas):
        self.ferramentas = [f.name for f in ferramentas]
        return self

    def invoke(self, mensagens):
        self.recebido.append(mensagens)
        return self.respostas.pop(0)


def test_grafo_chama_ferramenta_e_responde_com_o_resultado(abrir_sessao):
    modelo = ModeloFalso([
        AIMessage(content="", tool_calls=[{
            "name": "gasto_total", "id": "c1", "type": "tool_call",
            "args": {"data_inicio": "2026-10-01", "data_fim": "2026-10-31", "categoria": "carnes"}}]),
        AIMessage(content="<think>somando</think>Em outubro você gastou R$ 15,35 com carnes."),
    ])
    agente = criar_agente(modelo, abrir_sessao, hoje=date(2026, 11, 10))
    resposta = responder(agente, "quanto gastei com carne em outubro?")

    assert resposta.texto == "Em outubro você gastou R$ 15,35 com carnes."  # <think> removido
    assert resposta.ferramentas == [{"nome": "gasto_total", "argumentos": {
        "data_inicio": "2026-10-01", "data_fim": "2026-10-31", "categoria": "carnes"}}]
    # na 2ª rodada o modelo recebeu o resultado REAL da ferramenta, vindo do banco
    resultado_ferramenta = modelo.recebido[1][-1].content
    assert "R$ 15,35" in resultado_ferramenta
    # e as instruções com a data de hoje
    assert "2026-11-10" in modelo.recebido[0][0].content
    assert "estoque_atual" in modelo.ferramentas


def test_erro_de_parametro_volta_para_o_modelo_corrigir(abrir_sessao):
    chamada = lambda categoria, id_: AIMessage(content="", tool_calls=[{
        "name": "gasto_total", "id": id_, "type": "tool_call",
        "args": {"data_inicio": "2026-10-01", "data_fim": "2026-10-31", "categoria": categoria}}])
    modelo = ModeloFalso([chamada("carne", "c1"), chamada("carnes", "c2"),
                          AIMessage(content="R$ 15,35 com carnes em outubro.")])
    resposta = responder(criar_agente(modelo, abrir_sessao), "carne em outubro?")
    assert resposta.texto == "R$ 15,35 com carnes em outubro."
    assert "Categoria inválida" in modelo.recebido[1][-1].content  # o modelo viu o erro


def test_api_perguntas(monkeypatch, abrir_sessao):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import compras.api.rotas_perguntas as rotas
    from compras.api.app import app

    modelo = ModeloFalso([AIMessage(content="Você não tem compras de pet registradas.")])
    monkeypatch.setattr(rotas, "obter_agente", lambda provedor=None: criar_agente(modelo, abrir_sessao))
    r = TestClient(app).post("/perguntas", json={
        "pergunta": "gastei com pet?",
        "historico": [{"papel": "usuario", "texto": "oi"}, {"papel": "assistente", "texto": "olá!"}]})
    assert r.status_code == 200, r.text
    assert r.json() == {"resposta": "Você não tem compras de pet registradas.", "ferramentas": []}
    assert [m.content for m in modelo.recebido[0][1:]] == ["oi", "olá!", "gastei com pet?"]


def test_busca_aceita_hifen_e_variacoes(abrir_sessao):
    buscar = _ferramenta(abrir_sessao, "buscar_produtos")
    for texto in ("coca-cola", "Coca Cola", "COCA", "refri coca"):
        assert "REFRIGERANTE COCA COLA 2 L" in buscar.invoke({"texto": texto}), texto
    assert "nunca foi comprado" in buscar.invoke({"texto": "guaraná"})


def test_trava_valor_inventado_sem_ferramenta(abrir_sessao):
    from compras.ia.agente import SEM_DADO

    modelo = ModeloFalso([AIMessage(content="A Coca-Cola no Carrefour custa R$ 9,99.")])
    resposta = responder(criar_agente(modelo, abrir_sessao), "coca no carrefour?")
    assert resposta.texto == SEM_DADO and resposta.ferramentas == []


def test_instrucoes_limitam_o_assunto():
    from compras.ia.agente import RECUSA, instrucoes

    texto = instrucoes(date(2026, 11, 10))
    assert RECUSA in texto and "SÓ responde sobre as compras" in texto


def test_estoque_por_categoria_e_por_nome(abrir_sessao):
    estoque = _ferramenta(abrir_sessao, "estoque_atual")
    bebidas = estoque.invoke({"categoria": "bebidas"})
    assert "COCA COLA" in bebidas and "MUSCULO" not in bebidas  # "tem bebida?"
    assert "MUSCULO BOVINO" in estoque.invoke({"categoria": "carnes"})
    assert "COCA COLA" in estoque.invoke({"nome": "coca-cola"})
    assert estoque.invoke({"categoria": "limpeza"}) == "Nada no estoque de limpeza."
