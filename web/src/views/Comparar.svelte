<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE, NOMBRE_CORTO, type Comparativo, type Egresos, type MunicipioId, type Municipio } from '../lib/data';
  import { acumulado, pesos, pesosCorto } from '../lib/format';
  import { CAPITULOS } from '../lib/capitulos';
  import BarList from '../components/BarList.svelte';
  import LineChart from '../components/LineChart.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';
  import Seccion from '../components/Seccion.svelte';

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
  /** Highest and lowest of a set of bars (null values skipped). */
  function extremos(bs: { id: MunicipioId; valor: number | null }[]) {
    const v = bs.filter((b) => b.valor !== null && b.valor > 0).sort((a, b) => (b.valor ?? 0) - (a.valor ?? 0));
    return v.length > 1 ? { alto: v[0]!, bajo: v.at(-1)!, veces: (v[0]!.valor ?? 0) / (v.at(-1)!.valor || 1) } : null;
  }
  const unidad = $derived(porHab ? ' por habitante' : '');
  const xTrim = $derived(extremos(barrasTrim));
  const tTrim = $derived(
    xTrim
      ? `${NOMBRE_CORTO[xTrim.alto.id]} gastó ${xTrim.veces.toFixed(1)} veces lo de ${NOMBRE_CORTO[xTrim.bajo.id]}${unidad}`
      : 'Gasto de los tres municipios',
  );
  const anual = $derived(
    datos && ultimoAnio
      ? MUNICIPIOS.map((m) => {
          const a = datos!.comp.municipios[m].anual.find((x) => x.anio === ultimoAnio);
          return { id: m, valor: a ? (porHab ? a.gasto_por_habitante : a.gasto_total) : null };
        })
      : [],
  );
  const xAnual = $derived(extremos(anual));
  /** Spending type where the three differ the most (ratio highest ÷ lowest). */
  const mayorDif = $derived.by(() => {
    let mejor: { c: string; x: NonNullable<ReturnType<typeof extremos>> } | null = null;
    for (const c of caps) {
      const x = extremos(barrasCap(c));
      if (x && (!mejor || x.veces > mejor.x.veces)) mejor = { c, x };
    }
    return mejor;
  });
</script>

