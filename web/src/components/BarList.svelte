<script lang="ts" module>
  export interface Barra {
    id: string;
    etiqueta: string;
    valor: number | null;
    /** Optional second value drawn as a lighter bar behind (e.g. modificado behind devengado). */
    referencia?: number | null;
    color?: string; // colour class suffix: 'monterrey', 'cat-1', 'seq'…
    detalle?: string; // secondary text under the label
    tooltip?: { valor: string; etiqueta: string }[];
  }
</script>

<script lang="ts">
  // Horizontal bars: the best form for comparing magnitudes (and readable on a phone).
  // Thin bars (≤ 24px), rounded end, value at the tip, whole row is the hover/focus target.
  import { mostrar, ocultar, desde } from './Tooltip.svelte';
  import TablaAlterna from './TablaAlterna.svelte';

  let {
    barras,
    formato,
    titulo,
    referenciaEtiqueta,
    valorEtiqueta = 'Valor',
    onelegir,
    seleccionado = null,
  }: {
    barras: Barra[];
    formato: (n: number | null) => string;
    titulo: string;
    referenciaEtiqueta?: string;
    valorEtiqueta?: string;
    onelegir?: (id: string) => void;
    seleccionado?: string | null;
  } = $props();

  const max = $derived(Math.max(1, ...barras.map((b) => Math.max(b.valor ?? 0, b.referencia ?? 0))));

  function ancho(el: HTMLElement, v: number | null | undefined) {
    const set = (x: number | null | undefined) => {
      el.style.width = `${Math.max(0, ((x ?? 0) / max) * 100)}%`;
    };
    set(v);
    return { update: set };
  }

  function tip(ev: PointerEvent | FocusEvent, b: Barra) {
    const { x, y } = desde(ev);
    mostrar(x, y, b.etiqueta, b.tooltip ?? [{ valor: formato(b.valor), etiqueta: valorEtiqueta }]);
  }
</script>

<figure class="barlist">
  <figcaption class="sr-only">{titulo}</figcaption>
  <ul>
    {#each barras as b (b.id)}
      <li>
        {#if onelegir}
          <button
            type="button"
            class="row"
            class:sel={seleccionado === b.id}
            aria-pressed={seleccionado === b.id}
            aria-label={`${b.etiqueta}: ${formato(b.valor)}`}
            onclick={() => onelegir?.(b.id)}
            onpointermove={(e) => tip(e, b)}
            onpointerleave={ocultar}
            onfocus={(e) => tip(e, b)}
            onblur={ocultar}
          >
            {@render fila(b)}
          </button>
        {:else}
          <!-- Values are visible as text; the tooltip only adds detail (not a tab stop). -->
          <div class="row" role="presentation" onpointermove={(e) => tip(e, b)} onpointerleave={ocultar}>
            {@render fila(b)}
          </div>
        {/if}
      </li>
    {/each}
  </ul>
  {#if referenciaEtiqueta}
    <p class="leyenda small muted">
      <span class="sw ref" aria-hidden="true"></span>{referenciaEtiqueta}
      <span class="sw val" aria-hidden="true"></span>{valorEtiqueta}
    </p>
  {/if}
  <TablaAlterna
    {titulo}
    columnas={referenciaEtiqueta ? ['Concepto', valorEtiqueta, referenciaEtiqueta] : ['Concepto', valorEtiqueta]}
    filas={barras.map((b) =>
      referenciaEtiqueta ? [b.etiqueta, formato(b.valor), formato(b.referencia ?? null)] : [b.etiqueta, formato(b.valor)],
    )}
    alinearDerecha={[1, 2]}
  />
</figure>

{#snippet fila(b: Barra)}
  <span class="lab">
    <span class="name">{b.etiqueta}</span>
    {#if b.detalle}<span class="det">{b.detalle}</span>{/if}
  </span>
  <span class="track">
    {#if b.referencia != null}<span class="bar ref" use:ancho={b.referencia}></span>{/if}
    <span class="bar bg-{b.color ?? 'seq'}" use:ancho={b.valor}></span>
  </span>
  <span class="val num">{formato(b.valor)}</span>
{/snippet}

<style>
  .barlist {
    margin: 0;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.35rem;
  }
  .row {
    width: 100%;
    display: grid;
    grid-template-columns: minmax(0, 15rem) minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.75rem;
    padding: 0.4rem 0.5rem;
    border: 0;
    border-radius: var(--radius-sm);
    background: transparent;
    text-align: left;
    cursor: default;
  }
  button.row {
    cursor: pointer;
  }
  .row:hover,
  .row.sel {
    background: var(--surface-2);
  }
  .row.sel {
    outline: 2px solid var(--ink);
    outline-offset: -2px;
  }
  .lab {
    display: grid;
    min-width: 0;
  }
  .name {
    overflow-wrap: anywhere;
    line-height: 1.3;
  }
  .det {
    font-size: 0.8rem;
    color: var(--ink-2);
  }
  .track {
    position: relative;
    height: 20px;
  }
  .bar {
    position: absolute;
    left: 0;
    top: 2px;
    height: 16px;
    border-radius: 0 4px 4px 0;
    min-width: 2px;
  }
  .bar.ref {
    top: 0;
    height: 20px;
    background: var(--seq-200);
    opacity: 0.55;
  }
  .val {
    font-size: 0.9rem;
    white-space: nowrap;
  }
  .leyenda {
    display: flex;
    gap: 0.4rem 1rem;
    align-items: center;
    flex-wrap: wrap;
    margin: 0.5rem 0 0;
  }
  .sw {
    display: inline-block;
    width: 14px;
    height: 10px;
    border-radius: 2px;
    margin-right: 0.3rem;
  }
  .sw.ref {
    background: var(--seq-200);
  }
  .sw.val {
    background: var(--seq-450);
  }
  @media (max-width: 640px) {
    .row {
      grid-template-columns: minmax(0, 1fr) auto;
      grid-template-areas: 'lab val' 'track track';
      row-gap: 0.25rem;
    }
    .lab {
      grid-area: lab;
    }
    .val {
      grid-area: val;
    }
    .track {
      grid-area: track;
    }
  }
</style>
