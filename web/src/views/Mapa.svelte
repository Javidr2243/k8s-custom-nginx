<script lang="ts">
  import { api, NOMBRE, type Egresos, type Ingresos } from '../lib/data';
  import { acumulado, pesos, porcentaje } from '../lib/format';
  import { route, setQuery } from '../lib/router.svelte';
  import { CAPITULOS } from '../lib/capitulos';
  import Filtros from '../components/Filtros.svelte';
  import Estado from '../components/Estado.svelte';
  import GovGraph, { type Arista, type Nodo } from '../components/GovGraph.svelte';
  import PanelEntidad, { type Seleccion } from '../components/PanelEntidad.svelte';
  import BarList from '../components/BarList.svelte';
  import Termino from '../components/Termino.svelte';
  import Fuente from '../components/Fuente.svelte';

  let datos = $state<{ egr: Egresos; ing: Ingresos } | null>(null);
  let error = $state<string | null>(null);
  let medida = $state<'aprobado' | 'devengado'>('devengado');

  $effect(() => {
    const m = route.municipio;
    error = null;
    Promise.all([api.egresos(m), api.ingresos(m)])
      .then(([egr, ing]) => {
        if (route.municipio === m) datos = { egr, ing };
      })
      .catch((e: Error) => (error = e.message));
  });

  const m = $derived(route.municipio);
  const periodos = $derived(datos?.egr.periodos.map((p) => p.periodo) ?? []);
  const p = $derived(
    datos ? (datos.egr.periodos.find((x) => x.periodo === route.periodo) ?? datos.egr.periodos.at(-1)) : undefined,
  );
  const selId = $derived(route.params.get('n'));

  const GLOSARIO_RUBRO: Record<string, string> = {
    impuestos: 'impuestos',
    derechos: 'derechos',
    productos: 'productos',
    aprovechamientos: 'aprovechamientos',
    participaciones: 'participaciones',
    aportaciones: 'aportaciones',
    financiamiento: 'financiamiento',
  };
  const NOMBRE_RUBRO: Record<string, string> = {
    impuestos: 'Impuestos (predial y otros)',
    derechos: 'Derechos',
    productos: 'Productos',
    aprovechamientos: 'Aprovechamientos (multas…)',
    participaciones: 'Participaciones federales',
    aportaciones: 'Aportaciones federales y estatales',
    financiamiento: 'Financiamiento (préstamos)',
    otros: 'Otros ingresos',
    'contribuciones-de-mejoras': 'Contribuciones de mejoras',
    'disponibilidad-inicial': 'Dinero en caja al iniciar el año',
    'por-cuenta-de-terceros': 'Por cuenta de terceros',
  };

  // Income side: quarterly (same period) for Monterrey; for the others, the INEGI annual total of the latest
  // year available (labelled as such, never mixed with quarterly figures).
  const ingresos = $derived.by(() => {
    if (!datos || !p) return { anual: false, etiqueta: '', fuente: '', items: [] as Seleccion[] };
    const tri = datos.ing.trimestral.find((t) => t.periodo === p.periodo);
    if (tri) {
      return {
        anual: false,
        etiqueta: `Ingresos ${acumulado(p.periodo)}`,
        fuente: tri.fuente,
        items: tri.rubros.map(
          (r): Seleccion => ({
            id: `ing-${r.id}`,
            tipo: 'ingreso',
            etiqueta: r.nombre.startsWith('Participaciones, Aportaciones')
              ? 'Participaciones y aportaciones (federales)'
              : r.nombre,
            ingreso: { estimado: r.montos.estimado, recaudado: r.montos.recaudado, periodo: p.periodo, fuente: tri.fuente },
            glosario: r.nombre.startsWith('Participaciones') ? 'participaciones' : GLOSARIO_RUBRO[r.id],
          }),
        ),
      };
    }
    const anio = Number(p.periodo.slice(0, 4));
    const a = [...datos.ing.anual].reverse().find((x) => x.anio <= anio);
    if (!a) return { anual: true, etiqueta: '', fuente: '', items: [] };
    return {
      anual: true,
      etiqueta: `Ingresos del año ${a.anio} (INEGI${a.estatus.includes('Preliminar') ? ', cifras preliminares' : ''})`,
      fuente: datos.ing.fuente_anual,
      items: Object.entries(a.ingresos_rubro)
        .filter(([k, v]) => v > 0 && k !== 'disponibilidad-inicial' && k !== 'por-cuenta-de-terceros')
        .map(
          ([k, v]): Seleccion => ({
            id: `ing-${k}`,
            tipo: 'ingreso',
            etiqueta: NOMBRE_RUBRO[k] ?? k,
            ingreso: { estimado: null, recaudado: v, periodo: String(a.anio), fuente: datos!.ing.fuente_anual, anual: true },
            glosario: GLOSARIO_RUBRO[k],
          }),
        ),
    };
  });

  const unidades = $derived.by((): Seleccion[] => {
    if (!p) return [];
    if (p.dependencias)
      return p.dependencias.map((d) => ({ id: d.id, tipo: 'gasto', etiqueta: d.nombre, montos: d.montos }));
    return p.capitulos.map((c) => ({
      id: `cap-${c.clave}`,
      tipo: 'gasto',
      etiqueta: CAPITULOS[c.clave]?.sencillo ?? c.nombre,
      montos: c.montos,
    }));
  });

  const grafo = $derived.by(() => {
    if (!p) return { nodos: [] as Nodo[], aristas: [] as Arista[] };
    const nodos: Nodo[] = [
      { id: 'gobierno', etiqueta: `Gobierno de ${NOMBRE[m]}`, tipo: 'centro', valor: p.total[medida], detalle: medida },
      { id: 'cabildo', etiqueta: 'Ayuntamiento (cabildo)', tipo: 'organo', valor: null, detalle: 'aprueba el presupuesto' },
    ];
    const aristas: Arista[] = [{ de: 'cabildo', a: 'gobierno', tipo: 'aprueba', valor: null }];
    for (const i of ingresos.items) {
      const v = medida === 'aprobado' && !i.ingreso?.anual ? i.ingreso?.estimado : i.ingreso?.recaudado;
      if (!v || v <= 0) continue;
      nodos.push({ id: i.id, etiqueta: i.etiqueta, tipo: 'ingreso', valor: v, detalle: ingresos.anual ? `recibido en ${i.ingreso?.periodo}` : medida === 'aprobado' ? 'estimado' : 'recaudado' });
      aristas.push({ de: i.id, a: 'gobierno', tipo: 'dinero', valor: v });
    }
    const orden = [...unidades].sort((a, b) => (b.montos?.[medida] ?? 0) - (a.montos?.[medida] ?? 0));
    for (const u of orden) {
      const v = u.montos?.[medida] ?? null;
      if (!v || v <= 0) continue;
      nodos.push({ id: u.id, etiqueta: u.etiqueta, tipo: 'gasto', valor: v, detalle: medida === 'aprobado' ? 'aprobado' : 'gastado (devengado)' });
      aristas.push({ de: 'gobierno', a: u.id, tipo: 'dinero', valor: v });
    }
    return { nodos, aristas };
  });

  const seleccion = $derived.by((): Seleccion | null => {
    if (!selId || !p) return null;
    if (selId === 'gobierno') return { id: 'gobierno', tipo: 'centro', etiqueta: `Gobierno de ${NOMBRE[m]}`, montos: p.total };
    if (selId === 'cabildo') return { id: 'cabildo', tipo: 'organo', etiqueta: 'Ayuntamiento (cabildo)' };
    return unidades.find((u) => u.id === selId) ?? ingresos.items.find((i) => i.id === selId) ?? null;
  });

  // On phones the list is the primary view; the map scrolls sideways.
  const angosto = typeof window !== 'undefined' && window.matchMedia('(max-width: 640px)').matches;

  function elegir(id: string) {
    setQuery({ n: selId === id ? null : id });
  }
  const mayor = $derived(
    [...unidades].filter((u) => u.montos?.[medida] != null).sort((a, b) => (b.montos?.[medida] ?? 0) - (a.montos?.[medida] ?? 0))[0],
  );
  const totalMedida = $derived(p ? p.total[medida] : null);
