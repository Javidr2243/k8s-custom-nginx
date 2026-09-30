<script lang="ts">
  import type { Snippet } from 'svelte';
  import Fuente from './Fuente.svelte';

  let {
    label,
    value,
    sub,
    tone = 'neutral',
    origen,
    children,
  }: {
    label: Snippet | string;
    value: string;
    sub?: string;
    tone?: 'neutral' | 'good' | 'bad';
    /** How the figure is obtained (plain language) and the sources it comes from. */
    origen?: { calculo: string; fuentes: (string | null | undefined)[] };
    children?: Snippet;
  } = $props();
  /** "$1,457.0 millones" → the unit is set smaller so the number stays on one line. */
  const partes = $derived.by(() => {
    const i = value.indexOf(' millones');
    return i > 0 ? [value.slice(0, i), ' millones'] : [value, ''];
  });
</script>

<!-- Open figure (no box): place inside `.cifras`, which draws the separating rules. -->
<div class="tile">
  <div class="eyebrow label">{#if typeof label === 'string'}{label}{:else}{@render label()}{/if}</div>
  <div class="value num">{partes[0]}<span class="unidad">{partes[1]}</span></div>
  {#if sub}<div class="sub" class:good={tone === 'good'} class:bad={tone === 'bad'}>{sub}</div>{/if}
  {#if children}{@render children()}{/if}
  {#if origen}
    <details class="origen">
      <summary>¿De dónde sale?</summary>
      <p>{origen.calculo}</p>
      <Fuente ids={origen.fuentes} />
    </details>
  {/if}
</div>

<style>
  .tile {
    min-width: 0;
  }
  .label {
    margin-bottom: 0.2rem;
  }
  .value {
    font-size: clamp(1.5rem, 3vw, 2rem);
    font-weight: 750;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin: 0 0 0.2rem;
    overflow-wrap: break-word;
  }
  .unidad {
    font-size: 0.5em;
    font-weight: 600;
    letter-spacing: 0;
    color: var(--ink-2);
  }
  .sub {
    font-size: 0.875rem;
    color: var(--ink-2);
  }
  .origen {
    margin-top: 0.4rem;
    font-size: 0.85rem;
  }
  .origen summary {
    cursor: pointer;
    color: var(--link);
    min-height: 32px;
    display: inline-flex;
    align-items: center;
  }
  .origen p {
    margin: 0.3rem 0 0;
    color: var(--ink-2);
  }
  .good {
    color: var(--good-ink);
  }
  .bad {
    color: var(--critical-ink);
  }
</style>
