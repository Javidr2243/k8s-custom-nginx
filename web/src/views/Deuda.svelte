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
  import Seccion from '../components/Seccion.svelte';

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

  // Findings used as section headlines (actual values, no subjective words).
  const cambio12 = $derived(saldo && haceUnAnio?.total ? (saldo.total - haceUnAnio.total) / haceUnAnio.total : null);
  const sinDeuda = $derived(!!d && d.saldos.every((s) => s.total === 0));
  const tSaldo = $derived.by(() => {
    if (sinDeuda) return 'No tiene deuda registrada desde 2023';
    if (cambio12 === null) return `Deuda al ${fecha(saldo?.fecha)}: ${pesos(saldo?.total)}`;
    return `La deuda ${cambio12 < 0 ? 'bajó' : cambio12 > 0 ? 'subió' : 'no cambió'}${cambio12 !== 0 ? ` ${porcentaje(Math.abs(cambio12))}` : ''} en un año`;
  });
  const dSaldo = $derived(
    haceUnAnio && saldo && !sinDeuda
      ? `De ${pesos(haceUnAnio.total)} al ${fecha(haceUnAnio.fecha)} a ${pesos(saldo.total)} al ${fecha(saldo.fecha)}.`
      : null,
  );
  const ultimoPagoCompleto = $derived([...pagosAnuales].reverse().find((x) => !x.etiqueta.includes('hasta')));
  const anioActual = $derived(Number(saldo?.periodo.slice(0, 4) ?? 0));
  const detalleCompleto = $derived(d?.anual_detalle.filter((x) => x.anio < anioActual).at(-1));
  const bancos = $derived(new Set(d?.creditos.map((c) => c.acreedor) ?? []).size);
  const porHab = $derived(
    todas
      ? MUNICIPIOS.map((x) => {
          const s = todas![x].saldos.at(-1);
          return { id: x, valor: s && pob(x) ? s.total / (pob(x) ?? 1) : null };
        })
      : [],
  );
  const tComparacion = $derived.by(() => {
    const propio = porHab.find((x) => x.id === m)?.valor;
    if (!propio) return `${NOMBRE_CORTO[m]} no tiene deuda registrada`;
    const orden = porHab.filter((x) => x.valor).sort((a, b) => (b.valor ?? 0) - (a.valor ?? 0));
    const lugar = orden.findIndex((x) => x.id === m) + 1;
    const txt = lugar === 1 ? 'la más alta' : lugar === orden.length ? 'la más baja' : `la ${lugar}ª`;
    return `${NOMBRE_CORTO[m]} debe ${pesos(propio)} por habitante, ${txt} de los ${orden.length} con deuda`;
  });
</script>

