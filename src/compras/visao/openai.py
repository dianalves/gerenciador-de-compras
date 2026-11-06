import base64

from compras.visao.base import ProvedorVisao


class ProvedorOpenAI(ProvedorVisao):
    nome = "openai"

    def __init__(self, api_key: str, modelo: str):
        from openai import OpenAI

        self.cliente = OpenAI(api_key=api_key or None)
        self.modelo = modelo

    def analisar_imagem(self, imagem: bytes, tipo_mime: str, prompt: str) -> str:
        url = f"data:{tipo_mime};base64,{base64.b64encode(imagem).decode()}"
        resposta = self.cliente.chat.completions.create(
            model=self.modelo,
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": url}},
                ],
            }],
        )
        return resposta.choices[0].message.content or ""

    def analisar_texto(self, prompt: str) -> str:
        resposta = self.cliente.chat.completions.create(
            model=self.modelo, response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        return resposta.choices[0].message.content or ""
