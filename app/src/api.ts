// Chamadas à API do gerenciador (FastAPI rodando no Mac).
import { API_URL } from './config';

export type Duvida = {
  numero_item: number;
  descricao: string;
  leitura_inteira: string | null;
  leitura_zoom: string;
};

export type ItemNota = {
  descricao: string;
  quantidade: string;
  unidade: string;
  valor_total: string;
  categoria: string;
};

export type Nota = {
  estabelecimento_nome: string;
  data_emissao: string | null;
  chave_acesso: string | null;
  valor_total: string;
  itens: ItemNota[];
};

export type ResultadoImportacao = {
  salva: boolean;
  compra_id: number | null;
  mensagem: string;
  confere_total: boolean;
  diferenca: string;
  categorias: string | null;
  duvidas: Duvida[];
  nota: Nota;
};

export type CompraResumo = {
  id: number;
  estabelecimento: string;
  data_emissao: string | null;
  valor_total: string;
  quantidade_itens: number;
  origem: string;
};

export type GastoMensal = { ano: number; mes: number; total: string };
export type GastoCategoria = { categoria: string; total: string; percentual: number };

export type Produto = {
  id: number;
  nome: string;
  categoria: string;
  descricoes: string[];
  compras: number;
};

export type PrecoPago = {
  data: string | null;
  mercado: string;
  valor_unitario: string;
  unidade: string;
  quantidade: string;
  valor_total: string;
};

export type Comparacao = {
  produto_id: number;
  produto: string;
  unidade: string;
  mais_barato: string;
  preco_mais_barato: string;
  mais_caro: string;
  preco_mais_caro: string;
  diferenca: string;
  percentual: number;
};

export type ItemEstoque = {
  produto_id: number;
  nome: string;
  categoria: string;
  unidade: string;
  quantidade: string;
  ultima_entrada: string | null;
};

export type MensagemConversa = { papel: 'usuario' | 'assistente'; texto: string };
export type RespostaPergunta = {
  resposta: string;
  ferramentas: { nome: string; argumentos: Record<string, unknown> }[];
};

export type Casa = { adultos: number; criancas: number; pets: number };

export type Essencial = {
  id: number;
  nome: string;
  unidade: string;
  consumo_pessoa_mes: string;
  ativo: boolean;
  quantidade_pacote: string | null;
  dura_pacote_dias: number | null;
  produtos: { id: number; nome: string }[];
};

export type PreviaEssencial = {
  nome: string;
  encontrados: number;
  unidade: string;
  quantidade_pacote: string;
  em_estoque: string;
};

export type MudancaEssencial = {
  nome?: string;
  ativo?: boolean;
  duracao_dias?: number;
  produto_ids?: number[];
  quantidade?: number;
  unidade?: 'UN' | 'KG' | 'L';
};

export type PrevisaoEssencial = {
  essencial_id: number;
  nome: string;
  unidade: string;
  estoque: string; // estimado hoje
  registrado: string;
  desde: string | null;
  consumo_diario: string;
  dias_restantes: number | null;
  acaba_em: string | null;
  situacao: 'acabou' | 'acabando' | 'ok' | 'sem_tamanho';
  produtos: string[];
  sem_tamanho: string[];
  fonte: string;
};

export type ItemLista = {
  id: number;
  texto: string;
  quantidade: string | null;
  unidade: string | null;
  origem: 'sugestao' | 'manual';
  status: 'pendente' | 'comprado';
  essencial_id: number | null;
  situacao: 'acabou' | 'acabando' | 'ok' | 'sem_tamanho' | null;
  dias_restantes: number | null;
};

export class ErroApi extends Error {
  constructor(public status: number, mensagem: string) {
    super(mensagem);
  }
}

async function chamar<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`${API_URL}${caminho}`, {
      ...opcoes,
      headers: { 'Content-Type': 'application/json', ...(opcoes.headers ?? {}) },
    });
  } catch {
    throw new ErroApi(
      0,
      `Não consegui falar com a API em ${API_URL}. Confira se a API está rodando ` +
        '(compras api) e se o celular está no mesmo Wi-Fi do Mac.',
    );
  }
  if (!resposta.ok) {
    let detalhe = `Erro ${resposta.status}`;
    try {
      const corpo = await resposta.json();
      detalhe = typeof corpo.detail === 'string' ? corpo.detail : JSON.stringify(corpo.detail);
    } catch {
      // resposta sem JSON: fica a mensagem genérica
    }
    throw new ErroApi(resposta.status, detalhe);
  }
  return (resposta.status === 204 ? undefined : await resposta.json()) as T;
}

