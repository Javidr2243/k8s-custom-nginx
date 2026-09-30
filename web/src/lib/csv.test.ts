import { describe, expect, it } from 'vitest';
import { aCsv, celdaSegura } from './csv';

describe('csv', () => {
  it('neutralises spreadsheet formulas', () => {
    expect(celdaSegura('=HYPERLINK("http://x")')).toBe(`"'=HYPERLINK(""http://x"")"`);
    expect(celdaSegura('+52 81')).toBe("'+52 81");
    expect(celdaSegura('-5')).toBe("'-5");
    expect(celdaSegura('@SUM(A1)')).toBe("'@SUM(A1)");
  });
  it('quotes separators', () => {
    expect(celdaSegura('A, B')).toBe('"A, B"');
    expect(aCsv(['a', 'b'], [[1, null]])).toBe('a,b\r\n1,');
  });
});
