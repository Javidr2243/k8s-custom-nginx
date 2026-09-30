<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE, NOMBRE_CORTO, type Fuente, type Meta, type MunicipioId, type Validacion } from '../lib/data';
  import { fecha, entero, porcentaje } from '../lib/format';
  import { normalizar } from '../lib/search';
  import { aCsv, descargar } from '../lib/csv';
  import Estado from '../components/Estado.svelte';
  import Termino from '../components/Termino.svelte';

  let fuentes = $state<Record<string, Fuente> | null>(null);
  let val = $state<Validacion | null>(null);
  let meta = $state<Meta | null>(null);
  let error = $state<string | null>(null);
  let q = $state('');
  let mun = $state<MunicipioId | 'nacional' | 'todos'>('todos');
  let emisor = $state('todos');
  let pagina = $state(0);
  const POR_PAGINA = 30;

  Promise.all([api.fuentes(), api.validacion(), api.meta()])
    .then(([f, v, m]) => {
      fuentes = f;
      val = v;
      meta = m;
    })
    .catch((e: Error) => (error = e.message));

  const emisorBase = (e: string) => e.split(' — ')[0]!;
  const emisores = $derived(fuentes ? [...new Set(Object.values(fuentes).map((f) => emisorBase(f.emisor)))].sort() : []);
  const lista = $derived.by(() => {
    if (!fuentes) return [] as [string, Fuente][];
    const nq = normalizar(q);
    return Object.entries(fuentes)
      .filter(([id, f]) => {
        if (mun === 'nacional' && f.municipio !== null) return false;
        if (mun !== 'todos' && mun !== 'nacional' && f.municipio !== mun) return false;
        if (emisor !== 'todos' && emisorBase(f.emisor) !== emisor) return false;
        return !nq || normalizar(`${f.titulo} ${f.emisor} ${f.periodo ?? ''} ${id}`).includes(nq);
      })
      .sort((a, b) => (b[1].publicado ?? '').localeCompare(a[1].publicado ?? '') || a[0].localeCompare(b[0]));
  });
  const visibles = $derived(lista.slice(pagina * POR_PAGINA, (pagina + 1) * POR_PAGINA));
  const paginas = $derived(Math.max(1, Math.ceil(lista.length / POR_PAGINA)));
  const totalRev = $derived(val ? val.chequeos.reduce((s, c) => s + c.revisados, 0) : 0);
  const totalOk = $derived(val ? val.chequeos.reduce((s, c) => s + c.aprobados, 0) : 0);

  function barra(el: HTMLElement, x: number) {
    const set = (v: number) => (el.style.width = `${Math.round(v * 100)}%`);
    set(x);
    return { update: set };
  }

  function exportar() {
    if (!fuentes) return;
    descargar(
      'fuentes-adonde-va-tu-dinero-mty.csv',
      aCsv(
        ['id', 'titulo', 'emisor', 'municipio', 'periodo', 'formato', 'url_oficial', 'pagina', 'copia_archivada', 'publicado', 'descargado', 'sha256', 'sha256_original'],
        lista.map(([id, f]) => [id, f.titulo, f.emisor, f.municipio ?? 'nacional', f.periodo, f.formato, f.url, f.pagina, `${location.origin}${f.copia}`, f.publicado, f.descargado, f.sha256, f.sha256_original]),
      ),
    );
  }

  const ARCHIVOS = [
    ['meta.json', 'Fecha de los datos y periodos disponibles'],
    ['municipios.json', 'Municipios, población y qué datos existen'],
    ...MUNICIPIOS.flatMap((m) => [
      [`egresos/${m}.json`, `Gasto trimestral de ${NOMBRE_CORTO[m]} (por capítulo${m === 'monterrey' ? ' y dependencia' : ''})`],
      [`ingresos/${m}.json`, `Ingresos de ${NOMBRE_CORTO[m]}`],
      [`deuda/${m}.json`, `Deuda de ${NOMBRE_CORTO[m]}`],
      [`contratos/${m}.json`, `Contratos de ${NOMBRE_CORTO[m]}`],
    ]),
    ['comparativo.json', 'Comparación anual (INEGI) y por habitante'],
    ['movimientos.json', 'Movimientos recientes'],
    ['fuentes.json', 'Todas las fuentes con sus huellas'],
    ['validacion.json', 'Resultados de las verificaciones automáticas'],
    ['SHA256SUMS', 'Huellas SHA-256 de los archivos de datos'],
  ] as const;
