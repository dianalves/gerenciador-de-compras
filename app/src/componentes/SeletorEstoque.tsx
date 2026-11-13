// "Em casa | Essenciais" no topo da aba Estoque.
import { Pressable, Text, View } from 'react-native';

import { cores } from '../estilo';

export type ParteEstoque = 'em_casa' | 'essenciais';

type Props = { atual: ParteEstoque; aoTrocar: (parte: ParteEstoque) => void };

export default function SeletorEstoque({ atual, aoTrocar }: Props) {
  const opcoes: { id: ParteEstoque; rotulo: string }[] = [
    { id: 'em_casa', rotulo: 'Em casa' },
    { id: 'essenciais', rotulo: 'Essenciais' },
  ];
  return (
    <View
      style={{
        flexDirection: 'row',
        backgroundColor: cores.borda,
        borderRadius: 10,
        padding: 3,
        marginBottom: 12,
      }}
    >
      {opcoes.map((o) => {
        const ativa = o.id === atual;
        return (
          <Pressable
            key={o.id}
            onPress={() => aoTrocar(o.id)}
            style={{
              flex: 1,
              paddingVertical: 8,
              borderRadius: 8,
              alignItems: 'center',
              backgroundColor: ativa ? cores.cartao : 'transparent',
            }}
            accessibilityRole="tab"
            accessibilityState={{ selected: ativa }}
          >
            <Text style={{ fontWeight: ativa ? '700' : '500', color: ativa ? cores.texto : cores.suave }}>
              {o.rotulo}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}
