# Gerenciador de Compras

Sistema para autogerenciar as compras de mercado da casa: você tira a foto da
NFC-e, um modelo multimodal lê a nota e os itens vão para o PostgreSQL. Daí saem
gasto mensal, gasto por categoria e os produtos com que mais se gasta.

## Como a nota entra no sistema

1. **QR code + SEFAZ (principal)**: escaneia o QR do cupom, abre a consulta da
   SEFAZ, o usuário resolve o captcha e os itens vêm do HTML oficial: valores
   exatos, rápido, sem IA (categorias por palavras-chave).
2. **Foto do cupom + modelo de visão (alternativa)**: para QR danificado/ilegível.
   Funciona com modelo local (LM Studio) ou na nuvem, mas pode confundir dígitos
   (ex.: 6 e 8), por isso confere a soma, lê em fatias e aponta itens duvidosos.

## Arquitetura

```
foto da nota
   -> visao/     (Claude | Gemini | OpenAI | LM Studio local)
   -> nota/      (JSON validado)
   -> servicos/  (grava e consulta)
   -> PostgreSQL
   -> cli.py hoje; API + app no futuro
```

```
src/compras/
├── config.py          # lê o .env
├── visao/             # camada de provedor de visão (troca pela config)
│   ├── base.py        #   contrato ProvedorVisao
│   ├── claude.py / gemini.py / openai.py
│   └── fabrica.py     #   obter_provedor()
├── nota/
│   ├── esquema.py     # NotaFiscal / ItemNota (Pydantic) + categorias
│   ├── prompt.py      # prompt de extração
│   └── leitor.py      # ler_nota(imagem) -> NotaFiscal
├── banco/
│   ├── conexao.py     # engine/sessão SQLAlchemy
│   └── modelos.py     # estabelecimentos, compras, itens_compra
├── servicos/
│   ├── importar.py    # salvar_nota() (evita duplicar pela chave de acesso)
│   └── consultas.py   # gasto por mês / categoria / top produtos
├── sefaz/             # (próximo) importação via WebView + captcha
└── cli.py             # comando `compras`
```

## Como rodar

```bash
cd ~/git/gerenciador-de-compras
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[lmstudio,dev]"      # ou .[claude], .[gemini], .[openai], .[todos]
cp .env.exemplo .env                   # preencha a chave da API
docker compose up -d                   # sobe o PostgreSQL
compras iniciar-banco

compras ler notas/minha_nota.jpg       # só mostra o que foi lido
compras importar notas/minha_nota.jpg  # lê e grava
compras importar notas/x.jpg --provedor gemini
compras gastos
compras categorias 2026 11
compras top
pytest
```

### Importar pela SEFAZ (valores exatos)

```bash
pip install -e ".[lmstudio,sefaz,dev]"
playwright install chromium            # só na primeira vez (se não tiver o Chrome)
compras sefaz notas/minha_nota.jpg     # lê o QR code da foto
compras sefaz "https://www.nfce.fazenda.sp.gov.br/...?p=..."   # ou o link do QR
compras sefaz notas/minha_nota.jpg --salvar
```

Abre o navegador na consulta da SEFAZ; você resolve o captcha (SP exige) e o
programa lê os itens direto do HTML. O modelo só é usado para as categorias
(e como plano B, lendo o texto da página, se o layout for diferente).

## API

```bash
pip install -e ".[lmstudio,sefaz,api,dev]"
compras api                 # http://localhost:8000/docs (documentação interativa)
```

| Método | Rota | O que faz |
|---|---|---|
| POST | `/notas/sefaz` | Recebe `{html, link}` da consulta na SEFAZ e salva a nota |
| POST | `/notas/foto` | Recebe a foto do cupom (alternativa) |
| GET | `/compras`, `/compras/{id}` | Lista / detalha compras |
| DELETE | `/compras/{id}` | Apaga uma compra |
| GET | `/relatorios/gastos-mensais` | Total por mês |
| GET | `/relatorios/categorias?ano=&mes=` | Gasto por categoria (com %) |
| GET | `/relatorios/produtos` | Produtos com que mais se gasta |
| GET | `/saude` | API e banco no ar? |

Uma nota só é salva se a soma dos itens fechar com o total; senão a resposta traz as
divergências e é preciso reenviar com `forcar=true` depois de conferir.
`salvar=false` devolve só a prévia.

## App (Android, Expo)

```bash
cd app
cp .env.exemplo .env.local      # coloque o IP do Mac: http://SEU-IP:8000
npx expo start                  # abra no celular pelo Expo Go
```

Fluxo: **Escanear cupom** -> câmera lê o QR -> a consulta da SEFAZ abre dentro do app ->
você resolve o captcha -> o app captura a página e envia para a API -> "Compra salva!".

Observações aprendidas na prática:
- Celular e Mac na mesma rede, sem isolamento de clientes no roteador.
- A SEFAZ-SP bloqueia temporariamente o IP (inclusive de dados móveis) quando detecta acesso
  suspeito. A WebView fica no padrão, sem disfarçar user-agent ou cabeçalhos, e não se deve
  insistir quando aparecer "The requested URL was rejected".

## Próximos passos

- [x] API (FastAPI)
- [x] Importação pela SEFAZ no computador (navegador, usuário resolve o captcha)
- [x] App Android: câmera lê o QR -> WebView da SEFAZ (captcha) -> envia o HTML para a API
- [ ] App no iPhone
- [ ] API num servidor (usar o app fora de casa)
- [ ] Normalizar produtos (mesmo item com descrições diferentes)
- [ ] Estoque da casa (o que tem e quantidades)
- [ ] Perguntas e respostas sobre as compras (LangGraph / agentes)
- [ ] Migrações com Alembic
