const { test, expect, createUser, login } = require('../helpers');

test('creates a rental and records payment from the yearly dashboard', async ({ page, request }) => {
  const owner = await createUser(request);
  const propertyName = `Casa ${owner.username}`;
  const tenantName = `tenant_${owner.username}`;
  await login(page, owner);

  await page.getByRole('button', { name: 'Properties', exact: true }).click();
  await page.locator('#property-name').fill(propertyName);
  await page.locator('#property-address').fill('Calle de Prueba 12');
  await page.getByRole('button', { name: 'Create property', exact: true }).click();
  await expect(page.getByRole('heading', { name: propertyName, exact: true })).toBeVisible();

  await page.locator('#room-property-select').selectOption({ label: propertyName });
  await page.locator('#room-name').fill('Cuarto del patio');
  await page.locator('#room-default-amount').fill('5000');
  await page.locator('#room-default-pay-day').fill('5');
  await page.locator('#room-default-duration').fill('3');
  await page.getByRole('button', { name: 'Create room', exact: true }).click();
  await expect(page.locator('#message')).toHaveText('Room created: Cuarto del patio');

  await page.getByRole('button', { name: 'Tenants', exact: true }).click();
  await page.locator('#tenant-username').fill(tenantName);
  await page.locator('#tenant-email').fill(`${tenantName}@example.invalid`);
  await page.getByRole('button', { name: 'Create tenant', exact: true }).click();
  await expect(page.locator('#tenant-list')).toContainText(tenantName);
  await page.locator('#contract-tenant-select').selectOption({ label: `${tenantName} (${tenantName}@example.invalid)` });
  await page.locator('#contract-room-select').selectOption({ label: `${propertyName} / Cuarto del patio` });
  await expect(page.locator('#contract-amount')).toHaveValue('5000');
  await expect(page.locator('#contract-pay-day')).toHaveValue('5');
  await expect(page.locator('#contract-duration')).toHaveValue('3');
  await page.locator('#contract-start-year').fill('2030');
  await page.locator('#contract-start-month').fill('11');
  const created = page.waitForResponse(r => r.url().endsWith('/api/contracts') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create contract', exact: true }).click();
  const response = await created;
  expect(response.ok()).toBeTruthy();
  const contract = await response.json();
  await expect(page.locator('#message')).toHaveText('Contract created — 3 months');
  await expect(page.locator(`#contract-room-select option[value="${contract.room_id}"]`)).toHaveCount(0);

  await page.getByRole('button', { name: 'Dashboard', exact: true }).click();
  await page.locator('#overview-year').fill('2030');
  await page.getByRole('button', { name: 'Load', exact: true }).click();
  const row = page.locator('#year-grid tr').filter({ has: page.getByRole('cell', { name: propertyName, exact: true }) });
  const november = row.locator('[data-month="11"]');
  await expect(november).toHaveClass(/dot-unpaid/);
  await november.click();
  page.once('dialog', dialog => dialog.accept('5000'));
  await page.getByRole('button', { name: 'mark paid', exact: true }).click();
  await expect(november).toHaveClass(/dot-paid/);

  // Reload data through the UI to verify the change was persisted.
  await page.reload();
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await page.locator('#login-select').selectOption(String(owner.id));
  await page.getByRole('button', { name: 'Login →', exact: true }).click();
  await page.locator('#overview-year').fill('2030');
  await page.getByRole('button', { name: 'Load', exact: true }).click();
  await expect(november).toHaveClass(/dot-paid/);
});

test('requires an admin selection before entering the dashboard', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Ingresar →', exact: true }).click();
  await expect(page.locator('#message')).toHaveText('Selecciona un admin.');
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await page.getByRole('button', { name: 'Login →', exact: true }).click();
  await expect(page.locator('#message')).toHaveText('Select an admin.');
  await expect(page.locator('#main-nav')).toBeHidden();
});

test('rejects a blank property name without creating a record', async ({ page, request, rental }) => {
  await login(page, rental.owner);
  await page.getByRole('button', { name: 'Properties', exact: true }).click();
  const before = await (await request.get('/api/properties')).json();
  await page.locator('#property-address').fill('Calle 5');
  await page.getByRole('button', { name: 'Create property', exact: true }).click();
  expect(await page.locator('#property-name').evaluate(el => el.validity.valueMissing)).toBe(true);
  expect(await (await request.get('/api/properties')).json()).toEqual(before);
});

test('shows a failed property request and keeps the form available for retry', async ({ page, rental }) => {
  await login(page, rental.owner);
  await page.getByRole('button', { name: 'Properties', exact: true }).click();
  await page.route('**/api/properties', route => {
    if (route.request().method() === 'POST') return route.abort('failed');
    return route.continue();
  });
  await page.locator('#property-name').fill('Casa sin conexión');
  await page.locator('#property-address').fill('Calle 5');
  await page.getByRole('button', { name: 'Create property', exact: true }).click();
  await expect(page.locator('#message')).toHaveText('Failed to create property.');
  await expect(page.locator('#property-name')).toHaveValue('Casa sin conexión');
});

test('switches to Spanish and logs out', async ({ page, rental }) => {
  await login(page, rental.owner);
  await page.locator('#lang-btn').click();
  await expect(page.getByRole('button', { name: 'Propiedades', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Salir', exact: true }).click();
  await expect(page.locator('#login-section')).toBeVisible();
  await expect(page.locator('#main-nav')).toBeHidden();
});
