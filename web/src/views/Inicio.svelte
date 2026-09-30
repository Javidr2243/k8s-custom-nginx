<script lang="ts">
  import { api, NOMBRE, type Deuda, type Egresos, type Movimiento, type Municipio } from '../lib/data';
  import { acumulado, cambio, pesos, porcentaje, fecha } from '../lib/format';
  import { route, link, href } from '../lib/router.svelte';
  import { sencillo, CAPITULOS } from '../lib/capitulos';
  import Filtros from '../components/Filtros.svelte';
  import StatTile from '../components/StatTile.svelte';
  import Waffle from '../components/Waffle.svelte';
  import BarList from '../components/BarList.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';
  import MovimientoItem from '../components/MovimientoItem.svelte';

  let datos = $state<{ egr: Egresos; deuda: Deuda; muns: Municipio[]; movs: Movimiento[] } | null>(null);
  let error = $state<string | null>(null);

  $effect(() => {
    const m = route.municipio;
    error = null;
    Promise.all([api.egresos(m), api.deuda(m), api.municipios(), api.movimientos()])
      .then(([egr, deuda, muns, movs]) => {
        if (route.municipio === m) datos = { egr, deuda, muns, movs };
      })
      .catch((e: Error) => (error = e.message));
  });

  const m = $derived(route.municipio);
  const periodos = $derived(datos?.egr.periodos.map((p) => p.periodo) ?? []);
  const p = $derived(
    datos ? (datos.egr.periodos.find((x) => x.periodo === route.periodo) ?? datos.egr.periodos.at(-1)) : undefined,
  );
  const faltante = $derived(
    route.periodo && datos ? datos.egr.faltantes.find((f) => f.periodo === route.periodo) : undefined,
  );
  const mismoAnterior = $derived(
    p && datos ? datos.egr.periodos.find((x) => x.periodo === `${Number(p.periodo.slice(0, 4)) - 1}${p.periodo.slice(4)}`) : undefined,
  );
  const poblacion = $derived(datos?.muns.find((x) => x.id === m)?.poblacion ?? null);
  const saldo = $derived(datos?.deuda.saldos.at(-1));
  const ejercido = $derived(
    p && p.total.devengado !== null && p.total.modificado ? p.total.devengado / p.total.modificado : null,
  );
  const cambioAnual = $derived(
    p && mismoAnterior && mismoAnterior.total.devengado
      ? ((p.total.devengado ?? 0) - mismoAnterior.total.devengado) / mismoAnterior.total.devengado
      : null,
  );
  const partes = $derived(
    p?.capitulos.map((c) => ({ id: c.clave, etiqueta: sencillo(c.clave), valor: c.montos.devengado ?? 0 })) ?? [],
  );
  const barras = $derived.by(() => {
    if (!p) return [];
    const lista = p.dependencias
      ? p.dependencias.map((d) => ({ id: d.id, etiqueta: d.nombre, montos: d.montos }))
      : p.capitulos.map((c) => ({ id: c.clave, etiqueta: CAPITULOS[c.clave]?.sencillo ?? c.nombre, montos: c.montos }));
    return lista
      .sort((a, b) => (b.montos.devengado ?? 0) - (a.montos.devengado ?? 0))
      .slice(0, 8)
      .map((d) => ({
        id: d.id,
        etiqueta: d.etiqueta,
        valor: d.montos.devengado,
        referencia: d.montos.modificado,
        tooltip: [
          { valor: pesos(d.montos.devengado), etiqueta: 'gastado (devengado)' },
          { valor: pesos(d.montos.modificado), etiqueta: 'presupuesto modificado' },
          { valor: pesos(d.montos.aprobado), etiqueta: 'presupuesto aprobado' },
        ],
      }));
  });
  const movs = $derived(datos?.movs.filter((x) => x.municipio === m).slice(0, 5) ?? []);
</script>

