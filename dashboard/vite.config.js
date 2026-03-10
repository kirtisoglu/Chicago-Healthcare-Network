import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/api/health-atlas': {
        target: 'https://chicagohealthatlas.org',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api\/health-atlas/, '/api/v1'),
      },
    },
  },
});
