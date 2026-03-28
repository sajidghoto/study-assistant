// frontend/vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    // Proxy all /api requests to FastAPI backend.
    // This means Axios calls /api/v1/health — Vite forwards it to
    // http://localhost:8000/api/v1/health automatically.
    // No CORS issue during development because the browser sees
    // everything as same-origin (localhost:5173).
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})