<section aria-labelledby="h-inicio">
  <h1 id="h-inicio">¿A dónde va el dinero de {NOMBRE[m]}?</h1>
  <p class="lead muted">
    Cómo obtiene y gasta su dinero el gobierno municipal, explicado con datos oficiales.
  </p>

  <Filtros {periodos} />
  <Estado {error} cargando={!datos && !error} />

  {#if faltante}
    <p class="notice">
      No hay datos de gasto de {NOMBRE[m]} para {acumulado(faltante.periodo)}: {faltante.motivo} Se muestra el periodo
      más reciente disponible.
    </p>
  {/if}

  {#if datos && p}
    <p class="resumen">
      De {acumulado(p.periodo)}, el gobierno de {NOMBRE[m]}
      <Termino id="devengado">gastó</Termino>
      <strong>{pesos(p.total.devengado)}</strong>
      de un <Termino id="modificado">presupuesto</Termino> de <strong>{pesos(p.total.modificado)}</strong> para todo el
      año{#if cambioAnual !== null}, {cambio(cambioAnual)} frente al mismo periodo del año anterior{/if}.
      <Termino id="acumulado">Las cifras son acumuladas</Termino>.
    </p>

    <div class="grid grid-3 tiles">
      <StatTile
        value={pesos(p.total.devengado)}
        sub={`${porcentaje(ejercido)} del presupuesto modificado`}
        origen={{
          calculo: `Total de la columna «Devengado» del estado de gasto del municipio, acumulado de enero al ${fecha(p.fecha_corte)}. El porcentaje es Devengado ÷ Modificado.`,
          fuentes: [p.fuente],
        }}
      >
        {#snippet label()}Gastado ({acumulado(p.periodo)}){/snippet}
      </StatTile>
      <StatTile
        origen={{
          calculo: 'Columnas «Aprobado» (presupuesto autorizado a inicio de año) y «Modificado» (después de ampliaciones y reducciones) del mismo documento. El cambio es (Modificado − Aprobado) ÷ Aprobado.',
          fuentes: [p.fuente],
        }}
        value={pesos(p.total.modificado)}
        sub={`Aprobado: ${pesos(p.total.aprobado)} (${cambio(
          p.total.aprobado ? ((p.total.modificado ?? 0) - p.total.aprobado) / p.total.aprobado : null,
        )} en cambios)`}
      >
        {#snippet label()}<Termino id="modificado">Presupuesto modificado</Termino>{/snippet}
      </StatTile>
      <StatTile
        origen={{
          calculo: `Gasto devengado de ${acumulado(p.periodo)} dividido entre la población del municipio según el Censo de Población y Vivienda 2020 del INEGI.`,
          fuentes: [p.fuente, 'inegi-mgem-19'],
        }}
        value={poblacion && p.total.devengado ? pesos(p.total.devengado / poblacion) : 'Sin dato'}
        sub={`Población: ${poblacion?.toLocaleString('es-MX') ?? '—'} (Censo 2020)`}
      >
        {#snippet label()}Gasto <Termino id="por-habitante">por habitante</Termino>{/snippet}
      </StatTile>
      <StatTile
        value={saldo ? pesos(saldo.total) : 'Sin dato'}
        sub={saldo ? `Saldo al ${fecha(saldo.fecha)}` : ''}
        origen={{
          calculo: 'Saldo total de financiamientos y obligaciones inscritos a nombre del municipio en el Registro Público Único de la Secretaría de Hacienda (publicado en millones de pesos).',
          fuentes: [saldo?.fuente],
        }}
      >
        {#snippet label()}<Termino id="deuda">Deuda registrada</Termino>{/snippet}
      </StatTile>
    </div>

    <div class="grid grid-2 mt">
      <article class="card">
        <h2>De cada $100 que gastó</h2>
        <p class="muted small">
          Por tipo de gasto (<Termino id="capitulo">capítulo del gasto</Termino>), {acumulado(p.periodo)}. Pasa el cursor
          o toca un rubro para ver el monto.
        </p>
        <Waffle {partes} titulo={`De cada 100 pesos que gastó ${NOMBRE[m]} en ${acumulado(p.periodo)}`} />
        <Fuente ids={[p.fuente]} />
      </article>

      <article class="card">
        <h2>{p.dependencias ? '¿Quién gasta más?' : '¿En qué gasta más?'}</h2>
        <p class="muted small">
          {#if p.dependencias}
            Las 8 <Termino id="dependencia">dependencias</Termino> con más gasto. La barra clara es su presupuesto
            modificado para el año.
          {:else}
            {p.motivo_sin_dependencias} Se muestra el gasto por tipo; la barra clara es el presupuesto modificado.
          {/if}
        </p>
        <BarList
          {barras}
          formato={pesos}
          titulo={`Gasto de ${NOMBRE[m]} por ${p.dependencias ? 'dependencia' : 'tipo de gasto'}`}
          valorEtiqueta="Gastado (devengado)"
          referenciaEtiqueta="Presupuesto modificado"
        />
        <p class="small"><a href={href('/mapa')} use:link>Ver todas en el mapa del gobierno →</a></p>
        <Fuente ids={[p.fuente_dependencias ?? p.fuente]} />
      </article>
    </div>

    <article class="card mt">
      <h2>Movimientos recientes</h2>
      <ul class="movs">
        {#each movs as mv, i (i)}
          <MovimientoItem movimiento={mv} />
        {/each}
      </ul>
      <p class="small"><a href={href('/movimientos')} use:link>Ver todos los movimientos →</a></p>
    </article>

    {#if p.notas.length}
      <aside class="notice mt small">
        <strong>Notas sobre estos datos:</strong>
        {#each p.notas as n, i (i)}<span> {n}</span>{/each}
      </aside>
    {/if}
  {/if}
</section>

<style>
  .lead {
    font-size: 1.1rem;
    max-width: 60ch;
  }
  .resumen {
    font-size: 1.15rem;
    max-width: 70ch;
  }
  .tiles {
    margin-top: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  }
  .mt {
    margin-top: 1rem;
  }
  .movs {
    list-style: none;
    margin: 0;
    padding: 0;
  }
</style>