<section aria-labelledby="h-deuda">
  <header>
    <p class="eyebrow">Deuda pública</p>
    <h1 id="h-deuda">Deuda de {NOMBRE[m]}</h1>
    <p class="muted lead">
      Cuánto debe el municipio a los bancos, cuánto paga y qué tan manejable es su deuda según la Secretaría de Hacienda.
    </p>
    <Filtros mostrarPeriodo={false} />
  </header>
  <Estado {error} cargando={!todas && !error} />

  {#if d && todas}
    <p class="titular">
      {#if sinDeuda}
        <span>{NOMBRE_CORTO[m]} no tiene deuda con bancos inscrita en el registro de Hacienda.</span>
      {:else}
        <span>{NOMBRE_CORTO[m]} debe <strong class="num">{pesos(saldo?.total)}</strong> a los bancos.</span>
        <span class="suave">
          Saldo al {fecha(saldo?.fecha)}{cambio12 !== null ? `, ${porcentaje(Math.abs(cambio12))} ${cambio12 < 0 ? 'menos' : 'más'} que un año antes` : ''}{alerta?.etiqueta ? `. Hacienda lo califica como «${alerta.etiqueta.toLowerCase()}»` : ''}.
        </span>
      {/if}
    </p>

    <div class="cifras">
      <StatTile
        value={saldo ? pesos(saldo.total) : 'Sin dato'}
        sub={saldo ? `Al ${fecha(saldo.fecha)}` : ''}
        origen={{ calculo: 'Saldo total inscrito en el Registro Público Único de Hacienda (cuadro trimestral por municipio).', fuentes: [saldo?.fuente] }}
      >
        {#snippet label()}<Termino id="saldo">Deuda registrada</Termino>{/snippet}
      </StatTile>
      <StatTile
        value={saldo && haceUnAnio ? cambio(cambio12) : 'Sin dato'}
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
        value={alerta?.resultado ? `Nivel ${alerta.resultado} de 3` : 'Sin evaluación'}
        sub={alerta?.evaluacion ?? ''}
        origen={{ calculo: 'Resultado publicado por Hacienda en el Sistema de Alertas para municipios (1 = sostenible, 2 = en observación, 3 = elevado).', fuentes: [alerta?.fuente] }}
      >
        {#snippet label()}<Termino id="alertas">Calificación de Hacienda</Termino>{/snippet}
        {#if alerta?.resultado}
          <p class="status s{alerta.resultado}"><span aria-hidden="true">{ICONO[alerta.resultado]}</span> {alerta.etiqueta}</p>
        {/if}
      </StatTile>
    </div>

    <div class="banda">
      <div class="dos">
        <Seccion id="h-saldo" pregunta="Saldo de la deuda por trimestre" titular={tSaldo} detalle={dSaldo}>
          {#if !sinDeuda}
            <LineChart
              series={[{ id: m, etiqueta: NOMBRE_CORTO[m], color: m, puntos: d.saldos.map((s) => ({ x: s.periodo, v: s.total })) }]}
              formato={pesos}
              formatoEje={pesosCorto}
              etiquetaX={(p) => `${p.slice(-1)}T ${p.slice(2, 4)}`}
              titulo={`Saldo de la deuda de ${NOMBRE[m]} por trimestre`}
            />
          {:else}
            <p>Sin saldo en el <Termino id="rpu">Registro Público Único</Termino> en ningún trimestre.</p>
          {/if}
          <Fuente ids={[d.saldos.at(-1)?.fuente]} compacto />
        </Seccion>
        <Seccion
          id="h-pagos"
          pregunta="Pagos de deuda por año"
          titular={ultimoPagoCompleto && ultimoPagoCompleto.valor ? `En ${ultimoPagoCompleto.id} pagó ${pesos(ultimoPagoCompleto.valor)} de deuda` : 'Pagos de deuda por año'}
          detalle={d.nota_pagos}
        >
          <BarList barras={pagosAnuales} formato={pesos} titulo={`Pagos de deuda de ${NOMBRE[m]} por año`} valorEtiqueta="Pagado (devengado)" />
          <Fuente ids={[d.pagos_capitulo_9000.at(-1)?.fuente]} compacto />
        </Seccion>
      </div>
    </div>

    {#if d.anual_detalle.length}
      <Seccion
        id="h-intereses"
        pregunta="Intereses y pago de capital"
        titular={detalleCompleto
          ? `En ${detalleCompleto.anio} pagó ${pesos(detalleCompleto.intereses)} de intereses y ${pesos(detalleCompleto.amortizacion)} de capital`
          : 'Intereses y pago de capital'}
        detalle={detalleCompleto && detalleCompleto.amortizacion
          ? `Por cada peso que bajó la deuda, pagó $${(detalleCompleto.intereses / detalleCompleto.amortizacion).toFixed(2)} de intereses. El último año es parcial.`
          : 'El último año es parcial.'}
      >
        <p class="small muted">
          <Termino id="intereses">Intereses</Termino>: el costo del préstamo. <Termino id="amortizacion">Amortización</Termino>:
          lo que reduce la deuda.
        </p>
        <LineChart
          series={[
            { id: 'int', etiqueta: 'Intereses', color: 'cat-1', puntos: d.anual_detalle.map((x) => ({ x: String(x.anio), v: x.intereses })) },
            { id: 'amo', etiqueta: 'Amortización (capital)', color: 'cat-2', puntos: d.anual_detalle.map((x) => ({ x: String(x.anio), v: x.amortizacion })) },
          ]}
          formato={pesos}
          formatoEje={pesosCorto}
          titulo={`Intereses y amortización de la deuda de ${NOMBRE[m]} por año`}
        />
        <Fuente ids={[d.fuente_anual_detalle]} compacto />
      </Seccion>
    {/if}

    <Seccion
      id="h-creditos"
      banda
      pregunta="Créditos vigentes"
      titular={d.creditos.length
        ? `${d.creditos.length} ${d.creditos.length === 1 ? 'crédito' : 'créditos'} con ${bancos} ${bancos === 1 ? 'banco' : 'bancos'}`
        : `${NOMBRE_CORTO[m]} no tiene créditos inscritos`}
      detalle={d.creditos.length ? `${d.nota_creditos} Saldos al ${fecha(d.creditos[0]?.saldo_fecha)}.` : null}
    >
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
        <p class="small muted"><Termino id="tiie">¿Qué es la TIIE?</Termino></p>
      {/if}
      <Fuente ids={[d.fuente_creditos]} compacto />
    </Seccion>

    <Seccion
      id="h-alertas"
      pregunta="Calificación de Hacienda"
      titular={alerta?.resultado ? `Nivel ${alerta.resultado} de 3: ${alerta.etiqueta?.toLowerCase()}` : 'Sin evaluación reciente'}
      detalle={d.nota_alertas}
    >
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
      <Fuente ids={[d.alertas.at(-1)?.fuente]} compacto />
    </Seccion>

    <Seccion id="h-comp" banda pregunta="Comparación: deuda por habitante" titular={tComparacion}>
      <BarList
        barras={porHab.map((x) => ({ id: x.id, etiqueta: NOMBRE[x.id], valor: x.valor, color: x.id }))}
        formato={pesos}
        titulo="Deuda por habitante de los tres municipios"
        valorEtiqueta="Deuda por habitante"
      />
      <Fuente ids={[...MUNICIPIOS.map((x) => todas![x].saldos.at(-1)?.fuente), 'inegi-mgem-19']} compacto />
    </Seccion>
  {/if}
</section>

<style>
  .lead {
    max-width: 70ch;
    margin-bottom: 1.25rem;
  }
  .cifras {
    margin-bottom: 2.5rem;
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
