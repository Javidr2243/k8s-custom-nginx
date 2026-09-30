// Accent- and case-insensitive search. Ranking: exact > starts with > word starts with > contains.

export interface Resultado {
  tipo: 'pagina' | 'dependencia' | 'capitulo' | 'proveedor' | 'contrato' | 'termino';
  titulo: string;
  detalle: string;
  href: string;
}

export function normalizar(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

export function puntuar(consulta: string, texto: string): number {
  const q = normalizar(consulta);
  const t = normalizar(texto);
  if (!q) return 0;
  if (t === q) return 100;
  if (t.startsWith(q)) return 80;
  if (t.split(/[\s,.;:()/-]+/).some((w) => w.startsWith(q))) return 60;
  if (t.includes(q)) return 40;
  // All words present in any order.
  const words = q.split(' ');
  if (words.length > 1 && words.every((w) => t.includes(w))) return 30;
  return 0;
}

export function buscar(consulta: string, indice: Resultado[], limite = 30): Resultado[] {
  if (normalizar(consulta).length < 2) return [];
  return indice
    .map((r) => ({ r, s: Math.max(puntuar(consulta, r.titulo), puntuar(consulta, r.detalle) * 0.5) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s || a.r.titulo.localeCompare(b.r.titulo, 'es'))
    .slice(0, limite)
    .map((x) => x.r);
}
