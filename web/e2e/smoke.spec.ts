import { expect, test, type Page } from '@playwright/test';

const RUTAS = ['/', '/mapa', '/flujo', '/comparar', '/deuda', '/contratos', '/movimientos', '/glosario', '/acerca'];

/** Collect CSP violations and console errors for the page. */
async function vigilar(page: Page) {
  const problemas: string[] = [];
  await page.addInitScript(() => {
    document.addEventListener('securitypolicyviolation', (e) => {
      (window as unknown as { __csp: string[] }).__csp ??= [];
      (window as unknown as { __csp: string[] }).__csp.push(`${e.violatedDirective} ${e.blockedURI}`);
    });
  });
  page.on('console', (m) => {
    if (m.type() === 'error') problemas.push(m.text());
  });
  page.on('pageerror', (e) => problemas.push(e.message));
  return async () => {
    const csp = await page.evaluate(() => (window as unknown as { __csp?: string[] }).__csp ?? []);
    return [...problemas, ...csp.map((c) => `CSP: ${c}`)];
  };
}

for (const ruta of RUTAS) {
  test(`carga ${ruta} sin errores ni violaciones de CSP`, async ({ page }) => {
    const revisar = await vigilar(page);
    await page.goto(ruta);
    await expect(page.locator('h1')).toBeVisible();
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('No se pudieron cargar los datos')).toHaveCount(0);
    expect(await revisar()).toEqual([]);
    // No horizontal scroll on the page itself.
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

test('cada vista con cifras enlaza a su fuente', async ({ page }) => {
  for (const ruta of ['/', '/mapa', '/flujo', '/comparar', '/deuda', '/contratos']) {
    await page.goto(ruta);
    await page.waitForLoadState('networkidle');
    const fuentes = page.locator('p.fuente a[href^="https://"]');
    expect(await fuentes.count(), ruta).toBeGreaterThan(0);
  }
});

test('el mapa abre el panel al elegir una dependencia', async ({ page }) => {
  await page.goto('/mapa?m=monterrey');
  await page.waitForLoadState('networkidle');
  const nodo = page.locator('g.node.gasto').first();
  await nodo.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('aside.panel h2')).toBeVisible();
  await expect(page.locator('aside.panel')).toContainText('Aprobado');
  expect(page.url()).toContain('n=');
});

test('la búsqueda encuentra Seguridad', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Buscar/ }).click();
  await page.getByPlaceholder(/Busca una dependencia/).fill('seguridad');
  await expect(page.locator('dialog a').filter({ hasText: /Seguridad/ }).first()).toBeVisible();
});

test('el glosario explica "devengado"', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.locator('.termino button').first().click();
  await expect(page.locator('.termino .pop')).toBeVisible();
});

test('cambiar de municipio actualiza la URL y el título', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('radio', { name: /San Pedro/ }).click();
  await expect(page.locator('h1')).toContainText('San Pedro');
  expect(page.url()).toContain('m=san-pedro');
});
