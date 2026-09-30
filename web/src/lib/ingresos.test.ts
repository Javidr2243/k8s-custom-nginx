import { describe, expect, it } from 'vitest';
import { autonomia, comparacion, type AnioIngresos } from './ingresos';

const anio = (a: number, rubros: Record<string, number>, caps: Record<string, number> = {}): AnioIngresos => ({
  anio: a,
  estatus: 'Cifras definitivas',
  egresos_total: null,
  gasto_total: null,
  ingresos_total: null,
  ingresos_rubro: rubros,
  egresos_capitulo: caps,
});

describe('ingresos', () => {
  it('autonomia: own ÷ (own + federal), loans and carried-over cash excluded', () => {
    const r = autonomia(
      anio(2025, { impuestos: 30, derechos: 5, productos: 3, aprovechamientos: 2, participaciones: 40, aportaciones: 20, financiamiento: 100, 'disponibilidad-inicial': 50 }),
    );
    expect(r.propios).toBe(40);
    expect(r.federales).toBe(60);
    expect(r.pct).toBeCloseTo(0.4);
    expect(autonomia(anio(2025, {})).pct).toBeNull();
  });

  it('comparacion: groups with the previous year and relative change', () => {
    const filas = comparacion(
      [anio(2024, { impuestos: 100, aportaciones: 0 }, { '1000': 50 }), anio(2025, { impuestos: 110, aportaciones: 20 }, { '1000': 40 })],
      2025,
    );
    const f = Object.fromEntries(filas.map((x) => [x.id, x]));
    expect(f.impuestos?.cambio).toBeCloseTo(0.1);
    expect(f.aportaciones?.anterior).toBe(0);
    expect(f.aportaciones?.cambio).toBeNull(); // nothing to compare against
    expect(f.sueldos?.lado).toBe('salida');
    expect(f.sueldos?.cambio).toBeCloseTo(-0.2);
    expect(f.financiamiento).toBeUndefined(); // no money in either year
    expect(comparacion([anio(2025, { impuestos: 1 })], 2025)[0]?.anterior).toBeNull();
  });
});
