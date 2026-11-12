"""Agente de perguntas sobre as compras, montado como um grafo do LangGraph.

    START -> [pensar] --(pediu ferramenta?)--> [ferramentas] --+
                 ^                                             |
                 +---------------------------------------------+
             (resposta pronta) -> END

"pensar": o modelo lê a conversa e decide se responde ou se chama uma ferramenta.
"ferramentas": executa as consultas pedidas e devolve os resultados ao modelo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session

from compras.ia.ferramentas import criar_ferramentas

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]

RECUSA = ("Só consigo ajudar com as suas compras de mercado: gastos, produtos, preços, "
          "mercados e o que tem em casa.")
SEM_DADO = "Não encontrei esse dado nas suas compras registradas."

LIMITE_PASSOS = 12  # cada ida e volta pensar->ferramentas conta 2; evita laço infinito


def instrucoes(hoje: Optional[date] = None) -> str:
    hoje = hoje or date.today()
    return f"""Você é o assistente de compras de mercado de uma casa. Responda em português do Brasil,
de forma curta e direta.

Hoje é {hoje:%Y-%m-%d} ({hoje.day} de {MESES[hoje.month - 1]} de {hoje.year}).

Você SÓ responde sobre as compras de mercado desta casa: gastos, produtos, preços, mercados
e estoque. Para qualquer outro assunto (curiosidades, receitas, notícias, conversa), responda
exatamente: "{RECUSA}"

Regras:
- Qualquer número (valores, quantidades, preços, datas de compra) TEM que vir das ferramentas.
  Nunca invente nem estime. Se a ferramenta não trouxer o dado, diga que não há registro.
- Converta períodos em datas AAAA-MM-DD. "outubro" sem ano = outubro de {hoje.year} se já
  passou, senão do ano anterior. "este mês" = de {hoje:%Y-%m}-01 até hoje.
- Para perguntas sobre um produto específico, use primeiro buscar_produtos para achar o id.
  Se buscar_produtos não encontrar nada, o produto NUNCA foi comprado: diga isso.
- Se a pergunta citar um mercado, confira no historico_preco se houve compra nele. Se não houve,
  diga que não há compra desse produto nesse mercado e cite em quais mercados ele foi comprado.
- Categorias existentes: mercearia, carnes, bebidas, hortifruti, frios_laticinios, padaria,
  limpeza, higiene, pet, congelados. ("carne" = carnes; "frutas/verduras" = hortifruti.)
  Perguntas por TIPO de produto ("tem bebida?", "quanto gastei com limpeza?") usam o
  parâmetro categoria, não o nome.
- Valores em reais no formato R$ 1.234,56.
"""


@dataclass
class Resposta:
    texto: str
    ferramentas: list[dict] = field(default_factory=list)  # [{nome, argumentos}]


def _sem_pensamento(texto: str) -> str:
    """Alguns modelos (ex.: Qwen3) escrevem o raciocínio entre <think>...</think>."""
    return re.sub(r"<think>.*?</think>", "", texto or "", flags=re.S).strip()


def criar_agente(modelo_chat, abrir_sessao: Callable[[], Session], hoje: Optional[date] = None):
    """Monta e compila o grafo. `modelo_chat` é um modelo do LangChain com suporte a tools."""
    ferramentas = criar_ferramentas(abrir_sessao)
    modelo = modelo_chat.bind_tools(ferramentas)
    sistema = SystemMessage(instrucoes(hoje))

    def pensar(estado: MessagesState) -> dict:
        return {"messages": [modelo.invoke([sistema, *estado["messages"]])]}

    grafo = StateGraph(MessagesState)
    grafo.add_node("pensar", pensar)
    # Parâmetro inválido (categoria inexistente, data errada) volta ao modelo como mensagem
    # de erro, para ele corrigir e tentar de novo, em vez de derrubar a pergunta.
    grafo.add_node("ferramentas", ToolNode(ferramentas, handle_tool_errors=(ValueError,)))
    grafo.add_edge(START, "pensar")
    # tools_condition: se a última mensagem pede ferramenta -> "tools"; senão -> END
    grafo.add_conditional_edges("pensar", tools_condition, {"tools": "ferramentas", END: END})
    grafo.add_edge("ferramentas", "pensar")
    return grafo.compile()


def responder(agente, pergunta: str, historico: Optional[list[BaseMessage]] = None) -> Resposta:
    mensagens = [*(historico or []), HumanMessage(pergunta)]
    estado = agente.invoke({"messages": mensagens}, config={"recursion_limit": LIMITE_PASSOS})
    novas = estado["messages"][len(mensagens):]

    usadas = [{"nome": chamada["name"], "argumentos": chamada["args"]}
              for msg in novas if isinstance(msg, AIMessage) for chamada in msg.tool_calls]
    final = next((m for m in reversed(novas) if isinstance(m, AIMessage) and not m.tool_calls), None)
    texto = _sem_pensamento(final.content if final else "")
    if not usadas and _cita_valor(texto):
        texto = SEM_DADO  # citou dinheiro sem consultar nada: só pode ter inventado
    return Resposta(texto or "Não consegui chegar a uma resposta.", usadas)


def _cita_valor(texto: str) -> bool:
    return bool(re.search(r"R\$\s*\d", texto))


def modelo_padrao(provedor: Optional[str] = None):
    """Modelo de chat a partir da configuração (.env). LM Studio é o padrão (local, grátis)."""
    from langchain_openai import ChatOpenAI

    from compras.config import obter_configuracao

    cfg = obter_configuracao()
    nome = (provedor or cfg.provedor_visao).lower()
    if nome == "lmstudio":
        return ChatOpenAI(base_url=cfg.lmstudio_url, api_key="lm-studio",
                          model=cfg.modelo_lmstudio, temperature=0, timeout=120)
    if nome == "openai":
        return ChatOpenAI(model=cfg.modelo_openai, api_key=cfg.openai_api_key or None,
                          temperature=0, timeout=60)
    raise ValueError(f"Perguntas com IA ainda não configuradas para '{nome}'. "
                     "Use lmstudio ou openai.")
