import { mount } from 'svelte';
import App from './App.svelte';
// Self-hosted variable font with optical sizing (the CSP only allows fonts from this origin); browsers download only the subsets a page uses.
import '@fontsource-variable/inter/opsz.css';
import './app.css';

const target = document.getElementById('app');
if (!target) throw new Error('No se encontró el contenedor #app');

export default mount(App, { target });
