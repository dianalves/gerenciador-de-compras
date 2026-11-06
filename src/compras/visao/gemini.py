from compras.visao.base import ProvedorVisao


class ProvedorGemini(ProvedorVisao):
    nome = "gemini"

    def __init__(self, api_key: str, modelo: str):
        from google import genai

        self.cliente = genai.Client(api_key=api_key or None)
        self.modelo = modelo

    def analisar_imagem(self, imagem: bytes, tipo_mime: str, prompt: str) -> str:
        from google.genai import types

        resposta = self.cliente.models.generate_content(
            model=self.modelo,
            contents=[types.Part.from_bytes(data=imagem, mime_type=tipo_mime), prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return resposta.text

    def analisar_texto(self, prompt: str) -> str:
        from google.genai import types

        resposta = self.cliente.models.generate_content(
            model=self.modelo, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return resposta.text
