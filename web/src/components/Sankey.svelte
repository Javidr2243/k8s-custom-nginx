<script lang="ts" module>
  export interface SNodo {
    id: string;
    etiqueta: string;
    lado: 'fuente' | 'centro' | 'destino';
  }
  export interface SLink {
    de: string;
    a: string;
    valor: number;
  }
</script>

<script lang="ts">
  // Simplified flow diagram (Sankey). Kept as an explainer: few nodes, every node labelled with its amount,
  // plus a table alternative. On narrow screens it scrolls horizontally inside its own frame.
  import { sankey, sankeyLinkHorizontal, type SankeyGraph } from 'd3-sankey';
  import { mostrar, ocultar, desde } from './Tooltip.svelte';
  import TablaAlterna from './TablaAlterna.svelte';

  let {
    nodos,
    links,
    formato,
    titulo,
  }: { nodos: SNodo[]; links: SLink[]; formato: (n: number | null) => string; titulo: string } = $props();

  const W = 1040;
  const H = 540;
  type N = SNodo & { x0?: number; x1?: number; y0?: number; y1?: number; value?: number };
  type L = { source: N | number; target: N | number; value: number; width?: number; y0?: number; y1?: number; de: string; a: string };

  const grafo = $derived.by(() => {
    const idx = new Map(nodos.map((n, i) => [n.id, i]));
    const g = sankey<N, L>()
      .nodeWidth(14)
      .nodePadding(18)
      .nodeSort(null)
      .extent([
        [270, 40],
        [W - 270, H - 16],
      ])({
      nodes: nodos.map((n) => ({ ...n })),
      links: links
        .filter((l) => l.valor > 0 && idx.has(l.de) && idx.has(l.a))
        .map((l) => ({ source: idx.get(l.de)!, target: idx.get(l.a)!, value: l.valor, de: l.de, a: l.a })),
    } as SankeyGraph<N, L>);
    return g;
  });
  /** Label positions: node centres, spread apart on each side so two-line labels of small nodes never overlap. */
  const etiquetaY = $derived.by(() => {
    const MIN = 34;
    const out = new Map<string, number>();
    for (const lado of ['fuente', 'destino'] as const) {
      const ns = grafo.nodes.filter((n) => n.lado === lado).sort((a, b) => (a.y0 ?? 0) - (b.y0 ?? 0));
      const ys = ns.map((n) => ((n.y0 ?? 0) + (n.y1 ?? 0)) / 2);
      for (let i = 1; i < ys.length; i++) ys[i] = Math.max(ys[i]!, ys[i - 1]! + MIN);
      const exceso = (ys.at(-1) ?? 0) - (H - 12);
      if (exceso > 0) {
        ys[ys.length - 1]! -= exceso;
        for (let i = ys.length - 2; i >= 0; i--) ys[i] = Math.min(ys[i]!, ys[i + 1]! - MIN);
      }
      ns.forEach((n, i) => out.set(n.id, ys[i]!));
    }
    return out;
  });
  const camino = sankeyLinkHorizontal<N, L>();
  let hover = $state<string | null>(null);

  function tipLink(ev: PointerEvent | FocusEvent, l: L) {
    const s = l.source as N;
    const t = l.target as N;
    hover = `${s.id}>${t.id}`;
    const { x, y } = desde(ev);
    mostrar(x, y, `${s.etiqueta} → ${t.etiqueta}`, [{ valor: formato(l.value), etiqueta: '' }]);
  }
  function tipNodo(ev: PointerEvent | FocusEvent, n: N) {
    hover = n.id;
    const { x, y } = desde(ev);
    mostrar(x, y, n.etiqueta, [{ valor: formato(n.value ?? null), etiqueta: '' }]);
  }
  function salir() {
    hover = null;
    ocultar();
  }
  const activo = (l: L) =>
    !hover || hover === `${(l.source as N).id}>${(l.target as N).id}` || hover === (l.source as N).id || hover === (l.target as N).id;
</script>

<figure class="sankey">
  <div class="scroll">
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={titulo}>
      {#each grafo.links as l, i (i)}
        <path
          class="lk"
          class:dim={!activo(l)}
          d={camino(l)}
          stroke-width={Math.max(1, l.width ?? 1)}
          role="presentation"
          onpointermove={(e) => tipLink(e, l)}
          onpointerleave={salir}
        />
      {/each}
      {#each grafo.nodes as n (n.id)}
        <g
          class="nd {n.lado}"
          role="button"
          tabindex="0"
          aria-label={`${n.etiqueta}: ${formato(n.value ?? null)}`}
          onpointermove={(e) => tipNodo(e, n)}
          onpointerleave={salir}
          onfocus={(e) => tipNodo(e, n)}
          onblur={salir}
        >
          <rect x={n.x0} y={n.y0} width={(n.x1 ?? 0) - (n.x0 ?? 0)} height={Math.max(2, (n.y1 ?? 0) - (n.y0 ?? 0))} rx="3" />
          {#if n.lado === 'centro'}
            <text x={((n.x0 ?? 0) + (n.x1 ?? 0)) / 2} y={(n.y0 ?? 0) - 24} text-anchor="middle">
              <tspan class="n">{n.etiqueta}</tspan>
              <tspan class="v" x={((n.x0 ?? 0) + (n.x1 ?? 0)) / 2} dy="1.2em">{formato(n.value ?? null)}</tspan>
            </text>
          {:else if n.lado === 'fuente'}
            <text x={(n.x0 ?? 0) - 8} y={etiquetaY.get(n.id)} text-anchor="end">
              <tspan class="n" dy="-0.2em">{n.etiqueta}</tspan>
              <tspan class="v" x={(n.x0 ?? 0) - 8} dy="1.2em">{formato(n.value ?? null)}</tspan>
            </text>
          {:else}
            <text x={(n.x1 ?? 0) + 8} y={etiquetaY.get(n.id)}>
              <tspan class="n" dy="-0.2em">{n.etiqueta}</tspan>
              <tspan class="v" x={(n.x1 ?? 0) + 8} dy="1.2em">{formato(n.value ?? null)}</tspan>
            </text>
          {/if}
        </g>
      {/each}
    </svg>
  </div>
  <TablaAlterna
    {titulo}
    columnas={['De', 'A', 'Monto']}
    filas={grafo.links.map((l) => [(l.source as N).etiqueta, (l.target as N).etiqueta, formato(l.value)])}
    alinearDerecha={[2]}
  />
</figure>

<style>
  .sankey {
    margin: 0;
  }
  .scroll {
    overflow-x: auto;
  }
  svg {
    display: block;
    width: 100%;
    min-width: 680px;
    height: auto;
  }
  .lk {
    fill: none;
    stroke: var(--seq-300);
    opacity: 0.4;
    transition: opacity 0.15s;
  }
  .lk.dim {
    opacity: 0.08;
  }
  .nd rect {
    fill: var(--seq-450);
  }
  .nd.fuente rect {
    fill: var(--cat-4);
  }
  .nd.centro rect {
    fill: var(--ink);
  }
  .nd {
    outline: none;
  }
  .nd:focus-visible rect {
    stroke: var(--focus);
    stroke-width: 3;
  }
  text {
    font-size: 14px;
    fill: var(--ink);
  }
  .v {
    fill: var(--ink-2);
    font-size: 12.5px;
  }
</style>
