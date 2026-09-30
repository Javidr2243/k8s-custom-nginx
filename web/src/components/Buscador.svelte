<script lang="ts">
  // Search overlay (native <dialog>: focus trap and Esc for free). Grouped, accent-insensitive results.
  import { onMount } from 'svelte';
  import { api, MUNICIPIOS, NOMBRE_CORTO } from '../lib/data';
  import { GLOSARIO } from '../lib/glosario';
  import { CAPITULOS } from '../lib/capitulos';
  import { buscar, type Resultado } from '../lib/search';
  import { navigate } from '../lib/router.svelte';
  import { pesos } from '../lib/format';

  let { onclose }: { onclose: () => void } = $props();
  let dialog = $state<HTMLDialogElement | undefined>();
  let input = $state<HTMLInputElement | undefined>();
  let q = $state('');
  let indice = $state<Resultado[]>([]);
  let cargando = $state(true);

  const PAGINAS: Resultado[] = [
    { tipo: 'pagina', titulo: 'Mapa del gobierno', detalle: 'quién gasta y de dónde viene el dinero', href: '/mapa' },
    { tipo: 'pagina', titulo: 'Flujo del dinero', detalle: 'ingresos y gastos del año', href: '/flujo' },
    { tipo: 'pagina', titulo: 'Comparar municipios', detalle: 'gasto por habitante', href: '/comparar' },
    { tipo: 'pagina', titulo: '¿Se cumple el presupuesto?', detalle: 'aprobado contra gastado, dinero sin gastar', href: '/cumplimiento' },
    { tipo: 'pagina', titulo: 'Deuda', detalle: 'saldo, créditos, intereses, calificación', href: '/deuda' },
    { tipo: 'pagina', titulo: 'Contratos y proveedores', detalle: 'licitaciones, adjudicaciones', href: '/contratos' },
    { tipo: 'pagina', titulo: 'Movimientos recientes', detalle: 'cambios del último trimestre', href: '/movimientos' },
    { tipo: 'pagina', titulo: 'Acerca de los datos', detalle: 'método, límites y privacidad', href: '/acerca' },
    { tipo: 'pagina', titulo: 'Fuentes y verificación', detalle: 'documentos oficiales, copias, huellas y verificaciones', href: '/fuentes' },
  ];

  onMount(() => {
    dialog?.showModal();
    input?.focus();
    const base: Resultado[] = [
      ...PAGINAS,
      ...Object.entries(GLOSARIO).map(([id, e]) => ({ tipo: 'termino' as const, titulo: e.termino, detalle: e.corto, href: `/glosario#${id}` })),
      ...Object.entries(CAPITULOS).flatMap(([k, c]) =>
        MUNICIPIOS.map((m) => ({ tipo: 'capitulo' as const, titulo: c.sencillo, detalle: `${c.nombre} · ${NOMBRE_CORTO[m]}`, href: `/mapa?m=${m}&n=cap-${k}` })),
      ),
    ];
    indice = base;
    Promise.all([api.egresos('monterrey'), ...MUNICIPIOS.map((m) => api.contratos(m))])
      .then(([egr, ...cons]) => {
        const deps = egr.periodos.at(-1)?.dependencias ?? [];
        const extra: Resultado[] = deps.map((d) => ({
          tipo: 'dependencia',
          titulo: d.nombre,
          detalle: `Monterrey · gastado ${pesos(d.montos.devengado)}`,
          href: `/mapa?m=monterrey&n=${encodeURIComponent(d.id)}`,
        }));
        cons.forEach((c, i) => {
          const m = MUNICIPIOS[i]!;
          const vistos = new Set<string>();
          for (const x of c.contratos) {
            if (x.tipo_persona !== 'reservada' && !vistos.has(x.proveedor)) {
              vistos.add(x.proveedor);
              extra.push({ tipo: 'proveedor', titulo: x.proveedor, detalle: `${NOMBRE_CORTO[m]}${x.rfc ? ` · RFC ${x.rfc}` : ''}`, href: `/contratos?m=${m}` });
            }
          }
        });
        indice = [...base, ...extra];
      })
      .finally(() => (cargando = false));
  });

  const resultados = $derived(buscar(q, indice, 40));
  const GRUPOS: [Resultado['tipo'], string][] = [
    ['pagina', 'Secciones'],
    ['dependencia', 'Dependencias'],
    ['capitulo', 'Tipos de gasto'],
    ['proveedor', 'Proveedores'],
    ['termino', 'Glosario'],
  ];

  function ir(r: Resultado) {
    dialog?.close();
    navigate(r.href);
  }
</script>

<dialog bind:this={dialog} class="buscador" aria-label="Buscar" onclose={onclose} onclick={(e) => e.target === dialog && dialog?.close()}>
  <div class="caja">
    <div class="fila">
      <label class="campo">
        <span class="sr-only">Buscar dependencias, tipos de gasto, proveedores o términos</span>
        <input bind:this={input} bind:value={q} type="search" placeholder="Busca una dependencia, un proveedor o un término…" autocomplete="off" />
      </label>
      <button type="button" class="btn" onclick={() => dialog?.close()}>Cerrar</button>
    </div>
    <div class="res" aria-live="polite">
      {#if q.trim().length < 2}
        <p class="muted small">Escribe al menos dos letras. Ejemplos: «seguridad», «obra pública», «predial», un proveedor.</p>
      {:else if !resultados.length}
        <p class="muted small">{cargando ? 'Cargando…' : 'Sin resultados.'}</p>
      {:else}
        {#each GRUPOS as [tipo, nombre] (tipo)}
          {@const lista = resultados.filter((r) => r.tipo === tipo)}
          {#if lista.length}
            <h2 class="grupo">{nombre}</h2>
            <ul>
              {#each lista.slice(0, 8) as r, i (i)}
                <li>
                  <a href={r.href} onclick={(e) => { e.preventDefault(); ir(r); }}>
                    <span class="t">{r.titulo}</span>
                    <span class="d small muted">{r.detalle}</span>
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
        {/each}
      {/if}
    </div>
  </div>
</dialog>

<style>
  .buscador {
    width: min(720px, calc(100vw - 32px));
    max-height: min(80vh, 720px);
    margin: 8vh auto auto;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--ink);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
  }
  .buscador::backdrop {
    background: rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(2px);
  }
  .caja {
    display: grid;
    grid-template-rows: auto 1fr;
    max-height: inherit;
  }
  .fila {
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem;
    border-bottom: 1px solid var(--border);
  }
  .campo {
    flex: 1;
  }
  input {
    width: 100%;
    min-height: 48px;
    padding: 0.5rem 0.75rem;
    font: inherit;
    font-size: 1.05rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--page);
    color: var(--ink);
  }
  .res {
    overflow-y: auto;
    padding: 0.5rem 0.75rem 1rem;
  }
  .grupo {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-2);
    margin: 0.75rem 0 0.25rem;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  a {
    display: grid;
    padding: 0.5rem 0.6rem;
    border-radius: var(--radius-sm);
    text-decoration: none;
    color: var(--ink);
    min-height: 44px;
  }
  a:hover,
  a:focus-visible {
    background: var(--surface-2);
  }
  .d {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
