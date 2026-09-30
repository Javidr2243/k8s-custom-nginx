<script lang="ts" module>
  export interface Nodo {
    id: string;
    etiqueta: string;
    tipo: 'centro' | 'ingreso' | 'gasto' | 'organo';
    valor: number | null;
    detalle?: string;
  }
  export interface Arista {
    de: string;
    a: string;
    tipo: 'dinero' | 'aprueba';
    valor: number | null;
  }
</script>

<script lang="ts">
  // "Government map": fixed radial layout (readable and stable, unlike a force layout).
  // Centre: the municipal government. Left arc: where the money comes from. Right arc: who spends it
  // (dependencias) or what it is spent on (chapters). Top: the Ayuntamiento, which approves the budget.
  // Node area ∝ amount; money edges have width ∝ amount. Hover/focus highlights a node's connections.
  import { onMount } from 'svelte';
  import { select } from 'd3-selection';
  import { zoom, zoomIdentity, type ZoomBehavior } from 'd3-zoom';
  import { mostrar, ocultar, desde } from './Tooltip.svelte';

  let {
    nodos,
    aristas,
    formato,
    titulo,
    seleccionado = null,
    onelegir,
  }: {
    nodos: Nodo[];
    aristas: Arista[];
    formato: (n: number | null) => string;
    titulo: string;
    seleccionado?: string | null;
    onelegir: (id: string) => void;
  } = $props();

  const W = 1220;
  const H = 760;
  const C = { x: 600, y: 390 };
  const R = 350; // arc radius (vertical)

  // Nodes are spaced evenly in height along each arc, so labels never overlap;
  // x follows the circle so the shape still reads as a ring around the government.
  function arco(n: number, lado: 1 | -1, compacto: number) {
    const alto = Math.min(H - 110, Math.max(0, (n - 1) * compacto));
    return Array.from({ length: n }, (_, i) => {
      const y = n === 1 ? C.y : C.y - alto / 2 + (alto * i) / (n - 1);
      const dy = Math.min(R - 1, Math.abs(y - C.y));
      return { x: C.x + lado * Math.sqrt(R * R - dy * dy) * 0.92, y };
    });
  }

  const pos = $derived.by(() => {
    const out = new Map<string, { x: number; y: number; r: number; lado: 'izq' | 'der' | 'arriba' | 'centro' }>();
    const maxGasto = Math.max(1, ...nodos.filter((n) => n.tipo === 'gasto').map((n) => n.valor ?? 0));
    const maxIng = Math.max(1, ...nodos.filter((n) => n.tipo === 'ingreso').map((n) => n.valor ?? 0));
    const rad = (v: number | null, max: number, rmax: number) => Math.max(5, Math.sqrt(Math.max(0, v ?? 0) / max) * rmax);
    const ing = nodos.filter((n) => n.tipo === 'ingreso');
    const gas = nodos.filter((n) => n.tipo === 'gasto');
    const pi = arco(ing.length, -1, 64);
    ing.forEach((n, i) => out.set(n.id, { ...pi[i]!, r: rad(n.valor, maxIng, 28), lado: 'izq' }));
    const pg = arco(gas.length, 1, 64);
    gas.forEach((n, i) => out.set(n.id, { ...pg[i]!, r: rad(n.valor, maxGasto, gas.length > 12 ? 20 : 28), lado: 'der' }));
    for (const n of nodos) {
      if (n.tipo === 'centro') out.set(n.id, { x: C.x, y: C.y, r: 40, lado: 'centro' });
      if (n.tipo === 'organo') out.set(n.id, { x: C.x, y: 70, r: 18, lado: 'arriba' });
    }
    return out;
  });

  const maxArista = $derived(Math.max(1, ...aristas.map((a) => a.valor ?? 0)));
  let hover = $state<string | null>(null);
  const foco = $derived(hover ?? seleccionado);
  const vecinos = $derived.by(() => {
    if (!foco) return null;
    const s = new Set([foco]);
    for (const a of aristas) {
      if (a.de === foco) s.add(a.a);
      if (a.a === foco) s.add(a.de);
    }
    return s;
  });

  function curva(a: Arista): string {
    const p = pos.get(a.de);
    const q = pos.get(a.a);
    if (!p || !q) return '';
    const mx = (p.x + q.x) / 2;
    return `M${p.x},${p.y} C${mx},${p.y} ${mx},${q.y} ${q.x},${q.y}`;
  }
  const grosor = (a: Arista) => (a.tipo === 'aprueba' ? 1.5 : Math.max(1.5, ((a.valor ?? 0) / maxArista) * 26));

  function tip(ev: PointerEvent | FocusEvent, n: Nodo) {
    hover = n.id;
    const { x, y } = desde(ev);
    mostrar(x, y, n.etiqueta, [
      { valor: formato(n.valor), etiqueta: n.detalle ?? '' },
    ]);
  }
  function salir() {
    hover = null;
    ocultar();
  }

  // Zoom and pan (wheel, pinch, drag) plus buttons.
  let svgEl = $state<SVGSVGElement | undefined>();
  let gEl = $state<SVGGElement | undefined>();
  let zb: ZoomBehavior<SVGSVGElement, unknown> | undefined;
  onMount(() => {
    if (!svgEl || !gEl) return;
    const g = gEl;
    zb = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.6, 4])
      // Wheel only with Ctrl/⌘ (so the page still scrolls); touch drags scroll the page, zoom uses the buttons.
      .filter((ev: Event) => {
        if (ev.type === 'wheel') return (ev as WheelEvent).ctrlKey || (ev as WheelEvent).metaKey;
        if (ev.type.startsWith('touch')) return false;
        return !(ev as MouseEvent).button;
      })
      .on('zoom', (ev) => g.setAttribute('transform', ev.transform.toString()));
    select(svgEl).call(zb);
  });
  function zoomPor(k: number) {
    if (svgEl && zb) select(svgEl).call(zb.scaleBy, k);
  }
  function reiniciar() {
    if (svgEl && zb) select(svgEl).call(zb.transform, zoomIdentity);
  }
  function teclado(ev: KeyboardEvent, id: string) {
    if (ev.key === 'Enter' || ev.key === ' ') {
      ev.preventDefault();
      onelegir(id);
    }
  }
  const etiquetaCorta = (s: string) => (s.length > 30 ? `${s.slice(0, 28)}…` : s);
