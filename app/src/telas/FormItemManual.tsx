// "Adicionar item que já tenho": entra no estoque sem nota e sem preço.
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import { api, Produto } from '../api';
import { cores, estilos } from '../estilo';

type Unidade = 'UN' | 'KG' | 'L';
const UNIDADES: { id: Unidade; rotulo: string }[] = [
  { id: 'UN', rotulo: 'unidades' },
  { id: 'KG', rotulo: 'kg' },
  { id: 'L', rotulo: 'litros' },
];

const campo = {
  backgroundColor: cores.cartao,
  borderWidth: 1,
  borderColor: cores.borda,
  borderRadius: 12,
  padding: 12,
  fontSize: 16,
  color: cores.texto,
} as const;

export default function FormItemManual({ aoTerminar }: { aoTerminar: () => void }) {
  const [nome, setNome] = useState('');
  const [produto, setProduto] = useState<Produto | null>(null);
  const [sugestoes, setSugestoes] = useState<Produto[]>([]);
  const [quantidade, setQuantidade] = useState('1');
  const [unidade, setUnidade] = useState<Unidade>('UN');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // Sugere produtos já comprados: escolher um mantém o estoque ligado ao mesmo produto.
  useEffect(() => {
    const texto = nome.trim();
    if (produto || texto.length < 2) {
      setSugestoes([]);
      return;
    }
    const espera = setTimeout(() => {
      api.produtos(texto).then((lista) => setSugestoes(lista.slice(0, 5))).catch(() => setSugestoes([]));
    }, 400);
    return () => clearTimeout(espera);
  }, [nome, produto]);

  async function salvar() {
    const qtd = Number(quantidade.replace(',', '.'));
    if (!produto && !nome.trim()) return setErro('Digite o nome do item.');
    if (!qtd || qtd <= 0) return setErro('Informe a quantidade.');
    setSalvando(true);
    setErro(null);
    try {
      await api.adicionarManual({
        nome: produto ? '' : nome.trim(),
        produto_id: produto?.id,
        quantidade: qtd,
        unidade,
      });
      aoTerminar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <ScrollView style={estilos.tela} keyboardShouldPersistTaps="handled">
      <Pressable onPress={aoTerminar} hitSlop={12} style={{ marginBottom: 8 }}>
        <Text style={{ color: cores.primaria, fontWeight: '700' }}>‹ Voltar</Text>
      </Pressable>
      <Text style={estilos.titulo}>Item que já tenho</Text>
      <Text style={estilos.subtitulo}>Para o estoque começar certo. Não entra nos gastos.</Text>

      <Text style={rotulo}>O que é?</Text>
      {produto ? (
        <View style={[estilos.linha, campo, { backgroundColor: '#EAF5EF' }]}>
          <Text style={{ color: cores.texto, flex: 1 }}>{produto.nome}</Text>
          <Pressable onPress={() => setProduto(null)} hitSlop={8}>
            <Text style={{ color: cores.suave }}>trocar</Text>
          </Pressable>
        </View>
      ) : (
        <TextInput
          value={nome}
          onChangeText={setNome}
          placeholder="Ex.: Arroz, Café, Detergente"
          placeholderTextColor={cores.suave}
          style={campo}
        />
      )}
      {sugestoes.length > 0 && (
        <>
          <Text style={dica}>Já comprado antes (toque para usar):</Text>
          {sugestoes.map((p) => (
            <Pressable
              key={p.id}
              onPress={() => setProduto(p)}
              style={{ paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: cores.borda }}
            >
              <Text style={{ color: cores.texto }}>{p.nome}</Text>
            </Pressable>
          ))}
        </>
      )}

      <Text style={rotulo}>Quanto tem?</Text>
      <View style={estilos.linha}>
        <TextInput
          value={quantidade}
          onChangeText={(t) => setQuantidade(t.replace(/[^0-9.,]/g, ''))}
          keyboardType="decimal-pad"
          style={[campo, { width: 100 }]}
        />
        <View style={{ flexDirection: 'row', flex: 1, marginLeft: 8 }}>
          {UNIDADES.map((u) => {
            const ativa = unidade === u.id;
            return (
              <Pressable
                key={u.id}
                onPress={() => setUnidade(u.id)}
                style={[chip, ativa && { backgroundColor: cores.primaria, borderColor: cores.primaria }]}
              >
                <Text style={{ color: ativa ? '#FFF' : cores.texto, fontWeight: '600' }}>{u.rotulo}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>
      <Text style={dica}>Ex.: 2 kg de arroz, 3 unidades de sabonete, 1,5 litro de óleo.</Text>

      {erro && <Text style={[estilos.textoErro, { marginTop: 8 }]}>{erro}</Text>}

      <Pressable style={[estilos.botao, salvando && { opacity: 0.5 }]} onPress={salvar} disabled={salvando}>
        <Text style={estilos.botaoTexto}>Adicionar ao estoque</Text>
      </Pressable>
      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const rotulo = { fontWeight: '700', color: cores.texto, marginTop: 16, marginBottom: 6 } as const;
const dica = { color: cores.suave, fontSize: 13, marginTop: 8, marginBottom: 2 } as const;
const chip = {
  borderWidth: 1,
  borderColor: cores.borda,
  backgroundColor: cores.cartao,
  borderRadius: 16,
  paddingVertical: 8,
  paddingHorizontal: 12,
  marginRight: 6,
} as const;
