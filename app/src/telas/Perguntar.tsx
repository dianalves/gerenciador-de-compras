// Conversa com o assistente de compras (agente LangGraph na API).
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  type ScrollViewInstance,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from 'react-native';

import { api, MensagemConversa } from '../api';
import { cores, estilos } from '../estilo';

type Mensagem = MensagemConversa & { ferramentas?: string[]; erro?: boolean };

const SUGESTOES = [
  'Quanto gastei este mês?',
  'Com o que eu mais gasto?',
  'O que ficou mais caro?',
  'Onde a coca-cola é mais barata?',
  'O que tem de bebida em casa?',
];

// Nomes das ferramentas em português, para mostrar "consultou: gastos, estoque"
const NOMES: Record<string, string> = {
  gasto_total: 'gastos',
  gasto_por_categoria: 'gastos por categoria',
  produtos_mais_gastos: 'produtos',
  compras_no_periodo: 'compras',
  buscar_produtos: 'produtos',
  historico_preco: 'histórico de preço',
  comparar_mercados: 'mercados',
  produtos_que_mudaram_de_preco: 'variação de preço',
  estoque_atual: 'estoque',
};

export default function Perguntar() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [texto, setTexto] = useState('');
  const [pensando, setPensando] = useState(false);
  const rolagem = useRef<ScrollViewInstance>(null);

  async function enviar(pergunta: string) {
    pergunta = pergunta.trim();
    if (!pergunta || pensando) return;
    const historico: MensagemConversa[] = mensagens
      .filter((m) => !m.erro)
      .map(({ papel, texto: t }) => ({ papel, texto: t }));
    setMensagens((atuais) => [...atuais, { papel: 'usuario', texto: pergunta }]);
    setTexto('');
    setPensando(true);
    try {
      const r = await api.perguntar(pergunta, historico);
      const consultas = [...new Set(r.ferramentas.map((f) => NOMES[f.nome] ?? f.nome))];
      setMensagens((atuais) => [...atuais, { papel: 'assistente', texto: r.resposta, ferramentas: consultas }]);
    } catch (e) {
      setMensagens((atuais) => [...atuais, { papel: 'assistente', texto: (e as Error).message, erro: true }]);
    } finally {
      setPensando(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: cores.fundo }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        ref={rolagem}
        style={estilos.tela}
        onContentSizeChange={() => rolagem.current?.scrollToEnd({ animated: true })}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={estilos.titulo}>Perguntar</Text>
        <Text style={estilos.subtitulo}>Pergunte sobre gastos, preços e o que tem em casa</Text>

        {mensagens.length === 0 && (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginBottom: 12 }}>
            {SUGESTOES.map((s) => (
              <Pressable
                key={s}
                onPress={() => enviar(s)}
                style={{
                  borderWidth: 1,
                  borderColor: cores.borda,
                  backgroundColor: cores.cartao,
                  borderRadius: 16,
                  paddingVertical: 8,
                  paddingHorizontal: 12,
                  marginRight: 8,
                  marginBottom: 8,
                }}
              >
                <Text style={{ color: cores.texto }}>{s}</Text>
              </Pressable>
            ))}
          </View>
        )}

        {mensagens.map((m, i) => {
          const minha = m.papel === 'usuario';
          return (
            <View
              key={i}
              style={{
                alignSelf: minha ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                backgroundColor: minha ? cores.primaria : cores.cartao,
                borderWidth: minha ? 0 : 1,
                borderColor: cores.borda,
                borderRadius: 14,
                padding: 12,
                marginBottom: 8,
              }}
            >
              <Text style={{ color: minha ? '#FFF' : m.erro ? cores.erro : cores.texto, fontSize: 15 }}>
                {m.texto}
              </Text>
              {!!m.ferramentas?.length && (
                <Text style={{ color: cores.suave, fontSize: 12, marginTop: 6 }}>
                  consultou: {m.ferramentas.join(', ')}
                </Text>
              )}
            </View>
          );
        })}

        {pensando && (
          <View style={[estilos.linha, { alignSelf: 'flex-start', marginBottom: 8 }]}>
            <ActivityIndicator />
            <Text style={{ color: cores.suave, marginLeft: 8 }}>Pensando... (pode levar uns segundos)</Text>
          </View>
        )}
        <View style={{ height: 16 }} />
      </ScrollView>

      <View
        style={{
          flexDirection: 'row',
          padding: 8,
          borderTopWidth: 1,
          borderTopColor: cores.borda,
          backgroundColor: cores.cartao,
        }}
      >
        <TextInput
          value={texto}
          onChangeText={setTexto}
          placeholder="Escreva sua pergunta"
          placeholderTextColor={cores.suave}
          onSubmitEditing={() => enviar(texto)}
          returnKeyType="send"
          editable={!pensando}
          style={{
            flex: 1,
            borderWidth: 1,
            borderColor: cores.borda,
            borderRadius: 20,
            paddingHorizontal: 14,
            paddingVertical: 10,
            fontSize: 16,
            color: cores.texto,
            backgroundColor: cores.fundo,
          }}
        />
        <Pressable
          onPress={() => enviar(texto)}
          disabled={pensando || !texto.trim()}
          style={{
            marginLeft: 8,
            backgroundColor: cores.primaria,
            borderRadius: 20,
            paddingHorizontal: 16,
            justifyContent: 'center',
            opacity: pensando || !texto.trim() ? 0.4 : 1,
          }}
        >
          <Text style={{ color: '#FFF', fontWeight: '700' }}>Enviar</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}
