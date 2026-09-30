<script lang="ts">
  import {
    api,
    MUNICIPIOS,
    NOMBRE,
    NOMBRE_CORTO,
    type Deuda,
    type Egresos,
    type Meta,
    type Movimiento,
    type Municipio,
    type MunicipioId,
  } from '../lib/data';
  import { acumulado, pesos, porcentaje, fecha } from '../lib/format';
  import { route, link, href } from '../lib/router.svelte';
  import { sencillo, CAPITULOS } from '../lib/capitulos';
  import Filtros from '../components/Filtros.svelte';
  import Waffle, { deCada100 } from '../components/Waffle.svelte';
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
  let meta = $state<Meta | null>(null);
  api.meta().then((x) => (meta = x)).catch(() => {});
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
  const cambioAnual = $derived(
    p && mismoAnterior && mismoAnterior.total.devengado
      ? ((p.total.devengado ?? 0) - mismoAnterior.total.devengado) / mismoAnterior.total.devengado
      : null,
  );
  /** Spending per resident in the same period for every municipality that published it, highest first. */
  const porHabitante = $derived.by(() => {
    if (!datos || !p) return [];
    return MUNICIPIOS.flatMap((id) => {
      const per = datos!.todos[id].periodos.find((x) => x.periodo === p!.periodo);
      const pob = poblacion(id);
      return per?.total.devengado != null && pob ? [{ id, valor: per.total.devengado / pob, fuente: per.fuente }] : [];
    }).sort((a, b) => b.valor - a.valor);
  });
  const propioHab = $derived(porHabitante.find((x) => x.id === m));
  const lugarHab = $derived(propioHab ? porHabitante.indexOf(propioHab) + 1 : null);
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
  /** "$6,027.6 millones" → ["$6,027.6", " millones"], so the unit can be set smaller and the number stays on one line. */
  function monto(n: number | null | undefined): [string, string] {
    const t = pesos(n);
    const i = t.indexOf(' millones');
    return i > 0 ? [t.slice(0, i), ' millones'] : [t, ''];
  }
  const totalDev = $derived(p?.total.devengado ?? 0);
  const comparacion = $derived(
    cambioAnual !== null && p
      ? ` y ${porcentaje(Math.abs(cambioAnual))} ${cambioAnual >= 0 ? 'más' : 'menos'} que en el mismo periodo de ${Number(p.periodo.slice(0, 4)) - 1}`
      : '',
  );
  const mesesPasados = $derived(p ? Number(p.periodo.slice(-1)) * 3 : 0);
  const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  /** "de enero a junio de 2026" (the figures are cumulative from January). */
  const deEneroA = $derived(p ? `de enero a ${MESES[mesesPasados - 1]} de ${p.periodo.slice(0, 4)}` : '');
  /** Chart headlines state the finding in actual values (HIG: summarize the main message; avoid subjective terms). */
  const lecturaCap = $derived.by(() => {
    // Same grouping and rounding as the waffle (top five + "Otros"), so the sentence matches the squares.
    const orden = [...partes].filter((x) => x.valor > 0).sort((a, b) => b.valor - a.valor);
    if (orden.length < 2) return null;
    const grupos = orden.length <= 5 ? orden : [...orden.slice(0, 5), { valor: orden.slice(5).reduce((t, x) => t + x.valor, 0) }];
    const c = deCada100(grupos);
    return {
      titular: `Dos rubros se llevan $${c[0]! + c[1]!} de cada $100`,
      detalle: `${orden[0]!.etiqueta} ($${c[0]}) y ${orden[1]!.etiqueta.toLowerCase()} ($${c[1]}).`,
    };
  });
  const lecturaDep = $derived.by(() => {
    const top = barras[0];
    if (!top || top.valor === null || !totalDev) return null;
    return {
      titular: `${top.etiqueta.replace(/^Secretaría de /, '')}: ${porcentaje(top.valor / totalDev)} del gasto`,
      detalle: `${top.etiqueta} ${p?.dependencias ? 'es la dependencia que más gastó' : 'es el rubro más grande'}: ${pesos(top.valor)}.`,
    };
  });
  const movs = $derived(datos?.movs.filter((x) => x.municipio === m).slice(0, 4) ?? []);
</script>

