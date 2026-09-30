<script lang="ts">
  // Provenance of a figure: the official document(s) it comes from. Each source expands to show the
  // official link, the archived copy of the exact file used, dates, format and SHA-256 fingerprint,
  // so anyone can verify or analyse the number even if the government link stops working.
  import { api, type Fuente } from '../lib/data';
  import { fecha } from '../lib/format';
  import { link } from '../lib/router.svelte';

  let { ids, etiqueta = 'Fuente' }: { ids: (string | null | undefined)[]; etiqueta?: string } = $props();
  let fuentes = $state<Record<string, Fuente>>({});
  api.fuentes().then((f) => (fuentes = f));
  const lista = $derived([...new Set(ids.filter((x): x is string => !!x))].map((id) => [id, fuentes[id]] as const));
  const tam = (b: number | null) => (b === null ? '' : b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1e3))} KB`);
</script>

{#if lista.length}
  <div class="fuente small">
    <span class="lbl">{etiqueta}{lista.length > 1 ? 's' : ''}:</span>
    <ul>
      {#each lista as [id, f] (id)}
        <li>
          {#if f}
            <a href={f.url} rel="noopener noreferrer" target="_blank">{f.titulo}</a>
            <span class="muted">— {f.emisor}{f.publicado ? `, publicado el ${fecha(f.publicado)}` : ''}.</span>
            <details class="det">
              <summary>Detalles y copia del archivo</summary>
              <dl>
                <dt>Documento oficial</dt>
                <dd><a href={f.url} rel="noopener noreferrer" target="_blank">Abrir en el sitio del emisor</a> ({f.formato.toUpperCase()})</dd>
                <dt>Copia archivada</dt>
                <dd>
                  <a href={f.copia} download>Descargar la copia usada aquí</a>
                  {tam(f.bytes)}{#if f.extracto}
                    · <span class="muted">el original es un archivo nacional muy grande; la copia contiene solo las filas de los tres municipios</span>{/if}
                </dd>
                <dt>Dónde se publica</dt>
                <dd class="url">
                  {#if f.pagina.startsWith('https://')}<a href={f.pagina} rel="noopener noreferrer" target="_blank">{f.pagina}</a>{:else}{f.pagina}{/if}
                </dd>
                <dt>Fechas</dt>
                <dd>Publicado {f.publicado ? fecha(f.publicado) : 'sin fecha'} · descargado {fecha(f.descargado)}</dd>
                <dt>Huella SHA-256</dt>
                <dd class="hash">{f.sha256}{#if f.sha256_original}<br /><span class="muted">original completo: {f.sha256_original}</span>{/if}</dd>
              </dl>
              <p class="muted">
                Para comprobar que la copia no fue alterada, calcula su SHA-256 (p. ej. <code>sha256sum archivo</code>) y
                compáralo con esta huella. <a href="/fuentes" use:link>Ver todas las fuentes y verificaciones</a>.
              </p>
            </details>
          {:else}
            <span class="muted">{id}</span>
          {/if}
        </li>
      {/each}
    </ul>
  </div>
{/if}

<style>
  .fuente {
    margin: 0.5rem 0 0;
    color: var(--ink-2);
    overflow-wrap: break-word;
    container-type: inline-size;
  }
  .lbl {
    font-weight: 600;
  }
  ul {
    list-style: none;
    margin: 0.15rem 0 0;
    padding: 0;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 0.3rem;
  }
  .det summary {
    cursor: pointer;
    color: var(--link);
    display: inline-flex;
    min-height: 32px;
    align-items: center;
  }
  dl {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    gap: 0.25rem 0.75rem;
    margin: 0.35rem 0;
    padding: 0.6rem 0.75rem;
    background: var(--surface-2);
    border-radius: var(--radius-sm);
  }
  dt {
    font-weight: 600;
    color: var(--ink);
  }
  dd {
    margin: 0;
  }
  .hash {
    font-family: ui-monospace, 'SFMono-Regular', Menlo, monospace;
    font-size: 0.78rem;
  }
  code {
    font-size: 0.85em;
  }
  .hash,
  .url {
    overflow-wrap: anywhere;
  }
  /* Stack label over value wherever the list is narrow (phones, and inside stat tiles). */
  @container (max-width: 480px) {
    dl {
      grid-template-columns: minmax(0, 1fr);
      gap: 0.1rem;
    }
    dd {
      margin-bottom: 0.35rem;
    }
  }
</style>
