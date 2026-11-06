// Formatação brasileira feita à mão (não depende do suporte a Intl do aparelho).
export function reais(valor: string | number): string {
  const numero = typeof valor === 'string' ? Number(valor) : valor;
  const [inteiro, centavos] = Math.abs(numero).toFixed(2).split('.');
  const comPontos = inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${numero < 0 ? '-' : ''}R$ ${comPontos},${centavos}`;
}

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

export function nomeMes(mes: number, ano: number): string {
  return `${MESES[mes - 1]}/${ano}`;
}

export function nomeCategoria(categoria: string): string {
  const nomes: Record<string, string> = {
    frios_laticinios: 'Frios e laticínios',
    hortifruti: 'Hortifrúti',
  };
  return nomes[categoria] ?? categoria.charAt(0).toUpperCase() + categoria.slice(1);
}
