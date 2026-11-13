// Tela inicial: resumo dos gastos e o botão para escanear um cupom.
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { api, GastoCategoria, GastoMensal, PrevisaoEssencial } from '../api';
import { API_URL } from '../config';
import { cores, estilos } from '../estilo';
import { nomeCategoria, nomeMes, quandoAcaba, reais } from '../formato';

type Props = { aoEscanear: () => void; aoVerEssenciais: () => void };

export default function Inicio({ aoEscanear, aoVerEssenciais }: Props) {
  const [meses, setMeses] = useState<GastoMensal[]>([]);
  const [selecionado, setSelecionado] = useState<GastoMensal | null>(null);
  const [categorias, setCategorias] = useState<GastoCategoria[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [previsoes, setPrevisoes] = useState<PrevisaoEssencial[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      api.previsaoEssenciais().then(setPrevisoes).catch(() => setPrevisoes(null));
      const lista = await api.gastosMensais();
      setMeses(lista);
      setSelecionado((atual) => atual ?? lista[lista.length - 1] ?? null); // mês mais recente
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEffect(() => {
    if (!selecionado) return;
    api
      .categorias(selecionado.ano, selecionado.mes)
      .then(setCategorias)
      .catch((e: Error) => setErro(e.message));
  }, [selecionado]);

  return (
    <ScrollView
      style={estilos.tela}
      refreshControl={<RefreshControl refreshing={carregando} onRefresh={carregar} />}
    >
      <Text style={estilos.titulo}>Minhas compras</Text>
      <Text style={estilos.subtitulo}>Para onde vai o dinheiro do mercado</Text>

      <Pressable style={estilos.botao} onPress={aoEscanear}>
        <Text style={estilos.botaoTexto}>Escanear cupom</Text>
      </Pressable>

      {previsoes !== null && <CartaoAcabando previsoes={previsoes} aoAbrir={aoVerEssenciais} />}

      {erro && (
        <View style={estilos.cartao}>
          <Text style={estilos.textoErro}>{erro}</Text>
          <Text style={{ color: cores.suave, marginTop: 8 }}>API: {API_URL}</Text>
        </View>
      )}

      {carregando && meses.length === 0 && <ActivityIndicator style={{ marginTop: 24 }} />}

      {!carregando && !erro && meses.length === 0 && (
        <View style={estilos.cartao}>
          <Text>Nenhuma compra ainda. Escaneie o QR code de um cupom para começar.</Text>
        </View>
      )}

      {meses.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginVertical: 8 }}>
          {meses.map((m) => {
            const ativo = selecionado?.ano === m.ano && selecionado?.mes === m.mes;
            return (
              <Pressable
                key={`${m.ano}-${m.mes}`}
                onPress={() => setSelecionado(m)}
                style={{
                  paddingVertical: 8,
                  paddingHorizontal: 14,
                  borderRadius: 20,
                  marginRight: 8,
                  backgroundColor: ativo ? cores.primaria : cores.cartao,
                  borderWidth: 1,
                  borderColor: ativo ? cores.primaria : cores.borda,
                }}
              >
                <Text style={{ color: ativo ? '#FFF' : cores.texto, fontWeight: '600' }}>
                  {nomeMes(m.mes, m.ano)}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
      )}

      {selecionado && (
        <View style={estilos.cartao}>
          <Text style={{ color: cores.suave }}>Total em {nomeMes(selecionado.mes, selecionado.ano)}</Text>
          <Text style={{ fontSize: 32, fontWeight: '700', color: cores.texto, marginBottom: 12 }}>
            {reais(selecionado.total)}
          </Text>
          {categorias.map((c) => (
            <View key={c.categoria} style={{ marginBottom: 10 }}>
              <View style={estilos.linha}>
                <Text style={{ color: cores.texto }}>{nomeCategoria(c.categoria)}</Text>
                <Text style={{ color: cores.texto, fontWeight: '600' }}>
                  {reais(c.total)} <Text style={{ color: cores.suave }}>({c.percentual}%)</Text>
                </Text>
              </View>
              <View style={{ height: 6, backgroundColor: cores.borda, borderRadius: 3, marginTop: 4 }}>
                <View
                  style={{
                    height: 6,
                    width: `${Math.min(c.percentual, 100)}%`,
                    backgroundColor: cores.primaria,
                    borderRadius: 3,
                  }}
                />
              </View>
            </View>
          ))}
        </View>
      )}
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

function CartaoAcabando({ previsoes, aoAbrir }: { previsoes: PrevisaoEssencial[]; aoAbrir: () => void }) {
  if (previsoes.length === 0) {
    return (
      <Pressable style={estilos.cartao} onPress={aoAbrir}>
        <Text style={{ color: cores.texto, fontWeight: '600' }}>Avisos de reposição</Text>
        <Text style={{ color: cores.suave, marginTop: 4 }}>
          Marque os itens que não podem faltar e o app avisa quando estiverem acabando ›
        </Text>
      </Pressable>
    );
  }
  const urgentes = previsoes
    .filter((p) => p.situacao === 'acabou' || p.situacao === 'acabando')
    .sort((a, b) => (a.dias_restantes ?? 0) - (b.dias_restantes ?? 0));
  if (urgentes.length === 0) return null; // tudo em dia: não ocupa espaço
  return (
    <Pressable
      style={[estilos.cartao, { borderColor: cores.alerta, backgroundColor: '#FFF8EC' }]}
      onPress={aoAbrir}
    >
      <Text style={{ color: cores.alerta, fontWeight: '700', fontSize: 16, marginBottom: 6 }}>
        Está acabando
      </Text>
      {urgentes.map((p) => (
        <View key={p.essencial_id} style={[estilos.linha, { paddingVertical: 3 }]}>
          <Text style={{ color: cores.texto }}>{p.nome}</Text>
          <Text style={{ color: p.situacao === 'acabou' ? cores.erro : cores.alerta, fontWeight: '700' }}>
            {quandoAcaba(p.dias_restantes, p.acaba_em)}
          </Text>
        </View>
      ))}
      <Text style={{ color: cores.suave, fontSize: 12, marginTop: 6 }}>Toque para ver os essenciais ›</Text>
    </Pressable>
  );
}
