<script lang="ts">
  import { onMount } from 'svelte';
  import { link, route, href } from './lib/router.svelte';
  import { api, type Meta } from './lib/data';
  import { fecha, trimestre } from './lib/format';
  import Tooltip from './components/Tooltip.svelte';
  import Buscador from './components/Buscador.svelte';
  import Inicio from './views/Inicio.svelte';
  import Mapa from './views/Mapa.svelte';
  import Comparar from './views/Comparar.svelte';
  import Flujo from './views/Flujo.svelte';
  import Deuda from './views/Deuda.svelte';
  import Contratos from './views/Contratos.svelte';
  import Movimientos from './views/Movimientos.svelte';
  import Glosario from './views/Glosario.svelte';
  import Acerca from './views/Acerca.svelte';
  import Fuentes from './views/Fuentes.svelte';
  import NoEncontrado from './views/NoEncontrado.svelte';

  const NAV = [
    { path: '/', label: 'Inicio' },
    { path: '/mapa', label: 'Mapa del gobierno' },
    { path: '/flujo', label: 'Flujo del dinero' },
    { path: '/comparar', label: 'Comparar' },
    { path: '/deuda', label: 'Deuda' },
    { path: '/contratos', label: 'Contratos' },
    { path: '/movimientos', label: 'Movimientos' },
    { path: '/fuentes', label: 'Fuentes' },
  ];
  const VISTAS = {
    '/': Inicio,
    '/mapa': Mapa,
    '/flujo': Flujo,
    '/comparar': Comparar,
    '/deuda': Deuda,
    '/contratos': Contratos,
    '/movimientos': Movimientos,
    '/glosario': Glosario,
    '/acerca': Acerca,
    '/fuentes': Fuentes,
  } as const;
  const TITULOS: Record<string, string> = {
    '/': 'Inicio',
    '/mapa': 'Mapa del gobierno',
    '/flujo': 'Flujo del dinero',
    '/comparar': 'Comparar municipios',
    '/deuda': 'Deuda',
    '/contratos': 'Contratos y proveedores',
    '/movimientos': 'Movimientos recientes',
    '/glosario': 'Glosario',
    '/acerca': 'Acerca de los datos',
    '/fuentes': 'Fuentes y verificación',
  };

  const ruta = $derived(route.path.replace(/\/+$/, '') || '/');
  const Vista = $derived(VISTAS[ruta as keyof typeof VISTAS] ?? NoEncontrado);
  $effect(() => {
    document.title = `${TITULOS[ruta] ?? 'Página no encontrada'} · ¿A dónde va tu dinero? MTY`;
  });

  let meta = $state<Meta | null>(null);
  let buscando = $state(false);
  let tema = $state<'auto' | 'light' | 'dark'>('auto');

  onMount(() => {
    api.meta().then((m) => (meta = m));
    try {
      const t = localStorage.getItem('tema');
      if (t === 'light' || t === 'dark') tema = t;
    } catch {
      /* storage may be unavailable */
    }
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      const escribiendo = el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable;
      if ((e.key === '/' && !escribiendo) || (e.key === 'k' && (e.metaKey || e.ctrlKey))) {
        e.preventDefault();
        buscando = true;
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  $effect(() => {
    const root = document.documentElement;
    if (tema === 'auto') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', tema);
    try {
      if (tema === 'auto') localStorage.removeItem('tema');
      else localStorage.setItem('tema', tema);
    } catch {
      /* ignore */
    }
  });

  function cambiarTema() {
    const oscuro =
      tema === 'dark' || (tema === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    tema = oscuro ? 'light' : 'dark';
  }
</script>

<a class="skip-link" href="#contenido">Saltar al contenido</a>

<header class="top">
  <div class="container bar">
    <a class="brand" href={href('/')} use:link>
      <span class="logo" aria-hidden="true">$</span>
      <span>¿A dónde va tu dinero? <strong>MTY</strong></span>
    </a>
    <div class="acciones">
      <button type="button" class="btn icono" onclick={() => (buscando = true)} aria-label="Buscar (atajo: /)">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"
          ><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2" /><path
            d="m20 20-3.5-3.5"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          /></svg
        >
        <span class="solo-ancho">Buscar</span>
      </button>
      <button type="button" class="btn icono" onclick={cambiarTema} aria-label="Cambiar entre modo claro y oscuro">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"
          ><path
            d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9Z"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linejoin="round"
          /></svg
        >
      </button>
    </div>
  </div>
  <nav class="container nav" aria-label="Secciones">
    {#each NAV as n (n.path)}
      <a href={href(n.path)} use:link aria-current={ruta === n.path ? 'page' : undefined}>{n.label}</a>
    {/each}
  </nav>
</header>

<main id="contenido" tabindex="-1" class="container" class:ancho={ruta === '/mapa'}>
  {#key ruta}
    <Vista />
  {/key}
</main>

<footer class="pie">
  <div class="container">
    <p>
      <strong>Sitio independiente, no oficial.</strong> Todas las cifras provienen de documentos oficiales de los
      municipios de Monterrey, San Pedro Garza García y Santa Catarina, del INEGI y de la Secretaría de Hacienda,
      y cada una enlaza a su fuente. Montos en pesos mexicanos nominales (sin ajustar por inflación).
    </p>
    <p>
      {#if meta}
        Datos actualizados al {fecha(meta.datos_al)}; el periodo más reciente es el {trimestre(meta.periodo_mas_reciente)}.
      {/if}
      <a href="/fuentes" use:link>Fuentes y verificación</a> ·
      <a href="/acerca" use:link>Acerca de los datos y privacidad</a> ·
      <a href="/glosario" use:link>Glosario</a> ·
      <a href="https://github.com/javidr2243/k8s-custom-nginx" rel="noopener noreferrer">Código y datos abiertos</a>
    </p>
    <p class="small">Este sitio no usa cookies ni rastreadores y no recopila datos personales.</p>
  </div>
</footer>

<Tooltip />
{#if buscando}
  <Buscador onclose={() => (buscando = false)} />
{/if}

<style>
  .top {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 30;
  }
  .bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    min-height: 60px;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    color: var(--ink);
    text-decoration: none;
    font-size: 1.05rem;
  }
  .logo {
    display: inline-grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--accent);
    color: var(--accent-ink);
    font-weight: 800;
  }
  .acciones {
    display: flex;
    gap: 0.5rem;
  }
  .icono {
    padding: 0.4rem 0.7rem;
  }
  .nav {
    display: flex;
    gap: 0.25rem;
    overflow-x: auto;
    scrollbar-width: thin;
    padding-bottom: 0.4rem;
  }
  .nav a {
    flex: none;
    padding: 0.55rem 0.8rem;
    border-radius: 999px;
    color: var(--ink-2);
    text-decoration: none;
    min-height: 44px;
    display: inline-flex;
    align-items: center;
  }
  .nav a:hover {
    background: var(--surface-2);
    color: var(--ink);
  }
  .nav a[aria-current='page'] {
    background: var(--ink);
    color: var(--surface);
  }
  main.ancho {
    max-width: 1560px;
  }
  main {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    outline: none;
    min-height: 60vh;
  }
  .pie {
    border-top: 1px solid var(--border);
    background: var(--surface);
    color: var(--ink-2);
    padding: 1.5rem 0 2rem;
    font-size: 0.9rem;
  }
  @media (max-width: 640px) {
    .solo-ancho {
      display: none;
    }
    .brand {
      font-size: 0.95rem;
    }
  }
</style>
