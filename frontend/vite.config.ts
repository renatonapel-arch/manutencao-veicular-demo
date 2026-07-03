import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Clavis · Manutenção Veicular',
        short_name: 'Manutenção',
        description: 'Gestão de manutenção da frota Napel',
        theme_color: '#113C58',
        background_color: '#FAFCFD',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          // SVG inline (data URI) — evita 404 dos PNGs sem precisar gerar imagens
          {
            src: "data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'%3E%3Crect width='192' height='192' rx='32' fill='%23113C58'/%3E%3Ctext x='96' y='128' font-family='system-ui,Apple Color Emoji' font-size='110' font-weight='700' fill='white' text-anchor='middle'%3E🔧%3C/text%3E%3C/svg%3E",
            sizes: '192x192 512x512',
            type: 'image/svg+xml',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        // SW novo assume controle IMEDIATO das abas abertas em vez de esperar
        // todas fecharem. Sem isso, um SW antigo (ex: cacheando /api errado)
        // podia sobreviver dias em quem deixa a aba do Clavis sempre aberta.
        skipWaiting: true,
        clientsClaim: true,
        globPatterns: ['**/*.{js,css,html,svg,png,ico}'],
        // NetworkOnly pra tudo em /api — NUNCA cachear.
        //
        // Motivo crítico: o Workbox usa a URL como chave de cache por padrão,
        // SEM considerar o header Authorization. Com SSO (Opção D), o mesmo
        // browser/dispositivo pode servir usuários DIFERENTES na mesma sessão
        // (ex.: Renato entra, sai, Hudson entra no mesmo Chrome). Um NetworkFirst
        // com cache fazia `/api/auth/me` cacheado por um usuário vazar pro
        // próximo que acessasse a mesma URL — apareceu "Olá, Hudson" com token
        // do Renato. Dado que TODO endpoint de auth é RBAC-sensível por usuário,
        // a única opção segura é não cachear nada de /api.
        runtimeCaching: [
          {
            urlPattern: /\/api\/.*/i,
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8765', changeOrigin: true },
      '/uploads': { target: 'http://localhost:8765', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          query: ['@tanstack/react-query', 'axios'],
        },
      },
    },
  },
})
