import { Text, View } from 'react-native';

import { estilos } from '../estilo';

export default function EmBreve({ titulo, descricao }: { titulo: string; descricao: string }) {
  return (
    <View style={estilos.tela}>
      <Text style={estilos.titulo}>{titulo}</Text>
      <Text style={estilos.subtitulo}>{descricao}</Text>
      <View style={estilos.cartao}>
        <Text>Em construção.</Text>
      </View>
    </View>
  );
}
