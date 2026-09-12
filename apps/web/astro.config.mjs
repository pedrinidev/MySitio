// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

const SITE_URL = process.env.PUBLIC_SITE_URL ?? 'https://pedrinidev.com';

export default defineConfig({
  site: SITE_URL,

  // Estático puro. No hay adapter de servidor a propósito: el droplet tiene
  // 512 MB de RAM y un proceso Node de SSR costaría 80-120 MB que no existen.
  // Ver docs/decisions.md, ADR-001.
  output: 'static',

  integrations: [react(), sitemap({ i18n: { defaultLocale: 'es', locales: { es: 'es-BO', en: 'en' } } })],

  vite: {
    plugins: [tailwindcss()],
    build: {
      // Presupuesto de bundle: avisa antes de que la home engorde sin querer.
      chunkSizeWarningLimit: 120,
    },
  },

  build: {
    // 'directory' genera /es/proyectos/index.html. Es lo que exigen los
    // enlaces del sitio, que apuntan a /es/ y /es/proyectos.
    // Con 'file' Astro emite /es.html y /es/proyectos.html, y todo enlace
    // con barra final daría 404 en producción.
    format: 'directory',
    inlineStylesheets: 'auto',
  },

  // 'ignore' acepta la URL con y sin barra final. Nginx resuelve ambas con
  // try_files (ver infra/nginx/site.conf); así ningún enlace compartido en
  // LinkedIn o WhatsApp se rompe por una barra de más o de menos.
  trailingSlash: 'ignore',

  image: { responsiveStyles: true },

  prefetch: { prefetchAll: true, defaultStrategy: 'viewport' },
});
