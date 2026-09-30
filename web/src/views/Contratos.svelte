<script lang="ts">
  import { api, NOMBRE, type Contratos, type Contrato, type Fuente as FuenteDoc } from '../lib/data';
  import { fecha, pesos, porcentaje, entero } from '../lib/format';
  import { route, setQuery } from '../lib/router.svelte';
  import { normalizar } from '../lib/search';
  import { aCsv, descargar } from '../lib/csv';
  import Filtros from '../components/Filtros.svelte';
  import StatTile from '../components/StatTile.svelte';
  import BarList from '../components/BarList.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';
  import Seccion from '../components/Seccion.svelte';

  let d = $state<Contratos | null>(null);
  // Official document of each contract (by source id), to link every row to the municipality's own file.
  let docs = $state<Record<string, FuenteDoc>>({});
  api.fuentes().then((f) => (docs = f)).catch(() => {});
  let error = $state<string | null>(null);
  let q = $state('');
  let cat = $state('todas');
  let orden = $state<'fecha' | 'monto'>('fecha');
  let pagina = $state(0);
  const POR_PAGINA = 25;

  $effect(() => {
    const m = route.municipio;
    error = null;
    api
      .contratos(m)
      .then((x) => {
        if (route.municipio === m) {
          d = x;
          pagina = 0;
        }
      })
      .catch((e: Error) => (error = e.message));
  });

  const m = $derived(route.municipio);
  const r = $derived(d?.resumen);
  const directa = $derived(r ? (r.por_categoria.directa?.monto ?? 0) / (r.monto_total || 1) : null);
  // Department filter (?dep=), set from the government map or the "¿Qué área contrata más?" bars.
  const dep = $derived(route.params.get('dep'));
  const depInfo = $derived(dep && r ? r.por_dependencia?.[dep] : undefined);
  const filtrados = $derived.by(() => {
    if (!d) return [] as Contrato[];
    const nq = normalizar(q);
    const out = d.contratos.filter(
      (c) =>
        (!depInfo || c.dependencia === dep) &&
        (cat === 'todas' || c.categoria === cat) &&
        (!nq || normalizar(`${c.proveedor} ${c.descripcion} ${c.area} ${c.numero} ${c.rfc ?? ''}`).includes(nq)),
    );
    return orden === 'monto' ? [...out].sort((a, b) => (b.monto ?? -1) - (a.monto ?? -1)) : out;
  });
  const visibles = $derived(filtrados.slice(pagina * POR_PAGINA, (pagina + 1) * POR_PAGINA));
  const paginas = $derived(Math.max(1, Math.ceil(filtrados.length / POR_PAGINA)));
  const GLOS: Record<string, string> = {
    licitacion: 'licitacion',
    invitacion: 'invitacion-restringida',
    directa: 'adjudicacion-directa',
    modificatorio: 'convenio-modificatorio',
  };

  // Who asks for the money: budget departments where the municipality publishes them (Monterrey), else the
  // requesting area as published.
  const areas = $derived.by(() => {
    if (!r) return [];
    const deps = Object.entries(r.por_dependencia ?? {});
    const filas = deps.length
      ? deps.map(([id, g]) => ({ id, etiqueta: g.nombre, g }))
      : (r.por_area ?? []).map((g, i) => ({ id: `a${i}`, etiqueta: g.area, g }));
    return filas
      .sort((a, b) => b.g.monto - a.g.monto)
      .slice(0, 12)
      .map(({ id, etiqueta, g }) => ({
        id,
        etiqueta,
        valor: g.monto,
        detalle: `${entero(g.n)} contrato${g.n === 1 ? '' : 's'}${g.pct_directa !== null ? ` · ${porcentaje(g.pct_directa)} sin concurso abierto` : ''}`,
      }));
  });
  const porDependencia = $derived(!!r && Object.keys(r.por_dependencia ?? {}).length > 0);
  const s = $derived(d?.senales);

  function irATabla() {
    pagina = 0;
    queueMicrotask(() => document.getElementById('h-todos')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }
  function verProveedor(nombre: string) {
    q = nombre;
    cat = 'todas';
    setQuery({ dep: null });
    irATabla();
  }
  const meses = (dias: number) => Math.floor(dias / 30.44);

  const cats = $derived(r ? Object.entries(r.por_categoria).sort((a, b) => b[1].monto - a[1].monto) : []);
  const topProv = $derived(r?.proveedores_top[0]);

  function exportar() {
    descargar(
      `contratos-${m}.csv`,
      aCsv(
        ['Fecha', 'Número', 'Procedimiento', 'Proveedor', 'RFC (empresas)', 'Descripción', 'Área', 'Monto con impuestos (MXN)', 'Origen de los recursos', 'Fuente'],
        filtrados.map((c) => [c.fecha, c.numero, c.procedimiento, c.proveedor, c.rfc, c.descripcion, c.area, c.monto, c.origen_recursos, c.fuente]),
      ),
    );
  }
</script>

<section aria-labelledby="h-contratos">
  <header>
    <p class="eyebrow">Compras del gobierno</p>
    <h1 id="h-contratos">Contratos y proveedores de {NOMBRE[m]}</h1>
    <p class="muted lead">
      A quién le compra el municipio, cuánto y cómo eligió al proveedor. Útil para ciudadanos y para empresas que quieren
      venderle al gobierno.
    </p>
    <Filtros mostrarPeriodo={false} />
  </header>
  <Estado {error} cargando={!d && !error} />

  {#if d && r}
    <p class="titular">
      <span>
        {NOMBRE[m]} publicó <strong class="num">{entero(r.contratos)} contratos</strong> por
        <strong class="num">{pesos(r.monto_total)}</strong>.
      </span>
      <span class="suave">
        {porcentaje(directa)} del dinero se asignó sin concurso abierto y los 10 proveedores más grandes recibieron
        {porcentaje(r.concentracion_top10)}{r.fechas[0] ? ` (del ${fecha(r.fechas[0])} al ${fecha(r.fechas[1])})` : ''}.
      </span>
    </p>

    <div class="cifras">
      <StatTile
        label="Contratos publicados"
        value={entero(r.contratos)}
        sub={r.fechas[0] ? `Del ${fecha(r.fechas[0])} al ${fecha(r.fechas[1])}` : ''}
        origen={{ calculo: 'Número de contratos (renglones sin duplicados exactos) en los formatos de contratos publicados por el municipio.', fuentes: d.fuentes.length > 3 ? [d.fuentes[0], d.fuentes.at(-1)] : d.fuentes }}
      />
      <StatTile
        label="Monto total contratado"
        value={pesos(r.monto_total)}
        sub={`${entero(r.con_monto)} contratos con monto publicado`}
        origen={{ calculo: 'Suma de «Monto total del contrato con impuestos incluidos» de los contratos que lo publican; los que no tienen monto no se suman.', fuentes: d.fuentes.length > 3 ? [d.fuentes[0], d.fuentes.at(-1)] : d.fuentes }}
      />
    </div>

    <div class="banda">
      <div class="dos">
        <Seccion
          id="h-proc"
          pregunta="¿Cómo se eligió al proveedor?"
          titular={`${porcentaje(directa)} del dinero se asignó sin concurso abierto`}
          detalle={cats[0] ? `${cats[0][1].nombre} es el procedimiento con más dinero: ${pesos(cats[0][1].monto)} en ${entero(cats[0][1].n)} contratos.` : null}
        >
          <BarList
            barras={cats.map(([k, v]) => ({ id: k, etiqueta: v.nombre, valor: v.monto, detalle: `${entero(v.n)} contratos` }))}
            formato={pesos}
            titulo="Monto contratado por tipo de procedimiento"
            total={r.monto_total}
            valorEtiqueta="Monto"
            seleccionado={cat === 'todas' ? null : cat}
            onelegir={(id) => {
              cat = cat === id ? 'todas' : id;
              pagina = 0;
            }}
          />
          <p class="small muted">
            Toca un tipo para filtrar la tabla. Glosario:
            <Termino id="licitacion">licitación</Termino>, <Termino id="invitacion-restringida">invitación</Termino>,
            <Termino id="adjudicacion-directa">adjudicación directa</Termino>.
          </p>
        </Seccion>
        <Seccion
          id="h-prov"
          pregunta="Proveedores con más dinero"
          titular={topProv ? `${topProv.proveedor} recibió ${porcentaje(topProv.porcentaje, 1)} del total` : 'Proveedores con más dinero'}
          detalle={`Los 10 mayores de ${entero(r.proveedores)} proveedores recibieron ${porcentaje(r.concentracion_top10)} del monto.`}
        >
          <BarList
            barras={r.proveedores_top.slice(0, 10).map((p, i) => ({
              id: String(i),
              etiqueta: p.proveedor,
              valor: p.monto,
              detalle: `${entero(p.n)} contrato${p.n === 1 ? '' : 's'} · ${porcentaje(p.porcentaje, 1)} del total${p.rfc ? ` · RFC ${p.rfc}` : ''}`,
            }))}
            formato={pesos}
            titulo="Diez proveedores con mayor monto contratado"
            total={r.monto_total}
            valorEtiqueta="Monto"
          />
          {#if r.reservados}
            <p class="small notice">
              En {entero(r.reservados)} contratos el municipio no publicó el nombre del proveedor
              (<Termino id="reservada">información reservada</Termino>); no se cuentan aquí.
            </p>
          {/if}
        </Seccion>
      </div>
    </div>

    <Seccion
      id="h-area"
      pregunta={porDependencia ? '¿Qué dependencia contrata más?' : '¿Qué área contrata más?'}
      titular={areas[0] && r.monto_total
        ? `${areas[0].etiqueta} pidió ${porcentaje(areas[0].valor / r.monto_total)} del dinero contratado`
        : '¿Qué área contrata más?'}
      detalle={porDependencia
        ? `${entero(r.dependencias_ligadas.contratos)} de ${entero(r.dependencias_ligadas.de)} contratos dicen qué dependencia los pidió; los demás nombran una oficina que no aparece en el presupuesto o a varias dependencias. Toca una para ver sus contratos.`
        : 'Por área solicitante, tal como la publica el municipio (este municipio no publica su gasto por dependencia).'}
    >
      <BarList
        barras={areas}
        formato={pesos}
        titulo={`Monto contratado por ${porDependencia ? 'dependencia' : 'área'}`}
        total={r.monto_total}
        valorEtiqueta="Monto contratado"
        seleccionado={porDependencia && depInfo ? dep : null}
        onelegir={porDependencia
          ? (id) => {
              setQuery({ dep: dep === id ? null : id });
              irATabla();
            }
          : undefined}
      />
      <p class="small muted">
        <Termino id="area-solicitante">Área solicitante</Termino>: la oficina que necesitaba la compra, no necesariamente
        la que hizo el concurso.
      </p>
    </Seccion>

    {#if s}
      <section class="banda revisar" aria-labelledby="h-revisar">
        <p class="eyebrow">Vale la pena revisar</p>
        <h2 id="h-revisar">Patrones que periodistas y contralorías suelen revisar</h2>
        <p class="aviso">
          Estas señales <strong>no indican irregularidades</strong>: cada una puede tener una explicación válida. Son
          datos publicados por el municipio, ordenados para facilitar su revisión. No se incluyen contratos con
          personas físicas ni con proveedores reservados.
        </p>
        <div class="senales">
          <div class="senal">
            <p class="eyebrow">Empresas de reciente creación</p>
            {#if s.empresas_jovenes.length}
              <h3>
                {s.empresas_jovenes.length}
                {s.empresas_jovenes.length === 1 ? 'contrato' : 'contratos'} con empresas de menos de
                {s.umbrales.meses_empresa_joven} meses
              </h3>
              <ul>
                {#each s.empresas_jovenes.slice(0, 5) as c, i (i)}
                  <li>
                    <span><strong>{c.proveedor}</strong> · constituida el {fecha(c.constitucion)}, contratada
                      {meses(c.dias)} meses después · {c.descripcion}
                      {#if docs[c.fuente]}<a href={docs[c.fuente]!.url} rel="noopener noreferrer" target="_blank">Documento oficial ↗</a>{/if}</span>
                    <span class="num">{pesos(c.monto)}</span>
                  </li>
                {/each}
              </ul>
            {:else}
              <h3>Ninguna empresa tenía menos de {s.umbrales.meses_empresa_joven} meses al ser contratada</h3>
              {#if s.empresa_mas_joven}
                <p class="small muted">
                  La más joven: {s.empresa_mas_joven.proveedor}, constituida el {fecha(s.empresa_mas_joven.constitucion)} y
                  contratada {meses(s.empresa_mas_joven.dias)} meses después ({fecha(s.empresa_mas_joven.fecha)}).
                </p>
              {/if}
            {/if}
            <p class="small muted">
              La fecha de constitución sale del <Termino id="rfc">RFC</Termino> de la empresa (sus 6 números son año, mes
              y día).
            </p>
          </div>

          <div class="senal">
            <p class="eyebrow">Adjudicaciones directas repetidas</p>
            <h3>
              {#if s.directas_repetidas.length}
                {s.directas_repetidas.length}
                {s.directas_repetidas.length === 1 ? 'proveedor recibió' : 'proveedores recibieron'}
                {s.umbrales.min_directas_repetidas} o más contratos sin concurso abierto
              {:else}
                Ningún proveedor recibió {s.umbrales.min_directas_repetidas} o más adjudicaciones directas
              {/if}
            </h3>
            {#if s.directas_repetidas.length}
              <ul>
                {#each s.directas_repetidas.slice(0, 6) as p, i (i)}
                  <li>
                    <span>
                      <strong>{p.proveedor}</strong> · {entero(p.n)} contratos
                      <button type="button" class="enlace" onclick={() => verProveedor(p.proveedor)}>Ver contratos</button>
                    </span>
                    <span class="num">{p.monto !== null ? pesos(p.monto) : 'sin monto publicado'}</span>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>

          <div class="senal">
            <p class="eyebrow">Mayores adjudicaciones directas</p>
            <h3>
              {#if s.mayores_directas[0]}
                La mayor, por {pesos(s.mayores_directas[0].monto)}, fue sin concurso abierto
              {:else}
                Sin adjudicaciones directas con monto publicado
              {/if}
            </h3>
            {#if s.mayores_directas.length}
              <ul>
                {#each s.mayores_directas as c, i (i)}
                  <li>
                    <span><strong>{c.proveedor}</strong> · {c.descripcion}{c.fecha ? ` · ${fecha(c.fecha)}` : ''}
                      {#if docs[c.fuente]}<a href={docs[c.fuente]!.url} rel="noopener noreferrer" target="_blank">Documento oficial ↗</a>{/if}</span>
                    <span class="num">{pesos(c.monto)}</span>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>

          <div class="senal">
            <p class="eyebrow"><Termino id="convenio-modificatorio">Convenios modificatorios</Termino></p>
            <h3>
              {#if s.modificatorios.n}
                {entero(s.modificatorios.n)} convenios modificatorios por {pesos(s.modificatorios.monto)}
              {:else}
                Sin convenios modificatorios publicados
              {/if}
            </h3>
            {#if s.modificatorios.mayores.length}
              <ul>
                {#each s.modificatorios.mayores as c, i (i)}
                  <li>
                    <span><strong>{c.proveedor}</strong> · {c.descripcion}{c.fecha ? ` · ${fecha(c.fecha)}` : ''}
                      {#if docs[c.fuente]}<a href={docs[c.fuente]!.url} rel="noopener noreferrer" target="_blank">Documento oficial ↗</a>{/if}</span>
                    <span class="num">{pesos(c.monto)}</span>
                  </li>
                {/each}
              </ul>
            {:else}
              <p class="small muted">Un convenio modificatorio cambia el monto, el plazo o el objeto de un contrato ya firmado.</p>
            {/if}
          </div>
        </div>
      </section>
    {/if}

    <Seccion
      id="h-todos"
      pregunta="Todos los contratos"
      titular={`${entero(r.contratos)} contratos para buscar y descargar`}
      detalle="Filtra por proveedor, objeto, área, número o RFC. Cada contrato enlaza al archivo oficial del municipio; ahí se ubica por su número de contrato."
    >
      {#if depInfo}
        <p class="filtro-dep">
          <span class="small">Dependencia: <strong>{depInfo.nombre}</strong> ({entero(depInfo.n)} contratos)</span>
          <button type="button" class="btn btn-s" onclick={() => setQuery({ dep: null })}>Quitar filtro ×</button>
        </p>
      {/if}
      <div class="controles">
        <label class="buscar">
          <span class="sr-only">Buscar en contratos</span>
          <input type="search" placeholder="Buscar proveedor, objeto, área o RFC…" bind:value={q} oninput={() => (pagina = 0)} />
        </label>
        <label>
          <span class="small muted">Tipo</span>
          <select bind:value={cat} onchange={() => (pagina = 0)}>
            <option value="todas">Todos</option>
            {#each Object.entries(r.por_categoria) as [k, v] (k)}<option value={k}>{v.nombre}</option>{/each}
          </select>
        </label>
        <label>
          <span class="small muted">Ordenar</span>
          <select bind:value={orden}>
            <option value="fecha">Más recientes</option>
            <option value="monto">Mayor monto</option>
          </select>
        </label>
        <button type="button" class="btn" onclick={exportar}>Descargar CSV ({entero(filtrados.length)})</button>
      </div>
      <p class="small muted" aria-live="polite">{entero(filtrados.length)} contratos</p>
      <div class="table-wrap">
        <table class="data">
          <caption class="sr-only">Contratos de {NOMBRE[m]}</caption>
          <thead>
            <tr><th scope="col">Fecha</th><th scope="col">Proveedor</th><th scope="col">Objeto</th><th scope="col">Procedimiento</th><th scope="col" class="r">Monto</th></tr>
          </thead>
          <tbody>
            {#each visibles as c, i (i)}
              <tr>
                <td>
                  <span class="nw">{c.fecha ? fecha(c.fecha) : '—'}</span>
                  {#if c.numero}<br /><span class="small muted">No. {c.numero}</span>{/if}
                </td>
                <td>
                  {c.proveedor}
                  {#if c.rfc}<br /><span class="small muted">RFC {c.rfc}</span>{/if}
                  {#if c.tipo_persona === 'reservada'}<br /><Termino id="reservada">¿Por qué?</Termino>{/if}
                </td>
                <td>
                  <span class="desc">{c.descripcion || '—'}</span>
                  {#if c.area}<br /><span class="small muted">{c.area}</span>{/if}
                </td>
                <td>
                  {#if GLOS[c.categoria]}<Termino id={GLOS[c.categoria]!}>{c.procedimiento}</Termino>{:else}{c.procedimiento}{/if}
                  {#if docs[c.fuente]}
                    <br /><a class="small doc" href={docs[c.fuente]!.url} rel="noopener noreferrer" target="_blank" title={docs[c.fuente]!.titulo}>Documento oficial ↗</a>
                    {#if docs[c.fuente]!.publicado}<br /><span class="small muted nw">publicado {fecha(docs[c.fuente]!.publicado)}</span>{/if}
                  {/if}
                </td>
                <td class="r nw">{c.monto !== null ? pesos(c.monto) : c.monto_maximo !== null ? `Hasta ${pesos(c.monto_maximo)}` : 'Sin monto publicado'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if paginas > 1}
        <nav class="pag" aria-label="Páginas de contratos">
          <button type="button" class="btn" disabled={pagina === 0} onclick={() => (pagina -= 1)}>Anterior</button>
          <span class="small">Página {pagina + 1} de {paginas}</span>
          <button type="button" class="btn" disabled={pagina >= paginas - 1} onclick={() => (pagina += 1)}>Siguiente</button>
        </nav>
      {/if}
      {#each d.notas as n, i (i)}<p class="small muted">{n}</p>{/each}
      <Fuente ids={d.fuentes.length > 3 ? [d.fuentes[0], d.fuentes.at(-1)] : d.fuentes} etiqueta={d.fuentes.length > 3 ? `Fuentes (${d.fuentes.length} archivos; primero y último)` : 'Fuente'} />
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
  .doc {
    white-space: nowrap;
  }
  .revisar h2 {
    margin-bottom: 0.4rem;
  }
  .aviso {
    max-width: 75ch;
    color: var(--ink-2);
  }
  .senales {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 440px), 1fr));
    gap: 2rem 3rem;
    margin-top: 1rem;
  }
  .senal {
    min-width: 0;
    padding-top: 1rem;
    border-top: 2px solid var(--ink);
  }
  .senal h3 {
    font-size: 1.15rem;
    margin: 0 0 0.5rem;
    text-wrap: balance;
  }
  .senal ul {
    list-style: none;
    margin: 0 0 0.5rem;
    padding: 0;
    display: grid;
    gap: 0.5rem;
  }
  .senal li {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--grid);
    font-size: 0.9rem;
  }
  .senal li > span:first-child {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .senal li a,
  .enlace {
    margin-left: 0.35rem;
    white-space: nowrap;
  }
  .num {
    flex: none;
    font-variant-numeric: tabular-nums;
    font-weight: 600;
  }
  .enlace {
    border: 0;
    background: none;
    padding: 0;
    color: var(--link);
    text-decoration: underline;
    cursor: pointer;
    font-size: inherit;
  }
  .filtro-dep {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    align-items: center;
    margin: 0 0 0.75rem;
  }
  .btn-s {
    min-height: 36px;
    padding: 0.2rem 0.75rem;
    font-size: 0.85rem;
  }
  .desc {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
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
</style>
