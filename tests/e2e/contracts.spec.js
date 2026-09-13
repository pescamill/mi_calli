const { test, expect, post } = require('../helpers');

test('generates months across a year boundary, a PDF, and partial/full payment totals', async ({ request, rental }) => {
  const contract = await post(request, '/contracts', rental.contractData);
  expect(contract.months.map(m => [m.year, m.month]).sort()).toEqual([[2030, 11], [2030, 12], [2031, 1]]);
  expect((await (await request.get(`/api/rooms/${rental.room.id}`)).json()).occupied).toBe(true);
  const month = contract.months.find(m => m.month === 11);
  const pdf = await request.get(month.file_path);
  expect(pdf.ok()).toBeTruthy();
  expect(pdf.headers()['content-type']).toContain('application/pdf');
  expect((await pdf.body()).subarray(0, 5).toString()).toBe('%PDF-');

  const summary = async () => {
    const response = await request.get('/api/admin/year/2030');
    expect(response.ok()).toBeTruthy();
    return (await response.json())[rental.property.id].months['11'][0];
  };
  await post(request, `/contract_months/${month.id}/mark_paid`, { amount: 2000, recorded_by: rental.owner.id });
  expect(await summary()).toMatchObject({ amount: 5000, paid: 2000, paid_full: false });
  await post(request, `/contract_months/${month.id}/mark_paid`, { amount: 3000, recorded_by: rental.owner.id });
  expect(await summary()).toMatchObject({ paid: 5000, paid_full: true });
});

test('rejects a second active contract without adding billing months', async ({ request, rental }) => {
  const original = await post(request, '/contracts', rental.contractData);
  const response = await request.post('/api/contracts', { data: rental.contractData });
  expect(response.status()).toBe(400);
  expect(await response.json()).toEqual({ detail: 'room already has an active contract' });
  const contracts = await (await request.get(`/api/contracts?room_id=${rental.room.id}`)).json();
  expect(contracts).toHaveLength(1);
  expect(contracts[0].months).toEqual(original.months);
});

for (const [field, value] of [
  ['pay_day', 0], ['pay_day', 29], ['duration_months', 0],
  ['start_month', 0], ['start_month', 13], ['amount', 0], ['amount', -100],
]) {
  test(`rejects contract ${field}=${value} without occupying the room`, async ({ request, rental }) => {
    const response = await request.post('/api/contracts', { data: { ...rental.contractData, [field]: value } });
    expect(response.status()).toBe(422);
    expect((await response.json()).detail.some(error => error.loc.includes(field))).toBe(true);
    expect(await (await request.get(`/api/contracts?room_id=${rental.room.id}`)).json()).toEqual([]);
    expect((await (await request.get(`/api/rooms/${rental.room.id}`)).json()).occupied).toBe(false);
  });
}

for (const amount of [0, -100]) {
  test(`rejects payment ${amount} without changing the balance`, async ({ request, rental }) => {
    const contract = await post(request, '/contracts', rental.contractData);
    const month = contract.months[0];
    const response = await request.post(`/api/contract_months/${month.id}/mark_paid`, { data: { amount } });
    expect(response.status()).toBe(422);
    const [saved] = await (await request.get(`/api/contracts?room_id=${rental.room.id}`)).json();
    expect(saved.months.flatMap(m => m.payments)).toEqual([]);
  });
}

test('rejects a missing room and an admin used as a tenant', async ({ request, rental }) => {
  const missing = await request.post('/api/contracts', { data: { ...rental.contractData, room_id: 2147483647 } });
  expect(missing.status()).toBe(404);
  expect(await missing.json()).toEqual({ detail: 'room not found' });
  const wrongRole = await request.post('/api/contracts', { data: { ...rental.contractData, tenant_id: rental.owner.id } });
  expect(wrongRole.status()).toBe(400);
  expect(await wrongRole.json()).toEqual({ detail: 'user is not a tenant' });
  expect(await (await request.get(`/api/contracts?room_id=${rental.room.id}`)).json()).toEqual([]);
});

test('rejects tenant sign-off, accepts admin sign-off, and releases a terminated room', async ({ request, rental }) => {
  const contract = await post(request, '/contracts', rental.contractData);
  for (const action of ['admin_sign', 'terminate']) {
    const response = await request.post(`/api/contracts/${contract.id}/${action}`, { data: { admin_id: rental.tenant.id } });
    expect(response.status()).toBe(403);
    expect(await response.json()).toEqual({ detail: 'admin privileges required' });
  }
  const [unchanged] = await (await request.get(`/api/contracts?room_id=${rental.room.id}`)).json();
  expect(unchanged.admin_signed_at).toBeNull();
  expect(unchanged.terminated_at).toBeNull();
  await post(request, `/contracts/${contract.id}/admin_sign`, { admin_id: rental.owner.id });
  const [signed] = await (await request.get(`/api/contracts?room_id=${rental.room.id}`)).json();
  expect(signed.admin_signed_at).not.toBeNull();
  await post(request, `/contracts/${contract.id}/terminate`, { admin_id: rental.owner.id });
  expect((await (await request.get(`/api/rooms/${rental.room.id}`)).json()).occupied).toBe(false);
  const replacement = await post(request, '/contracts', rental.contractData);
  expect(replacement.id).not.toBe(contract.id);
});
