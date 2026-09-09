import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Dev only: forwards /api to the local Django server, so no CORS
      // configuration is needed while developing locally.
      '/api': 'http://127.0.0.1:8000',
      // Officer login is still server-rendered; proxy it too so the header
      // account menu reaches it from the Vite dev server.
      '/accounts': 'http://127.0.0.1:8000',
    },
  },
})
