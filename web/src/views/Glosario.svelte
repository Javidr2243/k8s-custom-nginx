<script lang="ts">
  import { GLOSARIO } from '../lib/glosario';
  import { normalizar } from '../lib/search';

  let q = $state('');
  const entradas = $derived(
    Object.entries(GLOSARIO)
      .filter(([, e]) => !q || normalizar(`${e.termino} ${e.corto}`).includes(normalizar(q)))
      .sort((a, b) => a[1].termino.localeCompare(b[1].termino, 'es')),
  );
</script>

<section aria-labelledby="h-glos">
  <p class="eyebrow">Palabras clave</p>
  <h1 id="h-glos">Glosario</h1>
  <p class="muted lead">Los términos de finanzas públicas que aparecen en el sitio, en palabras sencillas.</p>
  <label class="buscar">
    <span class="sr-only">Buscar término</span>
    <input type="search" placeholder="Buscar un término…" bind:value={q} />
  </label>
  <dl class="lista">
    {#each entradas as [id, e] (id)}
      <div class="item" {id}>
        <dt>{e.termino}</dt>
        <dd>
          <p>{e.corto}</p>
          {#if e.largo}<p class="muted">{e.largo}</p>{/if}
          {#if e.ver}
            <p class="small">Ver también: {#each e.ver as v, i (v)}<a href={`#${v}`}>{GLOSARIO[v]?.termino ?? v}</a>{i < e.ver.length - 1 ? ', ' : ''}{/each}</p>
          {/if}
        </dd>
      </div>
    {/each}
  </dl>
</section>

<style>
  .lead {
    max-width: 70ch;
  }
  .buscar input {
    width: min(100%, 420px);
    min-height: 44px;
    padding: 0.4rem 0.7rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    margin-bottom: 1rem;
  }
  /* Open two-column list separated by thin rules (no cards). */
  .lista {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 440px), 1fr));
    column-gap: 3rem;
    margin: 0;
  }
  .item {
    scroll-margin-top: 130px;
    padding: 1rem 0;
    border-top: 1px solid var(--grid);
  }
  .item:target {
    outline: 3px solid var(--focus);
    outline-offset: 4px;
    border-radius: 4px;
  }
  dt {
    font-weight: 700;
    font-size: 1.05rem;
  }
  dd {
    margin: 0.3rem 0 0;
  }
  dd p:last-child {
    margin-bottom: 0;
  }
</style>
