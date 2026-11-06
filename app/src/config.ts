// Endereço da API. Vem do arquivo .env.local (EXPO_PUBLIC_API_URL).
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://192.168.0.10:8000').replace(/\/$/, '');