// A chave de acesso (44 dígitos) vem dentro do link do QR: ...?p=CHAVE|2|1|1|HASH
export function chaveDoLink(link: string): string | null {
  const achado = link.match(/\d{44}/);
  return achado ? achado[0] : null;
}

export const api = {
  /** Compra já cadastrada com essa chave, ou null se ainda não existe. */
  compraPorChave: async (chave: string): Promise<CompraResumo | null> => {
    try {
      return await chamar<CompraResumo>(`/compras/chave/${chave}`);
    } catch (e) {
      if (e instanceof ErroApi && e.status === 404) return null;
      throw e;
    }
  },
  enviarSefaz: (html: string, link: string, forcar = false) =>
    chamar<ResultadoImportacao>(`/notas/sefaz?forcar=${forcar}`, {
      method: 'POST',
      body: JSON.stringify({ html, link }),
    }),
  produtos: (busca?: string) =>
    chamar<Produto[]>(`/produtos${busca ? `?busca=${encodeURIComponent(busca)}` : ''}`),
  precos: (produtoId: number) => chamar<PrecoPago[]>(`/produtos/${produtoId}/precos`),
  compararMercados: () => chamar<Comparacao[]>('/produtos/comparar-mercados'),
  estoque: () => chamar<ItemEstoque[]>('/estoque'),
  consumir: (produtoId: number, quantidade = 1) =>
    chamar<ItemEstoque>(`/estoque/${produtoId}/consumir`, {
      method: 'POST',
      body: JSON.stringify({ quantidade }),
    }),
  adicionarManual: (item: { nome: string; produto_id?: number; quantidade: number; unidade: 'UN' | 'KG' | 'L' }) =>
    chamar<ItemEstoque>('/estoque/manual', { method: 'POST', body: JSON.stringify(item) }),
  acabou: (produtoId: number) =>
    chamar<ItemEstoque>(`/estoque/${produtoId}/acabou`, { method: 'POST' }),
  perguntar: (pergunta: string, historico: MensagemConversa[]) =>
    chamar<RespostaPergunta>('/perguntas', {
      method: 'POST',
      body: JSON.stringify({ pergunta, historico }),
    }),
  casa: () => chamar<Casa>('/casa'),
  salvarCasa: (casa: Casa) => chamar<Casa>('/casa', { method: 'PUT', body: JSON.stringify(casa) }),
  essenciais: () => chamar<Essencial[]>('/essenciais'),
  editarEssencial: (id: number, mudanca: MudancaEssencial) =>
    chamar<Essencial>(`/essenciais/${id}`, { method: 'PATCH', body: JSON.stringify(mudanca) }),
  previaEssencial: (nome: string) =>
    chamar<PreviaEssencial>(`/essenciais/previa?nome=${encodeURIComponent(nome)}`),
  criarEssencial: (novo: {
    nome: string;
    produto_ids: number[];
    duracao_dias: number;
    quantidade?: number;
    unidade?: 'UN' | 'KG' | 'L';
  }) =>
    chamar<Essencial>('/essenciais', { method: 'POST', body: JSON.stringify(novo) }),
  apagarEssencial: (id: number) => chamar<void>(`/essenciais/${id}`, { method: 'DELETE' }),
  previsaoEssenciais: () => chamar<PrevisaoEssencial[]>('/essenciais/previsao'),
  lista: () => chamar<ItemLista[]>('/lista'),
  aindaTenho: (essencialId: number, quantidade: number) =>
    chamar<PrevisaoEssencial>(`/essenciais/${essencialId}/ainda-tenho`, {
      method: 'POST',
      body: JSON.stringify({ quantidade }),
    }),
  adicionarNaLista: (item: { texto: string; quantidade?: number; unidade?: 'UN' | 'KG' | 'L' }) =>
    chamar<ItemLista>('/lista', { method: 'POST', body: JSON.stringify(item) }),
  editarItemLista: (
    id: number,
    mudanca: { texto?: string; quantidade?: number; unidade?: 'UN' | 'KG' | 'L'; status?: 'pendente' | 'comprado' },
  ) => chamar<ItemLista>(`/lista/${id}`, { method: 'PATCH', body: JSON.stringify(mudanca) }),
  removerDaLista: (id: number) => chamar<void>(`/lista/${id}`, { method: 'DELETE' }),
  limparComprados: () => chamar<{ removidos: number }>('/lista/limpar-comprados', { method: 'POST' }),
  gastosMensais: () => chamar<GastoMensal[]>('/relatorios/gastos-mensais'),
  categorias: (ano: number, mes: number) =>
    chamar<GastoCategoria[]>(`/relatorios/categorias?ano=${ano}&mes=${mes}`),
};
