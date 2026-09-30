<script lang="ts">
  import {
    api,
    MUNICIPIOS,
    NOMBRE,
    type Deuda,
    type Egresos,
    type Movimiento,
    type Municipio,
    type MunicipioId,
  } from '../lib/data';
  import { acumulado, cambio, pesos, porcentaje, fecha } from '../lib/format';
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
  /** One-sentence takeaways that read each chart for the user (computed from the same figures). */
  const lecturaCap = $derived.by(() => {
    // Same grouping and rounding as the waffle (top five + "Otros"), so the sentence matches the squares.
    const orden = [...partes].filter((x) => x.valor > 0).sort((a, b) => b.valor - a.valor);
    if (orden.length < 2) return '';
    const grupos = orden.length <= 5 ? orden : [...orden.slice(0, 5), { valor: orden.slice(5).reduce((t, x) => t + x.valor, 0) }];
    const c = deCada100(grupos);
    return `Dos rubros se llevan $${c[0]! + c[1]!} de cada $100: ${orden[0]!.etiqueta.toLowerCase()} y ${orden[1]!.etiqueta.toLowerCase()}.`;
  });
  const lecturaDep = $derived.by(() => {
    const top = barras[0];
    if (!top || top.valor === null || !totalDev) return '';
    return `${top.etiqueta} es ${p?.dependencias ? 'la que más gasta' : 'el rubro más grande'}: ${pesos(top.valor)}, ${porcentaje(top.valor / totalDev)} del total.`;
  });
  const movs = $derived(datos?.movs.filter((x) => x.municipio === m).slice(0, 4) ?? []);
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
    <p class="resumen">
      De {acumulado(p.periodo)}, el gobierno de {NOMBRE[m]}
      <Termino id="devengado">gastó</Termino>
      <strong>{pesos(p.total.devengado)}</strong>
      de un <Termino id="modificado">presupuesto</Termino> de <strong>{pesos(p.total.modificado)}</strong> para todo el
      año{#if cambioAnual !== null}, {cambio(cambioAnual)} frente al mismo periodo del año anterior{/if}.
    </p>

    <!-- Key figures: an open row (no boxes), three at most, one line of context each; one shared "where from" below. -->
    <dl class="cifras">
      <div>
        <dt>Ya se gastó del <Termino id="modificado">presupuesto del año</Termino></dt>
        <dd class="valor num">{porcentaje(ejercido)}</dd>
        <dd class="ctx">{pesos(p.total.devengado)} de {pesos(p.total.modificado)}; han pasado {Number(p.periodo.slice(-1)) * 3} de 12 meses</dd>
      </div>
      <div>
        <dt>Gasto <Termino id="por-habitante">por habitante</Termino></dt>
        <dd class="valor num">{propioHab ? pesos(propioHab.valor) : 'Sin dato'}</dd>
        <dd class="ctx">
          {#if lugarHab && porHabitante.length > 1}
            {lugarHab === 1 ? 'El más alto' : lugarHab === porHabitante.length ? 'El más bajo' : `El ${lugarHab}º`} de los
            {porHabitante.length} municipios en el mismo periodo
          {:else}
            Población: {poblacion(m)?.toLocaleString('es-MX') ?? '—'} (Censo 2020)
          {/if}
        </dd>
      </div>
      <div>
        <dt><Termino id="deuda">Deuda registrada</Termino></dt>
        <dd class="valor num">{monto(saldo?.total)[0]}<span class="unidad">{monto(saldo?.total)[1]}</span></dd>
        <dd class="ctx">{saldo ? `Saldo al ${fecha(saldo.fecha)}` : ''}</dd>
      </div>
    </dl>
    <details class="origen small">
      <summary>¿De dónde salen estas cifras?</summary>
      <ul>
        <li>
          <strong>Gastado y presupuesto:</strong> columnas «Devengado», «Aprobado» y «Modificado» del estado de gasto del
          municipio, acumulado de enero al {fecha(p.fecha_corte)}. <Termino id="acumulado">Las cifras son acumuladas</Termino>
          y en pesos nominales.
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

    <div class="dos">
      <section aria-labelledby="h-100">
        <h2 id="h-100">De cada $100 que gastó</h2>
        <p class="lectura">{lecturaCap}</p>
        <p class="muted small">
          Por tipo de gasto (<Termino id="capitulo">capítulo del gasto</Termino>). Toca un rubro para ver el monto.
        </p>
        <Waffle {partes} titulo={`De cada 100 pesos que gastó ${NOMBRE[m]} en ${acumulado(p.periodo)}`} />
        <Fuente ids={[p.fuente]} compacto />
      </section>

      <section aria-labelledby="h-quien">
        <h2 id="h-quien">{p.dependencias ? '¿Quién gasta más?' : '¿En qué gasta más?'}</h2>
        <p class="lectura">{lecturaDep}</p>
        <p class="muted small">
          {#if p.dependencias}
            Las 8 <Termino id="dependencia">dependencias</Termino> con más gasto. La barra clara es su presupuesto del año.
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

    <section class="bloque" aria-labelledby="h-movs">
      <h2 id="h-movs">¿Qué cambió recientemente?</h2>
      <ul class="movs">
        {#each movs as mv, i (i)}
          <MovimientoItem movimiento={mv} compacto />
        {/each}
      </ul>
      <p class="small"><a href={href('/movimientos')} use:link>Ver todos los movimientos →</a></p>
    </section>

    <nav class="bloque sigue" aria-labelledby="h-sigue">
      <h2 id="h-sigue">Sigue explorando</h2>
      <ul>
        <li><a href={href('/mapa')} use:link>Mapa del gobierno</a> <span class="muted">— quién maneja cuánto</span></li>
        <li><a href={href('/flujo')} use:link>Flujo del dinero</a> <span class="muted">— de dónde entra y en qué se va</span></li>
        <li><a href={href('/comparar')} use:link>Comparar municipios</a> <span class="muted">— total y por habitante</span></li>
        <li><a href="/fuentes" use:link>Fuentes y datos abiertos</a> <span class="muted">— documentos oficiales y descargas</span></li>
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
  .lead {
    font-size: 1.1rem;
    max-width: 60ch;
  }
  .resumen {
    font-size: 1.2rem;
    line-height: 1.6;
    max-width: 62ch;
    margin: 0.5rem 0 1.5rem;
  }

  /* Key figures: open row separated by thin rules, CivLab-style (label, number, one line of context). */
  .cifras {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 0;
    border-top: 1px solid var(--grid);
    border-bottom: 1px solid var(--grid);
  }
  .cifras > div {
    padding: 1.1rem 1.25rem 1.1rem 0;
    min-width: 0;
  }
  .cifras > div + div {
    padding-left: 1.25rem;
    border-left: 1px solid var(--grid);
  }
  dt {
    font-size: 0.9rem;
    color: var(--ink-2);
  }
  dd {
    margin: 0;
  }
  .valor {
    font-size: clamp(1.4rem, 2.6vw, 1.85rem);
    font-weight: 700;
    letter-spacing: -0.01em;
    line-height: 1.2;
    margin: 0.2rem 0;
  }
  .unidad {
    font-size: 0.55em;
    font-weight: 600;
    color: var(--ink-2);
    letter-spacing: 0;
  }
  .lectura {
    font-size: 1.05rem;
    margin: 0 0 0.35rem;
  }
  .sigue ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.5rem 2rem;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 380px), 1fr));
  }
  .sigue a {
    font-weight: 600;
  }
  .ctx {
    font-size: 0.875rem;
    color: var(--ink-2);
  }
  .origen {
    margin: 0.5rem 0 0;
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

  /* Two open sections side by side, separated by space rather than boxes. */
  .dos {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 2.5rem 3rem;
    margin-top: 2.5rem;
  }
  .dos > section {
    min-width: 0;
  }
  .bloque {
    margin-top: 2.5rem;
    padding-top: 2rem;
    border-top: 1px solid var(--grid);
  }
  .movs {
    list-style: none;
    margin: 0;
    padding: 0;
    max-width: 80ch;
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
