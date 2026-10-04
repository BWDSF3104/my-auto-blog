import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://BWDSF3104.github.io',
  base: '/my-auto-blog',
  image: {
    domains: ['cdn.buymeacoffee.com'],
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
