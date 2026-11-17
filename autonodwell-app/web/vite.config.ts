import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development, /api is proxied to the FastAPI server, mirroring production where
// Firebase Hosting rewrites /api/** to Cloud Run. The browser only ever sees one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: true } },
    watch: { usePolling: true, interval: 500 },
  },
})
