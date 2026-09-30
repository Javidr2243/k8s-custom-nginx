import { describe, expect, it } from 'vitest';
import { acumulado, cambio, fecha, pesos, pesosCorto, trimestre } from './format';

describe('format', () => {
  it('pesos', () => {
    expect(pesos(6_027_598_288.12)).toBe('$6,027.6 millones');
    expect(pesos(845_300)).toBe('$845,300');
    expect(pesos(-205_900_000)).toBe('−$205.9 millones');
    expect(pesos(null)).toBe('Sin dato');
  });
  it('pesosCorto', () => {
    expect(pesosCorto(6_027_598_288)).toBe('$6,028 M');
    expect(pesosCorto(45_000)).toBe('$45 mil');
  });
  it('cambio', () => {
    expect(cambio(0.34)).toMatch(/^\+34\s?%$/);
    expect(cambio(-0.22)).toMatch(/^−22\s?%$/);
    expect(cambio(null)).toBe('Sin dato');
  });
  it('fechas y periodos', () => {
    expect(fecha('2026-06-30')).toBe('30 de junio de 2026');
    expect(trimestre('2026T2')).toBe('2º trimestre de 2026');
    expect(acumulado('2026T2')).toBe('enero–junio 2026');
  });
});
