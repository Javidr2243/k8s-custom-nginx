import { defineConfig } from 'vitest/config';
import type { Plugin } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { cpSync, createReadStream, existsSync, statSync } from 'node:fs';
import { resolve, normalize, sep } from 'node:path';

// The pipeline writes the app's JSON to ../data/public. In dev we serve it at
// /data/, and at build time we copy it into dist/data/.
const DATA_DIR = resolve(import.meta.dirname, '../data/public');

function publicData(): Plugin {
  return {
    name: 'public-data',
    configureServer(server) {
      server.middlewares.use('/data', (req, res, next) => {
        const rel = normalize(decodeURIComponent((req.url ?? '/').split('?')[0] ?? '/'));
        const file = resolve(DATA_DIR, '.' + rel);
        if (!file.startsWith(DATA_DIR + sep) || !existsSync(file) || !statSync(file).isFile()) {
          return next();
        }
        res.setHeader('Content-Type', file.endsWith('.json') ? 'application/json' : 'text/plain; charset=utf-8');
        createReadStream(file).pipe(res);
      });
    },
    writeBundle(options) {
      if (existsSync(DATA_DIR)) {
        cpSync(DATA_DIR, resolve(options.dir ?? 'dist', 'data'), { recursive: true });
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
