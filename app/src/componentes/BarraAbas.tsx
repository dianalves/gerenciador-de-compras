// Barra de navegação fixa no rodapé.
import { Pressable, Text, View } from 'react-native';

import { cores } from '../estilo';

export type Aba = 'inicio' | 'lista' | 'precos' | 'estoque' | 'perguntar';

const ABAS: { id: Aba; rotulo: string; icone: string }[] = [
  { id: 'inicio', rotulo: 'Início', icone: '⌂' },
  { id: 'lista', rotulo: 'Lista', icone: '☰' },
  { id: 'precos', rotulo: 'Preços', icone: '$' },
  { id: 'estoque', rotulo: 'Estoque', icone: '▦' },
  { id: 'perguntar', rotulo: 'Perguntar', icone: '?' },
];

type Props = { atual: Aba; aoTrocar: (aba: Aba) => void };

export default function BarraAbas({ atual, aoTrocar }: Props) {
  return (
    <View
      style={{
        flexDirection: 'row',
        borderTopWidth: 1,
        borderTopColor: cores.borda,
        backgroundColor: cores.cartao,
        paddingBottom: 18,
        paddingTop: 8,
      }}
    >
      {ABAS.map((aba) => {
        const ativa = aba.id === atual;
        const cor = ativa ? cores.primaria : cores.suave;
        return (
          <Pressable
            key={aba.id}
            onPress={() => aoTrocar(aba.id)}
            style={{ flex: 1, alignItems: 'center' }}
            accessibilityRole="tab"
            accessibilityState={{ selected: ativa }}
          >
            <Text style={{ fontSize: 20, color: cor }}>{aba.icone}</Text>
            <Text style={{ fontSize: 12, color: cor, fontWeight: ativa ? '700' : '500' }}>
              {aba.rotulo}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}
