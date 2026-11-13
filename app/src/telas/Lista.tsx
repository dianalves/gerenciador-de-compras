// Lista de compras: sugestões dos essenciais acabando + o que o usuário acrescentar.
import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, TextInput, View } from 'react-native';

import { api, ItemLista } from '../api';
import { cores, estilos } from '../estilo';
import { numero } from '../formato';

type Unidade = 'UN' | 'KG' | 'L';
const UNIDADES: { id: Unidade; rotulo: string }[] = [
  { id: 'UN', rotulo: 'un' },
  { id: 'KG', rotulo: 'kg' },
  { id: 'L', rotulo: 'L' },
];
const PARA_UNIDADE: Record<string, Unidade> = { un: 'UN', kg: 'KG', L: 'L' };

/** Situação AGORA do essencial por trás da sugestão. */
function situacaoTexto(i: ItemLista): { texto: string; cor: string } | null {
  if (i.situacao === 'acabou') return { texto: 'acabou', cor: cores.erro };
  if (i.situacao === 'acabando') {
    const d = Math.max(1, Math.round(i.dias_restantes ?? 1));
    return { texto: `acaba em ~${d} ${d === 1 ? 'dia' : 'dias'}`, cor: cores.alerta };
  }
  return null;
}

function quantidadeTexto(i: ItemLista): string {
  if (!i.quantidade) return '';
  const u = i.unidade === 'un' ? (Number(i.quantidade) === 1 ? 'unidade' : 'unidades') : i.unidade ?? '';
  return `${numero(i.quantidade, 3)} ${u}`;
}

const campo = {
  backgroundColor: cores.cartao,
  borderWidth: 1,
  borderColor: cores.borda,
  borderRadius: 12,
  paddingHorizontal: 12,
  paddingVertical: 10,
  fontSize: 16,
  color: cores.texto,
} as const;