</script>

<section aria-labelledby="h-mapa">
  <p class="eyebrow">Quién maneja el dinero</p>
  <h1 id="h-mapa">Mapa del gobierno de {NOMBRE[m]}</h1>
  <p class="muted lead">
    De dónde viene el dinero, quién lo gasta y en qué. El tamaño de cada círculo es el monto. Toca un círculo para ver
    su detalle.
  </p>
  <Filtros {periodos} />
  <div class="seg modo" role="radiogroup" aria-label="Tamaño de los círculos">
    <button type="button" class="btn" role="radio" aria-checked={medida === 'devengado'} onclick={() => (medida = 'devengado')}>
      Lo que se gastó
    </button>
    <button type="button" class="btn" role="radio" aria-checked={medida === 'aprobado'} onclick={() => (medida = 'aprobado')}>
      Lo que se aprobó
    </button>
    <span class="small muted">
      <Termino id="devengado">¿Gastado o aprobado?</Termino>
    </span>
  </div>
  <Estado {error} cargando={!datos && !error} />

  {#if datos && p}
    <p class="titular">
      <span>
        {unidades.length} {p.dependencias ? 'dependencias' : 'tipos de gasto'}
        {medida === 'aprobado' ? 'tenían un presupuesto aprobado de' : 'gastaron'}
        <strong class="num">{pesos(totalMedida)}</strong> {medida === 'aprobado' ? `para ${p.periodo.slice(0, 4)}` : `de ${acumulado(p.periodo)}`}.
      </span>
      {#if mayor && totalMedida}
        <span class="suave">
          {p.dependencias ? 'La que más' : 'El más grande'}: {mayor.etiqueta}, {pesos(mayor.montos?.[medida])}
          ({porcentaje((mayor.montos?.[medida] ?? 0) / totalMedida)} del total).
        </span>
      {/if}
    </p>
    {#if !p.dependencias}
      <p class="notice small">{p.motivo_sin_dependencias} Por eso el mapa muestra en qué se gasta (tipo de gasto).</p>
    {/if}
    <div class="banda">
    <div class="layout" class:con-panel={!!seleccion}>
      <div class="grafo">
        <p class="small muted cap">
          {ingresos.etiqueta ? `Izquierda: ${ingresos.etiqueta}. ` : ''}Derecha: gasto {medida === 'aprobado' ? 'aprobado' : 'devengado'},
          {acumulado(p.periodo)}.
        </p>
        <GovGraph
          nodos={grafo.nodos}
          aristas={grafo.aristas}
          formato={pesos}
          titulo={`Mapa del dinero del gobierno de ${NOMBRE[m]}, ${acumulado(p.periodo)}`}
          seleccionado={selId}
          onelegir={elegir}
        />
        <details class="lista" open={angosto}>
          <summary>Ver el mapa como lista</summary>
          <h2 class="h3">Quién gasta / en qué</h2>
          <BarList
            barras={unidades
              .map((u) => ({ id: u.id, etiqueta: u.etiqueta, valor: u.montos?.[medida] ?? null }))
              .sort((a, b) => (b.valor ?? 0) - (a.valor ?? 0))}
            formato={pesos}
            titulo="Gasto por unidad"
            valorEtiqueta={medida === 'aprobado' ? 'Aprobado' : 'Gastado'}
            seleccionado={selId}
            onelegir={elegir}
          />
          <h2 class="h3">De dónde viene</h2>
          <BarList
            barras={ingresos.items.map((i) => ({ id: i.id, etiqueta: i.etiqueta, valor: i.ingreso?.recaudado ?? null, color: 'cat-4' }))}
            formato={pesos}
            titulo="Ingresos por fuente"
            valorEtiqueta="Recaudado"
            seleccionado={selId}
            onelegir={elegir}
          />
        </details>
        <Fuente ids={[p.fuente, p.fuente_dependencias, ingresos.fuente]} />
      </div>
      {#if seleccion}
        <PanelEntidad
          sel={seleccion}
          egresos={datos.egr}
          periodo={p}
          nombreMunicipio={NOMBRE[m]}
          onclose={() => setQuery({ n: null })}
        />
      {/if}
    </div>
    </div>
  {/if}
</section>

<style>
  .lead {
    max-width: 70ch;
  }
  .modo {
    align-items: center;
    margin-bottom: 1rem;
  }
  .layout {
    display: grid;
    gap: 1rem;
  }
  .layout > :global(*) {
    min-width: 0;
  }
  @media (min-width: 1200px) {
    .layout.con-panel {
      grid-template-columns: minmax(0, 1fr) 380px;
    }
  }
  .banda {
    padding-block: 1.5rem 2rem;
  }
  .cap {
    margin: 0 0 0.5rem;
  }
  .lista {
    margin-top: 0.75rem;
  }
  .lista summary {
    cursor: pointer;
    color: var(--link);
    min-height: 44px;
    display: flex;
    align-items: center;
  }
  .h3 {
    font-size: 1.05rem;
    margin-top: 1rem;
  }

</style>
