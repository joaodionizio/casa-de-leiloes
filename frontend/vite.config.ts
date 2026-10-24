import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em desenvolvimento o navegador vê uma só origem (a do Vite); o proxy leva
// /api e /health ao uvicorn local. Sem CORS (AD-29).
const API_TARGET = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Porta fixa: o backend só aceita escritas da origem APP_ORIGIN (AD-29);
    // se a 5173 estiver ocupada, falha em vez de subir em outra porta.
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': API_TARGET,
      '/health': API_TARGET,
    },
  },
})
