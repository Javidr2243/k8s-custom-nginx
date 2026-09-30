// Was the budget spent as promised? Year-end execution (devengado ÷ final budget), how much the budget changed after
// approval, and this year's pace against the same quarter of last year. Pure functions over the published egresos.
import type { Egresos, Montos, PeriodoEgresos } from "./data";
import { CAPITULOS, sencillo } from "./capitulos";

export interface FilaCierre {
  id: string;
  nombre: string;
  aprobado: number | null;
  modificado: number | null;
  devengado: number | null;
  /** Final budget − devengado (never below zero); null when either is missing. */
  sinGastar: number | null;
  /** devengado ÷ final budget; null without a final budget. */
  ejecucion: number | null;
  /** (final − approved) ÷ approved; null without an approved amount. */
  cambioTrasAprobar: number | null;
}

export interface Cierre {
  anio: number;
  periodo: string;
  fuente: string;
  fuenteDependencias: string | null;
  total: FilaCierre;
  capitulos: FilaCierre[];
  dependencias: FilaCierre[] | null;
}

export function fila(id: string, nombre: string, m: Montos): FilaCierre {
  const { aprobado, modificado, devengado } = m;
  return {
    id,
    nombre,
    aprobado,
    modificado,
    devengado,
    sinGastar:
      modificado != null && devengado != null
        ? Math.max(0, modificado - devengado)
        : null,
    ejecucion: modificado && devengado != null ? devengado / modificado : null,
    cambioTrasAprobar:
      aprobado && modificado != null
        ? (modificado - aprobado) / aprobado
        : null,
  };
}

function filas(p: PeriodoEgresos) {
  return {
    total: fila("total", "Todo el presupuesto", p.total),
    capitulos: p.capitulos.map((c) =>
      fila(
        c.clave,
        CAPITULOS[c.clave] ? sencillo(c.clave) : c.nombre,
        c.montos,
      ),
    ),
    dependencias:
      p.dependencias?.map((d) => fila(d.id, d.nombre, d.montos)) ?? null,
  };
}

/** Years with a published 4th-quarter report (the year's close), oldest first. */
export const aniosCerrados = (egr: Egresos) =>
  egr.periodos
    .filter((p) => p.periodo.endsWith("T4"))
    .map((p) => Number(p.periodo.slice(0, 4)));

/** How the year closed (4th-quarter report, accumulated Jan–Dec). Null when that report is not published. */
export function cierre(egr: Egresos, anio?: number): Cierre | null {
  const a = anio ?? aniosCerrados(egr).at(-1);
  const p = egr.periodos.find((x) => x.periodo === `${a}T4`);
  if (!p || a === undefined) return null;
  return {
    anio: a,
    periodo: p.periodo,
    fuente: p.fuente,
    fuenteDependencias: p.fuente_dependencias,
    ...filas(p),
  };
}

export interface FilaRitmo {
  id: string;
  nombre: string;
  modificado: number | null;
  devengado: number | null;
  actual: number | null;
  previo: number | null;
  /** actual − previo, in percentage points ×1 (0.2 = 20 points). */
  diferencia: number | null;
}

export interface Ritmo {
  periodo: string;
  anterior: string;
  fuente: string;
  fuenteDependencias: string | null;
  total: FilaRitmo;
  capitulos: FilaRitmo[];
  dependencias: FilaRitmo[] | null;
}

/**
 * This year's execution so far against the same quarter of last year, row by row. Comparing each row with its own
 * pattern avoids penalising normal seasonality (e.g. public works are usually paid late in the year).
 */
export function ritmo(egr: Egresos, periodo?: string): Ritmo | null {
  const p = periodo
    ? egr.periodos.find((x) => x.periodo === periodo)
    : egr.periodos.at(-1);
  if (!p || p.periodo.endsWith("T4")) return null;
  const anterior = `${Number(p.periodo.slice(0, 4)) - 1}${p.periodo.slice(4)}`;
  const q = egr.periodos.find((x) => x.periodo === anterior);
  if (!q) return null;
  const hoy = filas(p);
  const antes = filas(q);
  const unir = (xs: FilaCierre[], ys: FilaCierre[] | null): FilaRitmo[] =>
    xs.map((x) => {
      const y = ys?.find((z) => z.id === x.id);
      const previo = y?.ejecucion ?? null;
      return {
        id: x.id,
        nombre: x.nombre,
        modificado: x.modificado,
        devengado: x.devengado,
        actual: x.ejecucion,
        previo,
        diferencia:
          x.ejecucion != null && previo != null ? x.ejecucion - previo : null,
      };
    });
  return {
    periodo: p.periodo,
    anterior,
    fuente: p.fuente,
    fuenteDependencias: p.fuente_dependencias,
    total: unir([hoy.total], [antes.total])[0]!,
    capitulos: unir(hoy.capitulos, antes.capitulos),
    dependencias: hoy.dependencias
      ? unir(hoy.dependencias, antes.dependencias)
      : null,
  };
}