</script>

<section aria-labelledby="h-fuentes" class="stack">
  <h1 id="h-fuentes">Fuentes y verificación de los datos</h1>
  <p class="muted lead">
    Cada número del sitio sale de un documento oficial. Aquí puedes ver todos esos documentos, descargar la copia exacta
    que se usó, comprobar su huella digital y revisar qué verificaciones pasaron los datos.
    {#if meta}Datos actualizados al <strong>{fecha(meta.datos_al)}</strong>.{/if}
  </p>
  <Estado {error} cargando={!fuentes && !error} />

  {#if val}
    <article class="card">
      <h2>Verificaciones automáticas</h2>
      <p class="small muted">
        Cada vez que se actualizan los datos, un programa revisa los documentos antes de publicarlos. Si un número propio
        no cuadra con su documento, la actualización se detiene. Las diferencias <em>dentro</em> de los documentos oficiales
        se publican tal cual y se listan abajo. En total: <strong>{entero(totalOk)} de {entero(totalRev)}</strong>
        revisiones correctas.
      </p>
      <ul class="checks">
        {#each val.chequeos as c (c.id)}
          <li>
            <div class="chk-head">
              <span class="icono" class:ok={c.fallas.length === 0} aria-hidden="true">{c.fallas.length === 0 ? '✓' : '!'}</span>
              <span>{c.descripcion}</span>
            </div>
            <div class="meter" role="img" aria-label={`${c.aprobados} de ${c.revisados} correctas`}>
              <span use:barra={c.revisados ? c.aprobados / c.revisados : 0}></span>
            </div>
            <p class="small muted">{entero(c.aprobados)} de {entero(c.revisados)} correctas ({porcentaje(c.revisados ? c.aprobados / c.revisados : null, 1)})</p>
            {#if c.fallas.length}
              <details class="small">
                <summary>Ver {c.fallas.length} {c.fallas.length === 1 ? 'caso' : 'casos'}</summary>
                <ul class="fallas">
                  {#each c.fallas as f, i (i)}
                    <li>
                      {#if f.municipio}<strong>{NOMBRE_CORTO[f.municipio]}:</strong>{/if}
                      {f.detalle || 'Ver documento'}
                      {#if f.fuente && fuentes?.[f.fuente]}· <a href={fuentes[f.fuente]!.url} rel="noopener noreferrer" target="_blank">documento</a> · <a href={fuentes[f.fuente]!.copia} download>copia</a>{/if}
                    </li>
                  {/each}
                </ul>
              </details>
            {/if}
          </li>
        {/each}
      </ul>
    </article>

    <article class="card">
      <h2>Inconsistencias en los documentos oficiales ({val.advertencias.length})</h2>
      <p class="small muted">{val.nota}</p>
      {#each [...MUNICIPIOS, null] as m (m ?? 'otros')}
        {@const items = val.advertencias.filter((a) => a.municipio === m)}
        {#if items.length}
          <h3>{m ? NOMBRE[m] : 'Otras fuentes'}</h3>
          <ul class="small adv">
            {#each items as a, i (i)}
              <li>
                {a.mensaje}
                {#if a.fuente && fuentes?.[a.fuente]}· <a href={fuentes[a.fuente]!.url} rel="noopener noreferrer" target="_blank">documento</a>{/if}
              </li>
            {/each}
          </ul>
        {/if}
      {/each}
    </article>
  {/if}

  {#if fuentes}
    <article class="card">
      <h2>Todos los documentos ({Object.keys(fuentes).length})</h2>
      <p class="small muted">
        «Oficial» abre el documento en el sitio del gobierno; «Copia» descarga el archivo exacto que se usó (útil si el
        enlace oficial cambia). La <Termino id="sha256">huella SHA-256</Termino> permite comprobar que la copia no fue
        alterada.
      </p>
      <div class="controles">
        <label class="buscar">
          <span class="sr-only">Buscar documento</span>
          <input type="search" placeholder="Buscar por título, periodo o emisor…" bind:value={q} oninput={() => (pagina = 0)} />
        </label>
        <label>
          <span class="small muted">Municipio</span>
          <select bind:value={mun} onchange={() => (pagina = 0)}>
            <option value="todos">Todos</option>
            {#each MUNICIPIOS as m (m)}<option value={m}>{NOMBRE_CORTO[m]}</option>{/each}
            <option value="nacional">INEGI y Hacienda</option>
          </select>
        </label>
        <label>
          <span class="small muted">Emisor</span>
          <select bind:value={emisor} onchange={() => (pagina = 0)}>
            <option value="todos">Todos</option>
            {#each emisores as e (e)}<option value={e}>{e}</option>{/each}
          </select>
        </label>
        <button type="button" class="btn" onclick={exportar}>Descargar lista (CSV)</button>
      </div>
      <p class="small muted" aria-live="polite">{entero(lista.length)} documentos</p>
      <div class="table-wrap">
        <table class="data">
          <caption class="sr-only">Documentos fuente</caption>
          <thead>
            <tr><th scope="col">Documento</th><th scope="col">Publicado</th><th scope="col">Archivos</th><th scope="col">Huella SHA-256</th></tr>
          </thead>
          <tbody>
            {#each visibles as [id, f] (id)}
              <tr>
                <td>
                  {f.titulo}
                  <br /><span class="small muted">{f.emisor}{f.municipio ? '' : ' · nacional'}</span>
                </td>
                <td class="nw">{f.publicado ? fecha(f.publicado) : '—'}<br /><span class="small muted">descargado {fecha(f.descargado)}</span></td>
                <td class="nw">
                  <a href={f.url} rel="noopener noreferrer" target="_blank">Oficial</a> ·
                  <a href={f.copia} download>Copia{f.extracto ? ' (extracto)' : ''}</a>
                </td>
                <td><code class="hash" title={f.sha256 ?? ''}>{f.sha256?.slice(0, 12)}…</code></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if paginas > 1}
        <nav class="pag" aria-label="Páginas de documentos">
          <button type="button" class="btn" disabled={pagina === 0} onclick={() => (pagina -= 1)}>Anterior</button>
          <span class="small">Página {pagina + 1} de {paginas}</span>
          <button type="button" class="btn" disabled={pagina >= paginas - 1} onclick={() => (pagina += 1)}>Siguiente</button>
        </nav>
      {/if}
    </article>

    <article class="card">
      <h2>Datos procesados para descargar</h2>
      <p class="small muted">
        Los mismos datos que usa el sitio, en JSON, para analizarlos por tu cuenta. Cada cifra incluye el identificador de
        su fuente. También está el <a href="/data/originales/manifest.json" download>manifiesto de originales</a> (URL,
        fechas, huellas e historial de cambios de cada documento).
      </p>
      <ul class="archivos small">
        {#each ARCHIVOS as [ruta, desc] (ruta)}
          <li><a href={`/data/v1/${ruta}`} download>{ruta}</a> — {desc}</li>
        {/each}
      </ul>
    </article>
  {/if}
</section>

<style>
  .lead {
    max-width: 75ch;
  }
  .checks {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.9rem;
  }
  .chk-head {
    display: flex;
    gap: 0.5rem;
    align-items: start;
  }
  .icono {
    flex: none;
    display: inline-grid;
    place-items: center;
    width: 1.4em;
    height: 1.4em;
    border-radius: 50%;
    background: var(--warning);
    color: #0b0b0b;
    font-weight: 700;
    font-size: 0.85em;
  }
  .icono.ok {
    background: var(--good);
    color: #fff;
  }
  .meter {
    height: 8px;
    border-radius: 4px;
    background: var(--seq-200);
    margin: 0.35rem 0 0.2rem 1.9rem;
    overflow: hidden;
  }
  .meter span {
    display: block;
    height: 100%;
    background: var(--seq-450);
    border-radius: 4px;
  }
  .checks p,
  .checks details {
    margin-left: 1.9rem;
  }
  details summary {
    cursor: pointer;
    color: var(--link);
  }
  .fallas,
  .adv {
    padding-left: 1.2rem;
    overflow-wrap: anywhere;
  }
  .fallas li,
  .adv li {
    margin-bottom: 0.3rem;
  }
  .controles {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    align-items: end;
  }
  .controles label {
    display: grid;
    gap: 0.2rem;
  }
  .buscar {
    flex: 1 1 260px;
  }
  input,
  select {
    min-height: 44px;
    padding: 0.4rem 0.65rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    width: 100%;
  }
  .nw {
    white-space: nowrap;
  }
  .hash {
    font-family: ui-monospace, 'SFMono-Regular', Menlo, monospace;
    font-size: 0.8rem;
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
  .archivos {
    columns: 2 18rem;
    padding-left: 1.2rem;
  }
</style>
