import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const backend = 'http://127.0.0.1:8765';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../staged/research-wiki/app',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
  },
  server: {
    proxy: { '/api': backend, '/files': backend },
  },
});
