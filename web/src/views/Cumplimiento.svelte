<script lang="ts">
  import { api, MUNICIPIOS, NOMBRE, NOMBRE_CORTO, type Egresos, type MunicipioId } from '../lib/data';
  import { acumulado, acumuladoCorto, cambio, pesos, porcentaje } from '../lib/format';
  import { route } from '../lib/router.svelte';
  import { cierre, hallazgos, ritmo, UMBRAL_RITMO, MINIMO_PESO, type FilaCierre } from '../lib/cumplimiento';
  import Filtros from '../components/Filtros.svelte';
  import StatTile from '../components/StatTile.svelte';
  import BarList from '../components/BarList.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';
  import Seccion from '../components/Seccion.svelte';

  const PNT = 'https://www.plataformadetransparencia.org.mx/';

  let todos = $state<Record<MunicipioId, Egresos> | null>(null);
  let error = $state<string | null>(null);
  Promise.all(MUNICIPIOS.map((x) => api.egresos(x)))
    .then((ds) => (todos = Object.fromEntries(MUNICIPIOS.map((x, i) => [x, ds[i]!])) as Record<MunicipioId, Egresos>))
    .catch((e: Error) => (error = e.message));

  const m = $derived(route.municipio);
  const egr = $derived(todos?.[m]);
  const c = $derived(egr ? cierre(egr) : null);
  const r = $derived(egr ? ritmo(egr) : null);
  const hs = $derived(hallazgos(c, r, NOMBRE[m]));
  const cierres = $derived(todos ? MUNICIPIOS.map((x) => ({ id: x, c: cierre(todos![x]) })) : []);

  const pesa = (f: FilaCierre) => (f.modificado ?? 0) >= (c?.total.modificado ?? 0) * MINIMO_PESO;
  const capitulos = $derived(c ? c.capitulos.filter(pesa) : []);

  // 1. Unspent at year-end.
  const mayorSin = $derived([...capitulos].filter((f) => f.sinGastar).sort((a, b) => b.sinGastar! - a.sinGastar!)[0]);
  const tSin = $derived.by(() => {
    if (!c) return '';
    if (!mayorSin || (mayorSin.ejecucion ?? 1) > 0.99)
      return `En ${c.anio} prácticamente todo el presupuesto se gastó: ningún rubro dejó más de 1% sin gastar`;
    return `${mayorSin.nombre}: ${pesos(mayorSin.sinGastar)} sin gastar, ${porcentaje(1 - (mayorSin.ejecucion ?? 0))} de su presupuesto final`;
  });
  const depsSin = $derived(
    c?.dependencias
      ? [...c.dependencias]
          .filter((f) => f.sinGastar && f.sinGastar >= 1e6)
          .sort((a, b) => b.sinGastar! - a.sinGastar!)
          .slice(0, 8)
      : [],
  );

  // 2. Change after approval.
  const mayorCambio = $derived(
    [...capitulos].filter((f) => f.cambioTrasAprobar != null).sort((a, b) => Math.abs(b.cambioTrasAprobar!) - Math.abs(a.cambioTrasAprobar!))[0],
  );
  const tCambio = $derived(
    c && mayorCambio
      ? `${mayorCambio.nombre}: ${mayorCambio.cambioTrasAprobar! >= 0 ? 'subió' : 'bajó'} ${porcentaje(Math.abs(mayorCambio.cambioTrasAprobar!))} después de aprobarse`
      : '',
  );

  // 3. This year's pace.
  const filasRitmo = $derived(r ? r.capitulos.filter((f) => (f.modificado ?? 0) >= (r.total.modificado ?? 0) * MINIMO_PESO) : []);
  const atrasados = $derived(filasRitmo.filter((f) => f.diferencia != null && f.diferencia <= -UMBRAL_RITMO));
  const puntos = (x: number | null) => (x == null ? '—' : `${x > 0 ? '+' : x < 0 ? '−' : ''}${Math.abs(Math.round(x * 100))} pts`);
  const tRitmo = $derived.by(() => {
    if (!r) return '';
    const t = r.total;
    const [meses, anio] = [acumulado(r.periodo).split(' ')[0]!.replace('–', ' a '), r.periodo.slice(0, 4)];
    const base = `De ${meses} de ${anio}, ${NOMBRE_CORTO[m]} gastó ${porcentaje(t.actual)} de su presupuesto`;
    return t.previo != null ? `${base}; un año antes llevaba ${porcentaje(t.previo)}` : base;
  });

  // Copy a question to the clipboard (falls back to selecting the text).
  let copiado = $state<string | null>(null);
  async function copiar(id: string, texto: string, el: HTMLElement | null) {
    try {
      await navigator.clipboard.writeText(texto);
      copiado = id;
      setTimeout(() => copiado === id && (copiado = null), 2500);
    } catch {
      if (el) {
        const sel = window.getSelection();
        const rango = document.createRange();
        rango.selectNodeContents(el);
        sel?.removeAllRanges();
        sel?.addRange(rango);
      }
    }
  }
  const nodos: Record<string, HTMLElement | null> = $state({});
