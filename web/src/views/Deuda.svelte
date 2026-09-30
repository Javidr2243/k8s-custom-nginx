<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE, NOMBRE_CORTO, type Deuda, type MunicipioId, type Municipio } from '../lib/data';
  import { cambio, fecha, pesos, pesosCorto, trimestre, porcentaje } from '../lib/format';
  import { route } from '../lib/router.svelte';
  import Filtros from '../components/Filtros.svelte';
  import StatTile from '../components/StatTile.svelte';
  import LineChart from '../components/LineChart.svelte';
  import BarList from '../components/BarList.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';

  let todas = $state<Record<MunicipioId, Deuda> | null>(null);
  let muns = $state<Municipio[]>([]);
  let error = $state<string | null>(null);
  Promise.all([api.municipios(), ...MUNICIPIOS.map((m) => api.deuda(m))])
    .then(([ms, ...ds]) => {
      muns = ms as Municipio[];
      todas = Object.fromEntries(MUNICIPIOS.map((m, i) => [m, ds[i]])) as Record<MunicipioId, Deuda>;
    })
    .catch((e: Error) => (error = e.message));

  const m = $derived(route.municipio);
  const d = $derived(todas?.[m]);
  const saldo = $derived(d?.saldos.at(-1));
  const haceUnAnio = $derived(
    d && saldo ? d.saldos.find((s) => s.periodo === `${Number(saldo.periodo.slice(0, 4)) - 1}${saldo.periodo.slice(4)}`) : undefined,
  );
  const pob = (x: MunicipioId) => muns.find((y) => y.id === x)?.poblacion ?? null;
  const alerta = $derived(d?.alertas.filter((a) => a.resultado !== null).at(-1));
  const ICONO: Record<number, string> = { 1: '✓', 2: '!', 3: '✕' };

  const pagosAnuales = $derived.by(() => {
    if (!d) return [];
    const porAnio = new Map<string, { periodo: string; v: number | null }>();
    for (const p of d.pagos_capitulo_9000) {
      const y = p.periodo.slice(0, 4);
      const prev = porAnio.get(y);
      if (!prev || p.periodo > prev.periodo) porAnio.set(y, { periodo: p.periodo, v: p.montos?.devengado ?? 0 });
    }
    return [...porAnio.entries()].map(([y, x]) => ({
      id: y,
      etiqueta: x.periodo.endsWith('T4') ? y : `${y} (hasta ${trimestre(x.periodo).split(' de ')[0]})`,
      valor: x.v,
    }));
  });
</script>

