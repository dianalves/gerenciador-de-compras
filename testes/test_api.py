"""Testes da API com um banco SQLite em memória (não mexe no PostgreSQL)."""
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from compras.api.app import app  # noqa: E402
from compras.api.dependencias import obter_sessao  # noqa: E402
from compras.banco.modelos import Base  # noqa: E402

HTML = """<html><body>
<div id="u20" class="txtTopo">SUPERMERCADO TESTE LTDA</div>
<div class="text">CNPJ: 12.345.678/0001-99</div>
<table id="tabResult">
<tr><td><span class="txtTit">CREAM CHEESE POLENGHI 30</span><span class="RCod">(Código: 79625 )</span>
<span class="Rqtd"><strong>Qtde.:</strong>1</span><span class="RUN"><strong>UN: </strong>UN</span>
<span class="RvlUnit"><strong>Vl. Unit.:</strong> 18,99</span></td>
<td class="txtTit noWrap">Vl. Total<br><span class="valor">18,99</span></td></tr>
<tr><td><span class="txtTit">FILE SALMAO FRESCO C/P</span><span class="RCod">(Código: 49649 )</span>
<span class="Rqtd"><strong>Qtde.:</strong>0,824</span><span class="RUN"><strong>UN: </strong>KG</span>
<span class="RvlUnit"><strong>Vl. Unit.:</strong> 109,9</span></td>
<td class="txtTit noWrap">Vl. Total<br><span class="valor">90,56</span></td></tr>
</table>
<div id="totalNota"><div id="linhaTotal" class="linhaShade"><label>Valor a pagar R$:</label>
<span class="totalNumb txtMax">109,55</span></div></div>
<div><strong>Emissão: </strong>01/11/2026 10:30:00 - Via Consumidor</div>
</body></html>"""
LINK = ("https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx"
        "?p=35261112345678000199650010000012341000123456|2|1|1|abc")


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False},
                          poolclass=StaticPool)
    Base.metadata.create_all(motor)
    SessaoTeste = sessionmaker(bind=motor, expire_on_commit=False)

    def sessao_de_teste():
        with SessaoTeste() as sessao:
            yield sessao

    import compras.api.rotas_notas as rotas_notas
    import compras.sefaz.importar as importar
    monkeypatch.setattr(importar, "PASTA_HTML", tmp_path / "sefaz")
    monkeypatch.setattr(rotas_notas, "PASTA_FOTOS", tmp_path / "fotos")

    app.dependency_overrides[obter_sessao] = sessao_de_teste
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"api": True, "banco": True}


def test_importa_pela_sefaz_e_nao_duplica(cliente, tmp_path):
    corpo = {"html": HTML, "link": LINK}
    r = cliente.post("/notas/sefaz?usar_modelo=false", json=corpo)
    assert r.status_code == 200, r.text
    dados = r.json()
    assert dados["salva"] and dados["confere_total"] and dados["compra_id"] == 1
    assert [i["categoria"] for i in dados["nota"]["itens"]] == ["frios_laticinios", "carnes"]
    assert (tmp_path / "sefaz" / "35261112345678000199650010000012341000123456.html").exists()

    assert cliente.post("/notas/sefaz?usar_modelo=false", json=corpo).status_code == 409


def test_previa_nao_salva(cliente):
    r = cliente.post("/notas/sefaz?usar_modelo=false&salvar=false", json={"html": HTML})
    assert r.status_code == 200 and r.json()["salva"] is False
    assert cliente.get("/compras").json() == []


def test_pagina_irreconhecivel_da_422(cliente):
    r = cliente.post("/notas/sefaz?usar_modelo=false", json={"html": "<html>captcha</html>"})
    assert r.status_code == 422


def test_compras_e_relatorios(cliente):
    cliente.post("/notas/sefaz?usar_modelo=false", json={"html": HTML, "link": LINK})

    compras = cliente.get("/compras").json()
    assert len(compras) == 1 and compras[0]["quantidade_itens"] == 2
    detalhe = cliente.get(f"/compras/{compras[0]['id']}").json()
    assert Decimal(detalhe["valor_total"]) == Decimal("109.55")

    categorias = cliente.get("/relatorios/categorias?ano=2026&mes=11").json()
    assert {c["categoria"] for c in categorias} == {"carnes", "frios_laticinios"}
    assert round(sum(c["percentual"] for c in categorias)) == 100

    produtos = cliente.get("/relatorios/produtos").json()
    assert produtos[0]["descricao"] == "FILE SALMAO FRESCO C/P"

    assert cliente.delete(f"/compras/{compras[0]['id']}").status_code == 204
    assert cliente.get("/compras").json() == []


def test_foto_com_conta_errada_so_salva_se_forcar(cliente, monkeypatch):
    from compras.nota.esquema import ItemNota, NotaFiscal

    def ler_nota_falso(caminho, provedor=None):
        return NotaFiscal(estabelecimento_nome="X", valor_total=Decimal("20.00"),
                          itens=[ItemNota(descricao="CREAM CHEESE", quantidade=1,
                                          valor_unitario=Decimal("16.99"),
                                          valor_total=Decimal("16.99"))])

    import compras.nota.leitor as leitor
    monkeypatch.setattr(leitor, "ler_nota", ler_nota_falso)

    arquivo = {"foto": ("cupom.jpg", b"falso", "image/jpeg")}
    r = cliente.post("/notas/foto", files=arquivo).json()
    assert r["salva"] is False and "forcar=true" in r["mensagem"]

    r = cliente.post("/notas/foto?forcar=true", files=arquivo).json()
    assert r["salva"] is True
