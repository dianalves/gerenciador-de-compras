// Envia a nota capturada para a API e mostra o que aconteceu.
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import { api, ErroApi, ResultadoImportacao } from '../api';
import { cores, estilos } from '../estilo';
import { nomeCategoria, reais } from '../formato';

type Props = {
  link: string;
  html: string;
  aoEscanearOutro: () => void;
  aoInicio: () => void;
};

export default function Resultado({ link, html, aoEscanearOutro, aoInicio }: Props) {
  const [resultado, setResultado] = useState<ResultadoImportacao | null>(null);
  const [erro, setErro] = useState<{ status: number; mensagem: string } | null>(null);
  const [enviando, setEnviando] = useState(true);

  async function enviar(forcar: boolean) {
    setEnviando(true);
    setErro(null);
    try {
      setResultado(await api.enviarSefaz(html, link, forcar));
    } catch (e) {
      const status = e instanceof ErroApi ? e.status : 0;
      setErro({ status, mensagem: (e as Error).message });
    } finally {
      setEnviando(false);
    }
  }

  useEffect(() => {
    enviar(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (enviando) {
    return (
      <View style={[estilos.tela, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" />
        <Text style={{ marginTop: 12, color: cores.suave }}>Enviando a nota...</Text>
      </View>
    );
  }

  const jaImportada = erro?.status === 409;
  const nota = resultado?.nota;
  const porCategoria = new Map<string, number>();
  nota?.itens.forEach((i) =>
    porCategoria.set(i.categoria, (porCategoria.get(i.categoria) ?? 0) + Number(i.valor_total)),
  );

  return (
    <ScrollView style={estilos.tela}>
      {resultado?.salva && <Text style={[estilos.titulo, { color: cores.primaria }]}>Compra salva!</Text>}
      {resultado && !resultado.salva && (
        <Text style={[estilos.titulo, { color: cores.alerta }]}>Confira antes de salvar</Text>
      )}
      {jaImportada && <Text style={estilos.titulo}>Essa nota já estava salva</Text>}
      {erro && !jaImportada && <Text style={[estilos.titulo, { color: cores.erro }]}>Não deu certo</Text>}

      {erro && (
        <View style={estilos.cartao}>
          <Text style={jaImportada ? { color: cores.texto } : estilos.textoErro}>{erro.mensagem}</Text>
        </View>
      )}

      {resultado && nota && (
        <View style={estilos.cartao}>
          <Text style={{ fontSize: 16, fontWeight: '700', color: cores.texto }}>
            {nota.estabelecimento_nome}
          </Text>
          <Text style={{ color: cores.suave, marginBottom: 8 }}>
            {nota.data_emissao ? new Date(nota.data_emissao).toLocaleDateString() : ''} ·{' '}
            {nota.itens.length} itens
          </Text>
          <Text style={{ fontSize: 28, fontWeight: '700', color: cores.texto, marginBottom: 12 }}>
            {reais(nota.valor_total)}
          </Text>
          {[...porCategoria.entries()]
            .sort((a, b) => b[1] - a[1])
            .map(([categoria, total]) => (
              <View key={categoria} style={[estilos.linha, { marginBottom: 4 }]}>
                <Text style={{ color: cores.texto }}>{nomeCategoria(categoria)}</Text>
                <Text style={{ color: cores.texto }}>{reais(total)}</Text>
              </View>
            ))}
          {!resultado.salva && (
            <Text style={{ color: cores.alerta, marginTop: 12 }}>{resultado.mensagem}</Text>
          )}
        </View>
      )}

      {resultado && !resultado.salva && (
        <Pressable style={[estilos.botao, { backgroundColor: cores.alerta }]} onPress={() => enviar(true)}>
          <Text style={estilos.botaoTexto}>Salvar mesmo assim</Text>
        </Pressable>
      )}
      {erro && !jaImportada && (
        <Pressable style={estilos.botao} onPress={() => enviar(false)}>
          <Text style={estilos.botaoTexto}>Tentar enviar de novo</Text>
        </Pressable>
      )}

      <Pressable style={estilos.botao} onPress={aoEscanearOutro}>
        <Text style={estilos.botaoTexto}>Escanear outro cupom</Text>
      </Pressable>
      <Pressable style={estilos.botaoSecundario} onPress={aoInicio}>
        <Text style={estilos.botaoSecundarioTexto}>Voltar ao início</Text>
      </Pressable>
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}
