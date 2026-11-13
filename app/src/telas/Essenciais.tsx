// Quem mora na casa + itens que não podem faltar (definidos pelo usuário) e a previsão.
import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback, useEffect, useState } from 'react';
import { Alert, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { api, Casa, Essencial, PrevisaoEssencial } from '../api';
import SeletorEstoque, { ParteEstoque } from '../componentes/SeletorEstoque';
import { cores, estilos } from '../estilo';
import { numero, quandoAcaba } from '../formato';
import FormEssencial from './FormEssencial';

type Props = { aoTrocarParte: (parte: ParteEstoque) => void };

const COR_SITUACAO: Record<string, string> = {
  acabou: cores.erro,
  acabando: cores.alerta,
  ok: cores.primaria,
  sem_tamanho: cores.suave,
};

function semAcento(texto: string): string {
  return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();
}

function compra(e: Essencial): string {
  const qtd = numero(e.quantidade_pacote ?? 1, 3);
  if (e.unidade === 'un') return `Compra ${qtd} ${Number(e.quantidade_pacote ?? 1) === 1 ? 'unidade' : 'unidades'}`;
  return `Compra ${qtd} ${e.unidade}`;
}

export default function Essenciais({ aoTrocarParte }: Props) {
  const [casa, setCasa] = useState<Casa | null>(null);
  const [essenciais, setEssenciais] = useState<Essencial[]>([]);
  const [previsoes, setPrevisoes] = useState<Record<number, PrevisaoEssencial>>({});
  const [formulario, setFormulario] = useState<{ essencial?: Essencial } | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const [c, e, p] = await Promise.all([api.casa(), api.essenciais(), api.previsaoEssenciais()]);
      setCasa(c);
      setEssenciais(e);
      setPrevisoes(Object.fromEntries(p.map((x) => [x.essencial_id, x])));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function mudarCasa(campo: keyof Casa, delta: number) {
    if (!casa) return;
    const minimo = campo === 'adultos' ? 1 : 0;
    const nova = { ...casa, [campo]: Math.max(minimo, casa[campo] + delta) };
    if (nova[campo] === casa[campo]) return;
    setCasa(nova);
    try {
      await api.salvarCasa(nova);
      await carregar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  function remover(e: Essencial) {
    Alert.alert('Remover essencial', `Remover "${e.nome}" dos essenciais?`, [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Remover',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.apagarEssencial(e.id);
            await carregar();
          } catch (err) {
            setErro((err as Error).message);
          }
        },
      },
    ]);
  }

  if (formulario) {
    return (
      <FormEssencial
        key={formulario.essencial?.id ?? 'novo'}
        inicial={formulario.essencial}
        aoTerminar={() => {
          setFormulario(null);
          carregar();
        }}
        aoAbrirExistente={(nome) => {
          const alvo = semAcento(nome);
          const existente = essenciais.find((e) => semAcento(e.nome) === alvo);
          setFormulario(existente ? { essencial: existente } : null);
        }}
      />
    );
  }

  const ativos = essenciais.filter((e) => e.ativo);

  return (
    <ScrollView
      style={estilos.tela}
      refreshControl={<RefreshControl refreshing={carregando} onRefresh={carregar} />}
    >
      <SeletorEstoque atual="essenciais" aoTrocar={aoTrocarParte} />
      <Text style={estilos.titulo}>Essenciais</Text>
      <Text style={estilos.subtitulo}>O que não pode faltar e quando vai acabar</Text>

      <Pressable style={estilos.botao} onPress={() => setFormulario({})}>
        <Text style={estilos.botaoTexto}>+ Adicionar essencial</Text>
      </Pressable>

      {erro && <Text style={[estilos.textoErro, { marginBottom: 12 }]}>{erro}</Text>}

      {ativos.length > 0 && (
        <View style={estilos.cartao}>
          <Text style={{ fontWeight: '700', color: cores.texto, marginBottom: 4 }}>Acompanhando</Text>
          {ativos.map((e, k) => {
            const p = previsoes[e.id];
            const cor = p ? COR_SITUACAO[p.situacao] : cores.suave;
            return (
              <View key={e.id} style={{ paddingVertical: 10, borderTopWidth: k ? 1 : 0, borderTopColor: cores.borda }}>
                <View style={estilos.linha}>
                  <Text style={{ color: cores.texto, fontSize: 16, fontWeight: '600', flex: 1 }}>{e.nome}</Text>
                  <Pressable
                    onPress={() => remover(e)}
                    hitSlop={10}
                    accessibilityRole="button"
                    accessibilityLabel={`Remover ${e.nome} dos essenciais`}
                  >
                    <Ionicons name="trash-outline" size={20} color={cores.suave} />
                  </Pressable>
                </View>
                {p && p.situacao !== 'sem_tamanho' && (
                  <Text style={{ color: cor, fontWeight: '700' }}>
                    {p.situacao === 'acabou'
                      ? 'Acabou'
                      : `~${numero(p.estoque)} ${p.unidade} · ${quandoAcaba(p.dias_restantes, p.acaba_em)}`}
                  </Text>
                )}
                {p && p.sem_tamanho.length > 0 && (
                  <Text style={{ color: cores.suave, fontSize: 12 }}>
                    Sem tamanho no cupom: {p.sem_tamanho.join(', ')}
                  </Text>
                )}
                <Pressable onPress={() => setFormulario({ essencial: e })} hitSlop={6}>
                  <Text style={{ color: cores.suave, fontSize: 13, marginTop: 2 }}>
                    {e.dura_pacote_dias
                      ? `${compra(e)} · dura ~${Math.round(e.dura_pacote_dias)} dias`
                      : 'Defina quanto dura'}{' '}
                    · <Text style={{ color: cores.primaria }}>editar</Text>
                  </Text>
                </Pressable>
              </View>
            );
          })}
        </View>
      )}

      {ativos.length === 0 && !carregando && (
        <View style={estilos.cartao}>
          <Text style={{ color: cores.texto }}>
            Adicione os itens que não podem faltar na sua casa. O app avisa quando estiverem
            acabando.
          </Text>
        </View>
      )}

      {casa && (
        <View style={estilos.cartao}>
          <Text style={{ fontWeight: '700', color: cores.texto, marginBottom: 8 }}>Quem mora na casa</Text>
          {(
            [
              ['adultos', 'Adultos'],
              ['criancas', 'Crianças'],
              ['pets', 'Pets'],
            ] as [keyof Casa, string][]
          ).map(([campo, rotulo]) => (
            <View key={campo} style={[estilos.linha, { paddingVertical: 6 }]}>
              <Text style={{ color: cores.texto, flex: 1 }}>{rotulo}</Text>
              <Pressable style={estilos.botaoMini} onPress={() => mudarCasa(campo, -1)} hitSlop={6}>
                <Text style={estilos.botaoMiniTexto}>−</Text>
              </Pressable>
              <Text style={{ width: 36, textAlign: 'center', fontSize: 17, fontWeight: '700' }}>
                {casa[campo]}
              </Text>
              <Pressable style={estilos.botaoMini} onPress={() => mudarCasa(campo, 1)} hitSlop={6}>
                <Text style={estilos.botaoMiniTexto}>+</Text>
              </Pressable>
            </View>
          ))}
          <Text style={{ color: cores.suave, fontSize: 12, marginTop: 4 }}>
            Criança conta como meia pessoa no consumo.
          </Text>
        </View>
      )}

      <View style={{ height: 24 }} />
    </ScrollView>
  );
}
