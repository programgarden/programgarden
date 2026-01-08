import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
      '/workflows': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
      '/workflow': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
      '/run': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
      '/stop': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
      '/events': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
})