<section aria-labelledby="h-inicio">
  <header class="cabeza">
    <p class="eyebrow">
      {meta?.datos_al ? `Finanzas municipales · datos al ${fecha(meta.datos_al)}` : 'Finanzas municipales'}
    </p>
    <h1 id="h-inicio">¿A dónde va el dinero de {NOMBRE[m]}?</h1>
    <p class="lead muted">Cómo obtiene y gasta su dinero el gobierno municipal, con datos oficiales. Cada cifra enlaza a su documento.</p>
    <Filtros {periodos} />
  </header>
  <Estado {error} cargando={!datos && !error} />

  {#if faltante}
    <p class="notice">
      No hay datos de gasto de {NOMBRE[m]} para {acumulado(faltante.periodo)}: {faltante.motivo} Se muestra el periodo
      más reciente disponible.
    </p>
  {/if}

  {#if datos && p}
    <!-- Two-tone statement: the fact in ink, its context in muted ink (one number in a plain sentence). -->
    <p class="titular">
      <span>
        {NOMBRE_CORTO[m]} <Termino id="devengado">gastó</Termino> <strong class="num">{pesos(p.total.devengado)}</strong>
        {deEneroA}.
      </span>
      <span class="suave">
        Es {porcentaje(ejercido)} de su <Termino id="modificado">presupuesto</Termino> para todo el año
        ({pesos(p.total.modificado)}){comparacion}.
      </span>
    </p>

    <dl class="cifras">
      <div>
        <dt class="eyebrow">Presupuesto ya gastado</dt>
        <dd class="valor num">{porcentaje(ejercido)}</dd>
        <dd class="ctx">Han pasado {mesesPasados} de 12 meses del año</dd>
      </div>
      <div>
        <dt class="eyebrow">Gasto <Termino id="por-habitante">por habitante</Termino></dt>
        <dd class="valor num">{propioHab ? pesos(propioHab.valor) : 'Sin dato'}</dd>
        <dd class="ctx">
          {#if lugarHab && porHabitante.length > 1}
            {lugarHab === 1 ? 'El más alto' : lugarHab === porHabitante.length ? 'El más bajo' : `El ${lugarHab}º`} de los
            {porHabitante.length} municipios
          {:else}
            Población: {poblacion(m)?.toLocaleString('es-MX') ?? '—'} (Censo 2020)
          {/if}
        </dd>
      </div>
      <div>
        <dt class="eyebrow"><Termino id="deuda">Deuda registrada</Termino></dt>
        <dd class="valor num">{monto(saldo?.total)[0]}<span class="unidad">{monto(saldo?.total)[1]}</span></dd>
        <dd class="ctx">{saldo ? `Saldo al ${fecha(saldo.fecha)}` : ''}</dd>
      </div>
    </dl>
    <details class="origen small">
      <summary>¿De dónde salen estas cifras?</summary>
      <ul>
        <li>
          <strong>Gasto y presupuesto:</strong> columnas «Devengado» y «Modificado» del estado de gasto del municipio,
          acumulado de enero al {fecha(p.fecha_corte)}. <Termino id="acumulado">Las cifras son acumuladas</Termino> y en
          pesos nominales.
        </li>
        <li>
          <strong>Por habitante:</strong> gasto del mismo periodo de cada municipio entre su población del Censo 2020 del
          INEGI: {porHabitante.map((h) => `${NOMBRE[h.id]} ${pesos(h.valor)}`).join(' · ')}.
        </li>
        <li>
          <strong>Deuda:</strong> saldo de préstamos inscritos a nombre del municipio en el Registro Público Único de la
          Secretaría de Hacienda.
        </li>
      </ul>
      <Fuente ids={[p.fuente, mismoAnterior?.fuente, ...porHabitante.map((h) => h.fuente), 'inegi-mgem-19', saldo?.fuente]} />
    </details>

    <div class="banda">
      <div class="dos">
        <section aria-labelledby="h-100">
          <p class="eyebrow">De cada $100 que gastó</p>
          <h2 id="h-100">{lecturaCap?.titular ?? 'De cada $100 que gastó'}</h2>
          {#if lecturaCap}<p class="detalle">{lecturaCap.detalle}</p>{/if}
          <p class="muted small">
            Por tipo de gasto (<Termino id="capitulo">capítulo del gasto</Termino>). Toca un rubro para ver el monto.
          </p>
          <Waffle {partes} titulo={`De cada 100 pesos que gastó ${NOMBRE[m]} ${deEneroA}`} />
          <Fuente ids={[p.fuente]} compacto />
        </section>

        <section aria-labelledby="h-quien">
          <p class="eyebrow">{p.dependencias ? '¿Quién gasta más?' : '¿En qué gasta más?'}</p>
          <h2 id="h-quien">{lecturaDep?.titular ?? '¿Quién gasta más?'}</h2>
          {#if lecturaDep}<p class="detalle">{lecturaDep.detalle}</p>{/if}
          <p class="muted small">
            {#if p.dependencias}
              Las 8 <Termino id="dependencia">dependencias</Termino> con más gasto. La barra clara es su presupuesto del
              año.
            {:else}
              {p.motivo_sin_dependencias} La barra clara es el presupuesto del año.
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
        </section>
      </div>
    </div>

    <section class="bloque" aria-labelledby="h-movs">
      <p class="eyebrow">Movimientos recientes</p>
      <h2 id="h-movs">¿Qué cambió recientemente?</h2>
      <ul class="movs">
        {#each movs as mv, i (i)}
          <MovimientoItem movimiento={mv} compacto />
        {/each}
      </ul>
      <p class="small"><a href={href('/movimientos')} use:link>Ver todos los movimientos →</a></p>
    </section>

    <nav class="banda sigue" aria-labelledby="h-sigue">
      <p class="eyebrow">Sigue explorando</p>
      <h2 id="h-sigue">Más formas de ver el dinero de {NOMBRE_CORTO[m]}</h2>
      <ul>
        {#each [
          { ruta: '/mapa', t: 'Mapa del gobierno', d: 'Quién es quién y cuánto maneja cada dependencia.' },
          { ruta: '/flujo', t: 'Flujo del dinero', d: 'De dónde entra el dinero y en qué se va.' },
          { ruta: '/comparar', t: 'Comparar municipios', d: 'Gasto total y por habitante, año por año.' },
          { ruta: '/fuentes', t: 'Fuentes y datos abiertos', d: 'Documentos oficiales, verificaciones y descargas.' },
        ] as e (e.ruta)}
          <li>
            <a href={e.ruta === '/fuentes' ? e.ruta : href(e.ruta)} use:link>
              <span><strong>{e.t}</strong><span class="muted">{e.d}</span></span>
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m6 3 5 5-5 5" /></svg>
            </a>
          </li>
        {/each}
      </ul>
    </nav>

    {#if p.notas.length}
      <aside class="notice small">
        <strong>Notas sobre estos datos:</strong>
        {#each p.notas as n, i (i)}<span> {n}</span>{/each}
      </aside>
    {/if}
  {/if}
</section>

<style>
  .cabeza {
    margin-bottom: 0.5rem;
  }
  .lead {
    font-size: 1.1rem;
    max-width: 58ch;
    margin-bottom: 1.25rem;
  }

  /* The headline statement (Stripe/Nubank-style two tones). */
  .titular {
    font-size: clamp(1.3rem, 2.8vw, 1.75rem);
    line-height: 1.35;
    letter-spacing: -0.015em;
    font-weight: 600;
    max-width: 34ch;
    margin: 1.25rem 0 1.75rem;
  }
  .titular strong {
    font-weight: 750;
  }
  @media (min-width: 900px) {
    .titular {
      max-width: 44ch;
    }
  }

  /* Key figures: open row separated by thin rules. */
  .cifras {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 0;
    border-top: 1px solid var(--grid);
    border-bottom: 1px solid var(--grid);
  }
  .cifras > div {
    padding: 1.15rem 1.25rem 1.15rem 0;
    min-width: 0;
  }
  .cifras > div + div {
    padding-left: 1.25rem;
    border-left: 1px solid var(--grid);
  }
  dd {
    margin: 0;
  }
  .valor {
    font-size: clamp(1.6rem, 3vw, 2.1rem);
    font-weight: 750;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin: 0.1rem 0 0.2rem;
  }
  .unidad {
    font-size: 0.5em;
    font-weight: 600;
    color: var(--ink-2);
    letter-spacing: 0;
  }
  .ctx {
    font-size: 0.875rem;
    color: var(--ink-2);
  }
  .origen {
    margin: 0.5rem 0 2.5rem;
  }
  .origen summary {
    cursor: pointer;
    color: var(--link);
    min-height: 36px;
    display: inline-flex;
    align-items: center;
  }
  .origen ul {
    margin: 0.25rem 0 0.5rem;
    padding-left: 1.1rem;
    color: var(--ink-2);
    max-width: 80ch;
  }

  /* Chart sections: question label, finding as headline, one-line detail, chart, quiet source. */
  .dos {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 2.5rem 3.5rem;
  }
  .dos > section {
    min-width: 0;
  }
  .detalle {
    font-size: 1.05rem;
    color: var(--ink-2);
    margin: 0 0 0.35rem;
  }

  .bloque {
    padding-block: clamp(2rem, 5vw, 3.25rem);
  }
  .movs {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 440px), 1fr));
    column-gap: 3rem;
  }

  /* GOV.UK-style link list: title, one-line description, chevron. */
  .sigue ul {
    list-style: none;
    margin: 0.5rem 0 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 440px), 1fr));
    column-gap: 3rem;
  }
  .sigue a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    min-height: 64px;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--grid);
    color: var(--ink);
    text-decoration: none;
  }
  .sigue a > span {
    display: grid;
    gap: 0.1rem;
  }
  .sigue strong {
    color: var(--link);
    font-weight: 650;
  }
  .sigue a:hover strong {
    text-decoration: underline;
  }
  .sigue svg {
    flex: none;
    width: 1.1rem;
    height: 1.1rem;
    fill: none;
    stroke: var(--ink-3);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .notice {
    margin-top: 2rem;
  }

  @media (max-width: 900px) {
    .dos {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  @media (max-width: 640px) {
    .cifras {
      grid-template-columns: minmax(0, 1fr);
    }
    .cifras > div,
    .cifras > div + div {
      padding: 0.9rem 0;
      border-left: 0;
    }
    .cifras > div + div {
      border-top: 1px solid var(--grid);
    }
  }
</style>
