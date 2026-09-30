<script lang="ts">
  import { NOMBRE_CORTO, type Movimiento } from '../lib/data';
  import { fecha } from '../lib/format';
  import Fuente from './Fuente.svelte';

  let { movimiento: mv }: { movimiento: Movimiento } = $props();
  const TIPO: Record<Movimiento['tipo'], string> = {
    periodo: 'Nuevo reporte',
    modificacion: 'Cambio al presupuesto',
    deuda: 'Deuda',
    alerta: 'Calificación de deuda',
    contrato: 'Contrato',
  };
</script>

<li class="mov">
  <div class="meta small">
    <span class="chip-dot dot-{mv.municipio}" aria-hidden="true"></span>
    <span>{NOMBRE_CORTO[mv.municipio]}</span>
    <span aria-hidden="true">·</span>
    <span class="tipo">{TIPO[mv.tipo]}</span>
    {#if mv.fecha}<span aria-hidden="true">·</span><time datetime={mv.fecha}>{fecha(mv.fecha)}</time>{/if}
  </div>
  <p class="tit">{mv.titulo}</p>
  <p class="det small muted">{mv.detalle}</p>
  <Fuente ids={[mv.fuente]} />
</li>

<style>
  .mov {
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--grid);
  }
  .mov:last-child {
    border-bottom: 0;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
    color: var(--ink-2);
  }
  .tipo {
    font-weight: 600;
  }
  .tit {
    margin: 0.2rem 0 0.1rem;
    font-weight: 600;
    overflow-wrap: anywhere;
  }
  .det {
    margin: 0;
  }
</style>
