import { StyleSheet } from 'react-native';

export const cores = {
  fundo: '#F6F7F9',
  cartao: '#FFFFFF',
  texto: '#1B1F24',
  suave: '#5F6B7A',
  primaria: '#1F7A4D',
  alerta: '#B26A00',
  erro: '#B3261E',
  borda: '#E2E6EB',
};

export const estilos = StyleSheet.create({
  tela: { flex: 1, backgroundColor: cores.fundo, paddingTop: 52, paddingHorizontal: 16 },
  titulo: { fontSize: 24, fontWeight: '700', color: cores.texto, marginBottom: 4 },
  subtitulo: { fontSize: 14, color: cores.suave, marginBottom: 16 },
  cartao: {
    backgroundColor: cores.cartao,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: cores.borda,
  },
  botao: {
    backgroundColor: cores.primaria,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginVertical: 8,
  },
  botaoTexto: { color: '#FFFFFF', fontSize: 17, fontWeight: '700' },
  botaoSecundario: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginVertical: 4,
    borderWidth: 1,
    borderColor: cores.borda,
    backgroundColor: cores.cartao,
  },
  botaoSecundarioTexto: { color: cores.texto, fontSize: 16, fontWeight: '600' },
  linha: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  textoErro: { color: cores.erro, fontSize: 15 },
});
