<script lang="ts">
  // What a budget department bought and from whom: its contracts (linked from the requesting area), shown in the
  // government map's side panel next to its spending.
  import { api, type Contratos, type Fuente as FuenteDoc, type MunicipioId } from '../lib/data';
  import { fecha, pesos, porcentaje, entero } from '../lib/format';
  import { href, link } from '../lib/router.svelte';
  import Termino from './Termino.svelte';

  let { municipio, dependencia }: { municipio: MunicipioId; dependencia: string } = $props();

  let datos = $state<Contratos | null>(null);
  let docs = $state<Record<string, FuenteDoc>>({});
  $effect(() => {
    const m = municipio;
    api
      .contratos(m)
      .then((d) => {
        if (municipio === m) datos = d;
      })
      .catch(() => (datos = null));
  });
  api.fuentes().then((f) => (docs = f)).catch(() => {});

  const g = $derived(datos?.resumen.por_dependencia?.[dependencia]);
</script>

{#if datos}
  <section class="contratos" aria-labelledby="h-contratos-dep">
    <h3 id="h-contratos-dep">Contratos de esta dependencia</h3>
    {#if g}
      <p class="hallazgo">
        <strong class="num">{entero(g.n)} {g.n === 1 ? 'contrato' : 'contratos'}</strong> por
        <strong class="num">{pesos(g.monto)}</strong>{#if g.pct_directa !== null}; {porcentaje(g.pct_directa)} del monto
          por <Termino id="adjudicacion-directa">adjudicación directa</Termino>{/if}.
      </p>
      <p class="small muted">
        Contratos publicados {g.fechas[0] ? `del ${fecha(g.fechas[0])} al ${fecha(g.fechas[1])}` : ''}, con impuestos. No
        cubren el mismo periodo que el gasto de arriba.
      </p>
      {#if g.proveedores.length}
        <p class="sub small">Proveedores con más dinero</p>
        <ol class="lista">
          {#each g.proveedores as p (p.rfc ?? p.proveedor)}
            <li><span class="nom">{p.proveedor}</span><span class="num">{pesos(p.monto)}</span></li>
          {/each}
        </ol>
      {/if}
      {#if g.contratos.length}
        <p class="sub small">Contratos más grandes</p>
        <ul class="lista">
          {#each g.contratos as c, i (i)}
            <li>
              <span class="nom">
                {c.descripcion || 'Sin descripción publicada'}
                <span class="small muted">{c.proveedor}{c.fecha ? ` · ${fecha(c.fecha)}` : ''}</span>
                {#if docs[c.fuente]}
                  <a class="small" href={docs[c.fuente]!.url} rel="noopener noreferrer" target="_blank">Documento oficial ↗</a>
                {/if}
              </span>
              <span class="num">{pesos(c.monto)}</span>
            </li>
          {/each}
        </ul>
      {/if}
      <p class="small"><a href={href('/contratos', { dep: dependencia })} use:link>Ver sus {entero(g.n)} contratos →</a></p>
    {:else}
      <p class="small muted">No hay contratos publicados que el municipio haya atribuido a esta dependencia.</p>
    {/if}
  </section>
{/if}

<style>
  .contratos {
    display: grid;
    gap: 0.35rem;
    margin-top: 0.5rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--grid);
  }
  h3 {
    margin: 0;
  }
  .hallazgo {
    margin: 0;
  }
  .sub {
    margin: 0.4rem 0 0;
    font-weight: 650;
    color: var(--ink-2);
  }
  .lista {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 0.4rem;
  }
  .lista li {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--grid);
  }
  .nom {
    display: grid;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .num {
    flex: none;
    font-variant-numeric: tabular-nums;
    font-weight: 600;
  }
</style>
