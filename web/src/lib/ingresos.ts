// Annual money flow (INEGI EFIPEM): groups used by the flow diagram, year-over-year comparison and how much of the
// municipality's income it raises itself versus what comes from the federal government.
import type { Ingresos } from './data';

export type AnioIngresos = Ingresos['anual'][number];

/** Where the money comes from: [id, label, EFIPEM revenue keys]. */
export const FUENTES: [string, string, string[]][] = [
  ['impuestos', 'Impuestos locales (predial…)', ['impuestos']],
  ['otros-propios', 'Derechos, multas y otros', ['derechos', 'productos', 'aprovechamientos', 'contribuciones-de-mejoras', 'otros', 'por-cuenta-de-terceros']],
  ['participaciones', 'Participaciones federales', ['participaciones']],
  ['aportaciones', 'Aportaciones (fondos federales)', ['aportaciones']],
  ['financiamiento', 'Préstamos (deuda nueva)', ['financiamiento']],
  ['caja-inicial', 'Dinero en caja del año anterior', ['disponibilidad-inicial']],
];

/** Where it goes: [id, label, EFIPEM spending keys (capítulos)]. */
export const DESTINOS: [string, string, string[]][] = [
  ['sueldos', 'Sueldos y prestaciones', ['1000']],
  ['servicios', 'Servicios (luz, limpia, rentas…)', ['3000']],
  ['materiales', 'Materiales y combustible', ['2000']],
  ['apoyos', 'Apoyos y subsidios', ['4000']],
  ['obra', 'Obra pública', ['6000']],
  ['deuda', 'Pago de deuda', ['9000']],
  ['otros', 'Equipo, reservas y otros', ['5000', '7000', '8000', 'otros', 'por-cuenta-de-terceros']],
  ['caja-final', 'Queda en caja al cierre', ['disponibilidad-final']],
];

/** Revenue the municipality raises itself, and transfers from the federal government. */
export const PROPIOS = ['impuestos', 'contribuciones-de-mejoras', 'derechos', 'productos', 'aprovechamientos'];
export const FEDERALES = ['participaciones', 'aportaciones'];

export const suma = (rec: Record<string, number>, keys: string[]) => keys.reduce((s, k) => s + (rec[k] ?? 0), 0);

/**
 * Share of income raised by the municipality itself in a year: own ÷ (own + federal). Loans and cash carried over
 * from the previous year are left out (they are neither). Null when there is nothing to divide.
 */
export function autonomia(a: AnioIngresos): { propios: number; federales: number; pct: number | null } {
  const propios = suma(a.ingresos_rubro, PROPIOS);
  const federales = suma(a.ingresos_rubro, FEDERALES);
  const base = propios + federales;
  return { propios, federales, pct: base > 0 ? propios / base : null };
}

export interface FilaComparacion {
  id: string;
  etiqueta: string;
  lado: 'entrada' | 'salida';
  actual: number;
  anterior: number | null;
  /** Relative change; null without a previous year or when the previous amount was zero. */
  cambio: number | null;
}

/** Each flow group in `anio` next to the previous year (rows with money in either year). */
export function comparacion(anual: AnioIngresos[], anio: number): FilaComparacion[] {
  const a = anual.find((x) => x.anio === anio);
  if (!a) return [];
  const p = anual.find((x) => x.anio === anio - 1);
  const filas: FilaComparacion[] = [];
  const agregar = (grupos: [string, string, string[]][], lado: FilaComparacion['lado'], campo: 'ingresos_rubro' | 'egresos_capitulo') => {
    for (const [id, etiqueta, keys] of grupos) {
      const actual = suma(a[campo], keys);
      const anterior = p ? suma(p[campo], keys) : null;
      if (actual === 0 && !anterior) continue;
      filas.push({ id, etiqueta, lado, actual, anterior, cambio: anterior ? (actual - anterior) / anterior : null });
    }
  };
  agregar(FUENTES, 'entrada', 'ingresos_rubro');
  agregar(DESTINOS, 'salida', 'egresos_capitulo');
  return filas;
}