export default function Lista() {
  const [itens, setItens] = useState<ItemLista[]>([]);
  const [novo, setNovo] = useState('');
  const [editando, setEditando] = useState<{ id: number; texto: string; quantidade: string; unidade: Unidade } | null>(
    null,
  );
  const [corrigindo, setCorrigindo] = useState<{ item: ItemLista; quantidade: string } | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setItens(await api.lista());
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function executar(acao: () => Promise<unknown>) {
    try {
      await acao();
      await carregar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  function adicionar() {
    const texto = novo.trim();
    if (!texto) return;
    setNovo('');
    executar(() => api.adicionarNaLista({ texto }));
  }

  function salvarEdicao() {
    if (!editando) return;
    const qtd = Number(editando.quantidade.replace(',', '.'));
    const mudanca = {
      texto: editando.texto.trim() || undefined,
      ...(qtd > 0 ? { quantidade: qtd, unidade: editando.unidade } : {}),
    };
    setEditando(null);
    executar(() => api.editarItemLista(editando.id, mudanca));
  }

  function corrigir() {
    if (!corrigindo?.item.essencial_id) return;
    const qtd = Number(corrigindo.quantidade.replace(',', '.'));
    if (!(qtd >= 0)) return;
    const id = corrigindo.item.essencial_id;
    setCorrigindo(null);
    executar(() => api.aindaTenho(id, qtd)); // sai da lista e do aviso do Início
  }

  const pendentes = itens.filter((i) => i.status === 'pendente');
  const comprados = itens.filter((i) => i.status === 'comprado');

  return (
    <ScrollView
      style={estilos.tela}
      keyboardShouldPersistTaps="handled"
      refreshControl={<RefreshControl refreshing={carregando} onRefresh={carregar} />}
    >
      <Text style={estilos.titulo}>Lista de compras</Text>
      <Text style={estilos.subtitulo}>
        {pendentes.length ? `${pendentes.length} ${pendentes.length === 1 ? 'item' : 'itens'} para comprar` : 'Nada para comprar agora'}
      </Text>

      <View style={[estilos.linha, { marginBottom: 12 }]}>
        <TextInput
          value={novo}
          onChangeText={setNovo}
          onSubmitEditing={adicionar}
          returnKeyType="done"
          placeholder="Adicionar item (ex.: pilhas)"
          placeholderTextColor={cores.suave}
          style={[campo, { flex: 1 }]}
        />
        <Pressable
          onPress={adicionar}
          disabled={!novo.trim()}
          style={{ marginLeft: 8, opacity: novo.trim() ? 1 : 0.4 }}
          accessibilityLabel="Adicionar à lista"
        >
          <Ionicons name="add-circle" size={40} color={cores.primaria} />
        </Pressable>
      </View>

      {erro && <Text style={[estilos.textoErro, { marginBottom: 12 }]}>{erro}</Text>}

      {corrigindo && (
        <View style={[estilos.cartao, { borderColor: cores.primaria }]}>
          <Text style={{ fontWeight: '700', color: cores.texto }}>
            Quanto de {corrigindo.item.texto.toLowerCase()} tem agora?
          </Text>
          <Text style={{ color: cores.suave, fontSize: 13, marginBottom: 8 }}>
            Corrige a estimativa. Se ainda dura, sai da lista e do aviso.
          </Text>
          <View style={estilos.linha}>
            <TextInput
              value={corrigindo.quantidade}
              onChangeText={(t) => setCorrigindo({ ...corrigindo, quantidade: t.replace(/[^0-9.,]/g, '') })}
              keyboardType="decimal-pad"
              autoFocus
              style={[campo, { width: 90 }]}
            />
            <Text style={{ color: cores.texto, marginLeft: 8, flex: 1 }}>
              {corrigindo.item.unidade === 'un' ? 'unidade(s)' : corrigindo.item.unidade}
            </Text>
            <Pressable onPress={() => setCorrigindo(null)} hitSlop={8} style={{ marginRight: 16 }}>
              <Text style={{ color: cores.suave }}>Cancelar</Text>
            </Pressable>
            <Pressable onPress={corrigir} hitSlop={8}>
              <Text style={{ color: cores.primaria, fontWeight: '700' }}>Corrigir</Text>
            </Pressable>
          </View>
        </View>
      )}

      {pendentes.length > 0 && (
        <View style={estilos.cartao}>
          {pendentes.map((i, k) =>
            editando?.id === i.id ? (
              <View key={i.id} style={{ paddingVertical: 8, borderTopWidth: k ? 1 : 0, borderTopColor: cores.borda }}>
                <TextInput
                  value={editando.texto}
                  onChangeText={(texto) => setEditando({ ...editando, texto })}
                  style={campo}
                />
                <View style={[estilos.linha, { marginTop: 8 }]}>
                  <TextInput
                    value={editando.quantidade}
                    onChangeText={(t) => setEditando({ ...editando, quantidade: t.replace(/[^0-9.,]/g, '') })}
                    placeholder="qtd"
                    placeholderTextColor={cores.suave}
                    keyboardType="decimal-pad"
                    style={[campo, { width: 80 }]}
                  />
                  {UNIDADES.map((u) => {
                    const ativa = editando.unidade === u.id;
                    return (
                      <Pressable
                        key={u.id}
                        onPress={() => setEditando({ ...editando, unidade: u.id })}
                        style={[chip, ativa && { backgroundColor: cores.primaria, borderColor: cores.primaria }]}
                      >
                        <Text style={{ color: ativa ? '#FFF' : cores.texto, fontWeight: '600' }}>{u.rotulo}</Text>
                      </Pressable>
                    );
                  })}
                  <Pressable onPress={salvarEdicao} hitSlop={8} style={{ marginLeft: 'auto' }}>
                    <Text style={{ color: cores.primaria, fontWeight: '700' }}>OK</Text>
                  </Pressable>
                </View>
              </View>
            ) : (
              <View
                key={i.id}
                style={[estilos.linha, { paddingVertical: 10, borderTopWidth: k ? 1 : 0, borderTopColor: cores.borda }]}
              >
                <Pressable
                  onPress={() => executar(() => api.editarItemLista(i.id, { status: 'comprado' }))}
                  hitSlop={8}
                  accessibilityLabel={`Marcar ${i.texto} como comprado`}
                >
                  <Ionicons name="square-outline" size={24} color={cores.suave} />
                </Pressable>
                <Pressable
                  style={{ flex: 1, marginLeft: 10 }}
                  onPress={() =>
                    setEditando({
                      id: i.id,
                      texto: i.texto,
                      quantidade: i.quantidade ? numero(i.quantidade, 3) : '',
                      unidade: PARA_UNIDADE[i.unidade ?? 'un'] ?? 'UN',
                    })
                  }
                >
                  <Text style={{ color: cores.texto, fontSize: 16 }}>{i.texto}</Text>
                  <Text style={{ color: cores.suave, fontSize: 13 }}>
                    {quantidadeTexto(i)}
                    {quantidadeTexto(i) && situacaoTexto(i) ? ' · ' : ''}
                    {situacaoTexto(i) && (
                      <Text style={{ color: situacaoTexto(i)!.cor, fontWeight: '700' }}>{situacaoTexto(i)!.texto}</Text>
                    )}
                  </Text>
                </Pressable>
                {i.origem === 'sugestao' && i.essencial_id && (
                  <Pressable
                    onPress={() => setCorrigindo({ item: i, quantidade: i.quantidade ? numero(i.quantidade, 3) : '1' })}
                    style={[estilos.botaoMini, { marginRight: 10 }]}
                    accessibilityLabel={`Ainda tenho ${i.texto}`}
                  >
                    <Text style={[estilos.botaoMiniTexto, { fontSize: 13 }]}>Ainda tenho</Text>
                  </Pressable>
                )}
                <Pressable
                  onPress={() => executar(() => api.removerDaLista(i.id))}
                  hitSlop={10}
                  accessibilityLabel={`Tirar ${i.texto} da lista`}
                >
                  <Ionicons name="trash-outline" size={20} color={cores.suave} />
                </Pressable>
              </View>
            ),
          )}
        </View>
      )}

      {comprados.length > 0 && (
        <View style={estilos.cartao}>
          <View style={[estilos.linha, { marginBottom: 4 }]}>
            <Text style={{ fontWeight: '700', color: cores.suave }}>Comprados</Text>
            <Pressable onPress={() => executar(() => api.limparComprados())} hitSlop={8}>
              <Text style={{ color: cores.primaria, fontWeight: '600' }}>Limpar</Text>
            </Pressable>
          </View>
          {comprados.map((i) => (
            <Pressable
              key={i.id}
              style={[estilos.linha, { paddingVertical: 8 }]}
              onPress={() => executar(() => api.editarItemLista(i.id, { status: 'pendente' }))}
              accessibilityLabel={`Desmarcar ${i.texto}`}
            >
              <Ionicons name="checkbox" size={24} color={cores.primaria} />
              <Text
                style={{ flex: 1, marginLeft: 10, color: cores.suave, textDecorationLine: 'line-through' }}
              >
                {i.texto} {quantidadeTexto(i) ? `· ${quantidadeTexto(i)}` : ''}
              </Text>
            </Pressable>
          ))}
        </View>
      )}
      <Text style={{ color: cores.suave, fontSize: 12, textAlign: 'center' }}>
        Toque no item para editar · ao importar uma nota, o que veio nela é marcado sozinho
      </Text>
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

const chip = {
  borderWidth: 1,
  borderColor: cores.borda,
  backgroundColor: cores.cartao,
  borderRadius: 14,
  paddingVertical: 6,
  paddingHorizontal: 10,
  marginLeft: 6,
} as const;
