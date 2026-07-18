import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // Relative assets keep the static build portable to a GitHub Pages project site.
  base: './',
  plugins: [react()],
})
