// Fluxo do app: Início -> Câmera (QR) -> Verificação (já existe?) -> SEFAZ (captcha) -> Resultado.
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { BackHandler } from 'react-native';

import Inicio from './src/telas/Inicio';
import Resultado from './src/telas/Resultado';
import Scanner from './src/telas/Scanner';
import Sefaz from './src/telas/Sefaz';
import Verificacao from './src/telas/Verificacao';

type Tela =
  | { nome: 'inicio' }
  | { nome: 'scanner' }
  | { nome: 'verificacao'; link: string }
  | { nome: 'sefaz'; link: string }
  | { nome: 'resultado'; link: string; html: string };

export default function App() {
  const [tela, setTela] = useState<Tela>({ nome: 'inicio' });

  // Botão "voltar" do Android volta para o início em vez de fechar o app.
  useEffect(() => {
    const assinatura = BackHandler.addEventListener('hardwareBackPress', () => {
      if (tela.nome === 'inicio') return false;
      setTela({ nome: 'inicio' });
      return true;
    });
    return () => assinatura.remove();
  }, [tela.nome]);

  const inicio = () => setTela({ nome: 'inicio' });
  const escanear = () => setTela({ nome: 'scanner' });

  return (
    <>
      <StatusBar style={tela.nome === 'scanner' ? 'light' : 'dark'} />
      {tela.nome === 'inicio' && <Inicio aoEscanear={escanear} />}
      {tela.nome === 'scanner' && (
        <Scanner aoVoltar={inicio} aoLer={(link) => setTela({ nome: 'verificacao', link })} />
      )}
      {tela.nome === 'verificacao' && (
        <Verificacao
          link={tela.link}
          aoNotaNova={() => setTela({ nome: 'sefaz', link: tela.link })}
          aoEscanearOutro={escanear}
          aoInicio={inicio}
        />
      )}
      {tela.nome === 'sefaz' && (
        <Sefaz
          link={tela.link}
          aoVoltar={inicio}
          aoCapturar={(html) => setTela({ nome: 'resultado', link: tela.link, html })}
        />
      )}
      {tela.nome === 'resultado' && (
        <Resultado link={tela.link} html={tela.html} aoEscanearOutro={escanear} aoInicio={inicio} />
      )}
    </>
  );
}
