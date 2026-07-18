import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // GitHub Actions supplies /repository-name/; local builds retain portable relative paths.
  base: process.env.VITE_BASE_PATH || './',
  plugins: [react()],
})