</script>

<section aria-labelledby="h-cumplimiento">
  <header>
    <p class="eyebrow">Presupuesto prometido contra gasto real</p>
    <h1 id="h-cumplimiento">¿Se cumple el presupuesto?</h1>
    <p class="muted lead">
      Cada año el Cabildo aprueba un presupuesto; durante el año se modifica y al final se reporta cuánto se gastó de
      verdad. Aquí se comparan las tres cifras, con los reportes oficiales del municipio.
    </p>
    <Filtros mostrarPeriodo={false} />
  </header>
  <Estado {error} cargando={!todos && !error} />

  {#if egr}
    {#if c}
      <p class="titular">
        <span>
          En {c.anio}, {NOMBRE_CORTO[m]} gastó <strong class="num">{porcentaje(c.total.ejecucion)}</strong> de su presupuesto
          final.
        </span>
        <span class="suave">
          Quedaron {pesos(c.total.sinGastar)} sin gastar de {pesos(c.total.modificado)}. El presupuesto aprobado era de
          {pesos(c.total.aprobado)}{c.total.cambioTrasAprobar != null ? ` (${cambio(c.total.cambioTrasAprobar)} después de los cambios)` : ''}.
        </span>
      </p>

      <div class="cifras">
        {#each cierres as x (x.id)}
          <StatTile
            label={`${NOMBRE_CORTO[x.id]}${x.c ? `, ${x.c.anio}` : ''}`}
            value={x.c?.total.ejecucion != null ? porcentaje(x.c.total.ejecucion) : 'Sin cierre'}
            sub={x.c ? `gastado · ${pesos(x.c.total.sinGastar)} sin gastar` : 'No publicó el 4º trimestre'}
            origen={{
              calculo: 'Gasto devengado de enero a diciembre dividido entre el presupuesto modificado (final), según el informe del 4º trimestre.',
              fuentes: [x.c?.fuente],
            }}
          />
        {/each}
      </div>

      <Seccion
        id="h-sin-gastar"
        banda
        pregunta="¿Qué se quedó sin gastar?"
        titular={tSin}
        detalle={`Barra oscura: lo gastado (devengado) en ${c.anio}. Barra clara: el presupuesto final. La diferencia es lo que no se gastó.`}
      >
        <BarList
          barras={capitulos.map((f) => ({
            id: f.id,
            etiqueta: f.nombre,
            valor: f.devengado,
            referencia: f.modificado,
            color: 'seq',
            detalle: f.sinGastar ? `${pesos(f.sinGastar)} sin gastar · ${porcentaje(f.ejecucion)} gastado` : `${porcentaje(f.ejecucion)} gastado`,
          }))}
          formato={pesos}
          valorEtiqueta="Gastado (devengado)"
          referenciaEtiqueta="Presupuesto final"
          titulo={`Gasto contra presupuesto final por tipo de gasto, ${NOMBRE[m]} ${c.anio}`}
        />
        {#if depsSin.length}
          <h3>Dependencias con más dinero sin gastar</h3>
          <BarList
            barras={depsSin.map((f) => ({
              id: f.id,
              etiqueta: f.nombre,
              valor: f.sinGastar,
              referencia: f.modificado,
              color: 'seq',
              detalle: `${porcentaje(f.ejecucion)} gastado de ${pesos(f.modificado)}`,
            }))}
            formato={pesos}
            valorEtiqueta="Sin gastar"
            referenciaEtiqueta="Presupuesto final"
            titulo={`Dependencias de ${NOMBRE[m]} con más presupuesto sin gastar en ${c.anio}`}
          />
        {/if}
        <p class="small muted">
          Gastar menos no siempre es malo: puede haber ahorros, licitaciones que se retrasaron u obras de varios años que
          se pagan después. Lo que no se explica sí vale una pregunta (abajo).
        </p>
        <Fuente ids={[c.fuente, depsSin.length ? c.fuenteDependencias : null]} compacto />
      </Seccion>

      {#if mayorCambio}
        <Seccion
          id="h-cambio"
          pregunta="¿Cuánto cambió el presupuesto después de aprobarse?"
          titular={tCambio}
          detalle={`Barra clara: lo que aprobó el Cabildo para ${c.anio}. Barra oscura: el presupuesto final después de ampliaciones y recortes.`}
        >
          <BarList
            barras={capitulos.map((f) => ({
              id: f.id,
              etiqueta: f.nombre,
              valor: f.modificado,
              referencia: f.aprobado,
              color: 'seq',
              detalle: f.cambioTrasAprobar != null ? `${cambio(f.cambioTrasAprobar)} vs. lo aprobado` : 'Sin monto aprobado',
            }))}
            formato={pesos}
            valorEtiqueta="Presupuesto final"
            referenciaEtiqueta="Aprobado"
            titulo={`Presupuesto aprobado contra final por tipo de gasto, ${NOMBRE[m]} ${c.anio}`}
          />
          <p class="small muted">
            Los cambios son normales cuando llegan ingresos no previstos o se mueve dinero entre áreas (<Termino
              id="ampliaciones">ampliaciones y reducciones</Termino
            >); deben aprobarse y publicarse. Uno muy grande indica que el presupuesto aprobado dijo poco de lo que
            realmente se iba a hacer.
          </p>
          <Fuente ids={[c.fuente]} compacto />
        </Seccion>
      {/if}
    {:else}
      <p class="aviso">{NOMBRE[m]} no ha publicado el informe del 4º trimestre de ningún año: no se puede saber cómo cerró.</p>
    {/if}

    {#if r}
      <Seccion
        id="h-ritmo"
        banda
        pregunta="¿Cómo va este año?"
        titular={tRitmo}
        detalle={atrasados.length
          ? `${atrasados.length === 1 ? 'Un rubro va' : `${atrasados.length} rubros van`} ${Math.round(UMBRAL_RITMO * 100)} puntos o más por debajo de su propio ritmo del año pasado (marcados con «!»).`
          : `Ningún rubro va ${Math.round(UMBRAL_RITMO * 100)} puntos o más por debajo de su ritmo del año pasado.`}
      >
        <div class="table-wrap">
          <table class="data ritmo">
            <caption class="sr-only">Parte del presupuesto gastada a {acumuladoCorto(r.periodo)} y un año antes, por tipo de gasto</caption>
            <thead>
              <tr>
                <th scope="col">Tipo de gasto</th>
                <th scope="col" class="r">{r.periodo.slice(0, 4)}</th>
                <th scope="col" class="r">{r.anterior.slice(0, 4)}</th>
                <th scope="col" class="r">Diferencia</th>
                <th scope="col" class="r">Presupuesto {r.periodo.slice(0, 4)}</th>
              </tr>
            </thead>
            <tbody>
              {#each filasRitmo as f (f.id)}
                {@const lento = f.diferencia != null && f.diferencia <= -UMBRAL_RITMO}
                <tr class:lento>
                  <th scope="row">{f.nombre}</th>
                  <td class="r num">{porcentaje(f.actual)}</td>
                  <td class="r num muted">{porcentaje(f.previo)}</td>
                  <td class="r num">
                    {#if lento}<span class="marca" aria-hidden="true">!</span><span class="sr-only">Atrasado: </span>{/if}{puntos(f.diferencia)}
                  </td>
                  <td class="r num muted">{pesos(f.modificado)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <p class="small muted">
          Cada rubro se compara con él mismo en el mismo trimestre del año anterior, porque algunos gastos (como la obra
          pública) se pagan sobre todo al final del año. Cifras <Termino id="acumulado">acumuladas</Termino> de enero a la
          fecha de corte.
        </p>
        <Fuente ids={[r.fuente]} compacto />
      </Seccion>
    {/if}

    {#if hs.length}
      <Seccion
        id="h-hacer"
        pregunta="¿Qué puedes hacer?"
        titular="Pregúntale al municipio: tiene la obligación de responderte"
        detalle="Cualquier persona puede hacer una solicitud de acceso a la información, gratis y sin dar motivos. Copia la pregunta y pégala en la Plataforma Nacional de Transparencia."
      >
        <ol class="preguntas">
          {#each hs as h (h.tipo)}
            <li>
              <p class="hallazgo">{h.titular}</p>
              <blockquote bind:this={nodos[h.tipo]}>{h.pregunta}</blockquote>
              <div class="acciones">
                <button type="button" class="btn" onclick={() => copiar(h.tipo, h.pregunta, nodos[h.tipo] ?? null)}>
                  {copiado === h.tipo ? 'Copiada ✓' : 'Copiar pregunta'}
                </button>
                <span class="sr-only" aria-live="polite">{copiado === h.tipo ? 'Pregunta copiada' : ''}</span>
              </div>
            </li>
          {/each}
        </ol>
        <p>
          <a class="btn primario" href={PNT} rel="noopener noreferrer" target="_blank">Abrir la Plataforma Nacional de Transparencia ↗</a>
        </p>
        <p class="small muted">
          Elige «{NOMBRE[m]}» como sujeto obligado (el Ayuntamiento). Deben responder en 20 días hábiles, ampliables. Más
          sobre la <Termino id="solicitud-informacion">solicitud de acceso a la información</Termino>.
        </p>
      </Seccion>
    {/if}

    <details class="contexto">
      <summary>Cómo leer estas cifras</summary>
      <ul>
        <li>
          <strong><Termino id="aprobado">Aprobado</Termino></strong>: lo que votó el Cabildo al inicio del año.
          <strong><Termino id="modificado">Presupuesto final (modificado)</Termino></strong>: el aprobado más ampliaciones y
          menos reducciones.
        </li>
        <li>
          <strong><Termino id="devengado">Gastado (devengado)</Termino></strong>: bienes recibidos o servicios prestados,
          aunque aún no se paguen. Lo que falta para llegar al presupuesto final es el
          <Termino id="subejercicio">subejercicio</Termino>.
        </li>
        <li>El «cierre» usa el informe del 4º trimestre (enero a diciembre). Si un municipio no lo publicó, no se calcula.</li>
        <li>Pesos nominales, tal como se reportaron. Solo se muestran rubros con al menos 1% del presupuesto.</li>
      </ul>
    </details>
  {/if}
</section>

<style>
  .lead {
    max-width: 70ch;
  }
  .cifras {
    margin-bottom: 1rem;
  }
  h3 {
    margin: 2rem 0 0.5rem;
    font-size: 1.1rem;
  }
  .ritmo tr.lento th,
  .ritmo tr.lento td {
    font-weight: 650;
  }
  .marca {
    display: inline-grid;
    place-items: center;
    width: 1.2em;
    height: 1.2em;
    margin-right: 0.35rem;
    border-radius: 50%;
    background: var(--warning);
    color: #0b0b0b;
    font-size: 0.8em;
    font-weight: 800;
  }
  .preguntas {
    list-style: none;
    padding: 0;
    margin: 1rem 0;
    display: grid;
    gap: 1.5rem;
    max-width: 75ch;
  }
  .preguntas li {
    border-top: 1px solid var(--border);
    padding-top: 1rem;
  }
  .hallazgo {
    font-weight: 650;
    margin: 0 0 0.5rem;
    text-wrap: balance;
  }
  blockquote {
    margin: 0 0 0.75rem;
    padding: 0.75rem 1rem;
    border-left: 3px solid var(--accent);
    background: var(--surface-2);
    border-radius: var(--radius-sm);
    text-wrap: pretty;
  }
  .acciones {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
  }
  .contexto {
    margin: 2rem 0 0;
    max-width: 75ch;
    color: var(--ink-2);
  }
  .contexto summary {
    cursor: pointer;
    min-height: 44px;
    display: flex;
    align-items: center;
    font-weight: 600;
  }
  .primario {
    background: var(--accent);
    color: var(--accent-ink);
    border-color: var(--accent);
    text-decoration: none;
  }
  .aviso {
    margin: 2rem 0;
  }
</style>
