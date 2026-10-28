import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fetchAudit, isAudit, type Audit } from './audit.ts'
const ID = '00000000-0000-4000-8000-000000000001'
function empty(): Audit {
  return { lot_id: ID, as_of: '2026-10-28T14:00:00.123456Z', integrity: 'verified', phase: 'live', settlement_status: 'pending', settlement: null, bid_count: 0, final_hash: '0'.repeat(64), bids: [] }
}
function filled(): Audit {
  return { ...empty(), bid_count: 1, final_hash: 'a'.repeat(64), bids: [{ sequence: 1, bidder_alias: 'Licitante-1234567890ABCDEF', amount_cents: 12000, placed_at: '2026-10-28T13:00:00.123456Z', canonical_version: 1, previous_hash: '0'.repeat(64), current_hash: 'a'.repeat(64) }] }
}
test('audit validates public chain and trusted states', () => {
  for (const phase of ['scheduled', 'live', 'ended'] as const) assert.equal(isAudit({ ...empty(), phase }, ID), true)
  assert.equal(isAudit({ ...empty(), phase: 'cancelled', settlement_status: 'not_applicable' }, ID), true)
  for (const outcome of ['sold', 'unsold'] as const) {
    const data = outcome === 'sold' ? filled() : empty()
    data.phase = 'ended'; data.settlement_status = 'settled'
    data.settlement = { outcome, winner_alias: data.bids[0]?.bidder_alias ?? null, final_amount_cents: data.bids[0]?.amount_cents ?? null, bid_count: data.bid_count!, final_hash: data.final_hash!, settled_at: data.as_of }
    assert.equal(isAudit(data, ID), true)
  }
})
test('audit rejects private fields, malformed states and sequences', () => {
  for (const mutation of [{ lot_id: 'other' }, { bid_count: -1 }, { final_hash: 'a' }, { phase: null }, { winner_user_id: ID }, { integrity: 'unknown' }, { settlement_status: 'settled' }, { phase: 'cancelled', settlement_status: 'not_applicable' }]) {
    assert.equal(isAudit({ ...filled(), ...mutation }, ID), false, JSON.stringify(mutation))
  }
  for (const mutation of [{ sequence: 2 }, { bidder_alias: 'private@example.com' }, { amount_cents: 1.5 }, { canonical_version: 2 }, { previous_hash: 'a'.repeat(64) }, { placed_at: '2026-02-30T00:00:00Z' }, { placed_at: '2027-01-01T00:00:00Z' }, { bidder_id: ID }]) {
    const data = filled(); Object.assign(data.bids[0], mutation)
    assert.equal(isAudit(data, ID), false, JSON.stringify(mutation))
  }
})
test('adulterated requires all untrusted fields withheld', () => {
  const data = { ...empty(), integrity: 'adulterated', phase: null, settlement_status: null, bid_count: null, final_hash: null }
  assert.equal(isAudit(data, ID), true)
  assert.equal(isAudit({ ...data, bids: filled().bids }, ID), false)
  assert.equal(isAudit({ ...data, phase: 'ended' }, ID), false)
})
test('fetchAudit uses same-origin/no-store and maps failures', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url: string, init: RequestInit) => {
    assert.equal(url, `/api/lots/${ID}/audit`); assert.equal(init.credentials, 'same-origin'); assert.equal(init.cache, 'no-store')
    return new Response(JSON.stringify(empty()), { status: 200 })
  })
  assert.deepEqual(await fetchAudit(ID, new AbortController().signal), { ok: true, data: empty() })
  for (const status of [404, 500, 200]) {
    t.mock.method(globalThis, 'fetch', async () => new Response('{}', { status }))
    assert.deepEqual(await fetchAudit(ID, new AbortController().signal), { ok: false, failure: status === 404 ? 'not_found' : 'server' })
  }
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('offline') })
  assert.deepEqual(await fetchAudit(ID, new AbortController().signal), { ok: false, failure: 'server' })
})
