<script lang="ts" module>
  import type { Montos } from '../lib/data';
export interface Seleccion {
  id: string;
  tipo: 'centro' | 'ingreso' | 'gasto' | 'organo';
  etiqueta: string;
  montos?: Montos;
  ingreso?: { estimado: number | null; recaudado: number | null; periodo: string; fuente: string; anual?: boolean };
  glosario?: string;
}

</script>

<script lang="ts">
  // Side panel for a node in the government map: budget approved vs modified vs spent, quarterly trend,
  // breakdown, mid-year changes and sources.
  import type { Egresos, PeriodoEgresos } from '../lib/data';
  import { acumulado, cambio, pesos, porcentaje, pesosCorto } from '../lib/format';
  import { CAPITULOS } from '../lib/capitulos';
  import BarList from './BarList.svelte';
  import LineChart from './LineChart.svelte';
  import Fuente from './Fuente.svelte';
  import Termino from './Termino.svelte';
  import ContratosDependencia from './ContratosDependencia.svelte';
  import { route } from '../lib/router.svelte';

  let {
    sel,
    egresos,
    periodo,
    nombreMunicipio,
    onclose,
  }: {
    sel: Seleccion;
    egresos: Egresos;
    periodo: PeriodoEgresos;
    nombreMunicipio: string;
    onclose: () => void;
  } = $props();

  function montosEn(p: PeriodoEgresos): Montos | null {
    if (sel.tipo === 'centro') return p.total;
    const d = p.dependencias?.find((x) => x.id === sel.id);
    if (d) return d.montos;
    const c = p.capitulos.find((x) => `cap-${x.clave}` === sel.id);
    return c?.montos ?? null;
  }

  const capitulo = $derived(periodo.capitulos.find((c) => `cap-${c.clave}` === sel.id));
  const dependencia = $derived(periodo.dependencias?.find((d) => d.id === sel.id));
  const m = $derived(sel.montos ?? montosEn(periodo));
  const cambioAnual = $derived(
    m && m.aprobado ? ((m.modificado ?? 0) - m.aprobado) / m.aprobado : null,
  );

  // Trend: one line per year, x = quarter (figures are cumulative from January).
  const tendencia = $derived.by(() => {
    const anios = [...new Set(egresos.periodos.map((p) => p.periodo.slice(0, 4)))].sort().slice(-4);
    return anios.map((a, i) => ({
      id: a,
      etiqueta: a,
      color: `y${i + (4 - anios.length)}`,
      puntos: ['T1', 'T2', 'T3', 'T4'].map((q) => {
        const p = egresos.periodos.find((x) => x.periodo === `${a}${q}`);
        return { x: q, v: p ? (montosEn(p)?.devengado ?? null) : null };
      }),
    }));
  });
  const hayTendencia = $derived(tendencia.some((s) => s.puntos.filter((p) => p.v !== null).length > 1));
</script>

