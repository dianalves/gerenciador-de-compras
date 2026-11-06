"""Contrato comum a todos os provedores de visão (Claude, Gemini, OpenAI...)."""
from abc import ABC, abstractmethod


class ProvedorVisao(ABC):
    nome: str = "base"

    @abstractmethod
    def analisar_imagem(self, imagem: bytes, tipo_mime: str, prompt: str) -> str:
        """Envia imagem + prompt e devolve o texto da resposta do modelo."""

    @abstractmethod
    def analisar_texto(self, prompt: str) -> str:
        """Envia só texto (ex.: HTML da SEFAZ) e devolve a resposta do modelo."""
