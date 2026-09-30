<script lang="ts" module>
  // A single floating tooltip shared by all charts. Content is plain text (never HTML).
  export interface TipLinea {
    valor: string;
    etiqueta: string;
    color?: string;
  }
  export const tip = $state({ visible: false, x: 0, y: 0, titulo: '', lineas: [] as TipLinea[] });

  export function mostrar(x: number, y: number, titulo: string, lineas: TipLinea[]): void {
    tip.x = x;
    tip.y = y;
    tip.titulo = titulo;
    tip.lineas = lineas;
    tip.visible = true;
  }
  export function ocultar(): void {
    tip.visible = false;
  }
  /** Position from a pointer event or from a focused element (keyboard). */
  export function desde(ev: PointerEvent | FocusEvent): { x: number; y: number } {
    if ('clientX' in ev && ev.clientX) return { x: ev.clientX, y: ev.clientY };
    const r = (ev.currentTarget as Element).getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top };
  }
</script>

<script lang="ts">
  let el = $state<HTMLDivElement | undefined>();

  // Placement through the CSSOM (allowed by the strict CSP, unlike style="" attributes).
  $effect(() => {
    if (!el || !tip.visible) return;
    const pad = 12;
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    let left = tip.x + pad;
    let top = tip.y - h - pad;
    if (left + w > window.innerWidth - 8) left = Math.max(8, tip.x - w - pad);
    if (top < 8) top = tip.y + pad + 8;
    el.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
  });
</script>

{#if tip.visible}
  <div class="tooltip" bind:this={el} role="status" aria-live="polite">
    <div class="t">{tip.titulo}</div>
    {#each tip.lineas as l, i (i)}
      <div class="row">
        {#if l.color}<span class="key bg-{l.color}" aria-hidden="true"></span>{/if}
        <strong class="num">{l.valor}</strong>
        <span class="lab">{l.etiqueta}</span>
      </div>
    {/each}
  </div>
{/if}

<style>
  .tooltip {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 60;
    pointer-events: none;
    max-width: min(320px, 90vw);
    padding: 0.55rem 0.7rem;
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.2);
    font-size: 0.85rem;
  }
  .t {
    color: var(--ink-2);
    margin-bottom: 0.2rem;
  }
  .row {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
  }
  .lab {
    color: var(--ink-2);
  }
  .key {
    display: inline-block;
    width: 12px;
    height: 3px;
    border-radius: 2px;
    align-self: center;
  }
</style>
