// Preços: onde cada produto saiu mais barato, busca e histórico de um produto.
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import { api, Comparacao, PrecoPago, Produto } from '../api';
import { cores, estilos } from '../estilo';
import { dataCurta, nomeCategoria, porUnidade, reais } from '../formato';

export default function Precos() {
  const [busca, setBusca] = useState('');
  const [resultados, setResultados] = useState<Produto[] | null>(null);
  const [comparacoes, setComparacoes] = useState<Comparacao[]>([]);
  const [selecionado, setSelecionado] = useState<{ id: number; nome: string } | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api.compararMercados().then(setComparacoes).catch((e: Error) => setErro(e.message));
  }, []);

  // Busca enquanto digita (espera 400 ms parado para não chamar a API a cada letra).
  useEffect(() => {
    const texto = busca.trim();
    if (texto.length < 2) {
      setResultados(null);
      return;
    }
    const espera = setTimeout(() => {
      api.produtos(texto).then(setResultados).catch((e: Error) => setErro(e.message));
    }, 400);
    return () => clearTimeout(espera);
  }, [busca]);

  if (selecionado) {
    return <Historico produto={selecionado} aoVoltar={() => setSelecionado(null)} />;
  }

  return (
    <ScrollView style={estilos.tela} keyboardShouldPersistTaps="handled">
      <Text style={estilos.titulo}>Preços</Text>
      <Text style={estilos.subtitulo}>Quanto você pagou e onde saiu mais barato</Text>

      <TextInput
        value={busca}
        onChangeText={setBusca}
        placeholder="Buscar produto (ex.: coca, arroz)"
        placeholderTextColor={cores.suave}
        autoCapitalize="characters"
        style={{
          backgroundColor: cores.cartao,
          borderWidth: 1,
          borderColor: cores.borda,
          borderRadius: 12,
          padding: 14,
          fontSize: 16,
          color: cores.texto,
          marginBottom: 12,
        }}
      />

      {erro && <Text style={[estilos.textoErro, { marginBottom: 12 }]}>{erro}</Text>}

      {resultados !== null && (
        <View style={estilos.cartao}>
          {resultados.length === 0 && <Text style={{ color: cores.suave }}>Nenhum produto encontrado.</Text>}
          {resultados.map((p) => (
            <Pressable
              key={p.id}
              onPress={() => setSelecionado({ id: p.id, nome: p.nome })}
              style={{ paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: cores.borda }}
            >
              <Text style={{ color: cores.texto, fontWeight: '600' }}>{p.nome}</Text>
              <Text style={{ color: cores.suave, fontSize: 13 }}>
                {nomeCategoria(p.categoria)} · comprado {p.compras}x
              </Text>
            </Pressable>
          ))}
        </View>
      )}

      {resultados === null && (
        <>
          <Text style={{ fontSize: 17, fontWeight: '700', color: cores.texto, marginVertical: 8 }}>
            Onde saiu mais barato
          </Text>
          {comparacoes.length === 0 && !erro && (
            <View style={estilos.cartao}>
              <Text style={{ color: cores.suave }}>
                Aparece aqui quando o mesmo produto for comprado em mais de um mercado.
              </Text>
            </View>
          )}
          {comparacoes.map((c) => (
            <Pressable
              key={`${c.produto_id}-${c.unidade}`}
              style={estilos.cartao}
              onPress={() => setSelecionado({ id: c.produto_id, nome: c.produto })}
            >
              <Text style={{ color: cores.texto, fontWeight: '700', marginBottom: 6 }}>{c.produto}</Text>
              <View style={estilos.linha}>
                <Text style={{ color: cores.primaria, flex: 1 }}>{c.mais_barato}</Text>
                <Text style={{ color: cores.primaria, fontWeight: '700' }}>
                  {reais(c.preco_mais_barato)}/{porUnidade(c.unidade)}
                </Text>
              </View>
              <View style={estilos.linha}>
                <Text style={{ color: cores.erro, flex: 1 }}>{c.mais_caro}</Text>
                <Text style={{ color: cores.erro }}>
                  {reais(c.preco_mais_caro)}/{porUnidade(c.unidade)}
                </Text>
              </View>
              <Text style={{ color: cores.suave, marginTop: 6 }}>
                Diferença de {reais(c.diferenca)} ({Math.round(c.percentual)}%)
              </Text>
            </Pressable>
          ))}
        </>
      )}
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

function Historico({ produto, aoVoltar }: { produto: { id: number; nome: string }; aoVoltar: () => void }) {
  const [precos, setPrecos] = useState<PrecoPago[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api.precos(produto.id).then(setPrecos).catch((e: Error) => setErro(e.message));
  }, [produto.id]);

  const valores = (precos ?? []).map((p) => Number(p.valor_unitario));
  const menor = Math.min(...valores);
  const maior = Math.max(...valores);

  return (
    <ScrollView style={estilos.tela}>
      <Pressable onPress={aoVoltar} hitSlop={12} style={{ marginBottom: 8 }}>
        <Text style={{ color: cores.primaria, fontWeight: '700' }}>‹ Voltar</Text>
      </Pressable>
      <Text style={estilos.titulo}>{produto.nome}</Text>
      <Text style={estilos.subtitulo}>Histórico de preço</Text>

      {erro && <Text style={estilos.textoErro}>{erro}</Text>}
      {!precos && !erro && <ActivityIndicator />}

      {precos && precos.length > 1 && (
        <View style={[estilos.cartao, estilos.linha]}>
          <View>
            <Text style={{ color: cores.suave }}>Menor preço</Text>
            <Text style={{ color: cores.primaria, fontSize: 20, fontWeight: '700' }}>
              {reais(menor)}/{porUnidade(precos[0].unidade)}
            </Text>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Text style={{ color: cores.suave }}>Maior preço</Text>
            <Text style={{ color: cores.erro, fontSize: 20, fontWeight: '700' }}>
              {reais(maior)}/{porUnidade(precos[0].unidade)}
            </Text>
          </View>
        </View>
      )}

      {precos && (
        <View style={estilos.cartao}>
          {precos.map((p, i) => {
            const valor = Number(p.valor_unitario);
            const destaque =
              precos.length > 1 && valor === menor ? cores.primaria : valor === maior && precos.length > 1 ? cores.erro : cores.texto;
            return (
              <View
                key={i}
                style={[estilos.linha, { paddingVertical: 10, borderBottomWidth: i < precos.length - 1 ? 1 : 0, borderBottomColor: cores.borda }]}
              >
                <View style={{ flex: 1 }}>
                  <Text style={{ color: cores.texto }}>{p.mercado}</Text>
                  <Text style={{ color: cores.suave, fontSize: 13 }}>{dataCurta(p.data)}</Text>
                </View>
                {/* Aba de comparação: só o preço unitário (total e quantidade ficam na API). */}
                <Text style={{ color: destaque, fontWeight: '700' }}>
                  {reais(p.valor_unitario)}/{porUnidade(p.unidade)}
                </Text>
              </View>
            );
          })}
        </View>
      )}
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}
