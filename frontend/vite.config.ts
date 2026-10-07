import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8102' } },
  // The initial bundle stays small; the only large chunk is the lazily loaded
  // three.js factory scene (~880 kB), which three.js alone keeps above 500 kB.
  build: { chunkSizeWarningLimit: 900 },
})
