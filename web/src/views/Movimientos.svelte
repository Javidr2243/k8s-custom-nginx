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
  /** Headline: what kinds of changes the list contains, in counts. */
  const resumen = $derived.by(() => {
    const n = (t: Movimiento['tipo']) => lista.filter((x) => x.tipo === t).length;
    const partes = [
      [n('contrato'), 'contrato grande', 'contratos grandes'],
      [n('modificacion'), 'cambio al presupuesto', 'cambios al presupuesto'],
      [n('periodo'), 'reporte nuevo', 'reportes nuevos'],
      [n('deuda') + n('alerta'), 'dato de deuda', 'datos de deuda'],
    ] as const;
    return partes
      .filter(([k]) => k > 0)
      .map(([k, uno, varios]) => `${k} ${k === 1 ? uno : varios}`)
      .join(', ');
  });
</script>

<section aria-labelledby="h-movs">
  <p class="eyebrow">Qué cambió</p>
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
    <p class="titular" aria-live="polite">
      <span><strong class="num">{lista.length}</strong> movimientos{mun !== 'todos' ? ` en ${NOMBRE_CORTO[mun]}` : ''}.</span>
      {#if resumen}<span class="suave">{resumen.charAt(0).toUpperCase() + resumen.slice(1)}.</span>{/if}
    </p>
    <ul class="lista banda">
      {#each lista as mv, i (i)}
        <MovimientoItem movimiento={mv} compacto />
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
    padding-inline: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 440px), 1fr));
    column-gap: 3rem;
  }
</style>
