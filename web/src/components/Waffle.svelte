<script lang="ts" module>
  export interface Parte {
    id: string;
    etiqueta: string;
    valor: number;
    detalle?: string;
  }

  /** Whole pesos out of 100 per part (largest remainder), always adding up to exactly 100. */
  export function deCada100(partes: { valor: number }[]): number[] {
    const total = partes.reduce((s, p) => s + Math.max(0, p.valor), 0);
    if (total <= 0) return partes.map(() => 0);
    const raw = partes.map((p) => (Math.max(0, p.valor) / total) * 100);
    const base = raw.map(Math.floor);
    let resto = 100 - base.reduce((a, b) => a + b, 0);
    const orden = raw.map((r, i) => [r - Math.floor(r), i] as const).sort((a, b) => b[0] - a[0]);
    for (const [, i] of orden) {
      if (resto <= 0) break;
      base[i]! += 1;
      resto -= 1;
    }
    return base;
  }
</script>

<script lang="ts">
  // "Out of every $100…": a 10×10 grid where each square is $1 out of every $100 spent. The top five
  // parts keep their own colour (validated categorical order); the rest are grouped as "Otros".
  import { mostrar, ocultar, desde } from './Tooltip.svelte';
  import { pesos } from '../lib/format';

  let { partes, titulo }: { partes: Parte[]; titulo: string } = $props();

  const ordenadas = $derived.by(() => {
    const s = [...partes].filter((p) => p.valor > 0).sort((a, b) => b.valor - a.valor);
    if (s.length <= 5) return s;
    const top = s.slice(0, 5);
    const resto = s.slice(5);
    return [
      ...top,
      {
        id: 'otros',
        etiqueta: 'Otros',
        valor: resto.reduce((a, b) => a + b.valor, 0),
        detalle: resto.map((r) => r.etiqueta).join(', '),
      },
    ];
  });
  const cuadros = $derived(deCada100(ordenadas));
  const color = (i: number, id: string) => (id === 'otros' ? 'otro' : `cat-${i + 1}`);
  const celdas = $derived.by(() => {
    const out: { parte: number }[] = [];
    cuadros.forEach((n, i) => {
      for (let k = 0; k < n; k++) out.push({ parte: i });
    });
    return out;
  });
  let activo = $state<number | null>(null);

  function tip(ev: PointerEvent | FocusEvent, i: number) {
    const p = ordenadas[i];
    if (!p) return;
    activo = i;
    const { x, y } = desde(ev);
    mostrar(x, y, p.etiqueta, [
      { valor: `$${cuadros[i]} de cada $100`, etiqueta: '' },
      { valor: pesos(p.valor), etiqueta: 'en total' },
    ]);
  }
  function salir() {
    activo = null;
    ocultar();
  }
</script>

<figure class="waffle">
  <svg
    viewBox="0 0 104 104"
    role="img"
    aria-label={`${titulo}. ${ordenadas.map((p, i) => `${p.etiqueta}: ${cuadros[i]} de cada 100 pesos`).join('; ')}.`}
  >
    {#each celdas as c, k (k)}
      <rect
        x={(k % 10) * 10.4 + 0.6}
        y={Math.floor(k / 10) * 10.4 + 0.6}
        width="9.2"
        height="9.2"
        rx="1.6"
        class="f-{color(c.parte, ordenadas[c.parte]?.id ?? '')}"
        class:dim={activo !== null && activo !== c.parte}
        role="presentation"
        onpointermove={(e) => tip(e, c.parte)}
        onpointerleave={salir}
      />
    {/each}
  </svg>
  <figcaption>
    <ul class="leyenda">
      {#each ordenadas as p, i (p.id)}
        <li>
          <button
            type="button"
            class="item"
            onpointerenter={(e) => tip(e, i)}
            onpointerleave={salir}
            onfocus={(e) => tip(e, i)}
            onblur={salir}
          >
            <span class="sw bg-{color(i, p.id)}" aria-hidden="true"></span>
            <span class="big num">${cuadros[i]}</span>
            <span class="txt">
              <span class="name">{p.etiqueta}</span>
              <span class="det">{pesos(p.valor)}{p.detalle ? ` · ${p.detalle}` : ''}</span>
            </span>
          </button>
        </li>
      {/each}
    </ul>
  </figcaption>
</figure>

<style>
  .waffle {
    margin: 0;
    display: grid;
    grid-template-columns: minmax(0, 260px) minmax(0, 1fr);
    gap: 1.25rem;
    align-items: start;
  }
  svg {
    width: 100%;
    height: auto;
    display: block;
  }
  rect {
    transition: opacity 0.15s;
  }
  rect.dim {
    opacity: 0.25;
  }
  .leyenda {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.25rem;
  }
  .item {
    display: grid;
    grid-template-columns: 14px 3.2rem minmax(0, 1fr);
    gap: 0.6rem;
    align-items: center;
    width: 100%;
    border: 0;
    background: none;
    text-align: left;
    padding: 0.35rem 0.4rem;
    border-radius: var(--radius-sm);
    min-height: 44px;
  }
  .item:hover {
    background: var(--surface-2);
  }
  .sw {
    width: 14px;
    height: 14px;
    border-radius: 3px;
  }
  .big {
    font-size: 1.25rem;
    font-weight: 650;
  }
  .txt {
    display: grid;
    min-width: 0;
  }
  .det {
    font-size: 0.8rem;
    color: var(--ink-2);
    overflow-wrap: anywhere;
  }
  @media (max-width: 640px) {
    .waffle {
      grid-template-columns: 1fr;
    }
    svg {
      max-width: 240px;
      margin: 0 auto;
    }
  }
</style>
