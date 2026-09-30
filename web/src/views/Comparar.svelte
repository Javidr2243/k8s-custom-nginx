<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE, NOMBRE_CORTO, type Comparativo, type Egresos, type MunicipioId, type Municipio } from '../lib/data';
  import { acumulado, pesos, pesosCorto } from '../lib/format';
  import { CAPITULOS } from '../lib/capitulos';
  import BarList from '../components/BarList.svelte';
  import LineChart from '../components/LineChart.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';

  let datos = $state<{ comp: Comparativo; egr: Record<MunicipioId, Egresos>; muns: Municipio[] } | null>(null);
  let error = $state<string | null>(null);
  let porHab = $state(true);

  Promise.all([api.comparativo(), api.municipios(), ...MUNICIPIOS.map((m) => api.egresos(m))])
    .then(([comp, muns, ...egs]) => {
      const egr = Object.fromEntries(MUNICIPIOS.map((m, i) => [m, egs[i]])) as Record<MunicipioId, Egresos>;
      datos = { comp: comp as Comparativo, egr, muns: muns as Municipio[] };
    })
    .catch((e: Error) => (error = e.message));

  const pob = (m: MunicipioId) => datos?.muns.find((x) => x.id === m)?.poblacion ?? 1;
  const escala = (m: MunicipioId, v: number | null) => (v === null ? null : porHab ? v / pob(m) : v);
  const fmt = (n: number | null) => (porHab ? pesos(n) : pesos(n));

  // Latest quarter available for all three municipalities.
  const comun = $derived.by(() => {
    if (!datos) return null;
    const sets = MUNICIPIOS.map((m) => new Set(datos!.egr[m].periodos.map((p) => p.periodo)));
    const todos = [...sets[0]!].filter((p) => sets.every((s) => s.has(p))).sort();
    return todos.at(-1) ?? null;
  });
  const ultimoAnio = $derived(datos ? Math.max(...datos.comp.anios) : null);
  const estatusUltimo = $derived(
    datos && ultimoAnio ? datos.comp.municipios.monterrey.anual.find((a) => a.anio === ultimoAnio)?.estatus ?? '' : '',
  );
  const barrasTrim = $derived(
    datos && comun
      ? MUNICIPIOS.map((m) => {
          const p = datos!.egr[m].periodos.find((x) => x.periodo === comun)!;
          return { id: m, etiqueta: NOMBRE[m], valor: escala(m, p.total.devengado), color: m };
        })
      : [],
  );
  const series = $derived(
    datos
      ? MUNICIPIOS.map((m) => ({
          id: m,
          etiqueta: NOMBRE_CORTO[m],
          color: m,
          puntos: datos!.comp.municipios[m].anual
            .filter((a) => a.anio >= 2018)
            .map((a) => ({ x: String(a.anio), v: porHab ? a.gasto_por_habitante : a.gasto_total })),
        }))
      : [],
  );
  const caps = ['1000', '3000', '2000', '4000', '6000', '9000'];
  function barrasCap(clave: string) {
    if (!datos || !ultimoAnio) return [];
    return MUNICIPIOS.map((m) => {
      const a = datos!.comp.municipios[m].anual.find((x) => x.anio === ultimoAnio);
      const v = a?.capitulos[clave] ?? null;
      return { id: m, etiqueta: NOMBRE_CORTO[m], valor: escala(m, v), color: m };
    });
  }
</script>

<section aria-labelledby="h-comp">
  <h1 id="h-comp">Comparar municipios</h1>
  <p class="muted lead">
    Monterrey tiene casi nueve veces la población de San Pedro, así que comparar totales engaña. Por eso aquí se
    compara, de entrada, el gasto <Termino id="por-habitante">por habitante</Termino>.
  </p>
  <div class="seg modo" role="radiogroup" aria-label="Unidad">
    <button type="button" class="btn" role="radio" aria-checked={porHab} onclick={() => (porHab = true)}>Por habitante</button>
    <button type="button" class="btn" role="radio" aria-checked={!porHab} onclick={() => (porHab = false)}>Total</button>
  </div>
  <Estado {error} cargando={!datos && !error} />

  {#if datos}
    <div class="grid grid-2">
      {#if comun}
        <article class="card">
          <h2>Gasto {porHab ? 'por habitante' : 'total'}, {acumulado(comun)}</h2>
          <p class="small muted">Último periodo con datos de los tres municipios (reportes trimestrales, gasto devengado).</p>
          <BarList barras={barrasTrim} formato={fmt} titulo={`Gasto ${porHab ? 'por habitante' : 'total'} ${acumulado(comun)}`} valorEtiqueta="Gastado" />
          <Fuente ids={MUNICIPIOS.map((m) => datos!.egr[m].periodos.find((p) => p.periodo === comun)?.fuente)} />
        </article>
      {/if}
      <article class="card">
        <h2>Gasto anual {porHab ? 'por habitante' : 'total'}, 2018–{ultimoAnio}</h2>
        <p class="small muted">
          Datos del INEGI (<Termino id="efipem">EFIPEM</Termino>) en el mismo formato para los tres.
          {#if estatusUltimo.includes('Preliminar')}Las cifras de {ultimoAnio} son preliminares.{/if}
          <Termino id="nominales">Pesos nominales</Termino>.
        </p>
        <LineChart {series} formato={fmt} formatoEje={pesosCorto} titulo={`Gasto anual ${porHab ? 'por habitante' : 'total'} por municipio`} />
        <Fuente ids={[datos.comp.fuente, datos.comp.fuente_poblacion]} />
      </article>
    </div>

    <h2 class="mt">¿En qué gasta cada uno? ({ultimoAnio}{porHab ? ', por habitante' : ''})</h2>
    <p class="muted small">Por <Termino id="capitulo">capítulo del gasto</Termino>. Cada tarjeta compara los tres municipios en un mismo tipo de gasto.</p>
    <div class="grid grid-3">
      {#each caps as c (c)}
        <article class="card">
          <h3>{CAPITULOS[c]?.sencillo} <span class="small muted">(<Termino id={CAPITULOS[c]?.glosario ?? 'capitulo'}>{c}</Termino>)</span></h3>
          <BarList barras={barrasCap(c)} formato={fmt} titulo={`${CAPITULOS[c]?.sencillo} ${ultimoAnio}`} valorEtiqueta={porHab ? 'Por habitante' : 'Total'} />
        </article>
      {/each}
    </div>
    <p class="small muted mt">{datos.comp.metodo}</p>
    <Fuente ids={[datos.comp.fuente, datos.comp.fuente_poblacion]} />
  {/if}
</section>

<style>
  .lead {
    max-width: 70ch;
  }
  .modo {
    margin-bottom: 1rem;
  }
  .mt {
    margin-top: 1.5rem;
  }
</style>
