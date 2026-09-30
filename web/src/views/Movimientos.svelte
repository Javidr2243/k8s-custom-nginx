<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE_CORTO, type Movimiento, type MunicipioId } from '../lib/data';
  import MovimientoItem from '../components/MovimientoItem.svelte';
  import Estado from '../components/Estado.svelte';

  let movs = $state<Movimiento[] | null>(null);
  let error = $state<string | null>(null);
  let mun = $state<MunicipioId | 'todos'>('todos');
  let tipo = $state<Movimiento['tipo'] | 'todos'>('todos');
  api
    .movimientos()
    .then((x) => (movs = x))
    .catch((e: Error) => (error = e.message));

  const TIPOS: [Movimiento['tipo'] | 'todos', string][] = [
    ['todos', 'Todos'],
    ['periodo', 'Nuevos reportes'],
    ['modificacion', 'Cambios al presupuesto'],
    ['deuda', 'Deuda'],
    ['contrato', 'Contratos grandes'],
    ['alerta', 'Calificación de deuda'],
  ];
  const lista = $derived(movs?.filter((x) => (mun === 'todos' || x.municipio === mun) && (tipo === 'todos' || x.tipo === tipo)) ?? []);
</script>

<section aria-labelledby="h-movs">
  <h1 id="h-movs">Movimientos recientes</h1>
  <p class="muted lead">
    Lo más importante del último trimestre publicado, comparado con el periodo anterior: cuánto se gastó, qué áreas
    recibieron o perdieron presupuesto, cómo cambió la deuda y los contratos más grandes.
  </p>
  <div class="filtros">
    <div class="seg" role="radiogroup" aria-label="Municipio">
      <button type="button" class="btn" role="radio" aria-checked={mun === 'todos'} onclick={() => (mun = 'todos')}>Los tres</button>
      {#each MUNICIPIOS as m (m)}
        <button type="button" class="btn" role="radio" aria-checked={mun === m} onclick={() => (mun = m)}>
          <span class="chip-dot dot-{m}" aria-hidden="true"></span>{NOMBRE_CORTO[m]}
        </button>
      {/each}
    </div>
    <label>
      <span class="sr-only">Tipo de movimiento</span>
      <select bind:value={tipo}>
        {#each TIPOS as [k, v] (k)}<option value={k}>{v}</option>{/each}
      </select>
    </label>
  </div>
  <Estado {error} cargando={!movs && !error} />
  {#if movs}
    <p class="small muted" aria-live="polite">{lista.length} movimientos</p>
    <ul class="card lista">
      {#each lista as mv, i (i)}
        <MovimientoItem movimiento={mv} />
      {:else}
        <li class="muted">No hay movimientos con estos filtros.</li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .lead {
    max-width: 70ch;
  }
  .filtros {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
    margin-bottom: 1rem;
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
  .lista {
    list-style: none;
    margin: 0;
    padding: 0.25rem 1.1rem;
  }
</style>