/** Rows at least this many points behind their own pace of last year are highlighted. */
export const UMBRAL_RITMO = 0.15;
/** Rows smaller than this share of the budget are left out of the findings (tiny items swing wildly). */
export const MINIMO_PESO = 0.01;
/** A year-end «unspent» finding needs at least this share of the final budget left over. */
export const MINIMO_SIN_GASTAR = 0.1;

export interface Hallazgo {
  tipo: "sin-gastar" | "cambio" | "ritmo";
  id: string;
  nombre: string;
  /** The finding in figures, no adjectives. */
  titular: string;
  /** A neutral question ready to paste into an information request. */
  pregunta: string;
  fuente: string;
}

const mill = (n: number) =>
  `$${(n / 1e6).toLocaleString("es-MX", { maximumFractionDigits: 0 })} millones`;
const pct = (x: number) => `${Math.round(x * 100)}%`;

/** The three most useful findings: largest unspent amount, largest change after approval, furthest behind pace. */
export function hallazgos(
  c: Cierre | null,
  r: Ritmo | null,
  municipio: string,
): Hallazgo[] {
  const out: Hallazgo[] = [];
  if (c) {
    const base = c.total.modificado ?? 0;
    const pesa = (f: FilaCierre) => (f.modificado ?? 0) >= base * MINIMO_PESO;
    const sin = c.capitulos
      .filter(
        (f) =>
          pesa(f) &&
          f.sinGastar &&
          f.ejecucion != null &&
          f.ejecucion <= 1 - MINIMO_SIN_GASTAR,
      )
      .sort((a, b) => b.sinGastar! - a.sinGastar!)[0];
    if (sin && sin.ejecucion != null)
      out.push({
        tipo: "sin-gastar",
        id: sin.id,
        nombre: sin.nombre,
        titular: `${sin.nombre}: ${mill(sin.sinGastar!)} sin gastar en ${c.anio} (${pct(1 - sin.ejecucion)} de su presupuesto final)`,
        pregunta: `Del presupuesto de ${sin.nombre.toLowerCase()} de ${c.anio} del municipio de ${municipio}, ¿qué programas, obras o compras previstas no se ejercieron, por qué motivo y en qué se utilizarán esos recursos?`,
        fuente: c.fuente,
      });
    const cam = c.capitulos
      .filter((f) => pesa(f) && f.cambioTrasAprobar != null)
      .sort(
        (a, b) =>
          Math.abs(b.cambioTrasAprobar!) - Math.abs(a.cambioTrasAprobar!),
      )[0];
    if (cam && Math.abs(cam.cambioTrasAprobar!) >= 0.1)
      out.push({
        tipo: "cambio",
        id: cam.id,
        nombre: cam.nombre,
        titular: `${cam.nombre}: el presupuesto de ${c.anio} ${cam.cambioTrasAprobar! > 0 ? "subió" : "bajó"} ${pct(Math.abs(cam.cambioTrasAprobar!))} después de aprobarse`,
        pregunta: `¿Qué modificaciones se hicieron en ${c.anio} al presupuesto de ${cam.nombre.toLowerCase()} del municipio de ${municipio} después de su aprobación, quién las autorizó, de dónde salieron o a dónde se destinaron los recursos y en qué acta de cabildo constan?`,
        fuente: c.fuente,
      });
  }
  if (r) {
    const base = r.total.modificado ?? 0;
    const lenta = r.capitulos
      .filter(
        (f) =>
          (f.modificado ?? 0) >= base * MINIMO_PESO &&
          f.diferencia != null &&
          f.diferencia <= -UMBRAL_RITMO,
      )
      // Money behind pace, so a large budget a little behind outranks a tiny one far behind.
      .sort(
        (a, b) =>
          a.diferencia! * (a.modificado ?? 0) -
          b.diferencia! * (b.modificado ?? 0),
      )[0];
    if (lenta)
      out.push({
        tipo: "ritmo",
        id: lenta.id,
        nombre: lenta.nombre,
        titular: `${lenta.nombre}: ${pct(lenta.actual!)} gastado al ${r.periodo.slice(-1)}º trimestre de ${r.periodo.slice(0, 4)}, contra ${pct(lenta.previo!)} un año antes`,
        pregunta: `¿Cuál es el calendario de ejecución de ${lenta.nombre.toLowerCase()} para ${r.periodo.slice(0, 4)} en el municipio de ${municipio}, qué avance lleva y por qué va más lento que en el mismo periodo de ${Number(r.periodo.slice(0, 4)) - 1}?`,
        fuente: r.fuente,
      });
  }
  return out;
}
