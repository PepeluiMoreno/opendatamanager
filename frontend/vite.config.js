import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/graphql': {
        target: process.env.API_TARGET || 'http://localhost:8002',
        changeOrigin: true,
      },
      '/api': {
        target: process.env.API_TARGET || 'http://localhost:8002',
        changeOrigin: true,
      }
    }
  }
})
