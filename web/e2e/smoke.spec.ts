import { expect, test, type Page } from '@playwright/test';

const RUTAS = ['/', '/mapa', '/flujo', '/comparar', '/deuda', '/contratos', '/cumplimiento', '/movimientos', '/glosario', '/acerca', '/fuentes'];

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
  for (const ruta of ['/', '/mapa', '/flujo', '/comparar', '/deuda', '/contratos', '/cumplimiento']) {
    await page.goto(ruta);
    await page.waitForLoadState('networkidle');
    const fuentes = page.locator('.fuente a[href^="https://"]');
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

test('cada cifra clave explica de dónde sale y enlaza a la copia archivada', async ({ page, request }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  const origen = page.locator('details.origen').first();
  await origen.locator('> summary').click();
  await expect(origen).toContainText('Devengado');
  const det = origen.locator('details.det').first();
  await det.locator('> summary').click();
  const copia = await det.locator('a[download]').first().getAttribute('href');
  expect(copia).toMatch(/^\/data\/originales\//);
  const r = await request.get(copia!);
  expect(r.status()).toBe(200);
  expect(r.headers()['content-disposition']).toContain('attachment');
});

test('la página de fuentes lista documentos y verificaciones', async ({ page }) => {
  await page.goto('/fuentes');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('.checks li').first()).toBeVisible();
  expect(await page.locator('.docs li.doc').count()).toBeGreaterThan(10);
  await page.getByPlaceholder(/Buscar por título/).fill('deuda');
  await expect(page.locator('.docs li.doc').first()).toContainText(/[Dd]euda/);
});

test('cada contrato enlaza a su documento oficial', async ({ page }) => {
  await page.goto('/contratos');
  await page.waitForLoadState('networkidle');
  const enlace = page.locator('section[aria-labelledby="h-todos"] table.data tbody tr').first().locator('a[href^="https://"]', { hasText: 'Documento oficial' });
  await expect(enlace).toHaveCount(1);
});

test('contratos muestra patrones para revisar y filtra por dependencia', async ({ page }) => {
  await page.goto('/contratos?m=monterrey');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('#h-revisar')).toBeVisible();
  await expect(page.locator('.revisar')).toContainText('no indican irregularidades');
  await page.goto('/contratos?m=monterrey&dep=secretaria-de-servicios-publicos');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('.filtro-dep')).toContainText('Secretaría de Servicios Públicos');
});

test('el panel de una dependencia muestra sus contratos', async ({ page }) => {
  await page.goto('/mapa?m=monterrey&n=secretaria-de-servicios-publicos');
  await page.waitForLoadState('networkidle');
  const bloque = page.locator('aside.panel .contratos');
  await expect(bloque).toContainText('Contratos de esta dependencia');
  await expect(bloque.locator('a[href*="dep=secretaria-de-servicios-publicos"]')).toHaveCount(1);
});

test('flujo compara con el año anterior y muestra la dependencia federal', async ({ page }) => {
  await page.goto('/flujo?m=monterrey');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('#h-cambios')).toContainText(/más|menos/);
  await expect(page.locator('table.comparacion tbody tr').first()).toBeVisible();
  await expect(page.locator('#h-autonomia')).toContainText('De cada $100');
});

test('¿se cumple? muestra lo que quedó sin gastar y una pregunta lista para copiar', async ({ page }) => {
  await page.goto('/cumplimiento?m=san-pedro');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('#h-sin-gastar')).toHaveText(/Obra pública: .* sin gastar, 47% de su presupuesto final/);
  await expect(page.locator('#h-ritmo')).toBeVisible();
  const primera = page.locator('.preguntas li').first();
  await expect(primera.locator('blockquote')).toContainText('¿qué programas, obras o compras');
  await expect(primera.getByRole('button', { name: 'Copiar pregunta' })).toBeVisible();
  await expect(page.locator('a[href="https://www.plataformadetransparencia.org.mx/"]')).toHaveCount(1);
});

test('el panel del mapa dice cómo cerró el año', async ({ page }) => {
  await page.goto('/mapa?m=monterrey&n=secretaria-de-servicios-publicos');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('aside.panel .cerro')).toContainText(/Cómo cerró \d{4}: gastó \d+%/);
});

test('el menú tiene 7 secciones y el pie enlaza a movimientos y fuentes', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('nav.nav a')).toHaveCount(7);
  await page.locator('footer a', { hasText: 'Movimientos recientes' }).click();
  await expect(page.locator('h1')).toContainText('Movimientos');
  await page.locator('footer a', { hasText: 'Fuentes y verificación' }).click();
  await expect(page.locator('h1')).toContainText('Fuentes');
});
