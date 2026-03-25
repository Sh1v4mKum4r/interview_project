import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    global: 'window',
  },
  optimizeDeps: {
    include: ['react-plotly.js/factory', 'plotly.js-dist-min'],
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:6969',
        changeOrigin: true,
      },
    },
  },
})
