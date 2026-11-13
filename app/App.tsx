// Abas: Início, Preços, Estoque, Perguntar.
// Fluxo de importação (tela cheia): Câmera -> Verificação -> SEFAZ -> Resultado.
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { BackHandler, View } from 'react-native';

import BarraAbas, { Aba } from './src/componentes/BarraAbas';
import { ParteEstoque } from './src/componentes/SeletorEstoque';
import { cores } from './src/estilo';
import Essenciais from './src/telas/Essenciais';
import Estoque from './src/telas/Estoque';
import Inicio from './src/telas/Inicio';
import Perguntar from './src/telas/Perguntar';
import Precos from './src/telas/Precos';
import Resultado from './src/telas/Resultado';
import Scanner from './src/telas/Scanner';
import Sefaz from './src/telas/Sefaz';
import Verificacao from './src/telas/Verificacao';

type Fluxo =
  | { nome: 'scanner' }
  | { nome: 'verificacao'; link: string }
  | { nome: 'sefaz'; link: string }
  | { nome: 'resultado'; link: string; html: string };

export default function App() {
  const [aba, setAba] = useState<Aba>('inicio');
  const [fluxo, setFluxo] = useState<Fluxo | null>(null);
  const [versao, setVersao] = useState(0); // muda após importar: recarrega as abas
  const [parteEstoque, setParteEstoque] = useState<ParteEstoque>('em_casa');

  // "Voltar" do Android: sai do fluxo de importação ou volta para o Início.
  useEffect(() => {
    const assinatura = BackHandler.addEventListener('hardwareBackPress', () => {
      if (fluxo) {
        setFluxo(null);
        return true;
      }
      if (aba !== 'inicio') {
        setAba('inicio');
        return true;
      }
      return false;
    });
    return () => assinatura.remove();
  }, [fluxo, aba]);

  const sairDoFluxo = () => {
    setFluxo(null);
    setVersao((v) => v + 1);
  };
  const escanear = () => setFluxo({ nome: 'scanner' });

  if (fluxo) {
    return (
      <>
        <StatusBar style={fluxo.nome === 'scanner' ? 'light' : 'dark'} />
        {fluxo.nome === 'scanner' && (
          <Scanner aoVoltar={sairDoFluxo} aoLer={(link) => setFluxo({ nome: 'verificacao', link })} />
        )}
        {fluxo.nome === 'verificacao' && (
          <Verificacao
            link={fluxo.link}
            aoNotaNova={() => setFluxo({ nome: 'sefaz', link: fluxo.link })}
            aoEscanearOutro={escanear}
            aoInicio={sairDoFluxo}
          />
        )}
        {fluxo.nome === 'sefaz' && (
          <Sefaz
            link={fluxo.link}
            aoVoltar={sairDoFluxo}
            aoCapturar={(html) => setFluxo({ nome: 'resultado', link: fluxo.link, html })}
          />
        )}
        {fluxo.nome === 'resultado' && (
          <Resultado link={fluxo.link} html={fluxo.html} aoEscanearOutro={escanear} aoInicio={sairDoFluxo} />
        )}
      </>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: cores.fundo }}>
      <StatusBar style="dark" />
      <View style={{ flex: 1 }} key={versao}>
        {aba === 'inicio' && (
          <Inicio
            aoEscanear={escanear}
            aoVerEssenciais={() => {
              setParteEstoque('essenciais');
              setAba('estoque');
            }}
          />
        )}
        {aba === 'precos' && <Precos />}
        {aba === 'estoque' && parteEstoque === 'em_casa' && <Estoque aoTrocarParte={setParteEstoque} />}
        {aba === 'estoque' && parteEstoque === 'essenciais' && (
          <Essenciais aoTrocarParte={setParteEstoque} />
        )}
        {aba === 'perguntar' && <Perguntar />}
      </View>
      <BarraAbas atual={aba} aoTrocar={setAba} />
    </View>
  );
}
