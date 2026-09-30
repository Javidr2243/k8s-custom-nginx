// CSV export. Cells starting with = + - @ (or tab/CR) are prefixed with an apostrophe so a spreadsheet
// never runs them as formulas (CSV/formula injection).

export function celdaSegura(v: unknown): string {
  let s = v === null || v === undefined ? '' : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n\r;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function aCsv(encabezados: string[], filas: unknown[][]): string {
  return [encabezados, ...filas].map((f) => f.map(celdaSegura).join(',')).join('\r\n');
}

export function descargar(nombre: string, contenido: string): void {
  const blob = new Blob(['﻿', contenido], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
