// Minimal History API router. The selected municipality (?m=) and period (?p=) live in the URL,
// so every view can be shared as a link.

import { esMunicipio, type MunicipioId } from './data';

class Route {
  path = $state(location.pathname);
  search = $state(location.search);

  get params(): URLSearchParams {
    return new URLSearchParams(this.search);
  }
  get municipio(): MunicipioId {
    const m = this.params.get('m');
    return esMunicipio(m) ? m : 'monterrey';
  }
  get periodo(): string | null {
    const p = this.params.get('p');
    return p && /^\d{4}T[1-4]$/.test(p) ? p : null;
  }
}

export const route = new Route();

function sync(): void {
  route.path = location.pathname;
  route.search = location.search;
}

window.addEventListener('popstate', sync);

export function navigate(url: string, opts: { replace?: boolean } = {}): void {
  const target = new URL(url, location.href);
  if (target.origin !== location.origin) {
    location.href = target.href;
    return;
  }
  const samePath = target.pathname === location.pathname;
  history[opts.replace ? 'replaceState' : 'pushState'](null, '', target.pathname + target.search + target.hash);
  sync();
  if (!samePath && !target.hash) {
    window.scrollTo(0, 0);
    // Move focus to the new content for screen-reader and keyboard users.
    queueMicrotask(() => document.getElementById('contenido')?.focus({ preventScroll: true }));
  }
}

/** Update query parameters without adding a history entry. */
export function setQuery(values: Record<string, string | null>): void {
  const params = new URLSearchParams(location.search);
  for (const [k, v] of Object.entries(values)) {
    if (v === null) params.delete(k);
    else params.set(k, v);
  }
  const qs = params.toString();
  navigate(location.pathname + (qs ? `?${qs}` : ''), { replace: true });
}

/** Build an internal link that keeps the current municipality/period. */
export function href(path: string, extra: Record<string, string | null> = {}): string {
  const params = new URLSearchParams();
  const cur = new URLSearchParams(route.search);
  for (const k of ['m', 'p']) {
    const v = cur.get(k);
    if (v) params.set(k, v);
  }
  for (const [k, v] of Object.entries(extra)) {
    if (v === null) params.delete(k);
    else params.set(k, v);
  }
  const qs = params.toString();
  return path + (qs ? `?${qs}` : '');
}

/** Svelte action: intercept clicks on internal links (<a use:link href="/…">). */
export function link(node: HTMLAnchorElement): { destroy(): void } {
  const onClick = (e: MouseEvent) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const url = new URL(node.href, location.href);
    if (url.origin !== location.origin || node.target === '_blank' || url.pathname.startsWith('/data/')) return;
    e.preventDefault();
    navigate(url.pathname + url.search + url.hash);
  };
  node.addEventListener('click', onClick);
  return { destroy: () => node.removeEventListener('click', onClick) };
}
