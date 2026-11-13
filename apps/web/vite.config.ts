import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { findEngineRoot } from './build-paths.mjs';

const backend = 'http://127.0.0.1:8765';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: `${findEngineRoot(new URL('.', import.meta.url))}/app`,
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
  },
  server: {
    proxy: { '/api': backend, '/files': backend },
  },
});
