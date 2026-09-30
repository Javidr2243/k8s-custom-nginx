import { defineConfig } from 'vitest/config';
import type { Plugin } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { cpSync, createReadStream, existsSync, statSync } from 'node:fs';
import { resolve, normalize, sep } from 'node:path';

// The pipeline writes the app's JSON to ../data/public. In dev we serve it at
// /data/, and at build time we copy it into dist/data/.
const DATA_DIR = resolve(import.meta.dirname, '../data/public');
// Archived copies of the official originals, served at /data/originales/ so any figure can be verified
// even if the government link stops working.
const RAW_DIR = resolve(import.meta.dirname, '../data/raw');

function publicData(): Plugin {
  return {
    name: 'public-data',
    configureServer(server) {
      server.middlewares.use('/data', (req, res, next) => {
        let rel = normalize(decodeURIComponent((req.url ?? '/').split('?')[0] ?? '/'));
        let base = DATA_DIR;
        if (rel.startsWith('/originales/')) {
          base = RAW_DIR;
          rel = rel.slice('/originales'.length);
        }
        const file = resolve(base, '.' + rel);
        if (!file.startsWith(base + sep) || !existsSync(file) || !statSync(file).isFile()) {
          return next();
        }
        res.setHeader('Content-Type', file.endsWith('.json') ? 'application/json' : 'application/octet-stream');
        if (base === RAW_DIR) res.setHeader('Content-Disposition', 'attachment');
        createReadStream(file).pipe(res);
      });
    },
    writeBundle(options) {
      if (existsSync(DATA_DIR)) {
        cpSync(DATA_DIR, resolve(options.dir ?? 'dist', 'data'), { recursive: true });
      }
      if (existsSync(RAW_DIR)) {
        cpSync(RAW_DIR, resolve(options.dir ?? 'dist', 'data', 'originales'), { recursive: true });
      }
    },
  };
}

export default defineConfig({
  plugins: [svelte(), publicData()],
  build: {
    target: 'es2022',
    sourcemap: false,
    // No inlined assets: keeps the CSP simple (everything is served from 'self').
    assetsInlineLimit: 0,
    modulePreload: { polyfill: false },
  },
  test: {
    include: ['src/**/*.test.ts'],
  },
});
