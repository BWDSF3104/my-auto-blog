import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: process.env.SITE_ORIGIN || 'https://BWDSF3104.github.io',
  base: process.env.SITE_BASE_PATH || '/my-auto-blog',
  image: {
    domains: ['cdn.buymeacoffee.com'],
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
