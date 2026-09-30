<script lang="ts">
  // One idea per section (docs/DISENO.md): the question as a small label, the finding as the headline (actual values,
  // no subjective words), one line of detail, then the content. `banda` puts it on a full-width tinted band.
  import type { Snippet } from 'svelte';

  let {
    id,
    pregunta,
    titular,
    detalle,
    banda = false,
    children,
  }: {
    id: string;
    pregunta?: string;
    titular: string;
    detalle?: string | null;
    banda?: boolean;
    children?: Snippet;
  } = $props();
</script>

<section class="seccion" class:banda aria-labelledby={id}>
  {#if pregunta}<p class="eyebrow">{pregunta}</p>{/if}
  <h2 {id}>{titular}</h2>
  {#if detalle}<p class="detalle">{detalle}</p>{/if}
  {@render children?.()}
</section>

<style>
  .seccion {
    min-width: 0;
    padding-block: clamp(1.75rem, 4vw, 2.75rem);
  }
  /* Side by side inside a band: the band already provides the vertical space. */
  :global(.dos) > .seccion {
    padding-block: 0;
  }
  .detalle {
    font-size: 1.05rem;
    color: var(--ink-2);
    max-width: 70ch;
    margin: 0 0 0.6rem;
  }
</style>
