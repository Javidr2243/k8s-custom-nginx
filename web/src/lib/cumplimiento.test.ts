import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { Egresos, Montos } from "./data";
import { cierre, fila, hallazgos, ritmo } from "./cumplimiento";

const real = (m: string) =>
  JSON.parse(
    readFileSync(
      new URL(`../../../data/public/v1/egresos/${m}.json`, import.meta.url),
      "utf8",
    ),
  ) as Egresos;

const montos = (
  aprobado: number | null,
  modificado: number | null,
  devengado: number | null,
): Montos => ({
  aprobado,
  ampliaciones: null,
  modificado,
  devengado,
  pagado: null,
  subejercicio: null,
});

describe("cumplimiento", () => {
  it("fila: unspent, execution and change after approval; guards against missing values and zero", () => {
    const f = fila("6000", "Obra pública", montos(100, 150, 120));
    expect(f.sinGastar).toBe(30);
    expect(f.ejecucion).toBeCloseTo(0.8);
    expect(f.cambioTrasAprobar).toBeCloseTo(0.5);
    const z = fila("x", "x", montos(0, 0, 0));
    expect(z.ejecucion).toBeNull();
    expect(z.cambioTrasAprobar).toBeNull();
    expect(fila("x", "x", montos(null, 10, null)).sinGastar).toBeNull();
    expect(fila("x", "x", montos(10, 10, 12)).sinGastar).toBe(0); // overspending is not negative «unspent»
  });

  it("cierre: last published 4th quarter; null when the year has no close", () => {
    const sp = real("san-pedro");
    const c = cierre(sp)!;
    expect(c.anio).toBe(2025);
    const obra = c.capitulos.find((x) => x.id === "6000")!;
    expect(Math.round(obra.ejecucion! * 100)).toBe(53); // checked by hand against the JSON
    expect(cierre(sp, 2024)).toBeNull(); // San Pedro did not publish 2024T4
    expect(cierre(real("monterrey"))!.dependencias?.length).toBeGreaterThan(5);
  });

  it("ritmo: compares with the same quarter of the previous year", () => {
    const r = ritmo(real("monterrey"))!;
    expect(r.periodo).toBe("2026T2");
    expect(r.anterior).toBe("2025T2");
    const obra = r.capitulos.find((x) => x.id === "6000")!;
    expect(obra.diferencia).toBeCloseTo(obra.actual! - obra.previo!);
    expect(ritmo(real("monterrey"), "2025T4")).toBeNull(); // a close is not «so far»
  });

  it("hallazgos: at most one per kind, ordered unspent → change → pace, with a ready question", () => {
    const e = real("san-pedro");
    const h = hallazgos(cierre(e), ritmo(e), "San Pedro Garza García");
    expect(h[0]?.tipo).toBe("sin-gastar");
    expect(h[0]?.id).toBe("6000");
    expect(new Set(h.map((x) => x.tipo)).size).toBe(h.length);
    for (const x of h) expect(x.pregunta).toMatch(/^¿|^Del/);
    expect(hallazgos(null, null, "X")).toEqual([]);
  });
});
