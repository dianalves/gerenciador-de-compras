// Criar/editar um essencial: 1) qual item  2) quanto costuma comprar  3) quanto isso dura.
// (Quanto tem em casa é com a aba Estoque; aqui é o hábito da casa.)
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import { api, ErroApi, Essencial, PreviaEssencial } from '../api';
import { cores, estilos } from '../estilo';
import { numero } from '../formato';

type Unidade = 'UN' | 'KG' | 'L';
const UNIDADES: { id: Unidade; rotulo: string }[] = [
  { id: 'UN', rotulo: 'unidades' },
  { id: 'KG', rotulo: 'kg' },
  { id: 'L', rotulo: 'litros' },
];
const UNIDADE_DO_ESSENCIAL: Record<string, Unidade> = { kg: 'KG', L: 'L', un: 'UN' };

const DURACOES = [
  { dias: 7, rotulo: '1 semana' },
  { dias: 14, rotulo: '2 semanas' },
  { dias: 30, rotulo: '1 mês' },
  { dias: 60, rotulo: '2 meses' },
];

type Props = {
  inicial?: Essencial; // sem inicial = criando um novo
  aoTerminar: () => void; // salvou ou cancelou: volta para a lista
  aoAbrirExistente: (nome: string) => void; // já acompanha esse item: abre ele para editar
};

const campo = {
  backgroundColor: cores.cartao,
  borderWidth: 1,
  borderColor: cores.borda,
  borderRadius: 12,
  padding: 12,
  fontSize: 16,
  color: cores.texto,
} as const;