<section aria-labelledby="h-deuda">
  <h1 id="h-deuda">Deuda de {NOMBRE[m]}</h1>
  <p class="muted lead">
    Cuánto debe el municipio a los bancos, cuánto paga y qué tan manejable es su deuda según la Secretaría de Hacienda.
  </p>
  <Filtros mostrarPeriodo={false} />
  <Estado {error} cargando={!todas && !error} />

  {#if d && todas}
    <div class="grid tiles">
      <StatTile
        value={saldo ? pesos(saldo.total) : 'Sin dato'}
        sub={saldo ? `Al ${fecha(saldo.fecha)}` : ''}
        origen={{ calculo: 'Saldo total inscrito en el Registro Público Único de Hacienda (cuadro trimestral por municipio).', fuentes: [saldo?.fuente] }}
      >
        {#snippet label()}<Termino id="saldo">Deuda registrada</Termino>{/snippet}
      </StatTile>
      <StatTile
        value={saldo && haceUnAnio ? cambio(haceUnAnio.total ? (saldo.total - haceUnAnio.total) / haceUnAnio.total : null) : 'Sin dato'}
        sub={haceUnAnio ? `vs. ${fecha(haceUnAnio.fecha)} (${pesos(haceUnAnio.total)})` : ''}
        tone={saldo && haceUnAnio && saldo.total < haceUnAnio.total ? 'good' : 'neutral'}
        label="Cambio en 12 meses"
        origen={{ calculo: 'Saldo del trimestre más reciente comparado con el del mismo trimestre del año anterior, ambos del Registro Público Único.', fuentes: [saldo?.fuente, haceUnAnio?.fuente] }}
      />
      <StatTile
        value={saldo && pob(m) ? pesos(saldo.total / (pob(m) ?? 1)) : 'Sin dato'}
        sub="Deuda entre población (Censo 2020)"
        origen={{ calculo: 'Saldo de la deuda registrada dividido entre la población del Censo 2020 (INEGI).', fuentes: [saldo?.fuente, 'inegi-mgem-19'] }}
      >
        {#snippet label()}Por <Termino id="por-habitante">habitante</Termino>{/snippet}
      </StatTile>
      <StatTile
        value={alerta?.etiqueta ?? 'Sin evaluación'}
        sub={alerta?.evaluacion ?? ''}
        origen={{ calculo: 'Resultado publicado por Hacienda en el Sistema de Alertas para municipios (1 = sostenible, 2 = en observación, 3 = elevado).', fuentes: [alerta?.fuente] }}
      >
        {#snippet label()}<Termino id="alertas">Calificación de Hacienda</Termino>{/snippet}
        {#if alerta?.resultado}
          <p class="status s{alerta.resultado}"><span aria-hidden="true">{ICONO[alerta.resultado]}</span> Nivel {alerta.resultado} de 3</p>
        {/if}
      </StatTile>
    </div>

    <div class="grid grid-2 mt">
      <article class="card">
        <h2>Saldo de la deuda por trimestre</h2>
        {#if d.saldos.every((s) => s.total === 0)}
          <p>{NOMBRE[m]} no tiene deuda inscrita en el <Termino id="rpu">Registro Público Único</Termino> en ningún trimestre desde 2023.</p>
        {:else}
          <LineChart
            series={[{ id: m, etiqueta: NOMBRE_CORTO[m], color: m, puntos: d.saldos.map((s) => ({ x: s.periodo, v: s.total })) }]}
            formato={pesos}
            formatoEje={pesosCorto}
            etiquetaX={(p) => `${p.slice(-1)}T ${p.slice(2, 4)}`}
            titulo={`Saldo de la deuda de ${NOMBRE[m]} por trimestre`}
          />
        {/if}
        <Fuente ids={[d.saldos.at(-1)?.fuente]} etiqueta="Fuente (último trimestre)" />
      </article>
      <article class="card">
        <h2>Pagos de deuda por año</h2>
        <p class="small muted">{d.nota_pagos}</p>
        <BarList barras={pagosAnuales} formato={pesos} titulo={`Pagos de deuda de ${NOMBRE[m]} por año`} valorEtiqueta="Pagado (devengado)" />
        <Fuente ids={[d.pagos_capitulo_9000.at(-1)?.fuente]} etiqueta="Fuente (último periodo)" />
      </article>
    </div>

    {#if d.anual_detalle.length}
      <article class="card mt">
        <h2>Intereses y pago de capital de Monterrey</h2>
        <p class="small muted">
          <Termino id="intereses">Intereses</Termino> (el costo del préstamo) frente a
          <Termino id="amortizacion">amortización</Termino> (lo que reduce la deuda). El último año es parcial.
        </p>
        <LineChart
          series={[
            { id: 'int', etiqueta: 'Intereses', color: 'cat-1', puntos: d.anual_detalle.map((x) => ({ x: String(x.anio), v: x.intereses })) },
            { id: 'amo', etiqueta: 'Amortización (capital)', color: 'cat-2', puntos: d.anual_detalle.map((x) => ({ x: String(x.anio), v: x.amortizacion })) },
          ]}
          formato={pesos}
          formatoEje={pesosCorto}
          titulo="Intereses y amortización de la deuda de Monterrey por año"
        />
        <Fuente ids={[d.fuente_anual_detalle]} />
      </article>
    {/if}

    <article class="card mt">
      <h2>Créditos vigentes</h2>
      {#if d.creditos.length}
        <div class="table-wrap">
          <table class="data">
            <caption class="sr-only">Créditos de {NOMBRE[m]}</caption>
            <thead>
              <tr>
                <th scope="col">Banco</th><th scope="col">Tipo</th><th scope="col" class="r">Monto original</th>
                <th scope="col" class="r">Saldo</th><th scope="col">Tasa</th><th scope="col">Vence</th><th scope="col">Garantía / destino</th>
              </tr>
            </thead>
            <tbody>
              {#each d.creditos as c, i (i)}
                <tr>
                  <td>{c.acreedor}</td>
                  <td>{c.tipo}</td>
                  <td class="r">{pesos(c.monto_original)}</td>
                  <td class="r">{c.saldo !== null ? pesos(c.saldo) : 'Sin dato'}</td>
                  <td>{c.tasa}{c.sobretasa !== null ? ` + ${porcentaje(c.sobretasa, 1)}` : ''}</td>
                  <td>{fecha(c.vencimiento)}</td>
                  <td>{c.fuente_pago || '—'}{c.destino ? ` · ${c.destino}` : ''}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <p class="small muted">{d.nota_creditos} Saldos al {fecha(d.creditos[0]?.saldo_fecha)}. <Termino id="tiie">¿Qué es la TIIE?</Termino></p>
      {:else}
        <p>No hay créditos inscritos a nombre de {NOMBRE[m]}.</p>
      {/if}
      <Fuente ids={[d.fuente_creditos]} />
    </article>

    <article class="card mt">
      <h2>Historial de la calificación de Hacienda</h2>
      <div class="table-wrap">
        <table class="data">
          <caption class="sr-only">Resultados del Sistema de Alertas</caption>
          <thead><tr><th scope="col">Evaluación</th><th scope="col">Resultado</th><th scope="col" class="r">Deuda / ingresos libres</th><th scope="col" class="r">Pago de deuda / ingresos libres</th></tr></thead>
          <tbody>
            {#each [...d.alertas].reverse() as a, i (i)}
              <tr>
                <td>{a.evaluacion}</td>
                <td>{#if a.resultado}<span class="status s{a.resultado}"><span aria-hidden="true">{ICONO[a.resultado]}</span> {a.etiqueta}</span>{:else}{a.nota || 'Sin evaluación'}{/if}</td>
                <td class="r">{porcentaje(a.indicadores[0], 1)}</td>
                <td class="r">{porcentaje(a.indicadores[1], 1)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="small muted">{d.nota_alertas}</p>
      <Fuente ids={[d.alertas.at(-1)?.fuente]} etiqueta="Fuente (última evaluación)" />
    </article>

    <article class="card mt">
      <h2>Comparación: deuda por habitante</h2>
      <BarList
        barras={MUNICIPIOS.map((x) => {
          const s = todas![x].saldos.at(-1);
          return { id: x, etiqueta: NOMBRE[x], valor: s && pob(x) ? s.total / (pob(x) ?? 1) : null, color: x };
        })}
        formato={pesos}
        titulo="Deuda por habitante de los tres municipios"
        valorEtiqueta="Deuda por habitante"
      />
    </article>
  {/if}
</section>

<style>
  .lead {
    max-width: 70ch;
  }
  .tiles {
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  }
  .mt {
    margin-top: 1rem;
  }
  .status {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-weight: 600;
    margin: 0.25rem 0 0;
  }
  .status span[aria-hidden] {
    display: inline-grid;
    place-items: center;
    width: 1.3em;
    height: 1.3em;
    border-radius: 50%;
    color: #fff;
    font-size: 0.8em;
  }
  .s1 span[aria-hidden] {
    background: var(--good);
  }
  .s2 span[aria-hidden] {
    background: var(--warning);
    color: #0b0b0b;
  }
  .s3 span[aria-hidden] {
    background: var(--critical);
  }
</style>
