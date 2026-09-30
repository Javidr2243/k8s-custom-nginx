<script lang="ts">
  import { api, NOMBRE, type Ingresos } from '../lib/data';
  import { pesos } from '../lib/format';
  import { route } from '../lib/router.svelte';
  import Filtros from '../components/Filtros.svelte';
  import Sankey, { type SLink, type SNodo } from '../components/Sankey.svelte';
  import Fuente from '../components/Fuente.svelte';
  import Termino from '../components/Termino.svelte';
  import Estado from '../components/Estado.svelte';

  let ing = $state<Ingresos | null>(null);
  let error = $state<string | null>(null);
  let anio = $state<number | null>(null);

  $effect(() => {
    const m = route.municipio;
    error = null;
    api
      .ingresos(m)
      .then((d) => {
        if (route.municipio === m) {
          ing = d;
          anio = d.anual.at(-1)?.anio ?? null;
        }
      })
      .catch((e: Error) => (error = e.message));
  });

  const m = $derived(route.municipio);
  const a = $derived(ing?.anual.find((x) => x.anio === anio));

  const FUENTES: [string, string, string[]][] = [
    ['impuestos', 'Impuestos locales (predial…)', ['impuestos']],
    ['otros-propios', 'Derechos, multas y otros', ['derechos', 'productos', 'aprovechamientos', 'contribuciones-de-mejoras', 'otros', 'por-cuenta-de-terceros']],
    ['participaciones', 'Participaciones federales', ['participaciones']],
    ['aportaciones', 'Aportaciones (fondos federales)', ['aportaciones']],
    ['financiamiento', 'Préstamos (deuda nueva)', ['financiamiento']],
    ['caja-inicial', 'Dinero en caja del año anterior', ['disponibilidad-inicial']],
  ];
  const DESTINOS: [string, string, string[]][] = [
    ['sueldos', 'Sueldos y prestaciones', ['1000']],
    ['servicios', 'Servicios (luz, limpia, rentas…)', ['3000']],
    ['materiales', 'Materiales y combustible', ['2000']],
    ['apoyos', 'Apoyos y subsidios', ['4000']],
    ['obra', 'Obra pública', ['6000']],
    ['deuda', 'Pago de deuda', ['9000']],
    ['otros', 'Equipo, reservas y otros', ['5000', '7000', '8000', 'otros', 'por-cuenta-de-terceros']],
    ['caja-final', 'Queda en caja al cierre', ['disponibilidad-final']],
  ];

  const g = $derived.by(() => {
    if (!a) return { nodos: [] as SNodo[], links: [] as SLink[] };
    const suma = (rec: Record<string, number>, keys: string[]) => keys.reduce((s, k) => s + (rec[k] ?? 0), 0);
    const nodos: SNodo[] = [{ id: 'mun', etiqueta: `Gobierno de ${NOMBRE[m]}`, lado: 'centro' }];
    const links: SLink[] = [];
    for (const [id, et, keys] of FUENTES) {
      const v = suma(a.ingresos_rubro, keys);
      if (v > 0) {
        nodos.push({ id, etiqueta: et, lado: 'fuente' });
        links.push({ de: id, a: 'mun', valor: v });
      }
    }
    for (const [id, et, keys] of DESTINOS) {
      const v = suma(a.egresos_capitulo, keys);
      if (v > 0) {
        nodos.push({ id, etiqueta: et, lado: 'destino' });
        links.push({ de: 'mun', a: id, valor: v });
      }
    }
    return { nodos, links };
  });
</script>

<section aria-labelledby="h-flujo">
  <h1 id="h-flujo">Flujo del dinero</h1>
  <p class="muted lead">
    Cómo entra el dinero al gobierno de {NOMBRE[m]} y hacia dónde sale en todo un año. A la izquierda, de dónde viene:
    <Termino id="impuestos">impuestos</Termino>, <Termino id="participaciones">participaciones</Termino> y
    <Termino id="aportaciones">aportaciones</Termino> federales o <Termino id="financiamiento">préstamos</Termino>. A la
    derecha, en qué se gasta.
  </p>
  <Filtros mostrarPeriodo={false} />
  <Estado {error} cargando={!ing && !error} />

  {#if ing}
    <label class="anio">
      <span>Año</span>
      <select bind:value={anio}>
        {#each [...ing.anual].reverse() as x (x.anio)}
          <option value={x.anio}>{x.anio}{x.estatus.includes('Preliminar') ? ' (preliminar)' : ''}</option>
        {/each}
      </select>
    </label>
    {#if a}
      <article class="card">
        <h2>{NOMBRE[m]}, {a.anio}</h2>
        <p class="small muted">
          Total que pasó por la tesorería: <strong>{pesos(a.ingresos_total)}</strong>.
          {#if a.estatus.includes('Preliminar')}Cifras preliminares del INEGI.{/if}
          Pasa el cursor sobre una franja para ver el monto.
        </p>
        <Sankey nodos={g.nodos} links={g.links} formato={pesos} titulo={`Flujo del dinero del gobierno de ${NOMBRE[m]} en ${a.anio}`} />
        <p class="small muted">
          Datos anuales del INEGI (<Termino id="efipem">EFIPEM</Termino>) para que ingresos y gastos cuadren en el mismo
          periodo. «Queda en caja» es la <Termino id="disponibilidad-final">disponibilidad final</Termino>: no es gasto.
        </p>
        <Fuente ids={[ing.fuente_anual]} />
      </article>
    {/if}
  {/if}
</section>

<style>
  .lead {
    max-width: 75ch;
  }
  .anio {
    display: inline-flex;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 1rem;
    color: var(--ink-2);
  }
  select {
    min-height: 44px;
    padding: 0.4rem 0.6rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
  }
</style>
