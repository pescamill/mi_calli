const { test: base, expect } = require('@playwright/test');
const { randomUUID } = require('node:crypto');

async function post(request, path, data) {
  const response = await request.post(`/api${path}`, { data });
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return response.json();
}

async function createUser(request, role = 'admin') {
  const username = `e2e_${role}_${randomUUID().slice(0, 8)}`;
  return post(request, '/users', {
    username, email: `${username}@example.invalid`, password: 'test-only', role,
  });
}

const test = base.extend({
  rental: async ({ request }, use) => {
    const owner = await createUser(request);
    const tenant = await createUser(request, 'tenant');
    const property = await post(request, '/properties', {
      name: `Casa ${owner.username}`, address: 'Calle de Prueba 12', owner_id: owner.id,
    });
    const room = await post(request, '/rooms', {
      property_id: property.id, name: 'Cuarto 1', default_amount: 5000,
      default_pay_day: 5, default_duration_months: 3,
    });
    const contractData = {
      room_id: room.id, tenant_id: tenant.id, start_year: 2030, start_month: 11,
      duration_months: 3, pay_day: 5, amount: 5000,
    };
    await use({ owner, tenant, property, room, contractData });
    // No delete endpoints exist for these entities. The disposable stack owns cleanup.
  },
});

async function login(page, owner) {
  await page.goto('/');
  await page.locator('#login-select').selectOption(String(owner.id));
  await page.getByRole('button', { name: 'Login →', exact: true }).click();
  await expect(page.locator('#current-admin-name')).toHaveText(owner.username);
}

module.exports = { test, expect, post, createUser, login };
