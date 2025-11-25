import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = fileURLToPath(new URL('.', import.meta.url));
const webDir = path.resolve(rootDir, '..');
const apiTarget = 'http://localhost:8000';
const proxyPaths = ['/files', '/search', '/ask', '/visibility', '/transcripts'];
const proxyConfig = Object.fromEntries(proxyPaths.map((key) => [key, { target: apiTarget, changeOrigin: true }]));
const htmlEntries = {
  index: path.resolve(rootDir, 'index.html'),
  admin: path.resolve(rootDir, 'admin.html'),
  docs: path.resolve(rootDir, 'dev.html'),
  chat: path.resolve(rootDir, 'chat.html'),
  login: path.resolve(rootDir, 'login.html'),
};

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5173,
    strictPort: true,
    proxy: proxyConfig,
    fs: {
      allow: [rootDir, webDir]
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(rootDir, 'src')
    }
  },
  build: {
    outDir: path.resolve(rootDir, '../react-dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: htmlEntries
    }
  },
  preview: {
    port: 4173,
    strictPort: true
  }
});

