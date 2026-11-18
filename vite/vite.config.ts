import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import svgr from "vite-plugin-svgr"

// https://vite.dev/config/
export default defineConfig({
  build: {
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      input: {
        main: 'index.html',
        t3k_callback: 't3k_response.html',  // your alternate page
      }
    }
  },
  plugins: [react(),svgr()],
  server: {
    proxy: {
      '/resources': {
        target: 'http://localhost:8080',
        changeOrigin: false,
      },
      '^/var/.*': {
        target: 'http://localhost:8080',
        changeOrigin: false,
      },
    }
  },
  preview: {
    host: true,
    port: 5173,
    proxy: {
      '/pipedal': {
        target: 'http://127.0.0.1:80',
        changeOrigin: false,
        ws: true,
      },
      '/resources': {
        target: 'http://127.0.0.1:80',
        changeOrigin: false,
      },
      '^/var/.*': {
        target: 'http://127.0.0.1:80',
        changeOrigin: false,
      },
    }
  }
})
