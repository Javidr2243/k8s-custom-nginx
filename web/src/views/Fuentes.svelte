<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE, NOMBRE_CORTO, type Fuente, type Meta, type MunicipioId, type Validacion } from '../lib/data';
  import { fecha, entero, porcentaje, trimestre } from '../lib/format';
  import { normalizar } from '../lib/search';
  import { aCsv, descargar } from '../lib/csv';
  import { ancho } from '../lib/ancho';
  import { CAPITULOS } from '../lib/capitulos';
  import Estado from '../components/Estado.svelte';
  import Termino from '../components/Termino.svelte';

  let fuentes = $state<Record<string, Fuente> | null>(null);
  let val = $state<Validacion | null>(null);
  let meta = $state<Meta | null>(null);
  let error = $state<string | null>(null);
  let q = $state('');
  let mun = $state<MunicipioId | 'nacional' | 'todos'>('todos');
  let pagina = $state(0);
  const POR_PAGINA = 25;

  Promise.all([api.fuentes(), api.validacion(), api.meta()])
    .then(([f, v, m]) => {
      fuentes = f;
      val = v;
      meta = m;
    })
    .catch((e: Error) => (error = e.message));

  const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  /** "2026-09-30" → "30 sep 2026". */
  const fechaCorta = (iso: string | null) => {
    const [y, m, d] = (iso ?? '').split('-').map(Number);
    return y && m && d ? `${d} ${MES[m - 1]} ${y}` : fecha(iso);
  };

  type Grupo = MunicipioId | 'nacional' | 'todos';
  const grupoDe = (f: Fuente): Grupo => f.municipio ?? 'nacional';
  const GRUPOS: { id: Grupo; nombre: string }[] = [
    { id: 'todos', nombre: 'Todos' },
    ...MUNICIPIOS.map((m) => ({ id: m as Grupo, nombre: NOMBRE_CORTO[m] })),
    { id: 'nacional', nombre: 'INEGI y Hacienda' },
  ];
  const conteo = $derived.by(() => {
    const c: Record<string, number> = { todos: 0 };
    for (const f of Object.values(fuentes ?? {})) {
      c.todos! += 1;
      c[grupoDe(f)] = (c[grupoDe(f)] ?? 0) + 1;
    }
    return c;
  });
  const lista = $derived.by(() => {
    if (!fuentes) return [] as [string, Fuente][];
    const nq = normalizar(q);
    return Object.entries(fuentes)
      .filter(([id, f]) => {
        if (mun !== 'todos' && grupoDe(f) !== mun) return false;
        return !nq || normalizar(`${f.titulo} ${f.emisor} ${f.periodo ?? ''} ${id}`).includes(nq);
      })
      .sort((a, b) => (b[1].publicado ?? '').localeCompare(a[1].publicado ?? '') || a[0].localeCompare(b[0]));
  });
  const visibles = $derived(lista.slice(pagina * POR_PAGINA, (pagina + 1) * POR_PAGINA));
  const paginas = $derived(Math.max(1, Math.ceil(lista.length / POR_PAGINA)));
  const totalRev = $derived(val ? val.chequeos.reduce((s, c) => s + c.revisados, 0) : 0);
  const totalOk = $derived(val ? val.chequeos.reduce((s, c) => s + c.aprobados, 0) : 0);
  const tInconsistencias = $derived.by(() => {
    if (!val) return '';
    const n = val.advertencias.length;
    if (!n) return 'Ninguna inconsistencia en los documentos oficiales';
    const muns = [...new Set(val.advertencias.map((a) => a.municipio))];
    const donde = muns.length === 1 && muns[0] ? `, todas en documentos de ${NOMBRE[muns[0]]}` : '';
    return `${n} ${n === 1 ? 'diferencia' : 'diferencias'} dentro de los documentos oficiales${donde}`;
  });
  const conDiferencias = $derived(val ? val.chequeos.filter((c) => c.fallas.length).length : 0);

  /** Short names for each automatic check (the long description stays below it). */
  const NOMBRE_CHEQUEO: Record<string, string> = {
    suma: 'Las sumas cuadran',
    periodo: 'Cada archivo es del periodo correcto',
    identidad: 'Las columnas cuadran entre sí',
    dependencias_vs_capitulos: 'Dos clasificaciones, mismo total',
    acumulado: 'El gasto acumulado no retrocede',
    repetidos: 'Sin cifras copiadas entre trimestres',
    cruce_inegi: 'Coincide con el INEGI',
    cruce_creditos: 'Créditos coinciden con el saldo',
    cruce_amortizacion: 'Pagos de deuda coinciden',
  };

  /** Warning text in plain language: no internal ids, "2023T1" → "1er trimestre de 2023", capítulo names, no list brackets. */
  function mensaje(a: { mensaje: string; fuente: string | null; municipio: MunicipioId | null }): string {
    let t = a.mensaje;
    if (a.fuente && t.startsWith(`${a.fuente} `)) t = t.slice(a.fuente.length + 1);
    if (a.municipio && t.startsWith(`${a.municipio}: `)) t = t.slice(a.municipio.length + 2);
    t = t.replace(/^(\d{4}T\d) clave/, '$1, clave');
    t = t.replace(/\bclave (\d{4})\b(?!\s*\()/g, (_, c: string) => {
      const nombre = CAPITULOS[c]?.sencillo;
      return `capítulo ${c}${nombre ? ` (${nombre})` : ''}`;
    });
    t = t.replace(/\bclave (\d{4}) \(/g, 'capítulo $1 (');
    t = t.replace(/\b(\d{4})T(\d)\b/g, (_, y: string, n: string) => trimestre(`${y}T${n}`));
    t = t.replace(/[[\]']/g, '');
    return t.charAt(0).toUpperCase() + t.slice(1);
  }

  function exportar() {
    if (!fuentes) return;
    descargar(
      'fuentes-adonde-va-tu-dinero-mty.csv',
      aCsv(
        ['id', 'titulo', 'emisor', 'municipio', 'periodo', 'formato', 'url_oficial', 'pagina', 'copia_archivada', 'publicado', 'descargado', 'sha256', 'sha256_original'],
        lista.map(([id, f]) => [id, f.titulo, f.emisor, f.municipio ?? 'nacional', f.periodo, f.formato, f.url, f.pagina, f.copia ? `${location.origin}${f.copia}` : '', f.publicado, f.descargado, f.sha256, f.sha256_original]),
      ),
    );
  }

  const GENERALES = [
    ['meta.json', 'Fecha de los datos y periodos disponibles'],
    ['municipios.json', 'Municipios, población y qué datos existen'],
    ['comparativo.json', 'Comparación anual (INEGI) y por habitante'],
    ['movimientos.json', 'Movimientos recientes'],
    ['fuentes.json', 'Todas las fuentes con sus huellas'],
    ['validacion.json', 'Resultados de las verificaciones'],
    ['SHA256SUMS', 'Huellas de los archivos de datos'],
  ] as const;
  const POR_MUNICIPIO = (m: MunicipioId) =>
    [
      [`egresos/${m}.json`, `Gasto trimestral${m === 'monterrey' ? ' (capítulo y dependencia)' : ' (por capítulo)'}`],
      [`ingresos/${m}.json`, 'Ingresos'],
      [`deuda/${m}.json`, 'Deuda'],
      [`contratos/${m}.json`, 'Contratos'],
    ] as const;
</script>

<section aria-labelledby="h-fuentes">
  <header class="cabeza">
    <p class="eyebrow">Transparencia del sitio</p>
    <h1 id="h-fuentes">Fuentes y verificación de los datos</h1>
    <p class="muted lead">
      Cada número del sitio sale de un documento oficial. Aquí están todos: puedes abrir el original, descargar la copia
      exacta que se usó, comprobar su huella digital y ver qué revisiones pasaron los datos.
    </p>
  </header>
  <Estado {error} cargando={!fuentes && !error} />

  {#if fuentes && val}
    <p class="titular">
      <span>Cada cifra del sitio sale de uno de <strong class="num">{entero(conteo.todos)} documentos oficiales</strong>.</span>
      <span class="suave">
        {entero(totalOk)} de {entero(totalRev)} revisiones automáticas salieron correctas; las diferencias están dentro de
        los propios documentos y se listan abajo.
      </span>
    </p>

    <ul class="kpis cifras" aria-label="Resumen">
      <li class="kpi">
        <span class="kpi-num num">{entero(conteo.todos)}</span>
        <span class="kpi-lbl">documentos oficiales</span>
        <span class="small muted">de 3 municipios, el INEGI y Hacienda</span>
      </li>
      <li class="kpi">
        <span class="kpi-num num">{porcentaje(totalRev ? totalOk / totalRev : null, 1)}</span>
        <span class="kpi-lbl">revisiones correctas</span>
        <span class="small muted">{entero(totalOk)} de {entero(totalRev)} en {val.chequeos.length} tipos de revisión</span>
      </li>
      <li class="kpi">
        <span class="kpi-num num">{entero(val.advertencias.length)}</span>
        <span class="kpi-lbl">inconsistencias en los originales</span>
        <span class="small muted">se publican tal cual, sin corregir</span>
      </li>
      <li class="kpi">
        <span class="kpi-num kpi-fecha">{meta ? fechaCorta(meta.datos_al) : '—'}</span>
        <span class="kpi-lbl">última actualización</span>
        <span class="small muted">se revisa cada semana</span>
      </li>
    </ul>

    <section class="banda pasos" aria-labelledby="h-pasos">
      <p class="eyebrow">En tres pasos</p>
      <h2 id="h-pasos">Cómo comprobar cualquier número</h2>
      <ol>
        <li>
          <span class="n" aria-hidden="true">1</span>
          <div>
            <strong>Toca «¿De dónde sale?» o «Fuente»</strong>
            <p class="small muted">Junto a cada cifra verás cómo se calcula y de qué documento viene.</p>
          </div>
        </li>
        <li>
          <span class="n" aria-hidden="true">2</span>
          <div>
            <strong>Abre el original o descarga la copia</strong>
            <p class="small muted">«Oficial» lleva al sitio del gobierno; «Copia» es el archivo exacto que se usó aquí.</p>
          </div>
        </li>
        <li>
          <span class="n" aria-hidden="true">3</span>
          <div>
            <strong>Compara la <Termino id="sha256">huella SHA-256</Termino></strong>
            <p class="small muted">Si coincide, el archivo no fue alterado (p. ej. <code>sha256sum archivo</code>).</p>
          </div>
        </li>
      </ol>
    </section>

    <section class="bloque" aria-labelledby="h-rev">
      <p class="eyebrow">Revisiones automáticas</p>
      <div class="h-fila">
        <h2 id="h-rev">{porcentaje(totalRev ? totalOk / totalRev : null, 1)} de las revisiones salieron correctas</h2>
        <span class="pill" class:warn={conDiferencias > 0}>
          {val.chequeos.length - conDiferencias} de {val.chequeos.length} sin diferencias
        </span>
      </div>
      <p class="small muted intro">
        Cada vez que se actualizan los datos, un programa revisa los documentos antes de publicarlos. Si un número propio
        no cuadra con su documento, la actualización se detiene. Las diferencias <em>dentro</em> de los documentos oficiales
        se publican tal cual y se listan abajo.
      </p>
      {#snippet tarjeta(c: Validacion['chequeos'][number])}
          {@const ok = c.fallas.length === 0}
          {@const frac = c.revisados ? c.aprobados / c.revisados : 0}
          <li class="chk" class:warn={!ok}>
            <div class="chk-top">
              <span class="icono" class:ok aria-hidden="true">
                <svg viewBox="0 0 16 16">
                  {#if ok}<path d="m4 8.5 2.5 2.5L12 5.5" />{:else}<path d="M8 4v5M8 11.5v.5" />{/if}
                </svg>
              </span>
              <strong class="chk-nom">{NOMBRE_CHEQUEO[c.id] ?? c.id}</strong>
              <span class="chk-frac num"><span class="sr-only">{ok ? 'Correcta' : 'Con diferencias'}: </span>{entero(c.aprobados)}/{entero(c.revisados)}</span>
            </div>
            <p class="small muted chk-desc">{c.descripcion}</p>
            <div class="meter" role="img" aria-label={`${c.aprobados} de ${c.revisados} correctas`}>
              <span use:ancho={frac}></span>
            </div>
            {#if c.fallas.length}
              <details class="small">
                <summary>Ver {c.fallas.length} {c.fallas.length === 1 ? 'caso' : 'casos'}</summary>
                <ul class="fallas">
                  {#each c.fallas as f, i (i)}
                    {@const doc = f.fuente ? fuentes?.[f.fuente] : undefined}
                    <li>
                      {#if f.municipio}<strong>{NOMBRE_CORTO[f.municipio]}:</strong>{/if}
                      {f.detalle || 'Ver documento'}
                      {#if doc}· <a href={doc.url} rel="noopener noreferrer" target="_blank">documento</a>{#if doc.copia} · <a href={doc.copia} download>copia</a>{/if}{/if}
                    </li>
                  {/each}
                </ul>
              </details>
            {/if}
          </li>
      {/snippet}
      <ul class="checks">
        {#each val.chequeos.filter((c) => c.fallas.length) as c (c.id)}{@render tarjeta(c)}{/each}
      </ul>
      {#if conDiferencias < val.chequeos.length}
        <details class="sin-dif">
          <summary>Ver las {val.chequeos.length - conDiferencias} revisiones sin diferencias</summary>
          <ul class="checks">
            {#each val.chequeos.filter((c) => !c.fallas.length) as c (c.id)}{@render tarjeta(c)}{/each}
          </ul>
        </details>
      {/if}
    </section>

    <section class="banda" aria-labelledby="h-inc">
      <p class="eyebrow">Inconsistencias en los documentos oficiales</p>
      <div class="h-fila">
        <h2 id="h-inc">{tInconsistencias}</h2>
        <span class="pill warn">{val.advertencias.length}</span>
      </div>
      <p class="small muted intro">{val.nota}</p>
      <div class="inc-grupos">
        {#each [...MUNICIPIOS, null] as m (m ?? 'otros')}
          {@const items = val.advertencias.filter((a) => a.municipio === m)}
          {#if items.length}
            <details class="inc" open={items.length <= 12}>
              <summary>
                {#if m}<span class="chip-dot dot-{m}" aria-hidden="true"></span>{/if}
                <strong>{m ? NOMBRE[m] : 'Otras fuentes'}</strong>
                <span class="muted small">{items.length} {items.length === 1 ? 'caso' : 'casos'}</span>
              </summary>
              <ul>
                {#each items as a, i (i)}
                  {@const f = a.fuente ? fuentes[a.fuente] : undefined}
                  <li>
                    <span class="small">{mensaje(a)}</span>
                    {#if f}
                      <span class="small muted inc-doc">
                        {f.titulo} ·
                        <a href={f.url} rel="noopener noreferrer" target="_blank">oficial</a>{#if f.copia}
                          · <a href={f.copia} download>copia</a>{/if}
                      </span>
                    {/if}
                  </li>
                {/each}
              </ul>
            </details>
          {/if}
        {/each}
      </div>
    </section>

    <section class="bloque" aria-labelledby="h-docs">
      <p class="eyebrow">Todos los documentos</p>
      <div class="h-fila">
        <h2 id="h-docs">{entero(conteo.todos)} documentos, cada uno con su copia y su huella</h2>
        <button type="button" class="btn" onclick={exportar}>
          <svg viewBox="0 0 16 16" aria-hidden="true" class="ico-s"><path d="M8 2v8m-3.5-3L8 10.5 11.5 7M3 13h10" /></svg>
          Descargar lista (CSV)
        </button>
      </div>
      <p class="small muted intro">
        «Oficial» abre el documento en el sitio del gobierno; «Copia» descarga el archivo exacto que se usó (útil si el
        enlace oficial cambia).
      </p>
      <div class="seg grupos" role="radiogroup" aria-label="Origen de los documentos">
        {#each GRUPOS as g (g.id)}
          <button
            type="button"
            class="btn"
            role="radio"
            aria-checked={mun === g.id}
            onclick={() => {
              mun = g.id;
              pagina = 0;
            }}
          >
            {#if g.id !== 'todos' && g.id !== 'nacional'}<span class="chip-dot dot-{g.id}" aria-hidden="true"></span>{/if}
            {g.nombre}
            <span class="cuenta num">{conteo[g.id] ?? 0}</span>
          </button>
        {/each}
      </div>
      <label class="buscar">
        <span class="sr-only">Buscar documento</span>
        <svg viewBox="0 0 16 16" aria-hidden="true" class="ico-s lupa"><circle cx="7" cy="7" r="4.5" /><path d="m10.5 10.5 3 3" /></svg>
        <input type="search" placeholder="Buscar por título, periodo o emisor…" bind:value={q} oninput={() => (pagina = 0)} />
      </label>
      <p class="small muted" aria-live="polite">{entero(lista.length)} documentos</p>

      <ul class="docs">
        {#each visibles as [id, f] (id)}
          <li class="doc">
            <div class="doc-main">
              <span class="doc-org small">
                {#if f.municipio}<span class="chip-dot dot-{f.municipio}" aria-hidden="true"></span>{/if}
                {f.emisor}
              </span>
              <span class="doc-tit">{f.titulo}</span>
              <span class="small muted">
                Publicado {f.publicado ? fecha(f.publicado) : 'sin fecha'} · descargado {fecha(f.descargado)} ·
                {f.formato.toUpperCase()}
              </span>
              <code class="hash" title={`SHA-256: ${f.sha256 ?? ''}`}>SHA-256 {f.sha256?.slice(0, 16)}…</code>
            </div>
            <div class="doc-acc">
              <a class="btn btn-s" href={f.url} rel="noopener noreferrer" target="_blank">
                Oficial <svg viewBox="0 0 16 16" aria-hidden="true" class="ico-s"><path d="M6 3H3v10h10v-3M9 3h4v4M13 3 7 9" /></svg>
              </a>
              {#if f.copia}
                <a class="btn btn-s" href={f.copia} download>
                  Copia{f.extracto ? ' (extracto)' : ''}
                  <svg viewBox="0 0 16 16" aria-hidden="true" class="ico-s"><path d="M8 2v8m-3.5-3L8 10.5 11.5 7M3 13h10" /></svg>
                </a>
              {:else}
                <span class="sin-copia small muted" title={f.sin_copia ?? ''}>Sin copia (datos personales)</span>
              {/if}
            </div>
          </li>
        {/each}
      </ul>
      {#if paginas > 1}
        <nav class="pag" aria-label="Páginas de documentos">
          <button type="button" class="btn" disabled={pagina === 0} onclick={() => (pagina -= 1)}>Anterior</button>
          <span class="small">Página {pagina + 1} de {paginas}</span>
          <button type="button" class="btn" disabled={pagina >= paginas - 1} onclick={() => (pagina += 1)}>Siguiente</button>
        </nav>
      {/if}
    </section>

    <section class="banda" aria-labelledby="h-desc">
      <p class="eyebrow">Datos abiertos</p>
      <h2 id="h-desc">Los mismos datos del sitio, listos para analizar</h2>
      <p class="small muted intro">
        Los mismos datos que usa el sitio, en JSON, para analizarlos por tu cuenta. Cada cifra incluye el identificador de
        su fuente. También está el <a href="/data/originales/manifest.json" download>manifiesto de originales</a> (URL,
        fechas, huellas e historial de cambios de cada documento).
      </p>
      <div class="desc-grid">
        {#each MUNICIPIOS as m (m)}
          <div class="desc">
            <h3><span class="chip-dot dot-{m}" aria-hidden="true"></span>{NOMBRE_CORTO[m]}</h3>
            <ul>
              {#each POR_MUNICIPIO(m) as [ruta, desc] (ruta)}
                <li><a href={`/data/v1/${ruta}`} download>{desc}</a> <code class="small muted">{ruta.split('/')[0]}</code></li>
              {/each}
            </ul>
          </div>
        {/each}
        <div class="desc">
          <h3>Generales</h3>
          <ul>
            {#each GENERALES as [ruta, desc] (ruta)}
              <li><a href={`/data/v1/${ruta}`} download>{desc}</a> <code class="small muted">{ruta}</code></li>
            {/each}
          </ul>
        </div>
      </div>
    </section>
  {/if}
</section>

<style>
  /* Vertical rhythm inside a section; bands, blocks and the heading row manage their own spacing. */
  section > * + *:not(.banda, .bloque, .h-fila, .kpis, .titular) {
    margin-top: 1rem;
  }
  .lead {
    max-width: 72ch;
    font-size: 1.05rem;
  }
  .intro {
    max-width: 80ch;
  }
  .h-fila {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem 1rem;
    margin-bottom: 0.4rem;
  }
  .h-fila h2 {
    margin: 0;
  }

  /* Summary numbers (inside the shared `.cifras` row) */
  .kpis {
    list-style: none;
    padding: 0;
    margin-bottom: 2rem;
  }
  @media (max-width: 520px) {
    .kpis {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  .kpi {
    display: grid;
    align-content: start;
    gap: 0.1rem;
  }
  .kpi-num {
    font-size: clamp(1.6rem, 3.5vw, 2.2rem);
    font-weight: 750;
    letter-spacing: -0.02em;
    line-height: 1.1;
  }
  .kpi-lbl {
    font-weight: 600;
  }
  .bloque {
    padding-block: clamp(1.75rem, 4vw, 2.75rem);
  }

  /* How to verify */
  .pasos ol {
    list-style: none;
    margin: 0.5rem 0 0;
    padding: 0;
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));
  }
  .pasos li {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
  }
  .pasos p {
    margin: 0.15rem 0 0;
  }
  .n {
    flex: none;
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    background: var(--accent);
    color: var(--accent-ink);
    font-weight: 700;
  }

  .pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    background: color-mix(in srgb, var(--good) 16%, transparent);
    color: var(--good-ink);
  }
  .pill.warn {
    background: color-mix(in srgb, var(--warning) 22%, transparent);
    color: var(--ink);
  }

  .sin-dif {
    margin-top: 1rem;
  }
  .sin-dif summary {
    cursor: pointer;
    min-height: 44px;
    display: flex;
    align-items: center;
    font-weight: 600;
  }
  /* Automatic checks as a grid of small cards */
  .checks {
    list-style: none;
    margin: 0.75rem 0 0;
    padding: 0;
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
  }
  .chk {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.75rem 0.85rem;
    background: var(--surface);
  }
  .chk.warn {
    border-left: 4px solid var(--warning);
  }
  .chk-top {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .chk-nom {
    flex: 1;
    line-height: 1.25;
  }
  .chk-frac {
    font-weight: 650;
    font-size: 0.95rem;
  }
  .chk-desc {
    margin: 0.35rem 0 0.5rem;
  }
  .icono {
    flex: none;
    display: grid;
    place-items: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background: var(--warning);
  }
  .icono svg {
    width: 1rem;
    height: 1rem;
    fill: none;
    stroke: #0b0b0b;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .icono.ok {
    background: var(--good);
  }
  .icono.ok svg {
    stroke: #fff;
  }
  .meter {
    height: 6px;
    border-radius: 3px;
    background: var(--seq-200);
    overflow: hidden;
  }
  .meter span {
    display: block;
    height: 100%;
    background: var(--seq-450);
    border-radius: 3px;
  }
  details summary {
    cursor: pointer;
    color: var(--link);
    min-height: 32px;
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }
  .chk details {
    margin-top: 0.35rem;
  }
  .fallas {
    padding-left: 1.1rem;
    overflow-wrap: anywhere;
  }
  .fallas li {
    margin-bottom: 0.3rem;
  }

  /* Inconsistencies */
  .inc-grupos {
    display: grid;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  .inc {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.25rem 0.85rem;
  }
  .inc summary {
    color: var(--ink);
    min-height: 44px;
  }
  .inc ul {
    list-style: none;
    margin: 0 0 0.6rem;
    padding: 0;
    display: grid;
    gap: 0.5rem;
  }
  .inc li {
    display: grid;
    gap: 0.1rem;
    padding: 0.5rem 0.65rem;
    border-radius: var(--radius-sm);
    background: var(--surface-2);
    overflow-wrap: anywhere;
  }

  /* Documents */
  .grupos {
    margin: 0.4rem 0 0.75rem;
  }
  .cuenta {
    font-size: 0.8rem;
    padding: 0 0.45rem;
    border-radius: 999px;
    background: var(--surface-2);
    color: var(--ink-2);
  }
  .btn[aria-checked='true'] .cuenta {
    background: color-mix(in srgb, var(--surface) 25%, transparent);
    color: inherit;
  }
  .buscar {
    position: relative;
    display: block;
    max-width: 560px;
  }
  .lupa {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--ink-3);
  }
  input {
    min-height: 44px;
    padding: 0.4rem 0.75rem 0.4rem 2.3rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    width: 100%;
  }
  .docs {
    list-style: none;
    margin: 0;
    padding: 0;
    border-top: 1px solid var(--grid);
  }
  .doc {
    display: flex;
    gap: 0.75rem 1.25rem;
    align-items: center;
    padding: 0.8rem 0;
    border-bottom: 1px solid var(--grid);
  }
  .doc-main {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 0.1rem;
  }
  .doc-org {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--ink-2);
    font-weight: 600;
  }
  .doc-tit {
    font-weight: 600;
    overflow-wrap: break-word;
  }
  .doc-acc {
    display: flex;
    gap: 0.4rem;
    flex: none;
  }
  .sin-copia {
    align-self: center;
    max-width: 12rem;
    line-height: 1.3;
  }
  .btn-s {
    min-height: 40px;
    padding: 0.3rem 0.8rem;
    font-size: 0.875rem;
    color: var(--link);
  }
  .ico-s {
    width: 1em;
    height: 1em;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .hash {
    font-family: ui-monospace, 'SFMono-Regular', Menlo, monospace;
    font-size: 0.75rem;
    color: var(--ink-3);
    overflow-wrap: anywhere;
  }
  .pag {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    justify-content: center;
    margin-top: 0.75rem;
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  /* Downloads */
  .desc-grid {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr));
  }
  .desc {
    padding: 0.8rem 0.9rem;
    border-radius: var(--radius-sm);
    background: var(--surface-2);
  }
  .desc h3 {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 1rem;
  }
  .desc ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.35rem;
  }
  .desc code {
    font-size: 0.75rem;
  }

  @media (max-width: 640px) {
    .doc {
      flex-direction: column;
      align-items: stretch;
    }
    .doc-acc .btn-s {
      flex: 1;
      justify-content: center;
    }
  }
</style>
