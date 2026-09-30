<script lang="ts">
  import { api, NOMBRE, type Contratos, type Contrato, type Fuente as FuenteDoc } from '../lib/data';
  import { fecha, pesos, porcentaje, entero } from '../lib/format';
  import { route } from '../lib/router.svelte';
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
  const filtrados = $derived.by(() => {
    if (!d) return [] as Contrato[];
    const nq = normalizar(q);
    const out = d.contratos.filter(
      (c) =>
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
      <StatTile
        value={porcentaje(directa)}
        sub="del monto, sin concurso abierto"
        origen={{ calculo: 'Monto de contratos por adjudicación directa, excepción o tres cotizaciones ÷ monto total contratado.', fuentes: [] }}
      >
        {#snippet label()}Por <Termino id="adjudicacion-directa">adjudicación directa</Termino>{/snippet}
      </StatTile>
      <StatTile
        value={porcentaje(r.concentracion_top10)}
        sub={`del monto fue a los 10 mayores de ${entero(r.proveedores)} proveedores`}
        origen={{ calculo: 'Monto de los 10 proveedores con más dinero ÷ monto total contratado. Los proveedores reservados por el municipio no se cuentan; los proveedores se agrupan por RFC (o por nombre si no hay RFC).', fuentes: [] }}
      >
        {#snippet label()}<Termino id="concentracion">Concentración</Termino>{/snippet}
      </StatTile>
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
      id="h-todos"
      pregunta="Todos los contratos"
      titular={`${entero(r.contratos)} contratos para buscar y descargar`}
      detalle="Filtra por proveedor, objeto, área, número o RFC. Cada contrato enlaza al archivo oficial del municipio; ahí se ubica por su número de contrato."
    >
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
