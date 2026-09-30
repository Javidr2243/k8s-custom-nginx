// Number and date formatting for Mexican Spanish. Amounts are nominal pesos.

const int = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 });
const one = new Intl.NumberFormat('es-MX', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pct0 = new Intl.NumberFormat('es-MX', { style: 'percent', maximumFractionDigits: 0 });
const pct1 = new Intl.NumberFormat('es-MX', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 });

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

/** "$6,027.6 millones", "$845,300" or "Sin dato". */
export function pesos(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return 'Sin dato';
  const sign = n < 0 ? '−' : '';
  const a = Math.abs(n);
  if (a >= 1e6) return `${sign}$${one.format(a / 1e6)} millones`;
  return `${sign}$${int.format(a)}`;
}

/** Short form for axes and tight spaces: "$6,028 M", "$845 mil". */
export function pesosCorto(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const sign = n < 0 ? '−' : '';
  const a = Math.abs(n);
  if (a >= 1e6) return `${sign}$${int.format(a / 1e6)} M`;
  if (a >= 1e3) return `${sign}$${int.format(a / 1e3)} mil`;
  return `${sign}$${int.format(a)}`;
}

/** Whole pesos with separators: "$1,457,039,380". */
export function pesosExactos(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return 'Sin dato';
  return `${n < 0 ? '−' : ''}$${int.format(Math.abs(n))}`;
}

export function porcentaje(x: number | null | undefined, decimales = 0): string {
  if (x === null || x === undefined || Number.isNaN(x)) return 'Sin dato';
  return (decimales ? pct1 : pct0).format(x);
}

/** Signed change: "+34 %", "−22 %". */
export function cambio(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return 'Sin dato';
  const s = pct0.format(Math.abs(x));
  return x > 0 ? `+${s}` : x < 0 ? `−${s}` : s;
}

export function entero(n: number | null | undefined): string {
  if (n === null || n === undefined) return 'Sin dato';
  return int.format(n);
}

/** "2026-06-30" → "30 de junio de 2026". */
export function fecha(iso: string | null | undefined): string {
  if (!iso) return 'Sin fecha';
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m) return iso;
  return d ? `${d} de ${MESES[m - 1]} de ${y}` : `${MESES[m - 1]} de ${y}`;
}

/** "2026T2" → "2º trimestre de 2026". */
export function trimestre(p: string): string {
  const q = Number(p.slice(-1));
  const ord = ['1er', '2º', '3er', '4º'][q - 1] ?? `${q}º`;
  return `${ord} trimestre de ${p.slice(0, 4)}`;
}

/** "2026T2" → "enero–junio 2026" (the figures are cumulative from January). */
export function acumulado(p: string): string {
  const q = Number(p.slice(-1));
  return `enero–${MESES[q * 3 - 1]} ${p.slice(0, 4)}`;
}

/** "2026T2" → "ene–jun 2026". */
export function acumuladoCorto(p: string): string {
  const q = Number(p.slice(-1));
  return `ene–${MESES[q * 3 - 1]!.slice(0, 3)} ${p.slice(0, 4)}`;
}
