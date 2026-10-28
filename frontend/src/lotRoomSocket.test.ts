import assert from 'node:assert/strict'
import test from 'node:test'
import type { BidRoom } from './api/bids.ts'
import { parseRoomMessage, roomSocketUrl, roomWithSettlement, sameRoomState, shouldApplyRoom } from './lotRoomSocket.ts'

const lot = '00000000-0000-4000-8000-000000000001'
const room: BidRoom = {
  as_of: '2026-10-27T12:00:00.123456Z', phase: 'live', ends_at: '2026-10-27T13:00:00Z',
  current_bid_cents: null, minimum_next_bid_cents: 10000, bid_count: 0, bids: [], settlement_status: 'pending', settlement: null,
}
test('count orders bids, timestamp only breaks ties, terminal and lot identity prevail', () => {
  assert.ok(shouldApplyRoom(null, room))
  assert.ok(shouldApplyRoom(room, { ...room, bid_count: 1, as_of: '2026-10-27T11:00:00Z' }))
  assert.equal(shouldApplyRoom({ ...room, bid_count: 2 }, { ...room, bid_count: 1 }), false)
  assert.ok(shouldApplyRoom(room, room))
  assert.ok(shouldApplyRoom(room, { ...room, phase: 'ended', as_of: '2026-10-27T12:00:00.123457Z' }))
  assert.equal(shouldApplyRoom(room, { ...room, as_of: '2026-10-27T12:00:00.123455Z' }), false)
  assert.ok(shouldApplyRoom(room, { ...room, as_of: '2026-10-27T14:00:00.123456+02:00' }))
  assert.equal(shouldApplyRoom(room, room, true), false)
  assert.equal(shouldApplyRoom(null, room, true), false)
  assert.equal(shouldApplyRoom(room, room, false, lot, 'another'), false)
})
test('validated discriminated payload and same-origin ws/wss URL', () => {
  for (const type of ['room_snapshot', 'bid_accepted']) {
    assert.deepEqual(parseRoomMessage(JSON.stringify({ type, lot_id: lot, room })), { type, lot_id: lot, room })
  }
  assert.ok(parseRoomMessage(JSON.stringify({ type: 'lot_cancelled', lot_id: lot, cancelled_at: room.as_of })))
  for (const invalid of [null, '{', '{}', JSON.stringify({ type: 'bid', lot_id: lot, room }),
    JSON.stringify({ type: 'room_snapshot', lot_id: lot, room: {} }),
    JSON.stringify({ type: 'lot_cancelled', lot_id: lot, cancelled_at: room.as_of, secret: 'x' })]) {
    assert.equal(parseRoomMessage(invalid), null)
  }
  assert.equal(roomSocketUrl(lot, 'https://example.com'), `wss://example.com/ws/lots/${lot}`)
  assert.equal(roomSocketUrl(lot, 'http://localhost:5173'), `ws://localhost:5173/ws/lots/${lot}`)
})
test('same public state ignores only as_of, which the server renews on every reread', () => {
  const bid = { sequence: 1, bidder_alias: 'Licitante-0123456789abcdef', amount_cents: 11000, placed_at: '2026-10-27T11:59:00Z' }
  const base: BidRoom = { ...room, bid_count: 1, current_bid_cents: 11000, bids: [bid] }
  assert.ok(sameRoomState(base, { ...base, as_of: '2026-10-27T12:00:05.000001Z' }))
  assert.equal(sameRoomState(base, { ...base, phase: 'ended' }), false)
  assert.equal(sameRoomState(base, { ...base, ends_at: '2026-10-27T13:02:00Z' }), false)
  assert.equal(sameRoomState(base, { ...base, bid_count: 2 }), false)
  assert.equal(sameRoomState(base, { ...base, minimum_next_bid_cents: null }), false)
  assert.equal(sameRoomState(base, { ...base, bids: [{ ...bid, amount_cents: 12000 }] }), false)
  assert.equal(sameRoomState(base, { ...base, bids: [] }), false)
})

test('T18/T19/T20 lot_closed validates its exact whitelist, persistent time and outcome', () => {
  const unsold = { outcome: 'unsold' as const, winner_alias: null, final_amount_cents: null,
    bid_count: 0, final_hash: '0'.repeat(64), settled_at: '2026-10-27T13:00:00.123456Z' }
  const frame = { type: 'lot_closed', lot_id: lot, ...unsold, as_of: unsold.settled_at }
  assert.deepEqual(parseRoomMessage(JSON.stringify(frame)), frame)
  const sold = { ...frame, outcome: 'sold', winner_alias: 'Licitante-0123456789ABCDEF',
    final_amount_cents: Number.MAX_SAFE_INTEGER, bid_count: 1, final_hash: 'f'.repeat(64) }
  assert.deepEqual(parseRoomMessage(JSON.stringify(sold)), sold)
  for (const invalid of [{ ...frame, winner_user_id: lot }, { ...frame, anchor_hmac: 'a'.repeat(64) },
    { ...frame, as_of: '2026-10-27T13:00:00.123457Z' }, { ...frame, final_amount_cents: 0 },
    { ...sold, winner_alias: 'private@example.com' }, { ...sold, bid_count: 0 },
    { ...sold, final_amount_cents: Number.MAX_SAFE_INTEGER + 1 }, { ...frame, final_hash: 'f'.repeat(64) }]) {
    assert.equal(parseRoomMessage(JSON.stringify(invalid)), null)
  }
})

test('T38/T40 equal-count settlement wins and pending or divergent terminal never replaces it', () => {
  const settlement = { outcome: 'unsold' as const, winner_alias: null, final_amount_cents: null,
    bid_count: 0, final_hash: '0'.repeat(64), settled_at: '2026-10-27T13:00:00.123456Z' }
  const terminal = roomWithSettlement(room, settlement)
  assert.equal(sameRoomState(room, terminal), false)
  assert.ok(shouldApplyRoom(room, terminal))
  assert.equal(shouldApplyRoom(terminal, { ...room, as_of: '2026-10-29T13:00:00Z' }), false)
  assert.equal(shouldApplyRoom(terminal, { ...terminal, settlement: { ...settlement, settled_at: '2026-10-27T13:00:00.123457Z' } }), false)
  assert.ok(sameRoomState(terminal, { ...terminal, as_of: '2026-10-29T13:00:00Z' }))
  assert.equal(terminal.bids, room.bids)
})
