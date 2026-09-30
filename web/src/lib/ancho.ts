/** Svelte action: sets an element's width to a fraction (0–1) via the CSSOM, since the CSP forbids inline styles. */
export function ancho(el: HTMLElement, fraccion: number) {
  const set = (x: number) => {
    el.style.width = `${Math.max(0, Math.min(1, x)) * 100}%`;
  };
  set(fraccion);
  return { update: set };
}
