// =============================================================================
// IPA Platform - Vite Configuration
// =============================================================================
// Sprint 5: Frontend UI - Build Tool Configuration
// Sprint 102: Added vitest configuration for unit tests
//
// Vite configuration for React + TypeScript development.
// Includes path aliases, proxy settings, build optimization, and test config.
//
// Dependencies:
//   - @vitejs/plugin-react
// =============================================================================

/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 4070,
    proxy: {
      '/api': {
        target: 'http://localhost:8044',
        changeOrigin: true,
        // SSE streaming requires these settings to prevent buffering
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            // Disable compression so SSE events flow through immediately
            proxyReq.setHeader('Accept-Encoding', 'identity');
          });
          proxy.on('proxyRes', (proxyRes) => {
            // Disable buffering for SSE streams
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache';
              proxyRes.headers['x-accel-buffering'] = 'no';
            }
          });
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/'],
    },
  },
});