<aside class="panel card" aria-labelledby="panel-titulo">
  <div class="head">
    <div>
      <p class="tipo small muted">
        {#if sel.tipo === 'gasto'}{dependencia ? 'Dependencia' : 'Tipo de gasto'}{:else if sel.tipo === 'ingreso'}Fuente de ingreso{:else if sel.tipo === 'organo'}Órgano de gobierno{:else}Gobierno municipal{/if}
      </p>
      <h2 id="panel-titulo">{sel.etiqueta}</h2>
    </div>
    <button type="button" class="btn cerrar" onclick={onclose} aria-label="Cerrar panel">×</button>
  </div>

  {#if sel.tipo === 'organo'}
    <p>
      El Ayuntamiento (cabildo) —la presidenta o el presidente municipal, síndicos y regidores— aprueba cada año la
      <Termino id="presupuesto">Ley de Ingresos y el Presupuesto de Egresos</Termino>, autoriza sus modificaciones y la
      contratación de deuda, y revisa la <Termino id="cuenta-publica">Cuenta Pública</Termino>.
    </p>
  {:else if sel.tipo === 'ingreso' && sel.ingreso}
    <dl class="montos">
      <div><dt>{sel.ingreso.anual ? 'Recibido en el año' : 'Recaudado'}</dt><dd>{pesos(sel.ingreso.recaudado)}</dd></div>
      {#if !sel.ingreso.anual}
        <div><dt>Estimado para el año</dt><dd>{pesos(sel.ingreso.estimado)}</dd></div>
        <div>
          <dt>Avance</dt>
          <dd>{porcentaje(sel.ingreso.estimado ? (sel.ingreso.recaudado ?? 0) / sel.ingreso.estimado : null)}</dd>
        </div>
      {/if}
    </dl>
    <p class="small muted">
      {sel.ingreso.anual ? `Total del año ${sel.ingreso.periodo} (INEGI).` : `Acumulado ${acumulado(sel.ingreso.periodo)}.`}
      {#if sel.glosario}<Termino id={sel.glosario}>¿Qué es esto?</Termino>{/if}
    </p>
    <Fuente ids={[sel.ingreso.fuente]} />
  {:else if m}
    <dl class="montos">
      <div><dt><Termino id="aprobado">Aprobado</Termino></dt><dd>{pesos(m.aprobado)}</dd></div>
      <div><dt><Termino id="modificado">Modificado</Termino></dt><dd>{pesos(m.modificado)}</dd></div>
      <div><dt><Termino id="devengado">Gastado (devengado)</Termino></dt><dd>{pesos(m.devengado)}</dd></div>
      <div><dt><Termino id="pagado">Pagado</Termino></dt><dd>{pesos(m.pagado)}</dd></div>
    </dl>
    <p class="small">
      Avance: {porcentaje(m.modificado ? (m.devengado ?? 0) / m.modificado : null)} del presupuesto modificado, al cierre de
      {acumulado(periodo.periodo)}.
    </p>

    <h3>Cambios durante el año</h3>
    <p class="small">
      {#if m.ampliaciones && Math.abs(m.ampliaciones) >= 1}
        El presupuesto {m.ampliaciones > 0 ? 'aumentó' : 'se redujo'}
        <strong>{pesos(Math.abs(m.ampliaciones))}</strong> ({cambio(cambioAnual)}) respecto a lo aprobado.
        <Termino id="ampliaciones">¿Por qué cambia?</Termino>
      {:else}
        Sin cambios respecto a lo aprobado.
      {/if}
    </p>

    {#if hayTendencia}
      <h3>Gasto acumulado por trimestre</h3>
      <LineChart
        series={tendencia}
        formato={pesos}
        formatoEje={pesosCorto}
        etiquetaX={(q) => `${q.replace('T', '')}er trim.`.replace('2er', '2º').replace('4er', '4º')}
        titulo={`Gasto acumulado por trimestre de ${sel.etiqueta}, por año`}
        alto={200}
      />
    {/if}

    {#if capitulo && capitulo.conceptos.length}
      <h3>¿En qué exactamente?</h3>
      <BarList
        barras={capitulo.conceptos
          .filter((c) => (c.montos.devengado ?? 0) > 0 || (c.montos.modificado ?? 0) > 0)
          .sort((a, b) => (b.montos.devengado ?? 0) - (a.montos.devengado ?? 0))
          .map((c, i) => ({ id: String(i), etiqueta: c.nombre, valor: c.montos.devengado, referencia: c.montos.modificado }))}
        formato={pesos}
        titulo={`Conceptos de ${sel.etiqueta}`}
        valorEtiqueta="Gastado"
        referenciaEtiqueta="Modificado"
      />
    {:else if capitulo}
      <p class="small muted">
        <Termino id={CAPITULOS[capitulo.clave]?.glosario ?? 'capitulo'}>¿Qué incluye este tipo de gasto?</Termino>
      </p>
    {:else if dependencia}
      <p class="small muted">
        El municipio no publica en formato abierto el detalle por tipo de gasto de cada dependencia.
      </p>
    {/if}

    {#if dependencia?.notas}
      {#each dependencia.notas as n, i (i)}<p class="small notice">{n}</p>{/each}
    {/if}
    <Fuente ids={[dependencia ? periodo.fuente_dependencias : periodo.fuente]} />
    {#if dependencia}
      <ContratosDependencia municipio={route.municipio} dependencia={dependencia.id} />
    {/if}
  {/if}
  <p class="small muted">{nombreMunicipio} · montos en pesos nominales.</p>
</aside>

<style>
  .panel {
    display: grid;
    gap: 0.5rem;
    align-content: start;
  }
  .head {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    align-items: start;
  }
  .tipo {
    margin: 0;
  }
  h2 {
    margin: 0.1rem 0 0;
    overflow-wrap: anywhere;
  }
  h3 {
    margin-top: 0.75rem;
  }
  .cerrar {
    min-width: 44px;
    justify-content: center;
    font-size: 1.3rem;
    padding: 0.2rem;
  }
  .montos {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.6rem;
    margin: 0.25rem 0;
  }
  .montos div {
    background: var(--surface-2);
    border-radius: var(--radius-sm);
    padding: 0.55rem 0.7rem;
  }
  dt {
    font-size: 0.8rem;
    color: var(--ink-2);
  }
  dd {
    margin: 0.15rem 0 0;
    font-weight: 650;
    font-size: 1.05rem;
    overflow-wrap: anywhere;
  }
</style>