<section aria-labelledby="h-comp">
  <header>
    <p class="eyebrow">Los tres municipios</p>
    <h1 id="h-comp">Comparar municipios</h1>
    <p class="muted lead">
      Monterrey tiene casi nueve veces la población de San Pedro, así que comparar totales engaña. Por eso aquí se
      compara, de entrada, el gasto <Termino id="por-habitante">por habitante</Termino>.
    </p>
    <div class="seg modo" role="radiogroup" aria-label="Unidad">
      <button type="button" class="btn" role="radio" aria-checked={porHab} onclick={() => (porHab = true)}>Por habitante</button>
      <button type="button" class="btn" role="radio" aria-checked={!porHab} onclick={() => (porHab = false)}>Total</button>
    </div>
  </header>
  <Estado {error} cargando={!datos && !error} />

  {#if datos}
    {#if xTrim && comun}
      <p class="titular">
        <span>
          De {acumulado(comun)}, {NOMBRE_CORTO[xTrim.alto.id]} gastó <strong class="num">{fmt(xTrim.alto.valor)}</strong>{unidad}.
        </span>
        <span class="suave">
          Es {xTrim.veces.toFixed(1)} veces lo de {NOMBRE_CORTO[xTrim.bajo.id]} ({fmt(xTrim.bajo.valor)}){porHab ? '; así se compara sin que pese el tamaño de cada municipio' : ''}.
        </span>
      </p>
    {/if}

    <div class="banda">
      <div class="dos">
        {#if comun}
          <Seccion
            id="h-trim"
            pregunta={`Gasto${unidad}, ${acumulado(comun)}`}
            titular={tTrim}
            detalle="Último periodo con datos de los tres municipios (reportes trimestrales, gasto devengado)."
          >
            <BarList barras={barrasTrim} formato={fmt} titulo={`Gasto${unidad} ${acumulado(comun)}`} valorEtiqueta="Gastado" />
            <Fuente ids={MUNICIPIOS.map((m) => datos!.egr[m].periodos.find((p) => p.periodo === comun)?.fuente)} compacto />
          </Seccion>
        {/if}
        <Seccion
          id="h-anual"
          pregunta={`Gasto anual${unidad}, 2018–${ultimoAnio}`}
          titular={xAnual
            ? `En ${ultimoAnio}: ${NOMBRE_CORTO[xAnual.alto.id]} ${fmt(xAnual.alto.valor)}, ${NOMBRE_CORTO[xAnual.bajo.id]} ${fmt(xAnual.bajo.valor)}`
            : `Gasto anual, 2018–${ultimoAnio}`}
          detalle={`Datos del INEGI en el mismo formato para los tres${estatusUltimo.includes('Preliminar') ? `; las cifras de ${ultimoAnio} son preliminares` : ''}. Pesos nominales.`}
        >
          <p class="small muted">
            Fuente: <Termino id="efipem">EFIPEM</Termino> · <Termino id="nominales">¿Qué son pesos nominales?</Termino>
          </p>
          <LineChart {series} formato={fmt} formatoEje={pesosCorto} titulo={`Gasto anual${unidad} por municipio`} />
          <Fuente ids={[datos.comp.fuente, datos.comp.fuente_poblacion]} compacto />
        </Seccion>
      </div>
    </div>

    <Seccion
      id="h-caps"
      pregunta={`¿En qué gasta cada uno? (${ultimoAnio}${unidad})`}
      titular={mayorDif
        ? `La mayor diferencia está en ${CAPITULOS[mayorDif.c]?.sencillo.toLowerCase()}: ${mayorDif.x.veces.toFixed(1)} veces`
        : '¿En qué gasta cada uno?'}
      detalle={mayorDif
        ? `${NOMBRE_CORTO[mayorDif.x.alto.id]} ${fmt(mayorDif.x.alto.valor)} frente a ${NOMBRE_CORTO[mayorDif.x.bajo.id]} ${fmt(mayorDif.x.bajo.valor)}${unidad}. Cada renglón compara a los tres en un mismo tipo de gasto.`
        : null}
    >
      <div class="table-wrap">
        <table class="data caps">
          <caption class="sr-only">Gasto{unidad} por tipo de gasto y municipio en {ultimoAnio}</caption>
          <thead>
            <tr>
              <th scope="col">Tipo de gasto</th>
              {#each MUNICIPIOS as x (x)}<th scope="col" class="r"><span class="punto bg-{x}" aria-hidden="true"></span>{NOMBRE_CORTO[x]}</th>{/each}
              <th scope="col" class="r">Mayor ÷ menor</th>
            </tr>
          </thead>
          <tbody>
            {#each caps as c (c)}
              {@const bs = barrasCap(c)}
              {@const x = extremos(bs)}
              <tr class:destacada={mayorDif?.c === c}>
                <th scope="row">{CAPITULOS[c]?.sencillo} <span class="small muted">(<Termino id={CAPITULOS[c]?.glosario ?? 'capitulo'}>{c}</Termino>)</span></th>
                {#each bs as b (b.id)}
                  <td class="r num" class:alto={x?.alto.id === b.id}>{fmt(b.valor)}</td>
                {/each}
                <td class="r num">{x ? `${x.veces.toFixed(1)}×` : '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="small muted">En negritas, el que más gasta en cada tipo. Resaltado, el tipo de gasto con la mayor diferencia.</p>
      <p class="small muted">{datos.comp.metodo}</p>
      <Fuente ids={[datos.comp.fuente, datos.comp.fuente_poblacion]} compacto />
    </Seccion>
  {/if}
</section>

<style>
  .lead {
    max-width: 70ch;
  }
  .modo {
    margin-bottom: 0.5rem;
  }
  .caps td.alto {
    font-weight: 700;
  }
  .caps tr.destacada > * {
    background: var(--surface-2);
  }
  .punto {
    display: inline-block;
    width: 0.6em;
    height: 0.6em;
    margin-right: 0.35em;
    border-radius: 50%;
  }
</style>
