// Câmera lendo o QR code do cupom.
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRef, useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { cores, estilos } from '../estilo';

type Props = { aoLer: (link: string) => void; aoVoltar: () => void };

// O QR da NFC-e leva à consulta da SEFAZ (ex.: ...fazenda.sp.gov.br/...?p=CHAVE|...)
function pareceNfce(texto: string): boolean {
  return /^https?:\/\//i.test(texto) && /(fazenda|sefaz|nfce)/i.test(texto);
}

export default function Scanner({ aoLer, aoVoltar }: Props) {
  const [permissao, pedirPermissao] = useCameraPermissions();
  const [aviso, setAviso] = useState<string | null>(null);
  const jaLeu = useRef(false); // a câmera dispara várias leituras por segundo

  if (!permissao) return <View style={estilos.tela} />;

  if (!permissao.granted) {
    return (
      <View style={estilos.tela}>
        <Text style={estilos.titulo}>Câmera</Text>
        <Text style={estilos.subtitulo}>Precisamos da câmera para ler o QR code do cupom.</Text>
        <Pressable style={estilos.botao} onPress={pedirPermissao}>
          <Text style={estilos.botaoTexto}>Permitir câmera</Text>
        </Pressable>
        <Pressable style={estilos.botaoSecundario} onPress={aoVoltar}>
          <Text style={estilos.botaoSecundarioTexto}>Voltar</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#000' }}>
      <CameraView
        style={{ flex: 1 }}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
        onBarcodeScanned={({ data }) => {
          if (jaLeu.current) return;
          if (!pareceNfce(data)) {
            setAviso('Esse QR code não parece ser de uma nota fiscal (NFC-e).');
            return;
          }
          jaLeu.current = true;
          aoLer(data);
        }}
      />
      <View style={{ position: 'absolute', top: 60, left: 16, right: 16 }}>
        <Text style={{ color: '#FFF', fontSize: 18, fontWeight: '700', textAlign: 'center' }}>
          Aponte para o QR code do cupom
        </Text>
        {aviso && (
          <Text style={{ color: '#FFD27A', textAlign: 'center', marginTop: 8 }}>{aviso}</Text>
        )}
      </View>
      <View style={{ position: 'absolute', bottom: 40, left: 16, right: 16 }}>
        <Pressable style={[estilos.botaoSecundario, { backgroundColor: cores.cartao }]} onPress={aoVoltar}>
          <Text style={estilos.botaoSecundarioTexto}>Cancelar</Text>
        </Pressable>
      </View>
    </View>
  );
}
