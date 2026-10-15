import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Dev: cùng origin với backend FastAPI (docker compose up) để cookie refresh HttpOnly hoạt động không cần CORS.
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
