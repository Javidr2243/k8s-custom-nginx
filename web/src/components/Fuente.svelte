<script lang="ts">
  // Link to the official source document(s) of a figure, with the document's publication date.
  import { api, type Fuente } from '../lib/data';
  import { fecha } from '../lib/format';

  let { ids, etiqueta = 'Fuente' }: { ids: (string | null | undefined)[]; etiqueta?: string } = $props();
  let fuentes = $state<Record<string, Fuente>>({});
  api.fuentes().then((f) => (fuentes = f));
  const lista = $derived([...new Set(ids.filter((x): x is string => !!x))].map((id) => [id, fuentes[id]] as const));
</script>

{#if lista.length}
  <p class="fuente small">
    <span class="lbl">{etiqueta}:</span>
    {#each lista as [id, f], i (id)}
      {#if f}
        <a href={f.url} rel="noopener noreferrer" target="_blank">{f.titulo}</a>
        <span class="muted">— {f.emisor}{f.publicado ? `, publicado el ${fecha(f.publicado)}` : ''}</span>
      {:else}
        <span class="muted">{id}</span>
      {/if}{#if i < lista.length - 1}<span aria-hidden="true"> · </span>{/if}
    {/each}
  </p>
{/if}

<style>
  .fuente {
    margin: 0.5rem 0 0;
    color: var(--ink-2);
    overflow-wrap: anywhere;
  }
  .lbl {
    font-weight: 600;
  }
</style>