/** "arroz" -> "Arroz" */
function capitalizar(texto: string): string {
  const t = texto.trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export default function FormEssencial({ inicial, aoTerminar, aoAbrirExistente }: Props) {
  const [nome, setNome] = useState(inicial?.nome ?? '');
  const [previa, setPrevia] = useState<PreviaEssencial | null>(null);

  const [quantidade, setQuantidade] = useState(
    inicial?.quantidade_pacote ? numero(inicial.quantidade_pacote, 3) : '',
  );
  const [unidade, setUnidade] = useState<Unidade>(UNIDADE_DO_ESSENCIAL[inicial?.unidade ?? 'un'] ?? 'UN');
  const [quantidadeMexida, setQuantidadeMexida] = useState(!!inicial); // não sobrescrever o usuário

  const diasIniciais = inicial?.dura_pacote_dias ? Math.round(inicial.dura_pacote_dias) : null;
  const [dias, setDias] = useState<number | null>(
    diasIniciais && DURACOES.some((d) => d.dias === diasIniciais) ? diasIniciais : null,
  );
  const [outro, setOutro] = useState(
    diasIniciais && !DURACOES.some((d) => d.dias === diasIniciais) ? String(diasIniciais) : '',
  );
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [jaExiste, setJaExiste] = useState(false);

  // Enquanto digita: acha o item nas compras e sugere a quantidade (ex.: 5 kg do último arroz).
  useEffect(() => {
    const texto = nome.trim();
    if (texto.length < 2) {
      setPrevia(null);
      return;
    }
    const espera = setTimeout(() => {
      api
        .previaEssencial(texto)
        .then((p) => {
          setPrevia(p);
          if (!quantidadeMexida && p.encontrados > 0) {
            setQuantidade(numero(p.quantidade_pacote, 3));
            setUnidade(UNIDADE_DO_ESSENCIAL[p.unidade] ?? 'UN');
          }
        })
        .catch(() => setPrevia(null));
    }, 400);
    return () => clearTimeout(espera);
  }, [nome, quantidadeMexida]);

  async function salvar() {
    const duracao = dias ?? Number(outro);
    const qtd = Number(quantidade.replace(',', '.'));
    if (!nome.trim()) return setErro('Digite qual item não pode faltar.');
    if (!qtd || qtd <= 0) return setErro('Informe quanto você geralmente compra.');
    if (!duracao || duracao < 1) return setErro('Diga quanto tempo isso dura na sua casa.');
    setSalvando(true);
    setErro(null);
    setJaExiste(false);
    const dados = { nome: capitalizar(nome), duracao_dias: duracao, quantidade: qtd, unidade };
    try {
      if (inicial) {
        await api.editarEssencial(inicial.id, { ...dados, ativo: true });
      } else {
        await api.criarEssencial({ ...dados, produto_ids: [] });
      }
      aoTerminar();
    } catch (e) {
      setErro((e as Error).message);
      setJaExiste(e instanceof ErroApi && e.status === 409);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <ScrollView style={estilos.tela} keyboardShouldPersistTaps="handled">
      <Pressable onPress={aoTerminar} hitSlop={12} style={{ marginBottom: 8 }}>
        <Text style={{ color: cores.primaria, fontWeight: '700' }}>‹ Voltar</Text>
      </Pressable>
      <Text style={estilos.titulo}>{inicial ? 'Editar essencial' : 'Novo essencial'}</Text>

      <Text style={rotulo}>1. Qual item não pode faltar?</Text>
      <TextInput
        value={nome}
        onChangeText={setNome}
        placeholder="Ex.: Arroz, Papel higiênico, Ração"
        placeholderTextColor={cores.suave}
        style={campo}
      />
      {previa && (
        <Text style={[dica, { color: previa.encontrados ? cores.primaria : cores.suave }]}>
          {previa.encontrados
            ? `Encontrado nas suas compras (${previa.encontrados} ${previa.encontrados === 1 ? 'item' : 'itens'})`
            : 'Ainda não há compras com esse nome. Conta a partir da próxima compra.'}
        </Text>
      )}

      <Text style={rotulo}>2. Quantidade que você geralmente compra</Text>
      <View style={estilos.linha}>
        <TextInput
          value={quantidade}
          onChangeText={(t) => {
            setQuantidade(t.replace(/[^0-9.,]/g, ''));
            setQuantidadeMexida(true);
          }}
          placeholder="Ex.: 2"
          placeholderTextColor={cores.suave}
          keyboardType="decimal-pad"
          style={[campo, { width: 100 }]}
        />
        <View style={{ flexDirection: 'row', flex: 1, marginLeft: 8 }}>
          {UNIDADES.map((u) => {
            const ativa = unidade === u.id;
            return (
              <Pressable
                key={u.id}
                onPress={() => {
                  setUnidade(u.id);
                  setQuantidadeMexida(true);
                }}
                style={[chipPequeno, ativa && { backgroundColor: cores.primaria, borderColor: cores.primaria }]}
              >
                <Text style={{ color: ativa ? '#FFF' : cores.texto, fontWeight: '600' }}>{u.rotulo}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <Text style={rotulo}>3. Quanto tempo isso geralmente dura?</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        {DURACOES.map((d) => {
          const ativo = dias === d.dias;
          return (
            <Pressable
              key={d.dias}
              onPress={() => {
                setDias(d.dias);
                setOutro('');
              }}
              style={[chip, ativo && { backgroundColor: cores.primaria, borderColor: cores.primaria }]}
            >
              <Text style={{ color: ativo ? '#FFF' : cores.texto, fontWeight: '600' }}>{d.rotulo}</Text>
            </Pressable>
          );
        })}
      </View>
      <View style={[estilos.linha, { marginTop: 4 }]}>
        <Text style={{ color: cores.suave, marginRight: 8 }}>ou</Text>
        <TextInput
          value={outro}
          onChangeText={(texto) => {
            setOutro(texto.replace(/\D/g, ''));
            setDias(null);
          }}
          placeholder="dias"
          placeholderTextColor={cores.suave}
          keyboardType="number-pad"
          style={[campo, { width: 90, paddingVertical: 8 }]}
        />
        <Text style={{ color: cores.suave, marginLeft: 8, flex: 1 }}>dias</Text>
      </View>

      {erro && <Text style={[estilos.textoErro, { marginTop: 8 }]}>{erro}</Text>}
      {jaExiste && (
        <Pressable style={estilos.botaoSecundario} onPress={() => aoAbrirExistente(nome)}>
          <Text style={estilos.botaoSecundarioTexto}>Abrir para editar</Text>
        </Pressable>
      )}

      <Pressable style={[estilos.botao, salvando && { opacity: 0.5 }]} onPress={salvar} disabled={salvando}>
        <Text style={estilos.botaoTexto}>{inicial ? 'Salvar' : 'Adicionar essencial'}</Text>
      </Pressable>
      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const rotulo = { fontWeight: '700', color: cores.texto, marginTop: 16, marginBottom: 6 } as const;
const dica = { color: cores.suave, fontSize: 13, marginTop: 8, marginBottom: 2 } as const;
const chipPequeno = {
  borderWidth: 1,
  borderColor: cores.borda,
  backgroundColor: cores.cartao,
  borderRadius: 16,
  paddingVertical: 8,
  paddingHorizontal: 12,
  marginRight: 6,
} as const;
const chip = {
  borderWidth: 1,
  borderColor: cores.borda,
  backgroundColor: cores.cartao,
  borderRadius: 16,
  paddingVertical: 8,
  paddingHorizontal: 14,
  marginRight: 8,
  marginBottom: 8,
} as const;
