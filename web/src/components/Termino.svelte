<script lang="ts">
  // A technical term with its plain-language explanation. Click (or Enter/Space) opens it; Esc or an outside
  // click closes it. On narrow screens the explanation is pinned to the bottom of the screen.
  import type { Snippet } from 'svelte';
  import { entrada } from '../lib/glosario';
  import { link } from '../lib/router.svelte';

  let { id, children }: { id: string; children?: Snippet } = $props();
  const e = $derived(entrada(id));
  let open = $state(false);
  let root = $state<HTMLSpanElement | undefined>();
  const uid = `def-${Math.random().toString(36).slice(2, 9)}`;

  $effect(() => {
    if (!open) return;
    const onDoc = (ev: MouseEvent) => {
      if (root && !root.contains(ev.target as Node)) open = false;
    };
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') open = false;
    };
    document.addEventListener('click', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('click', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  });
</script>

{#if e}
  <span class="termino" bind:this={root}>
    <button
      type="button"
      class="t"
      aria-expanded={open}
      aria-controls={uid}
      aria-describedby={open ? uid : undefined}
      onclick={() => (open = !open)}
    >
      {#if children}{@render children()}{:else}{e.termino.toLowerCase()}{/if}<span class="q" aria-hidden="true">?</span>
    </button>
    {#if open}
      <span class="pop" id={uid} role="note">
        <strong>{e.termino}</strong>
        <span class="txt">{e.corto}</span>
        <a href={`/glosario#${id}`} use:link>Ver en el glosario</a>
      </span>
    {/if}
  </span>
{:else if children}
  {@render children()}
{/if}

<style>
  .termino {
    position: relative;
    display: inline;
  }
  .t {
    background: none;
    border: 0;
    padding: 0;
    cursor: help;
    text-decoration: underline dotted;
    text-underline-offset: 3px;
    text-decoration-thickness: 1.5px;
    color: inherit;
    font: inherit;
    text-transform: inherit;
    letter-spacing: inherit;
  }
  .q {
    display: inline-grid;
    place-items: center;
    width: 1em;
    height: 1em;
    margin-left: 0.15em;
    font-size: min(0.7em, 0.75rem);
    font-weight: 700;
    text-transform: none;
    letter-spacing: 0;
    border-radius: 50%;
    background: var(--surface-2);
    color: var(--ink-2);
    vertical-align: super;
  }
  .pop {
    position: absolute;
    left: 0;
    top: calc(100% + 6px);
    z-index: 40;
    display: grid;
    gap: 0.35rem;
    width: max-content;
    max-width: min(340px, 86vw);
    padding: 0.75rem 0.85rem;
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
    font-size: 0.9rem;
    font-weight: 400;
    line-height: 1.45;
    text-align: left;
  }
  .txt {
    color: var(--ink-2);
  }
  @media (max-width: 600px) {
    .pop {
      position: fixed;
      left: 16px;
      right: 16px;
      bottom: 16px;
      top: auto;
      width: auto;
      max-width: none;
    }
  }
</style>
