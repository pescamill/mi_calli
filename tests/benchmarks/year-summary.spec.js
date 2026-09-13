const { test, expect, post, createUser } = require('../helpers');
const { performance } = require('node:perf_hooks');
const os = require('node:os');

test('year summary latency with 10 rooms and 120 billing months', async ({ request }, testInfo) => {
  // Use a clean stack so the dataset remains comparable across runs.
  expect(await (await request.get('/api/contracts')).json(), 'Run test:down and test:up before benchmarking').toEqual([]);
  const owner = await createUser(request);
  const tenant = await createUser(request, 'tenant');
  const property = await post(request, '/properties', { name: 'Benchmark', address: 'Test data', owner_id: owner.id });
  for (let i = 0; i < 10; i++) {
    const room = await post(request, '/rooms', { name: `Room ${i + 1}`, property_id: property.id });
    await post(request, '/contracts', {
      room_id: room.id, tenant_id: tenant.id, start_year: 2030, start_month: 1,
      duration_months: 12, pay_day: 5, amount: 5000,
    });
  }
  const samples = [];
  for (let i = 0; i < 35; i++) {
    const start = performance.now();
    const response = await request.get('/api/admin/year/2030');
    const body = await response.body();
    const elapsed = performance.now() - start;
    expect(response.status()).toBe(200);
    const months = JSON.parse(body)[property.id].months;
    expect(Object.keys(months)).toHaveLength(12);
    expect(Object.values(months).every(entries => entries.length === 10)).toBe(true);
    if (i >= 5) samples.push(elapsed);
  }
  const sorted = [...samples].sort((a, b) => a - b);
  const result = {
    endpoint: '/api/admin/year/2030', rooms: 10, billingMonths: 120,
    warmupRequests: 5, measuredRequests: samples.length, concurrency: 1,
    medianMs: (sorted[14] + sorted[15]) / 2,
    p95Ms: sorted[Math.ceil(sorted.length * 0.95) - 1],
    minMs: sorted[0], maxMs: sorted.at(-1), samplesMs: samples,
    node: process.version, platform: `${os.platform()} ${os.arch()}`, cpu: os.cpus()[0]?.model,
    timestamp: new Date().toISOString(),
  };
  console.log(JSON.stringify(result, null, 2));
  await testInfo.attach('year-summary-benchmark', { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
});
