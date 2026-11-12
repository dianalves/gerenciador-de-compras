"""Perguntas em linguagem natural sobre as compras (agente LangGraph)."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from compras.api.esquemas import EntradaPergunta, RespostaPergunta

roteador = APIRouter(prefix="/perguntas", tags=["perguntas (IA)"])


def obter_agente(provedor: Optional[str] = None):
    """Separado para os testes poderem trocar o modelo por um falso."""
    from compras.banco.conexao import Sessao
    from compras.ia.agente import criar_agente, modelo_padrao

    return criar_agente(modelo_padrao(provedor), Sessao)


@roteador.post("", response_model=RespostaPergunta,
               summary='Ex.: "quanto gastei com carne em outubro?"')
def perguntar(entrada: EntradaPergunta,
              provedor: Optional[str] = Query(None, description="lmstudio | openai")):
    from langchain_core.messages import AIMessage, HumanMessage

    from compras.ia.agente import responder

    historico = [HumanMessage(m.texto) if m.papel == "usuario" else AIMessage(m.texto)
                 for m in entrada.historico[-10:]]  # últimas 10 bastam de contexto
    try:
        agente = obter_agente(provedor)
        resposta = responder(agente, entrada.pergunta, historico)
    except ValueError as erro:
        raise HTTPException(422, str(erro))
    except Exception as erro:  # modelo fora do ar, tempo esgotado...
        nome = type(erro).__name__
        if "Connection" in nome or "Timeout" in nome:
            raise HTTPException(503, "Não consegui falar com o modelo. O LM Studio está com o "
                                     "servidor ligado e o modelo carregado?")
        raise HTTPException(500, f"Erro ao responder ({nome}): {erro}")
    return RespostaPergunta(resposta=resposta.texto, ferramentas=resposta.ferramentas)
