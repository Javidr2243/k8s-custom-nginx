import { describe, expect, it } from 'vitest';
import { buscar, normalizar, puntuar, type Resultado } from './search';

const indice: Resultado[] = [
  { tipo: 'dependencia', titulo: 'Secretaría de Seguridad y Protección Ciudadana', detalle: 'Monterrey', href: '/a' },
  { tipo: 'dependencia', titulo: 'Tesorería Municipal', detalle: 'Monterrey', href: '/b' },
  { tipo: 'proveedor', titulo: 'Seguros Atlas', detalle: 'San Pedro', href: '/c' },
  { tipo: 'termino', titulo: 'Presidente', detalle: '', href: '/d' },
];

describe('search', () => {
  it('ignores accents and case', () => {
    expect(normalizar('Tesorería MUNICIPAL')).toBe('tesoreria municipal');
    expect(puntuar('tesoreria', 'Tesorería Municipal')).toBe(80);
  });
  it('ranks word starts above loose matches', () => {
    const r = buscar('segur', indice);
    expect(r.map((x) => x.href)).toEqual(['/c', '/a']);
  });
  it('does not return unrelated rows (the CivLab "treas" problem)', () => {
    expect(buscar('treas', indice)).toEqual([]);
    expect(buscar('seguridad', indice)[0]?.href).toBe('/a');
  });
  it('needs at least two characters', () => {
    expect(buscar('s', indice)).toEqual([]);
  });
});
