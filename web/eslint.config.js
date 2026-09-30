import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import ts from 'typescript-eslint';
import globals from 'globals';
import svelteConfig from './svelte.config.js';

export default ts.config(
  { ignores: ['dist/', 'node_modules/', 'test-results/', 'playwright-report/'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...svelte.configs.recommended,
  {
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts'],
    languageOptions: {
      parserOptions: { projectService: true, extraFileExtensions: ['.svelte'], parser: ts.parser, svelteConfig },
    },
  },
  {
    rules: {
      // Security: text from government files must never be rendered as HTML.
      'svelte/no-at-html-tags': 'error',
      'no-restricted-properties': [
        'error',
        { property: 'innerHTML', message: 'No uses innerHTML: los datos externos deben escaparse.' },
        { property: 'outerHTML', message: 'No uses outerHTML.' },
        { property: 'insertAdjacentHTML', message: 'No uses insertAdjacentHTML.' },
      ],
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
    },
  },
);
