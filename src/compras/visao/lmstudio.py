"""Modelo local rodando no LM Studio (servidor compatível com a API da OpenAI)."""
import base64

from compras.visao.base import ProvedorVisao


class ProvedorLMStudio(ProvedorVisao):
    nome = "lmstudio"

    def __init__(self, url: str, modelo: str):
        from openai import OpenAI

        # O LM Studio não exige chave; qualquer texto serve.
        self.cliente = OpenAI(base_url=url, api_key="lm-studio")
        self.modelo = modelo

    def analisar_imagem(self, imagem: bytes, tipo_mime: str, prompt: str) -> str:
        url = f"data:{tipo_mime};base64,{base64.b64encode(imagem).decode()}"
        resposta = self.cliente.chat.completions.create(
            model=self.modelo,
            temperature=0,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": url}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return resposta.choices[0].message.content or ""

    def analisar_texto(self, prompt: str) -> str:
        resposta = self.cliente.chat.completions.create(
            model=self.modelo, temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return resposta.choices[0].message.content or ""
