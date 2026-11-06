// Depois de ler o QR: pergunta à API se a nota já existe ANTES de abrir a SEFAZ.
// Evita acessos repetidos à SEFAZ, que o firewall dela trata como suspeitos.
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import { api, chaveDoLink, CompraResumo } from '../api';
import { cores, estilos } from '../estilo';
import { reais } from '../formato';

type Props = {
  link: string;
  aoNotaNova: () => void;
  aoEscanearOutro: () => void;
  aoInicio: () => void;
};

export default function Verificacao({ link, aoNotaNova, aoEscanearOutro, aoInicio }: Props) {
  const [existente, setExistente] = useState<CompraResumo | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    const chave = chaveDoLink(link);
    if (!chave) {
      aoNotaNova(); // link sem chave reconhecível: segue para a SEFAZ
      return;
    }
    setErro(null);
    api
      .compraPorChave(chave)
      .then((compra) => (compra ? setExistente(compra) : aoNotaNova()))
      .catch((e: Error) => setErro(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [link, tentativa]);

  if (existente) {
    return (
      <View style={estilos.tela}>
        <Text style={estilos.titulo}>Essa nota já está cadastrada</Text>
        <Text style={estilos.subtitulo}>Não precisa consultar a SEFAZ de novo.</Text>
        <View style={estilos.cartao}>
          <Text style={{ fontSize: 16, fontWeight: '700', color: cores.texto }}>
            {existente.estabelecimento}
          </Text>
          <Text style={{ color: cores.suave, marginBottom: 8 }}>
            {existente.data_emissao ? new Date(existente.data_emissao).toLocaleDateString() : ''} ·{' '}
            {existente.quantidade_itens} itens · compra #{existente.id}
          </Text>
          <Text style={{ fontSize: 28, fontWeight: '700', color: cores.texto }}>
            {reais(existente.valor_total)}
          </Text>
        </View>
        <Pressable style={estilos.botao} onPress={aoEscanearOutro}>
          <Text style={estilos.botaoTexto}>Escanear outro cupom</Text>
        </Pressable>
        <Pressable style={estilos.botaoSecundario} onPress={aoInicio}>
          <Text style={estilos.botaoSecundarioTexto}>Voltar ao início</Text>
        </Pressable>
      </View>
    );
  }

  if (erro) {
    return (
      <View style={estilos.tela}>
        <Text style={[estilos.titulo, { color: cores.erro }]}>Não consegui verificar a nota</Text>
        <View style={estilos.cartao}>
          <Text style={estilos.textoErro}>{erro}</Text>
        </View>
        <Pressable style={estilos.botao} onPress={() => setTentativa((n) => n + 1)}>
          <Text style={estilos.botaoTexto}>Tentar de novo</Text>
        </Pressable>
        <Pressable style={estilos.botaoSecundario} onPress={aoInicio}>
          <Text style={estilos.botaoSecundarioTexto}>Voltar ao início</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={[estilos.tela, { justifyContent: 'center', alignItems: 'center' }]}>
      <ActivityIndicator size="large" />
      <Text style={{ marginTop: 12, color: cores.suave }}>Verificando se a nota já existe...</Text>
    </View>
  );
}
