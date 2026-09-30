<script lang="ts">
  // Loading / error state for a view. While reloading, the previous content stays (no layout jumps).
  let { error = null, cargando = false }: { error?: string | null; cargando?: boolean } = $props();
</script>

{#if error}
  <div class="notice" role="alert">
    <strong>No se pudieron cargar los datos.</strong>
    {error}. Revisa tu conexión e intenta de nuevo.
  </div>
{:else if cargando}
  <p class="muted" aria-live="polite">Cargando datos…</p>
{/if}
