import json

from compras.nota.esquema import CATEGORIAS, NotaFiscal

PROMPT_LEITURA = f"""Você recebe a foto de um cupom fiscal brasileiro (NFC-e) de supermercado.
Extraia os dados e responda APENAS com um JSON válido, sem texto antes ou depois,
seguindo exatamente este JSON Schema:

{json.dumps(NotaFiscal.model_json_schema(), ensure_ascii=False)}

Regras:
- Use ponto como separador decimal (ex.: 12.90).
- CNPJ e chave de acesso só com dígitos.
- data_emissao no formato ISO 8601 (AAAA-MM-DDTHH:MM:SS).
- categoria deve ser uma de: {", ".join(CATEGORIAS)}.
- Se um campo não estiver legível, use null.
- Cada linha do cupom começa com o número do item (coluna "#": 001, 002...) e depois
  o código do produto. Coloque o número em numero_item e o código em codigo,
  SEPARADOS. Ex.: "003 49649 FILE SALMAO" -> numero_item=3, codigo="49649".
- Preencha quantidade_itens com o "QTD. TOTAL DE ITENS" do rodapé, se houver.
- Categorias: carnes inclui peixes, frango e suínos; frutas, verduras e legumes são
  hortifruti; frios_laticinios é leite, queijo, iogurte, manteiga, presunto.
- ITENS VENDIDOS POR PESO (carnes, peixes, frios, hortifruti): o cupom mostra o peso
  e o preço do quilo, por exemplo "0,824 KG x 109,90 = 90,56". Nesse caso
  quantidade=0.824, unidade="KG", valor_unitario=109.90 e valor_total=90.56.
  NUNCA use o preço do quilo como valor_total, nem quantidade 1 para item pesado.
- DESCONTO x ECONOMIA: muitos mercados já imprimem o preço promocional na linha do
  item e no rodapé só informam "você economizou R$ X". Isso vai em economia e
  desconto fica 0. Use desconto apenas se existir uma linha DESCONTO que diminui
  o total. Nunca invente desconto para fazer a conta fechar.
- Para todo item, quantidade x valor_unitario deve ser igual a valor_total.
  O valor_total da linha (último número) é o que foi cobrado.
- A soma dos valor_total dos itens, menos o desconto, deve dar o valor_total da nota.
"""

PROMPT_CORRECAO = """Você já leu esta nota e respondeu o JSON abaixo, mas ele tem um erro:
a soma dos itens menos o desconto dá {soma}, porém o total da nota é {total}
(diferença de {diferenca}).
{suspeitos}
Olhe a imagem de novo e confira valor por valor: itens vendidos por peso (KG),
itens que podem ter sido pulados ou duplicados, o desconto e o total. Responda APENAS com o JSON corrigido, no mesmo formato.

JSON anterior:
{json_anterior}
"""

PROMPT_FATIA = """Esta imagem é um TRECHO ampliado de um cupom fiscal (NFC-e).
Liste apenas as linhas de produto que aparecem COMPLETAS neste trecho
(ignore linhas cortadas no topo ou no rodapé da imagem e ignore cabeçalho/totais).
Leia cada dígito com cuidado: 6 e 8, 3 e 8, 1 e 7, 5 e 6 são fáceis de confundir.
Para item vendido por peso: quantidade = peso, valor_unitario = preço do kg.
Responda APENAS com JSON no formato:
{"itens": [{"numero_item": 3, "codigo": "49649", "descricao": "...",
            "quantidade": 0.824, "unidade": "KG", "valor_unitario": 109.90,
            "valor_total": 90.56, "categoria": "carnes"}]}
"""
