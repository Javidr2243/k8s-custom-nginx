<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE, NOMBRE_CORTO, type Ingresos, type MunicipioId } from '../lib/data';
  import { cambio, pesos, pesosCorto, porcentaje } from '../lib/format';
  import { route } from '../lib/router.svelte';
  import { autonomia, comparacion, DESTINOS, FUENTES, suma } from '../lib/ingresos';
  import Filtros from '../components/Filtros.svelte';
  import Sankey, { type SLink, type SNodo } from '../components/Sankey.svelte';
  import LineChart from '../components/LineChart.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';
  import Seccion from '../components/Seccion.svelte';

  let todos = $state<Record<MunicipioId, Ingresos> | null>(null);
  let error = $state<string | null>(null);

  Promise.all(MUNICIPIOS.map((x) => api.ingresos(x)))
    .then((ds) => (todos = Object.fromEntries(MUNICIPIOS.map((x, i) => [x, ds[i]!])) as Record<MunicipioId, Ingresos>))
    .catch((e: Error) => (error = e.message));

  const m = $derived(route.municipio);
  const ing = $derived(todos?.[m]);
  // Latest year by default (reset when the municipality changes); the year selector overrides it.
  let anio = $derived<number | null>(ing?.anual.at(-1)?.anio ?? null);
  const a = $derived(ing?.anual.find((x) => x.anio === anio));

  const g = $derived.by(() => {
    if (!a) return { nodos: [] as SNodo[], links: [] as SLink[] };
    const nodos: SNodo[] = [{ id: 'mun', etiqueta: `Gobierno de ${NOMBRE[m]}`, lado: 'centro' }];
    const links: SLink[] = [];
    for (const [id, et, keys] of FUENTES) {
      const v = suma(a.ingresos_rubro, keys);
      if (v > 0) {
        nodos.push({ id, etiqueta: et, lado: 'fuente' });
        links.push({ de: id, a: 'mun', valor: v });
      }
    }
    for (const [id, et, keys] of DESTINOS) {
      const v = suma(a.egresos_capitulo, keys);
      if (v > 0) {
        nodos.push({ id, etiqueta: et, lado: 'destino' });
        links.push({ de: 'mun', a: id, valor: v });
      }
    }
    return { nodos, links };
  });
  // Finding for the headline: largest source and largest destination (from the same links the diagram draws).
  const lectura = $derived.by(() => {
    const et = new Map(g.nodos.map((n) => [n.id, n.etiqueta]));
    const ent = g.links.filter((l) => l.a === 'mun').sort((x, y) => y.valor - x.valor);
    const sal = g.links.filter((l) => l.de === 'mun' && l.a !== 'caja-final').sort((x, y) => y.valor - x.valor);
    const totalEnt = ent.reduce((t, l) => t + l.valor, 0);
    const totalSal = g.links.filter((l) => l.de === 'mun').reduce((t, l) => t + l.valor, 0);
    if (!ent[0] || !sal[0] || !totalEnt) return null;
    return {
      titular: `${et.get(ent[0].de)}: ${porcentaje(ent[0].valor / totalEnt)} de lo que entró`,
      detalle: `El destino más grande fue ${et.get(sal[0].a)?.toLowerCase()}: ${pesos(sal[0].valor)}, ${porcentaje(sal[0].valor / (totalSal || 1))} de lo que salió.`,
    };
  });

  // What changed against the previous year: every flow group, the biggest change (in pesos) as the headline.
  const filas = $derived(ing && anio ? comparacion(ing.anual, anio) : []);
  const hayAnterior = $derived(filas.some((f) => f.anterior !== null));
  const mayorCambio = $derived(
    [...filas].filter((f) => f.anterior !== null).sort((x, y) => Math.abs(y.actual - (y.anterior ?? 0)) - Math.abs(x.actual - (x.anterior ?? 0)))[0],
  );

  // How much of its income each municipality raises itself (vs. federal transfers), per year.
  const aut = $derived(a ? autonomia(a) : null);
  const de100 = $derived(aut?.pct != null ? Math.round(aut.pct * 100) : null);
  const otros = $derived(
    todos && anio
      ? MUNICIPIOS.filter((x) => x !== m).map((x) => {
          const y = todos![x].anual.find((z) => z.anio === anio);
          const p = y ? autonomia(y).pct : null;
          return { id: x, de100: p != null ? Math.round(p * 100) : null };
        })
      : [],
  );
  const primero = $derived(ing?.anual.find((x) => autonomia(x).pct != null));
  const seriesAut = $derived(
    todos
      ? MUNICIPIOS.map((x) => ({
          id: x,
          etiqueta: NOMBRE_CORTO[x],
          color: x,
          puntos: todos![x].anual.map((y) => ({ x: String(y.anio), v: autonomia(y).pct })),
        }))
      : [],
  );
