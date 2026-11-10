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

export function dataCurta(iso: string | null): string {
  if (!iso) return '-';
  const [ano, mes, dia] = iso.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}

/** "UN" -> "un", "KG" -> "kg": para mostrar "R$ 10,99/un". */
export function porUnidade(unidade: string): string {
  return unidade.toLowerCase();
}

/** "2.000" UN -> "2 un"; "0.824" KG -> "0,824 kg" */
export function quantidade(valor: string, unidade: string): string {
  const numero = Number(valor);
  const sigla = unidade.toLowerCase();
  if (sigla === 'kg' || sigla === 'l') return `${numero.toFixed(3).replace('.', ',')} ${sigla}`;
  return `${Number.isInteger(numero) ? numero : String(numero).replace('.', ',')} ${sigla}`;
}