</script>

<div class="graph">
  <div class="controles" role="group" aria-label="Zoom del mapa">
    <button type="button" class="btn" onclick={() => zoomPor(1.3)} aria-label="Acercar">+</button>
    <button type="button" class="btn" onclick={() => zoomPor(1 / 1.3)} aria-label="Alejar">−</button>
    <button type="button" class="btn" onclick={reiniciar}>Restablecer</button>
  </div>
  <div class="scroll">
  <svg bind:this={svgEl} viewBox={`0 0 ${W} ${H}`} role="group" aria-label={titulo}>
    <g bind:this={gEl}>
      <text class="arco" x={24} y={30}>De dónde viene ←</text>
      <text class="arco" x={W - 24} y={30} text-anchor="end">→ Quién lo gasta / en qué</text>
      {#each aristas as a, i (i)}
        <path
          class="edge {a.tipo}"
          class:dim={vecinos && !(vecinos.has(a.de) && vecinos.has(a.a))}
          d={curva(a)}
          stroke-width={grosor(a)}
        />
      {/each}
      {#each nodos as n (n.id)}
        {@const p = pos.get(n.id)}
        {#if p}
          <g
            class="node {n.tipo}"
            class:dim={vecinos && !vecinos.has(n.id)}
            class:sel={seleccionado === n.id}
            transform={`translate(${p.x},${p.y})`}
            role="button"
            tabindex="0"
            aria-pressed={seleccionado === n.id}
            aria-label={`${n.etiqueta}: ${formato(n.valor)}${n.detalle ? `, ${n.detalle}` : ''}`}
            onclick={() => onelegir(n.id)}
            onkeydown={(e) => teclado(e, n.id)}
            onpointerenter={(e) => tip(e, n)}
            onpointermove={(e) => tip(e, n)}
            onpointerleave={salir}
            onfocus={(e) => tip(e, n)}
            onblur={salir}
          >
            <circle class="hit" r={Math.max(p.r, 14) + 6} />
            <circle class="dot" r={p.r} />
            {#if p.lado === 'der'}
              <text x={p.r + 8} dy="0.32em">{etiquetaCorta(n.etiqueta)}</text>
            {:else if p.lado === 'izq'}
              <text x={-p.r - 8} dy="0.32em" text-anchor="end">{etiquetaCorta(n.etiqueta)}</text>
            {:else if p.lado === 'arriba'}
              <text y={-p.r - 10} text-anchor="middle">{n.etiqueta}</text>
            {:else}
              <text class="centro-txt" text-anchor="middle" y={p.r + 22}>{n.etiqueta}</text>
              <text class="centro-val" text-anchor="middle" y={p.r + 42}>{formato(n.valor)}</text>
            {/if}
          </g>
        {/if}
      {/each}
    </g>
  </svg>
  </div>
  <p class="leyenda small muted">
    <span class="k dinero" aria-hidden="true"></span> Flujo de dinero (el grosor es el monto)
    <span class="k aprueba" aria-hidden="true"></span> Aprueba el presupuesto y supervisa
    <span>· Usa + y − para acercar; en computadora también Ctrl + rueda y arrastrar.</span>
  </p>
</div>

<style>
  .graph {
    position: relative;
  }
  .scroll {
    overflow-x: auto;
    border-radius: var(--radius);
  }
  .controles {
    position: absolute;
    right: 0.5rem;
    bottom: 3.2rem;
    display: flex;
    gap: 0.35rem;
    z-index: 2;
  }
  .controles .btn {
    min-width: 44px;
    justify-content: center;
    padding: 0.3rem 0.6rem;
  }
  svg {
    display: block;
    width: 100%;
    height: auto;
    min-width: 720px;
    background: var(--surface);
    cursor: grab;
  }
  .arco {
    fill: var(--ink-2);
    font-size: 16px;
    font-weight: 600;
  }
  .edge {
    fill: none;
    transition: opacity 0.15s;
  }
  .edge.dinero {
    stroke: var(--seq-300);
    opacity: 0.55;
  }
  .edge.aprueba {
    stroke: var(--ink-2);
    stroke-dasharray: 5 5;
  }
  .edge.dim {
    opacity: 0.08;
  }
  .node {
    cursor: pointer;
    outline: none;
    transition: opacity 0.15s;
  }
  .node.dim {
    opacity: 0.22;
  }
  .hit {
    fill: transparent;
  }
  .dot {
    stroke: var(--surface);
    stroke-width: 2;
  }
  .ingreso .dot {
    fill: var(--cat-4);
  }
  .gasto .dot {
    fill: var(--seq-450);
  }
  .centro .dot {
    fill: var(--ink);
  }
  .organo .dot {
    fill: var(--surface-2);
    stroke: var(--ink-2);
    stroke-width: 1.5;
  }
  .node:focus-visible .dot,
  .node.sel .dot {
    stroke: var(--ink);
    stroke-width: 3;
  }
  .node:focus-visible .hit {
    stroke: var(--focus);
    stroke-width: 3;
  }
  text {
    fill: var(--ink);
    font-size: 16px;
    paint-order: stroke;
    stroke: var(--surface);
    stroke-width: 4px;
    stroke-linejoin: round;
  }
  .centro-txt {
    font-size: 17px;
    font-weight: 700;
  }
  .centro-val {
    font-size: 15px;
    fill: var(--ink-2);
  }
  .leyenda {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3rem 0.8rem;
    margin: 0.5rem 0 0;
  }
  .k {
    display: inline-block;
    width: 22px;
    height: 0;
    border-top: 4px solid var(--seq-300);
    vertical-align: middle;
  }
  .k.aprueba {
    border-top: 2px dashed var(--ink-2);
  }
</style>
