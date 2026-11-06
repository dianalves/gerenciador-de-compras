"""Atribui categorias a itens que vieram sem (ex.: importados da SEFAZ). Só texto."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from compras.nota.esquema import CATEGORIAS, ItemNota
from compras.visao.base import ProvedorVisao

PROMPT_CATEGORIAS = """Classifique cada produto de supermercado em UMA categoria entre:
{categorias}
(carnes inclui peixes, frango e suínos; frutas, verduras e legumes são hortifruti;
frios_laticinios é leite, queijo, iogurte, manteiga, presunto, cream cheese).

Produtos:
{produtos}

Responda APENAS com JSON: {{"categorias": {{"1": "mercearia", "2": "carnes", ...}}}}
"""


# Classificação por palavras-chave: funciona sem modelo nenhum (ordem importa).
PALAVRAS_CHAVE = {
    # Primeiro: doces/snacks ("CHOC... AO LEITE" não é laticínio) e básicos
    # de mercearia, para não dependerem do modelo.
    "mercearia": [
        "CHOC", "BISC", "BALA", "WAFER", "BOMBOM", "PIRULITO", "CHICLE", "ARROZ",
        "FEIJAO", "ACUCAR", "OLEO", "AZEITE", "AZEIT.", "FARINHA", "FERMENTO",
        "MIST.BOLO", "MISTURA BOLO", "MOLHO", "CAFE", "CAPS.CAFE", "MILHO", "PIPOCA",
        "MACARRAO", "MASSA", "CAPELETTI", "NOODLES", "OVO", "SAL ", "ALCAPARRA",
        "SALG.", "SALGAD", "PRINGLES", "TEMPERO", "EXTRATO", "MAIONESE", "KETCHUP",
        "MOSTARDA", "VINAGRE", "ACHOC",
    ],
    "pet": [
        "RACAO", "PET ", "AREIA GATO", "PETISCO",
    ],
    "limpeza": [
        "LIMPA", "ESP.D", "S.BRITE", "SCOTCH", "DETERG", "SABAO", "AMACIANTE", "DESINF",
        "AGUA SANIT", "ALVEJ", "ESPONJA", "LIMPADOR", "MULTIUSO", "VEJA ", "YPE",
        "PAPEL TOALHA", "SACO LIXO",
    ],
    "higiene": [
        "SABO.", "ESC.D", "ORAL B", "ESCOVA", "SHAMPOO", "CONDIC", "SABONETE",
        "CREME DENT", "ESCOVA DENT", "DESOD", "PAPEL HIG", "ABSORV", "FIO DENT",
        "FRALDA",
    ],
    "bebidas": [
        "BBS ", "BB ", "MUPY", "AGUARDENTE", "CACHACA", "VODKA", "WHISK", "GIN ",
        "H2OH", "REFR", "REFRIG", "SUCO", "CERVEJA", "CERV ", "AGUA MIN", "AGUA ",
        "VINHO", "ENERGETICO", "BEB.", "BEBIDA", "CHA ", "ISOTON", "COCA", "PEPSI",
        "GUARANA",
    ],
    "congelados": [
        "CONGEL", "SORVETE", "PIZZA", "LASANHA", "NUGGETS", "HAMBURG",
    ],
    "frios_laticinios": [
        "LEITE", "QUEIJO", "MUSSARELA", "MUSS ", "IOGURTE", "MANTEIGA", "REQUEIJ",
        "CREAM CHEESE", "PRESUNTO", "MORTADELA", "SALAME", "C.LEITE", "CREME LEITE",
        "MARGARINA", "PETIT ",
    ],
    "carnes": [
        "SUIN", "BISTECA", "CARNE", "BOVIN", "FRANGO", "COXA", "SOBRE COXA", "PEITO",
        "ASA ", "SUINO", "PERNIL", "LOMBO", "COSTELA", "LINGUICA", "SALMAO", "TILAPIA",
        "PEIXE", "CAMARAO", "PATINHO", "ACEM", "ALCATRA", "PICANHA", "FILE ", "MIGN",
        "BACON",
    ],
    "padaria": [
        "PAO ", "BISNAGA", "BOLO PRONTO", "TORRADA", "BAGUETE",
    ],
    "hortifruti": [
        "FLV ", "MEXERICA", "TANGERINA", "ABOBORA", "TOMATE", "CEBOLA", "ALHO",
        "BATATA KG", "CENOURA", "ALFACE", "RUCULA", "BANANA", "MACA ", "UVA", "LARANJA",
        "CAJU", "LIMAO", "ABACAXI", "MAMAO", "MELAO", "MELANCIA", "MORANGO", "MANGA",
        "PIMENTAO", "ABOBRINHA", "BROCOLIS", "COUVE", "CHEIRO", "SALSA", "MANDIOCA",
        "PEPINO", "ABACATE", "KIWI",
    ],
}


def _sem_acento(texto: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texto.upper())
                   if unicodedata.category(c) != "Mn")


def _padrao(palavra: str) -> re.Pattern:
    """Casa só no INÍCIO de uma palavra ("VEJA" não casa em "CERVEJA").
    Palavra terminada em espaço exige a palavra inteira ("MACA " não casa em "MACARRAO")."""
    inteira = palavra.endswith(" ")
    corpo = re.escape(palavra.strip())
    return re.compile(r"(?<![A-Z0-9])" + corpo + (r"(?![A-Z0-9])" if inteira else ""))


_PADROES = {cat: [_padrao(p) for p in palavras] for cat, palavras in PALAVRAS_CHAVE.items()}


CATEGORIA_PADRAO = "mercearia"  # no supermercado, o que sobra quase sempre é mercearia


def categoria_por_palavras_ou_nada(descricao: str) -> str | None:
    """Categoria pela lista de palavras-chave, ou None se nenhuma palavra combinou."""
    texto = _sem_acento(descricao)
    for categoria, padroes in _PADROES.items():
        if any(p.search(texto) for p in padroes):
            return categoria
    return None


def categoria_por_palavras(descricao: str) -> str:
    return categoria_por_palavras_ou_nada(descricao) or CATEGORIA_PADRAO


def categorizar_por_palavras(itens: list[ItemNota]) -> list[ItemNota]:
    return [i.model_copy(update={"categoria": categoria_por_palavras(i.descricao)})
            for i in itens]


TAMANHO_LOTE = 40  # modelo local se perde com listas muito longas


@dataclass
class ResultadoCategorias:
    itens: list[ItemNota]
    # por item: "palavras" (regra combinou), "modelo" (LM decidiu) ou "padrao" (ninguém soube)
    origens: list[str] = field(default_factory=list)
    erro_modelo: str | None = None  # motivo, se o modelo falhou por inteiro

    def contar(self, origem: str) -> int:
        return self.origens.count(origem)

    def resumo(self) -> str:
        partes = [f"{self.contar('palavras')} por palavras-chave"]
        if self.contar("modelo"):
            partes.append(f"{self.contar('modelo')} pelo modelo")
        if self.contar("padrao"):
            partes.append(f"{self.contar('padrao')} no padrão ({CATEGORIA_PADRAO})")
        texto = "Categorias: " + ", ".join(partes) + "."
        if self.erro_modelo:
            texto += f" Modelo indisponível ({self.erro_modelo})."
        return texto


def _consultar_modelo(itens: list[ItemNota], modelo: ProvedorVisao) -> dict[str, str]:
    from compras.nota.leitor import _extrair_json

    produtos = "\n".join(f"{n}: {i.descricao}" for n, i in enumerate(itens, start=1))
    resposta = modelo.analisar_texto(
        PROMPT_CATEGORIAS.format(categorias=", ".join(CATEGORIAS), produtos=produtos))
    mapa = _extrair_json(resposta).get("categorias", {})
    return {str(k): str(v) for k, v in mapa.items()} if isinstance(mapa, dict) else {}


def categorizar_detalhado(itens: list[ItemNota],
                          modelo: ProvedorVisao | None) -> ResultadoCategorias:
    """Palavras-chave primeiro (confiáveis quando combinam). O modelo só decide os
    produtos que nenhuma palavra-chave reconheceu; se ele falhar, vai o padrão."""
    categorias: list[str | None] = [categoria_por_palavras_ou_nada(i.descricao) for i in itens]
    origens = ["palavras" if c else "padrao" for c in categorias]
    pendentes = [k for k, c in enumerate(categorias) if c is None]

    erro_modelo = None
    if modelo is not None and pendentes:
        for inicio in range(0, len(pendentes), TAMANHO_LOTE):
            lote = pendentes[inicio:inicio + TAMANHO_LOTE]
            try:
                mapa = _consultar_modelo([itens[k] for k in lote], modelo)
            except Exception as erro:  # LM Studio desligado, sem internet, JSON quebrado...
                erro_modelo = type(erro).__name__
                break
            for n, k in enumerate(lote, start=1):
                bruto = mapa.get(str(n), "").strip().lower().replace(" ", "_")
                if bruto in CATEGORIAS and bruto != "outros":
                    categorias[k], origens[k] = bruto, "modelo"

    resultado = [i.model_copy(update={"categoria": c or CATEGORIA_PADRAO})
                 for i, c in zip(itens, categorias)]
    return ResultadoCategorias(resultado, origens, erro_modelo)


def categorizar(itens: list[ItemNota], modelo: ProvedorVisao | None) -> list[ItemNota]:
    return categorizar_detalhado(itens, modelo).itens
