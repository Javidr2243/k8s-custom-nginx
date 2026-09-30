<script lang="ts">
  // Global filters: municipality and (optionally) period. They live in the URL (?m=&p=) and scope the whole view.
  import { MUNICIPIOS, NOMBRE_CORTO, type MunicipioId } from '../lib/data';
  import { acumulado } from '../lib/format';
  import { route, setQuery } from '../lib/router.svelte';

  let {
    periodos = [],
    mostrarPeriodo = true,
  }: { periodos?: string[]; mostrarPeriodo?: boolean } = $props();

  const actual = $derived(route.periodo && periodos.includes(route.periodo) ? route.periodo : periodos.at(-1));

  function elegir(m: MunicipioId) {
    setQuery({ m, p: null });
  }
</script>

<div class="filtros" role="group" aria-label="Filtros">
  <div class="seg" role="radiogroup" aria-label="Municipio">
    {#each MUNICIPIOS as m (m)}
      <button
        type="button"
        class="btn"
        role="radio"
        aria-checked={route.municipio === m}
        onclick={() => elegir(m)}
      >
        <span class="chip-dot dot-{m}" aria-hidden="true"></span>{NOMBRE_CORTO[m]}
      </button>
    {/each}
  </div>
  {#if mostrarPeriodo && periodos.length}
    <label class="per">
      <span>Periodo</span>
      <select value={actual} onchange={(e) => setQuery({ p: (e.currentTarget as HTMLSelectElement).value })}>
        {#each [...periodos].reverse() as p (p)}
          <option value={p}>{acumulado(p)}</option>
        {/each}
      </select>
    </label>
  {/if}
</div>

<style>
  .filtros {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1rem;
    align-items: center;
    margin: 0 0 1.25rem;
  }
  .per {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--ink-2);
  }
  select {
    min-height: 44px;
    padding: 0.4rem 0.6rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
  }
</style>
