<script lang="ts">
  // "Ver como tabla": every chart has a table with the same data (accessibility and verification).
  let {
    titulo,
    columnas,
    filas,
    alinearDerecha = [],
  }: { titulo: string; columnas: string[]; filas: (string | number)[][]; alinearDerecha?: number[] } = $props();
</script>

<details class="tabla">
  <summary>Ver como tabla</summary>
  <div class="table-wrap">
    <table class="data">
      <caption class="sr-only">{titulo}</caption>
      <thead>
        <tr>
          {#each columnas as c, i (i)}<th scope="col" class:r={alinearDerecha.includes(i)}>{c}</th>{/each}
        </tr>
      </thead>
      <tbody>
        {#each filas as f, j (j)}
          <tr>
            {#each f as v, i (i)}
              {#if i === 0}<th scope="row">{v}</th>{:else}<td class:r={alinearDerecha.includes(i)}>{v}</td>{/if}
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</details>

<style>
  .tabla {
    margin-top: 0.75rem;
  }
  summary {
    cursor: pointer;
    color: var(--link);
    min-height: 44px;
    display: flex;
    align-items: center;
    width: max-content;
  }
  th[scope='row'] {
    font-weight: 500;
    color: var(--ink);
  }
</style>
