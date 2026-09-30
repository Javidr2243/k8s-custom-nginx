<script lang="ts">
  import {
    api,
    MUNICIPIOS,
    NOMBRE,
    NOMBRE_CORTO,
    type Deuda,
    type Egresos,
    type Movimiento,
    type Municipio,
    type MunicipioId,
  } from '../lib/data';
  import { acumulado, cambio, pesos, porcentaje, fecha } from '../lib/format';
  import { route, link, href } from '../lib/router.svelte';
  import { sencillo, CAPITULOS } from '../lib/capitulos';
  import { ancho } from '../lib/ancho';
  import Filtros from '../components/Filtros.svelte';
  import StatTile from '../components/StatTile.svelte';
  import Waffle from '../components/Waffle.svelte';
  import BarList from '../components/BarList.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';
  import MovimientoItem from '../components/MovimientoItem.svelte';

  let datos = $state<{
    egr: Egresos;
    todos: Record<MunicipioId, Egresos>;
    deuda: Deuda;
    muns: Municipio[];
    movs: Movimiento[];
  } | null>(null);
  let error = $state<string | null>(null);

  $effect(() => {
    const m = route.municipio;
    error = null;
    Promise.all([Promise.all(MUNICIPIOS.map((x) => api.egresos(x))), api.deuda(m), api.municipios(), api.movimientos()])
      .then(([egrs, deuda, muns, movs]) => {
        const todos = Object.fromEntries(MUNICIPIOS.map((x, i) => [x, egrs[i]!])) as Record<MunicipioId, Egresos>;
        if (route.municipio === m) datos = { egr: todos[m], todos, deuda, muns, movs };
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
  const poblacion = (id: MunicipioId) => datos?.muns.find((x) => x.id === id)?.poblacion ?? null;
  const saldo = $derived(datos?.deuda.saldos.at(-1));
  const ejercido = $derived(
    p && p.total.devengado !== null && p.total.modificado ? p.total.devengado / p.total.modificado : null,
  );
  /** Share of the year elapsed at the period's cut-off (T2 → 6 of 12 months). */
  const avanceAnio = $derived(p ? Number(p.periodo.slice(-1)) / 4 : null);
  const cambioAnual = $derived(
    p && mismoAnterior && mismoAnterior.total.devengado
      ? ((p.total.devengado ?? 0) - mismoAnterior.total.devengado) / mismoAnterior.total.devengado
      : null,
  );
  const cambioPresupuesto = $derived(
    p && p.total.aprobado ? ((p.total.modificado ?? 0) - p.total.aprobado) / p.total.aprobado : null,
  );
  /** Spending per resident for the same period in all three municipalities (null where it isn't published). */
  const porHabitante = $derived.by(() => {
    if (!datos || !p) return [];
    const filas = MUNICIPIOS.map((id) => {
      const per = datos!.todos[id].periodos.find((x) => x.periodo === p!.periodo);
      const pob = poblacion(id);
      return { id, valor: per?.total.devengado != null && pob ? per.total.devengado / pob : null, fuente: per?.fuente };
    });
    const max = Math.max(...filas.map((f) => f.valor ?? 0));
    return filas.map((f) => ({ ...f, frac: max > 0 && f.valor !== null ? f.valor / max : 0 }));
  });
  const propioHab = $derived(porHabitante.find((x) => x.id === m)?.valor ?? null);
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

  const EXPLORA = [
    { ruta: '/mapa', titulo: 'Mapa del gobierno', texto: 'Quién es quién y cuánto maneja cada dependencia.', icono: 'mapa' },
    { ruta: '/flujo', titulo: 'Flujo del dinero', texto: 'De dónde entra el dinero y en qué se va.', icono: 'flujo' },
    { ruta: '/comparar', titulo: 'Comparar municipios', texto: 'Gasto total y por habitante, año por año.', icono: 'comparar' },
    { ruta: '/deuda', titulo: 'Deuda', texto: 'Cuánto se debe, a quién y a qué tasa.', icono: 'deuda' },
    { ruta: '/contratos', titulo: 'Contratos', texto: 'Proveedores, montos y cómo se adjudicaron.', icono: 'contratos' },
    { ruta: '/fuentes', titulo: 'Fuentes', texto: 'Documentos oficiales y verificaciones.', icono: 'fuentes' },
  ] as const;
</script>

<section aria-labelledby="h-inicio">
  <h1 id="h-inicio">¿A dónde va el dinero de {NOMBRE[m]}?</h1>
  <p class="lead muted">Cómo obtiene y gasta su dinero el gobierno municipal, explicado con datos oficiales.</p>

  <Filtros {periodos} />
  <Estado {error} cargando={!datos && !error} />

  {#if faltante}
    <p class="notice">
      No hay datos de gasto de {NOMBRE[m]} para {acumulado(faltante.periodo)}: {faltante.motivo} Se muestra el periodo
      más reciente disponible.
    </p>
  {/if}

  {#if datos && p}
    <article class="card hero" aria-labelledby="h-gasto">
      <div class="hero-cifra">
        <p class="eyebrow">
          <span class="chip-dot dot-{m}" aria-hidden="true"></span>{NOMBRE_CORTO[m]} · {acumulado(p.periodo)}
        </p>
        <h2 id="h-gasto" class="sr-only">Gasto del periodo</h2>
        <p class="big num">{pesos(p.total.devengado)}</p>
        <p class="big-lbl">
          <Termino id="devengado">gastados</Termino> de un <Termino id="modificado">presupuesto</Termino> anual de
          <strong class="num">{pesos(p.total.modificado)}</strong>
        </p>

        {#if ejercido !== null}
          <div class="avance">
            <div
              class="barra"
              role="img"
              aria-label={`Se ha gastado ${porcentaje(ejercido)} del presupuesto del año; han pasado ${porcentaje(avanceAnio)} del año.`}
            >
              <span class="fill" use:ancho={ejercido}></span>
              {#if avanceAnio !== null && avanceAnio < 1}<span class="marca" use:ancho={avanceAnio}></span>{/if}
            </div>
            <div class="avance-txt small">
              <span><strong class="num">{porcentaje(ejercido)}</strong> del presupuesto ya se gastó</span>
              {#if avanceAnio !== null && avanceAnio < 1}
                <span class="muted"><span class="guia" aria-hidden="true"></span>han pasado {Number(p.periodo.slice(-1)) * 3} de 12 meses</span>
              {/if}
            </div>
          </div>
        {/if}

        <ul class="chips">
          {#if cambioAnual !== null}
            <li class="chip">
              <strong class="num">{cambio(cambioAnual)}</strong> frente a {acumulado(mismoAnterior!.periodo)}
            </li>
          {/if}
          {#if cambioPresupuesto !== null}
            <li class="chip">
              Presupuesto <strong class="num">{cambio(cambioPresupuesto)}</strong> desde que se aprobó
            </li>
          {/if}
          <li class="chip"><Termino id="acumulado">Cifras acumuladas</Termino> en pesos nominales</li>
        </ul>

        <details class="origen small">
          <summary>¿De dónde salen estas cifras?</summary>
          <p>
            «Gastados» es el total de la columna «Devengado» del estado de gasto del municipio, acumulado de enero al
            {fecha(p.fecha_corte)}. El presupuesto anual es la columna «Modificado» (aprobado más ampliaciones y
            reducciones). El porcentaje es Devengado ÷ Modificado. La comparación con el año anterior usa el mismo
            periodo del documento del año pasado.
          </p>
          <Fuente ids={[p.fuente, mismoAnterior?.fuente]} />
        </details>
      </div>

      <div class="hero-waffle">
        <h2>De cada $100 que gastó</h2>
        <p class="muted small">
          Por tipo de gasto (<Termino id="capitulo">capítulo del gasto</Termino>). Pasa el cursor o toca un rubro para
          ver el monto.
        </p>
        <Waffle {partes} titulo={`De cada 100 pesos que gastó ${NOMBRE[m]} en ${acumulado(p.periodo)}`} />
        <Fuente ids={[p.fuente]} compacto />
      </div>
    </article>

    <div class="grid tiles">
      <StatTile
        origen={{
          calculo: 'Columnas «Aprobado» (presupuesto autorizado a inicio de año) y «Modificado» (después de ampliaciones y reducciones) del estado de gasto. El cambio es (Modificado − Aprobado) ÷ Aprobado.',
          fuentes: [p.fuente],
        }}
        value={pesos(p.total.aprobado)}
        sub={`Hoy: ${pesos(p.total.modificado)} (${cambio(cambioPresupuesto)} en cambios)`}
      >
        {#snippet label()}<Termino id="aprobado">Presupuesto aprobado</Termino> para {p.periodo.slice(0, 4)}{/snippet}
      </StatTile>

      <StatTile
        value={propioHab !== null ? pesos(propioHab) : 'Sin dato'}
        sub={`Por cada uno de sus ${poblacion(m)?.toLocaleString('es-MX') ?? '—'} habitantes (Censo 2020)`}
        origen={{
          calculo: `Gasto devengado de ${acumulado(p.periodo)} de cada municipio dividido entre su población según el Censo de Población y Vivienda 2020 del INEGI. Se compara solo el mismo periodo; si un municipio no lo publicó, aparece «sin dato».`,
          fuentes: [...porHabitante.map((x) => x.fuente), 'inegi-mgem-19'],
        }}
      >
        {#snippet label()}Gasto <Termino id="por-habitante">por habitante</Termino>{/snippet}
        <ul class="vs" aria-label={`Gasto por habitante en ${acumulado(p.periodo)}, comparado con los otros municipios`}>
          {#each porHabitante as f (f.id)}
            <li class:actual={f.id === m}>
              <span class="vs-nom small">{NOMBRE_CORTO[f.id]}</span>
              <span class="vs-barra" aria-hidden="true"><span class="bg-{f.id}" use:ancho={f.frac}></span></span>
              <span class="vs-val small num">{f.valor !== null ? pesos(f.valor) : 'sin dato'}</span>
            </li>
          {/each}
        </ul>
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
        {#if saldo && p.total.modificado}
          <p class="small muted tile-nota">
            Equivale a <strong class="num">{porcentaje(saldo.total / p.total.modificado)}</strong> del presupuesto anual.
          </p>
        {/if}
      </StatTile>
    </div>

    <div class="grid grid-2 mt">
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
        <Fuente ids={[p.fuente_dependencias ?? p.fuente]} compacto />
      </article>

      <article class="card">
        <h2>Movimientos recientes</h2>
        <p class="muted small">Nuevos reportes, cambios al presupuesto, deuda y contratos grandes.</p>
        <ul class="movs">
          {#each movs as mv, i (i)}
            <MovimientoItem movimiento={mv} compacto />
          {/each}
        </ul>
        <p class="small"><a href={href('/movimientos')} use:link>Ver todos los movimientos →</a></p>
      </article>
    </div>

    <nav class="explora mt" aria-labelledby="h-explora">
      <h2 id="h-explora">Explora más</h2>
      <ul>
        {#each EXPLORA as e (e.ruta)}
          <li>
            <a href={href(e.ruta)} use:link class="ex">
              <svg viewBox="0 0 24 24" aria-hidden="true" class="ico">
                {#if e.icono === 'mapa'}
                  <circle cx="12" cy="12" r="2.5" /><circle cx="4.5" cy="6" r="2" /><circle cx="19.5" cy="6" r="2" /><circle cx="4.5" cy="18" r="2" /><circle cx="19.5" cy="18" r="2" /><path d="M10 10.5 6.2 7.2M14 10.5l3.8-3.3M10 13.5l-3.8 3.3M14 13.5l3.8 3.3" />
                {:else if e.icono === 'flujo'}
                  <path d="M3 6h5c4 0 4 12 8 12h5M3 18h5c4 0 4-12 8-12h5" />
                {:else if e.icono === 'comparar'}
                  <path d="M5 20V11M12 20V4M19 20v-6" />
                {:else if e.icono === 'deuda'}
                  <rect x="3" y="6" width="18" height="12" rx="2" /><path d="M3 10h18M7 15h4" />
                {:else if e.icono === 'contratos'}
                  <path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4M10 12h5M10 16h5" />
                {:else}
                  <path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6z" /><path d="m9 12 2 2 4-4" />
                {/if}
              </svg>
              <span>
                <strong>{e.titulo}</strong>
                <span class="small muted">{e.texto}</span>
              </span>
            </a>
          </li>
        {/each}
      </ul>
    </nav>

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
  .mt {
    margin-top: 1rem;
  }

  /* Hero: the headline figure (like CivLab's big panel numbers) next to the "de cada $100" waffle. */
  .hero {
    display: grid;
    grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
    gap: 1.5rem 2.25rem;
    padding: clamp(1.1rem, 3vw, 1.75rem);
    background:
      linear-gradient(135deg, color-mix(in srgb, var(--accent) 7%, transparent), transparent 55%),
      var(--surface);
  }
  .hero-cifra {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
  }
  .hero-waffle {
    min-width: 0;
    padding-left: 2.25rem;
    border-left: 1px solid var(--grid);
  }
  .eyebrow {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.78rem;
    font-weight: 650;
    color: var(--ink-2);
    margin: 0 0 0.35rem;
  }
  .big {
    font-size: clamp(2.3rem, 6.2vw, 3.6rem);
    font-weight: 750;
    letter-spacing: -0.02em;
    line-height: 1.02;
    margin: 0 0 0.35rem;
    overflow-wrap: break-word;
  }
  .big-lbl {
    font-size: 1.08rem;
    color: var(--ink-2);
    margin: 0 0 1.1rem;
  }
  .big-lbl strong {
    color: var(--ink);
  }
  .avance {
    margin-bottom: 1rem;
  }
  .barra {
    position: relative;
    height: 14px;
    border-radius: 7px;
    background: var(--seq-200);
  }
  .barra .fill {
    display: block;
    height: 100%;
    border-radius: 7px;
    background: var(--seq-450);
  }
  .barra .marca {
    position: absolute;
    inset: -5px auto -5px 0;
    border-right: 2px dashed var(--ink-2);
    pointer-events: none;
  }
  .avance-txt {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 0.25rem 1rem;
    margin-top: 0.45rem;
  }
  .guia {
    display: inline-block;
    height: 0.9em;
    margin-right: 0.35rem;
    vertical-align: -0.1em;
    border-right: 2px dashed var(--ink-2);
  }
  .chips {
    list-style: none;
    padding: 0;
    margin: 0 0 0.75rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .chip {
    font-size: 0.85rem;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--ink-2);
  }
  .chip strong {
    color: var(--ink);
  }
  .origen summary {
    cursor: pointer;
    color: var(--link);
    min-height: 32px;
    display: inline-flex;
    align-items: center;
  }
  .origen p {
    color: var(--ink-2);
    margin: 0.3rem 0 0;
  }

  .tiles {
    margin-top: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 270px), 1fr));
  }
  .tile-nota {
    margin: 0.4rem 0 0;
  }
  .vs {
    list-style: none;
    padding: 0;
    margin: 0.6rem 0 0;
    display: grid;
    gap: 0.3rem;
  }
  .vs li {
    display: grid;
    grid-template-columns: 6.8rem minmax(0, 1fr) auto;
    gap: 0.5rem;
    align-items: center;
    color: var(--ink-2);
  }
  .vs li.actual {
    color: var(--ink);
    font-weight: 650;
  }
  .vs-barra {
    height: 8px;
    border-radius: 4px;
    background: var(--surface-2);
    overflow: hidden;
  }
  .vs-barra span {
    display: block;
    height: 100%;
    border-radius: 4px;
  }
  .vs li:not(.actual) .vs-barra span {
    opacity: 0.55;
  }

  .movs {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .explora ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
  }
  .ex {
    display: flex;
    gap: 0.8rem;
    align-items: flex-start;
    height: 100%;
    padding: 0.9rem 1rem;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--ink);
    text-decoration: none;
    transition:
      border-color 0.15s,
      transform 0.15s;
  }
  .ex:hover {
    border-color: var(--accent);
    transform: translateY(-1px);
  }
  .ex > span {
    display: grid;
    gap: 0.1rem;
  }
  .ico {
    flex: none;
    width: 38px;
    height: 38px;
    padding: 7px;
    border-radius: 10px;
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    stroke: var(--accent);
    fill: none;
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  @media (max-width: 860px) {
    .hero {
      grid-template-columns: minmax(0, 1fr);
    }
    .hero-waffle {
      padding-left: 0;
      border-left: 0;
      padding-top: 1.25rem;
      border-top: 1px solid var(--grid);
    }
  }
</style>
