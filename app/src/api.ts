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
  gastosMensais: () => chamar<GastoMensal[]>('/relatorios/gastos-mensais'),
  categorias: (ano: number, mes: number) =>
    chamar<GastoCategoria[]>(`/relatorios/categorias?ano=${ano}&mes=${mes}`),
};
