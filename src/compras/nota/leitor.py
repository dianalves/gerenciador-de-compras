"""Lê a foto de uma nota usando o provedor de visão configurado.

Estratégia:
1. trata a imagem (contraste/nitidez) e lê a nota inteira;
2. se a soma não bater, lê o cupom em fatias ampliadas e concilia os itens;
3. se ainda não bater, pede ao modelo uma revisão mostrando a diferença.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from compras.nota.esquema import ItemNota, NotaFiscal
from compras.nota.imagem import fatiar, preparar_imagem
from compras.nota.prompt import PROMPT_CORRECAO, PROMPT_FATIA, PROMPT_LEITURA
from compras.visao.base import ProvedorVisao
from compras.visao.fabrica import obter_provedor

Progresso = Optional[Callable[[str], None]]


def _extrair_json(texto: str) -> dict:
    texto = texto.strip()
    bloco = re.search(r"```(?:json)?\s*(.*?)```", texto, re.S)
    if bloco:
        texto = bloco.group(1)
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError(f"Resposta sem JSON: {texto[:200]}")
    return json.loads(texto[inicio : fim + 1])


def _ler_itens_em_fatias(modelo: ProvedorVisao, imagem: bytes,
                         avisar: Progresso = None) -> dict[int, ItemNota]:
    """Lê cada fatia e devolve os itens encontrados, indexados pelo número do item."""
    itens: dict[int, ItemNota] = {}
    fatias = fatiar(imagem)
    for n, fatia in enumerate(fatias, start=1):
        if avisar:
            avisar(f"Conferindo com zoom: fatia {n}/{len(fatias)}...")
        try:
            dados = _extrair_json(modelo.analisar_imagem(fatia, "image/jpeg", PROMPT_FATIA))
        except (ValueError, json.JSONDecodeError):
            continue
        for bruto in dados.get("itens", []):
            try:
                item = ItemNota.model_validate(bruto)
            except ValidationError:
                continue
            if item.numero_item and item.confere():
                itens.setdefault(item.numero_item, item)
    return itens


@dataclass
class Duvida:
    numero_item: int
    descricao: str
    leitura_inteira: Optional[Decimal]
    leitura_zoom: Decimal


MAX_COMBINACOES = 4096


def conciliar(nota: NotaFiscal, itens_fatias: dict[int, ItemNota]) -> tuple[NotaFiscal, list[Duvida]]:
    """Aplica trocas vindas das fatias SÓ se alguma combinação fechar a conta exatamente.

    Se nenhuma combinação fechar, mantém a leitura original e devolve as divergências
    como dúvidas para o usuário conferir (evita um erro "compensar" outro).
    """
    por_numero = {i.numero_item: i for i in nota.itens if i.numero_item}
    divergentes = [
        f for n, f in sorted(itens_fatias.items())
        if n not in por_numero or por_numero[n].valor_total != f.valor_total
    ]
    duvidas = [
        Duvida(f.numero_item, f.descricao,
               por_numero[f.numero_item].valor_total if f.numero_item in por_numero else None,
               f.valor_total)
        for f in divergentes
    ]
    if not divergentes or 2 ** len(divergentes) > MAX_COMBINACOES:
        return nota, duvidas

    def aplicar(trocas) -> NotaFiscal:
        novos = {i.numero_item or -k: i for k, i in enumerate(nota.itens, start=1)}
        for f in trocas:
            novos[f.numero_item] = f
        return nota.model_copy(update={"itens": sorted(novos.values(),
                                                        key=lambda i: i.numero_item or 0)})

    for tamanho in range(1, len(divergentes) + 1):  # prefere o menor número de trocas
        for trocas in combinations(divergentes, tamanho):
            candidata = aplicar(trocas)
            if candidata.confere_total():
                trocados = {f.numero_item for f in trocas}
                return candidata, [d for d in duvidas if d.numero_item not in trocados]
    return nota, duvidas


def ler_nota(caminho_imagem: str | Path, provedor: str | None = None,
             tentativas_correcao: int = 1, usar_fatias: bool = True,
             ao_progredir: Progresso = None) -> NotaFiscal:
    avisar = ao_progredir or (lambda _msg: None)
    imagem = preparar_imagem(Path(caminho_imagem).read_bytes())
    modelo = obter_provedor(provedor)

    avisar("Lendo a nota inteira...")
    resposta = modelo.analisar_imagem(imagem, "image/jpeg", PROMPT_LEITURA)
    nota = NotaFiscal.model_validate(_extrair_json(resposta))

    duvidas: list[Duvida] = []
    if not nota.confere_total() and usar_fatias:
        nota, duvidas = conciliar(nota, _ler_itens_em_fatias(modelo, imagem, avisar))

    for _ in range(tentativas_correcao):
        if nota.confere_total():
            break
        avisar("Pedindo revisão ao modelo...")
        suspeitos = nota.itens_inconsistentes()
        texto_suspeitos = (
            "Itens em que quantidade x valor_unitario não dá valor_total: "
            + "; ".join(i.descricao for i in suspeitos) + "."
        ) if suspeitos else ""
        prompt = PROMPT_CORRECAO.format(
            soma=nota.soma_itens() - nota.desconto,
            total=nota.valor_total,
            diferenca=nota.diferenca(),
            suspeitos=texto_suspeitos,
            json_anterior=nota.model_dump_json(),
        )
        try:
            revisada = NotaFiscal.model_validate(
                _extrair_json(modelo.analisar_imagem(imagem, "image/jpeg", prompt)))
        except (ValueError, ValidationError, json.JSONDecodeError):
            break
        if revisada.confere_total():  # só aceita revisão que feche a conta
            nota, duvidas = revisada, []

    nota._duvidas = duvidas
    return nota
