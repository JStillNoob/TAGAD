import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendTarget = process.env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000'
const websocketTarget = backendTarget.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [vue()],
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: websocketTarget,
        ws: true,
      },
      '/admin': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/static/admin': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
})
