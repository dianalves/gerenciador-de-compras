// Estoque: o que tem em casa, por categoria. "−1" e "Acabou" registram a saída.
import { useCallback, useEffect, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, TextInput, View } from 'react-native';

import { api, ItemEstoque } from '../api';
import { cores, estilos } from '../estilo';
import { nomeCategoria, quantidade } from '../formato';

export default function Estoque() {
  const [itens, setItens] = useState<ItemEstoque[]>([]);
  const [filtro, setFiltro] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<number | null>(null); // produto sendo atualizado

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setItens(await api.estoque());
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function atualizar(produtoId: number, acao: () => Promise<ItemEstoque>) {
    setOcupado(produtoId);
    try {
      const novo = await acao();
      setItens((atuais) =>
        Number(novo.quantidade) > 0
          ? atuais.map((i) => (i.produto_id === produtoId ? novo : i))
          : atuais.filter((i) => i.produto_id !== produtoId), // acabou: sai da lista
      );
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  const texto = filtro.trim().toUpperCase();
  const visiveis = texto ? itens.filter((i) => i.nome.includes(texto)) : itens;
  const porCategoria = new Map<string, ItemEstoque[]>();
  visiveis.forEach((i) => porCategoria.set(i.categoria, [...(porCategoria.get(i.categoria) ?? []), i]));

  return (
    <ScrollView
      style={estilos.tela}
      keyboardShouldPersistTaps="handled"
      refreshControl={<RefreshControl refreshing={carregando} onRefresh={carregar} />}
    >
      <Text style={estilos.titulo}>Estoque</Text>
      <Text style={estilos.subtitulo}>
        {itens.length} {itens.length === 1 ? 'produto' : 'produtos'} em casa
      </Text>

      <TextInput
        value={filtro}
        onChangeText={setFiltro}
        placeholder="Filtrar (ex.: arroz)"
        placeholderTextColor={cores.suave}
        autoCapitalize="characters"
        style={{
          backgroundColor: cores.cartao,
          borderWidth: 1,
          borderColor: cores.borda,
          borderRadius: 12,
          padding: 12,
          fontSize: 16,
          color: cores.texto,
          marginBottom: 12,
        }}
      />

      {erro && <Text style={[estilos.textoErro, { marginBottom: 12 }]}>{erro}</Text>}

      {!carregando && itens.length === 0 && !erro && (
        <View style={estilos.cartao}>
          <Text style={{ color: cores.suave }}>
            Estoque vazio. Os itens entram aqui quando você importa um cupom.
          </Text>
        </View>
      )}

      {[...porCategoria.entries()].map(([categoria, lista]) => (
        <View key={categoria} style={estilos.cartao}>
          <Text style={{ fontWeight: '700', color: cores.suave, marginBottom: 4 }}>
            {nomeCategoria(categoria)}
          </Text>
          {lista.map((item, k) => {
            const porUnidade = item.unidade.toUpperCase() === 'UN';
            const desabilitado = ocupado === item.produto_id;
            return (
              <View
                key={item.produto_id}
                style={[
                  estilos.linha,
                  { paddingVertical: 10, borderTopWidth: k ? 1 : 0, borderTopColor: cores.borda },
                ]}
              >
                <View style={{ flex: 1, paddingRight: 8 }}>
                  <Text style={{ color: cores.texto }}>{item.nome}</Text>
                  <Text style={{ color: cores.primaria, fontWeight: '700' }}>
                    {quantidade(item.quantidade, item.unidade)}
                  </Text>
                </View>
                {porUnidade && (
                  <Pressable
                    disabled={desabilitado}
                    onPress={() => atualizar(item.produto_id, () => api.consumir(item.produto_id))}
                    style={[estilos.botaoMini, desabilitado && { opacity: 0.4 }]}
                    accessibilityLabel={`Usei um ${item.nome}`}
                  >
                    <Text style={estilos.botaoMiniTexto}>−1</Text>
                  </Pressable>
                )}
                <Pressable
                  disabled={desabilitado}
                  onPress={() => atualizar(item.produto_id, () => api.acabou(item.produto_id))}
                  style={[estilos.botaoMini, { marginLeft: 8 }, desabilitado && { opacity: 0.4 }]}
                  accessibilityLabel={`${item.nome} acabou`}
                >
                  <Text style={[estilos.botaoMiniTexto, { color: cores.erro }]}>Acabou</Text>
                </Pressable>
              </View>
            );
          })}
        </View>
      ))}
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}
