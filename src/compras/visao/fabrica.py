"""Escolhe o provedor de visão a partir da configuração (PROVEDOR_VISAO)."""
from __future__ import annotations

from compras.config import obter_configuracao
from compras.visao.base import ProvedorVisao


def obter_provedor(nome: str | None = None) -> ProvedorVisao:
    cfg = obter_configuracao()
    nome = (nome or cfg.provedor_visao).lower()

    if nome == "claude":
        from compras.visao.claude import ProvedorClaude
        return ProvedorClaude(cfg.anthropic_api_key, cfg.modelo_claude)
    if nome == "gemini":
        from compras.visao.gemini import ProvedorGemini
        return ProvedorGemini(cfg.google_api_key, cfg.modelo_gemini)
    if nome == "openai":
        from compras.visao.openai import ProvedorOpenAI
        return ProvedorOpenAI(cfg.openai_api_key, cfg.modelo_openai)

    if nome == "lmstudio":
        from compras.visao.lmstudio import ProvedorLMStudio
        return ProvedorLMStudio(cfg.lmstudio_url, cfg.modelo_lmstudio)

    raise ValueError(
        f"Provedor de visão desconhecido: {nome!r} (use claude, gemini, openai ou lmstudio)"
    )
