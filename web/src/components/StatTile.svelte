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
</script>

<div class="tile">
  <div class="label">{#if typeof label === 'string'}{label}{:else}{@render label()}{/if}</div>
  <div class="value">{value}</div>
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
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.9rem 1rem;
    min-width: 0;
  }
  .label {
    color: var(--ink-2);
    font-size: 0.9rem;
  }
  .value {
    font-size: clamp(1.35rem, 3.2vw, 1.75rem);
    font-weight: 650;
    line-height: 1.2;
    margin: 0.25rem 0;
    overflow-wrap: break-word;
    hyphens: auto;
  }
  .sub {
    font-size: 0.875rem;
    color: var(--ink-2);
  }
  .origen {
    margin-top: 0.5rem;
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
