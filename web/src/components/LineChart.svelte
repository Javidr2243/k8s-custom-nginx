<script lang="ts" module>
  export interface Serie {
    id: string;
    etiqueta: string;
    color: string; // class suffix: 'monterrey' | 'seq' …
    puntos: { x: string; v: number | null }[];
  }
</script>

<script lang="ts">
  // Line chart over a shared x axis (periods or years). One y axis starting at zero, recessive grid,
  // 2px lines, end dots with a surface ring, direct end labels only when there are ≤ 4 series,
  // and a crosshair that snaps to the nearest x with a single tooltip listing every series.
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { line } from 'd3-shape';
  import { mostrar, ocultar } from './Tooltip.svelte';
  import TablaAlterna from './TablaAlterna.svelte';
  import { cambio } from '../lib/format';

  let {
    series,
    formato,
    formatoEje,
    etiquetaX = (x: string) => x,
    titulo,
    alto = 240,
  }: {
    series: Serie[];
    formato: (n: number | null) => string;
    formatoEje: (n: number) => string;
    etiquetaX?: (x: string) => string;
    titulo: string;
    alto?: number;
  } = $props();

  let ancho = $state(600);
  const m = { t: 12, r: 16, b: 28, l: 64 };
  const xs = $derived([...new Set(series.flatMap((s) => s.puntos.map((p) => p.x)))].sort());
  const maxV = $derived(Math.max(1, ...series.flatMap((s) => s.puntos.map((p) => p.v ?? 0))));
  const x = $derived(scalePoint<string>().domain(xs).range([m.l, ancho - m.r]).padding(0.2));
  const y = $derived(scaleLinear().domain([0, maxV]).nice(4).range([alto - m.b, m.t]));
  const ticks = $derived(y.ticks(4));
  const cadaX = $derived(Math.max(1, Math.ceil(xs.length / Math.max(2, Math.floor(ancho / 90)))));
  const path = (s: Serie) =>
    line<{ x: string; v: number | null }>()
      .defined((p) => p.v !== null)
      .x((p) => x(p.x) ?? 0)
      .y((p) => y(p.v ?? 0))(s.puntos) ?? '';
  let hover = $state<string | null>(null);

  function mover(ev: PointerEvent) {
    const svg = ev.currentTarget as SVGSVGElement;
    const r = svg.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * ancho;
    let best = xs[0] ?? null;
    let dist = Infinity;
    for (const v of xs) {
      const d = Math.abs((x(v) ?? 0) - px);
      if (d < dist) [best, dist] = [v, d];
    }
    if (!best) return;
    hover = best;
    const px2 = r.left + ((x(best) ?? 0) / ancho) * r.width;
    mostrar(
      px2,
      ev.clientY,
      etiquetaX(best),
      series.map((s) => ({
        valor: formato(s.puntos.find((p) => p.x === best)?.v ?? null),
        etiqueta: s.etiqueta,
        color: s.color,
      })),
    );
  }
  function salir() {
    hover = null;
    ocultar();
  }
  const ultimo = (s: Serie) => [...s.puntos].reverse().find((p) => p.v !== null);
</script>

<figure class="line">
  <div class="box" bind:clientWidth={ancho}>
    <svg
      viewBox={`0 0 ${ancho} ${alto}`}
      width={ancho}
      height={alto}
      role="img"
      aria-label={titulo}
      onpointermove={mover}
      onpointerleave={salir}
    >
      {#each ticks as t (t)}
        <line class="grid" x1={m.l} x2={ancho - m.r} y1={y(t)} y2={y(t)} />
        <text class="ax" x={m.l - 8} y={y(t)} dy="0.32em" text-anchor="end">{formatoEje(t)}</text>
      {/each}
      {#each xs as v, i (v)}
        {#if (i % cadaX === 0 && xs.length - 1 - i >= Math.ceil(cadaX / 2)) || i === xs.length - 1}
          <text class="ax" x={x(v)} y={alto - 8} text-anchor="middle">{etiquetaX(v)}</text>
        {/if}
      {/each}
      {#if hover}
        <line class="cross" x1={x(hover)} x2={x(hover)} y1={m.t} y2={alto - m.b} />
      {/if}
      {#each series as s (s.id)}
        <path class="ln s-{s.color}" d={path(s)} />
        {#each s.puntos as p (p.x)}
          {#if p.v !== null && (p.x === hover || p === ultimo(s))}
            <circle class="dot f-{s.color}" cx={x(p.x)} cy={y(p.v)} r="4.5" />
          {/if}
        {/each}
      {/each}
    </svg>
  </div>
  {#if series.length > 1}
    <ul class="leyenda small">
      {#each series as s (s.id)}
        <li><span class="key bg-{s.color}" aria-hidden="true"></span>{s.etiqueta}</li>
      {/each}
    </ul>
  {/if}
  <TablaAlterna
    {titulo}
    columnas={series.length === 1 ? ['Periodo', series[0]!.etiqueta, 'Cambio vs. periodo anterior'] : ['Periodo', ...series.map((s) => s.etiqueta)]}
    filas={xs.map((v, i) => {
      const valores = series.map((s) => s.puntos.find((p) => p.x === v)?.v ?? null);
      if (series.length !== 1) return [etiquetaX(v), ...valores.map((x) => formato(x))];
      // One series: the table adds what the line only suggests, the change from the previous point.
      const previo = i > 0 ? (series[0]!.puntos.find((p) => p.x === xs[i - 1])?.v ?? null) : null;
      const actual = valores[0] ?? null;
      return [etiquetaX(v), formato(actual), actual != null && previo ? cambio((actual - previo) / previo) : '—'];
    })}
    alinearDerecha={series.length === 1 ? [1, 2] : series.map((_, i) => i + 1)}
  />
</figure>

<style>
  .line {
    margin: 0;
  }
  .box {
    width: 100%;
  }
  svg {
    display: block;
    width: 100%;
    height: auto;
    touch-action: pan-y;
  }
  .grid {
    stroke: var(--grid);
    stroke-width: 1;
  }
  .ax {
    fill: var(--ink-2);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }
  .cross {
    stroke: var(--axis);
    stroke-width: 1;
  }
  .ln {
    fill: none;
    stroke-width: 2;
    stroke-linejoin: round;
    stroke-linecap: round;
  }
  .dot {
    stroke: var(--surface);
    stroke-width: 2;
  }
  .leyenda {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1rem;
    padding: 0;
    margin: 0.4rem 0 0;
  }
  .key {
    display: inline-block;
    width: 14px;
    height: 3px;
    border-radius: 2px;
    margin-right: 0.35rem;
    vertical-align: middle;
  }
</style>
