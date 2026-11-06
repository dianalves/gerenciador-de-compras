// Abre a consulta da SEFAZ; o usuário resolve o captcha e a nota é capturada sozinha.
import { useRef, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { WebView, WebViewMessageEvent } from 'react-native-webview';

import { cores, estilos } from '../estilo';

type Props = {
  link: string;
  aoCapturar: (html: string) => void;
  aoVoltar: () => void;
};

// O link vai como o Chrome mandaria: a WebView usa o mesmo motor e faz a mesma codificação.
// Nada de disfarçar user-agent ou cabeçalhos: firewalls anti-robô detectam a incoerência
// e bloqueiam o IP inteiro por um tempo.
export function linkSeguro(link: string): string {
  return link.trim();
}

// Roda dentro da página da SEFAZ: espera os itens e o total aparecerem e devolve o HTML.
const OBSERVAR_NOTA = `
(function () {
  if (window.__comprasObservando) return;
  window.__comprasObservando = true;
  var enviado = false;
  function verificar() {
    if (enviado || !document.body) return;
    if (/requested URL was rejected/i.test(document.body.innerText)) {
      enviado = true;
      window.ReactNativeWebView.postMessage(JSON.stringify({ tipo: 'bloqueado' }));
      return;
    }
    var temItens = document.querySelector('span.txtTit');
    var temTotal = /valor a pagar/i.test(document.body.innerText);
    if (temItens && temTotal) {
      enviado = true;
      window.ReactNativeWebView.postMessage(JSON.stringify({
        tipo: 'nota', html: document.documentElement.outerHTML
      }));
    }
  }
  setInterval(verificar, 1000);
  verificar();
})();
true;
`;

export default function Sefaz({ link, aoCapturar, aoVoltar }: Props) {
  const [carregando, setCarregando] = useState(true);
  const [bloqueado, setBloqueado] = useState(false);
  const capturou = useRef(false);

  function aoReceber(evento: WebViewMessageEvent) {
    if (capturou.current) return;
    try {
      const mensagem = JSON.parse(evento.nativeEvent.data);
      if (mensagem.tipo === 'bloqueado') {
        setBloqueado(true);
        return;
      }
      if (mensagem.tipo === 'nota' && typeof mensagem.html === 'string') {
        capturou.current = true;
        aoCapturar(mensagem.html);
      }
    } catch {
      // mensagem que não é nossa: ignora
    }
  }

  return (
    <View style={{ flex: 1, backgroundColor: cores.fundo, paddingTop: 44 }}>
      <View style={{ paddingHorizontal: 16, paddingBottom: 8 }}>
        <View style={estilos.linha}>
          <Text style={{ fontSize: 16, fontWeight: '700', color: cores.texto, flex: 1 }}>
            Resolva o captcha e consulte
          </Text>
          <Pressable onPress={aoVoltar} hitSlop={12}>
            <Text style={{ color: cores.primaria, fontWeight: '700' }}>Cancelar</Text>
          </Pressable>
        </View>
        <Text style={{ color: cores.suave, fontSize: 13 }}>
          Quando a nota aparecer, ela será importada automaticamente.
        </Text>
      </View>
      <WebView
        source={{ uri: linkSeguro(link) }}
        injectedJavaScript={OBSERVAR_NOTA}
        onMessage={aoReceber}
        onLoadEnd={() => setCarregando(false)}
        javaScriptEnabled
        domStorageEnabled
        style={{ flex: 1 }}
      />
      {bloqueado && (
        <View style={[estilos.cartao, { position: 'absolute', top: 140, left: 16, right: 16 }]}>
          <Text style={estilos.textoErro}>
            O site da SEFAZ recusou o acesso pelo app ("The requested URL was rejected").
          </Text>
          <Text style={{ color: cores.suave, marginTop: 8 }}>
            O firewall da SEFAZ bloqueia a sua conexão por um tempo (geralmente 30 a 60
            minutos). Não tente de novo agora: cada tentativa pode prolongar o bloqueio.
          </Text>
          <Pressable style={estilos.botaoSecundario} onPress={aoVoltar}>
            <Text style={estilos.botaoSecundarioTexto}>Voltar</Text>
          </Pressable>
        </View>
      )}
      {carregando && (
        <ActivityIndicator style={{ position: 'absolute', top: '50%', alignSelf: 'center' }} />
      )}
    </View>
  );
}
