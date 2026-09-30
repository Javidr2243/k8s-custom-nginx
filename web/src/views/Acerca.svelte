<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE, type Egresos, type Fuente, type Meta, type MunicipioId } from '../lib/data';
  import { acumulado, fecha, trimestre } from '../lib/format';

  let fuentes = $state<Record<string, Fuente> | null>(null);
  let meta = $state<Meta | null>(null);
  let egr = $state<Partial<Record<MunicipioId, Egresos>>>({});
  api.fuentes().then((f) => (fuentes = f));
  api.meta().then((m) => (meta = m));
  for (const m of MUNICIPIOS) api.egresos(m).then((e) => (egr[m] = e));

  const grupos = $derived.by(() => {
    if (!fuentes) return [];
    const g = new Map<string, [string, Fuente][]>();
    for (const [id, f] of Object.entries(fuentes)) {
      const k = f.emisor.split(' — ')[0]!;
      g.set(k, [...(g.get(k) ?? []), [id, f]]);
    }
    return [...g.entries()].sort((a, b) => a[0].localeCompare(b[0], 'es'));
  });
</script>

<section aria-labelledby="h-acerca" class="stack">
  <h1 id="h-acerca">Acerca de los datos</h1>

  <article class="card">
    <h2>Qué es este sitio</h2>
    <p>
      <strong>¿A dónde va tu dinero? MTY</strong> es un sitio <strong>independiente y no oficial</strong> que explica
      cómo obtienen y gastan su dinero los gobiernos municipales de Monterrey, San Pedro Garza García y Santa Catarina.
      No está afiliado a ningún gobierno ni partido.
    </p>
    {#if meta}
      <p>
        Datos actualizados al <strong>{fecha(meta.datos_al)}</strong>. Periodo más reciente:
        {trimestre(meta.periodo_mas_reciente)} ({acumulado(meta.periodo_mas_reciente)}).
      </p>
    {/if}
  </article>

  <article class="card">
    <h2>Cómo se hacen los números</h2>
    <ul>
      <li>Todas las cifras se copian de documentos oficiales publicados en formato abierto (Excel, CSV o JSON). Un programa los descarga, revisa que las sumas cuadren con los totales del propio documento y los convierte para este sitio.</li>
      <li><strong>Nunca se inventan, estiman ni rellenan cifras.</strong> Si un dato no existe o el documento no es confiable, se marca como faltante y se explica por qué.</li>
      <li>Montos en <strong>pesos mexicanos nominales</strong>: tal como se reportaron, sin ajustar por inflación.</li>
      <li>Los reportes trimestrales son <strong>acumulados</strong>: el 2º trimestre incluye de enero a junio.</li>
      <li>Para comparar municipios se usan los datos anuales del INEGI (mismo formato para todos) divididos entre la población del Censo 2020.</li>
      <li>Cuando un documento oficial tiene inconsistencias internas (por ejemplo, un "modificado" que no cuadra), se publica tal cual y se registra en el reporte de validación.</li>
    </ul>
  </article>

  <article class="card">
    <h2>Límites de los datos</h2>
    <ul>
      <li>San Pedro y Santa Catarina publican el gasto por dependencia y los ingresos trimestrales solo en PDF escaneado; aquí se muestra su gasto por tipo (capítulo) y sus ingresos anuales del INEGI.</li>
      <li>Los organismos paramunicipales y los fideicomisos no aparecen en los reportes principales de los municipios.</li>
      <li>Las cifras anuales más recientes del INEGI son preliminares.</li>
      <li>La deuda es la inscrita en el Registro Público Único de Hacienda; obligaciones no inscritas no aparecen.</li>
      <li>Contratos: San Pedro publica su relación de contratos de adquisiciones (no incluye obra pública); Santa Catarina solo publica invitaciones y licitaciones; Monterrey reserva el nombre del proveedor en algunos contratos.</li>
    </ul>
    <h3>Periodos faltantes</h3>
    {#each MUNICIPIOS as m (m)}
      {#if egr[m]?.faltantes.length}
        <p><strong>{NOMBRE[m]}:</strong></p>
        <ul class="small">
          {#each egr[m]!.faltantes as f (f.periodo)}<li>{acumulado(f.periodo)}: {f.motivo}</li>{/each}
        </ul>
      {:else if egr[m]}
        <p><strong>{NOMBRE[m]}:</strong> sin periodos faltantes desde 2023.</p>
      {/if}
    {/each}
  </article>

  <article class="card">
    <h2>Privacidad</h2>
    <p>
      Este sitio no usa cookies, no tiene analítica ni rastreadores y no carga recursos de terceros. No recopila datos
      personales. El único dato que se guarda en tu navegador es tu preferencia de modo claro u oscuro.
    </p>
    <p>
      En los contratos solo se muestra el RFC de empresas; el de personas físicas se oculta. No se publican domicilios ni
      listas de beneficiarios de apoyos.
    </p>
  </article>

  <article class="card">
    <h2>Fuentes ({fuentes ? Object.keys(fuentes).length : '…'} documentos)</h2>
    <p class="small muted">
      Cada documento se guarda con su huella digital (SHA-256) para poder comprobar que no cambió. La lista de huellas de
      los datos del sitio está en <a href="/data/v1/SHA256SUMS">/data/v1/SHA256SUMS</a>.
    </p>
    {#each grupos as [emisor, lista] (emisor)}
      <details>
        <summary>{emisor} ({lista.length})</summary>
        <ul class="small fuentes">
          {#each lista as [id, f] (id)}
            <li>
              <a href={f.url} rel="noopener noreferrer" target="_blank">{f.titulo}</a>
              <span class="muted">{f.publicado ? `· publicado ${fecha(f.publicado)}` : ''} · descargado {fecha(f.descargado)}</span>
            </li>
          {/each}
        </ul>
      </details>
    {/each}
  </article>

  <article class="card">
    <h2>Código abierto y errores</h2>
    <p>
      El código y los datos procesados son abiertos. Si encuentras un número distinto al documento oficial, repórtalo
      con el enlace al documento en
      <a href="https://github.com/javidr2243/k8s-custom-nginx/issues" rel="noopener noreferrer">GitHub</a>.
    </p>
  </article>
</section>

<style>
  ul {
    padding-left: 1.2rem;
  }
  li {
    margin-bottom: 0.35rem;
  }
  details summary {
    cursor: pointer;
    min-height: 44px;
    display: flex;
    align-items: center;
    color: var(--link);
  }
  .fuentes {
    overflow-wrap: anywhere;
  }
</style>
