import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { fetchWins, isMyWinsResponse } from './wins.ts'
const item = { lot_id: '00000000-0000-0000-0000-000000000001', title: 'Obra', artist_display: null, image_url: '/api/catalog/images/abc-123', phase: 'ended', settlement_status: 'settled', result: 'won', winner_alias: 'Licitante-0123456789ABCDEF', final_amount_cents: 12000, settled_at: '2026-10-28T12:00:00Z', bid_count: 3 }
const body = { as_of: '2026-10-28T12:00:01Z', items: [item] }
const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })
test('accepts persisted wins, pending participation and empty snapshots', () => {
  assert.equal(isMyWinsResponse(body), true)
  assert.equal(isMyWinsResponse({ ...body, items: [] }), true)
  for (const phase of ['live', 'scheduled', 'ended']) assert.equal(isMyWinsResponse({ ...body, items: [{ ...item, phase, settlement_status: 'pending', result: null, winner_alias: null, final_amount_cents: null, settled_at: null }] }), true)
})
test('rejects inconsistent victory, disclosure on loss, duplicates and malformed data', () => {
  for (const patch of [{ phase: 'live' }, { settlement_status: 'pending' }, { winner_alias: 'real-name' }, { final_amount_cents: 1.2 }, { settled_at: 'invalid' }, { result: 'not_won' }, { bid_count: 0 }, { image_url: 'https://external.example/image' }]) assert.equal(isMyWinsResponse({ ...body, items: [{ ...item, ...patch }] }), false)
  assert.equal(isMyWinsResponse({ ...body, items: [item, item] }), false)
  assert.equal(isMyWinsResponse(null), false)
})
test('fetch uses session identity and no-store and classifies safe errors', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/me/wins')
    assert.equal(options?.credentials, 'same-origin')
    assert.equal(options?.cache, 'no-store')
    return Response.json(body)
  }
  assert.deepEqual(await fetchWins(), { ok: true, data: body })
  for (const [status, failure] of [[401, 'unauthorized'], [403, 'forbidden'], [409, 'integrity'], [500, 'server']] as const) {
    globalThis.fetch = async () => Response.json({ code: 'lot_integrity_conflict' }, { status })
    assert.deepEqual(await fetchWins(), { ok: false, failure })
  }
  globalThis.fetch = async () => Response.json({ items: [] })
  assert.deepEqual(await fetchWins(), { ok: false, failure: 'server' })
  globalThis.fetch = async () => { throw new Error('network') }
  assert.deepEqual(await fetchWins(), { ok: false, failure: 'server' })
})