</script>

<section aria-labelledby="h-flujo">
  <header>
    <p class="eyebrow">Ingresos y gastos de todo un año</p>
    <h1 id="h-flujo">Flujo del dinero</h1>
    <p class="muted lead">
      Cómo entra el dinero al gobierno de {NOMBRE[m]} y hacia dónde sale en todo un año. A la izquierda, de dónde viene:
      <Termino id="impuestos">impuestos</Termino>, <Termino id="participaciones">participaciones</Termino> y
      <Termino id="aportaciones">aportaciones</Termino> federales o <Termino id="financiamiento">préstamos</Termino>. A la
      derecha, en qué se gasta.
    </p>
    <Filtros mostrarPeriodo={false} />
  </header>
  <Estado {error} cargando={!todos && !error} />

  {#if ing}
    <label class="anio">
      <span>Año</span>
      <select bind:value={anio}>
        {#each [...ing.anual].reverse() as x (x.anio)}
          <option value={x.anio}>{x.anio}{x.estatus.includes('Preliminar') ? ' (preliminar)' : ''}</option>
        {/each}
      </select>
    </label>
    {#if a}
      <p class="titular">
        <span>
          En {a.anio} pasaron <strong class="num">{pesos(a.ingresos_total)}</strong> por la tesorería de {NOMBRE[m]}.
        </span>
        <span class="suave">
          {a.estatus.includes('Preliminar') ? 'Cifras preliminares del INEGI. ' : ''}A la izquierda, de dónde vino; a la derecha, en qué se fue.
        </span>
      </p>

      <Seccion
        id="h-sankey"
        banda
        pregunta={`${NOMBRE[m]}, ${a.anio}`}
        titular={lectura?.titular ?? `${NOMBRE[m]}, ${a.anio}`}
        detalle={lectura?.detalle}
      >
        <p class="small muted">Pasa el cursor o toca una franja para ver el monto.</p>
        <Sankey nodos={g.nodos} links={g.links} formato={pesos} titulo={`Flujo del dinero del gobierno de ${NOMBRE[m]} en ${a.anio}`} tabla={false} />
        <p class="small muted">
          Datos anuales del INEGI (<Termino id="efipem">EFIPEM</Termino>) para que ingresos y gastos cuadren en el mismo
          periodo. «Queda en caja» es la <Termino id="disponibilidad-final">disponibilidad final</Termino>: no es gasto.
        </p>
        <Fuente ids={[ing.fuente_anual]} compacto />
      </Seccion>

      <Seccion
        id="h-cambios"
        pregunta={hayAnterior ? `¿Qué cambió respecto a ${a.anio - 1}?` : 'Montos del año'}
        titular={mayorCambio
          ? `${mayorCambio.etiqueta}: ${pesos(Math.abs(mayorCambio.actual - (mayorCambio.anterior ?? 0)))} ${mayorCambio.actual >= (mayorCambio.anterior ?? 0) ? 'más' : 'menos'} que en ${a.anio - 1}${mayorCambio.cambio !== null ? ` (${cambio(mayorCambio.cambio)})` : ''}`
          : `Entradas y salidas de ${a.anio}`}
        detalle={hayAnterior
          ? 'Cada entrada y salida del diagrama junto al año anterior. Pesos nominales: parte del aumento se explica por la inflación.'
          : 'Primer año con datos: no hay con qué comparar.'}
      >
        <div class="table-wrap">
          <table class="data comparacion">
            <caption class="sr-only">Entradas y salidas de {NOMBRE[m]} en {a.anio}{hayAnterior ? ` comparadas con ${a.anio - 1}` : ''}</caption>
            <thead>
              <tr>
                <th scope="col">Concepto</th>
                <th scope="col" class="r">{a.anio}</th>
                {#if hayAnterior}<th scope="col" class="r">{a.anio - 1}</th><th scope="col" class="r">Cambio</th>{/if}
              </tr>
            </thead>
            {#each [['entrada', 'De dónde vino'], ['salida', 'En qué se fue']] as [lado, titulo] (lado)}
              <tbody>
                <tr class="grupo"><th scope="rowgroup" colspan={hayAnterior ? 4 : 2}>{titulo}</th></tr>
                {#each filas.filter((f) => f.lado === lado) as f (f.id)}
                  <tr>
                    <th scope="row">{f.etiqueta}</th>
                    <td class="r num">{pesos(f.actual)}</td>
                    {#if hayAnterior}
                      <td class="r num muted">{f.anterior !== null ? pesos(f.anterior) : '—'}</td>
                      <td class="r num">{f.cambio !== null ? cambio(f.cambio) : f.anterior === 0 ? 'nuevo' : '—'}</td>
                    {/if}
                  </tr>
                {/each}
              </tbody>
            {/each}
          </table>
        </div>
        <Fuente ids={[ing.fuente_anual]} compacto />
      </Seccion>

      {#if de100 !== null}
        <Seccion
          id="h-autonomia"
          banda
          pregunta="¿Cuánto depende de la federación?"
          titular={`De cada $100 que recibió en ${a.anio}, ${NOMBRE_CORTO[m]} recaudó $${de100}; $${100 - de100} vinieron de la federación`}
          detalle={`${otros
            .filter((o) => o.de100 !== null)
            .map((o) => `${NOMBRE_CORTO[o.id]}: $${o.de100}`)
            .join(' · ')}${primero && primero.anio !== a.anio ? ` · En ${primero.anio}, ${NOMBRE_CORTO[m]} recaudaba $${Math.round((autonomia(primero).pct ?? 0) * 100)}.` : ''}`}
        >
          <p class="small muted">
            Parte de los <Termino id="ingresos-propios">ingresos propios</Termino> (impuestos como el predial, derechos,
            productos y aprovechamientos) frente a <Termino id="participaciones">participaciones</Termino> y
            <Termino id="aportaciones">aportaciones</Termino> federales. No cuenta préstamos ni el dinero en caja del año
            anterior.
          </p>
          <LineChart
            series={seriesAut}
            formato={(n) => porcentaje(n)}
            formatoEje={(n) => porcentaje(n)}
            titulo="Parte de los ingresos que recauda cada municipio, por año"
          />
          <p class="small muted">
            Datos anuales del INEGI{a.estatus.includes('Preliminar') ? `; ${a.anio} es preliminar` : ''}. Montos de
            {NOMBRE_CORTO[m]} en {a.anio}: propios {pesosCorto(aut?.propios)}, federales {pesosCorto(aut?.federales)}.
          </p>
          <Fuente ids={[ing.fuente_anual]} compacto />
        </Seccion>
      {/if}
    {/if}
  {/if}
</section>

<style>
  .lead {
    max-width: 75ch;
  }
  .anio {
    display: inline-flex;
    gap: 0.5rem;
    align-items: center;
    margin: 0.25rem 0 0;
    color: var(--ink-2);
  }
  .comparacion .grupo th {
    padding-top: 1rem;
    font-weight: 700;
    color: var(--ink);
    border-bottom: 1px solid var(--axis);
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
