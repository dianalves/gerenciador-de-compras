import base64

from compras.visao.base import ProvedorVisao


class ProvedorClaude(ProvedorVisao):
    nome = "claude"

    def __init__(self, api_key: str, modelo: str):
        import anthropic  # import tardio: só exige o SDK de quem for usado

        self.cliente = anthropic.Anthropic(api_key=api_key or None)
        self.modelo = modelo

    def analisar_imagem(self, imagem: bytes, tipo_mime: str, prompt: str) -> str:
        resposta = self.cliente.messages.create(
            model=self.modelo,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": tipo_mime,
                        "data": base64.b64encode(imagem).decode(),
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return "".join(b.text for b in resposta.content if b.type == "text")

    def analisar_texto(self, prompt: str) -> str:
        resposta = self.cliente.messages.create(
            model=self.modelo, max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resposta.content if b.type == "text")
