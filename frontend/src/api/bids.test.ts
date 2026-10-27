// Contrato da sala (Story 3.5): guardas dos GETs e classificação do POST.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  classifyBidResponse,
  isBidRoom,
  isMyBids,
  isPlacedBidResponse,
} from './bids.ts'

const ALIAS = 'Licitante-A83F19C2D4E5B601'

function bidItem(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    sequence: 1,
    bidder_alias: ALIAS,
    amount_cents: 125000,
    placed_at: '2026-10-26T14:29:41.500000Z',
    ...overrides,
  }
}

function room(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    as_of: '2026-10-26T14:30:00.123456Z',
    phase: 'live',
    ends_at: '2026-10-26T15:00:00Z',
    current_bid_cents: 125000,
    minimum_next_bid_cents: 130000,
    bid_count: 1,
    bids: [bidItem()],
    ...overrides,
  }
}

function placed(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    bid: bidItem(),
    lot: {
      current_bid_cents: 125000,
      ends_at: '2026-10-26T15:02:00Z',
      anti_sniping_applied: true,
    },
    wallet: {
      total_balance_cents: 500000,
      committed_balance_cents: 125000,
      available_balance_cents: 375000,
    },
    ...overrides,
  }
}

test('sala válida: vazia, com nulos e no limite de 50', () => {
  assert.equal(isBidRoom(room()), true)
  assert.equal(
    isBidRoom(
      room({ current_bid_cents: null, minimum_next_bid_cents: null, bid_count: 0, bids: [] }),
    ),
    true,
  )
  const fifty = Array.from({ length: 50 }, (_, i) => bidItem({ sequence: 51 - i }))
  assert.equal(isBidRoom(room({ bid_count: 51, bids: fifty })), true)
  assert.equal(isBidRoom(room({ bid_count: 52, bids: [...fifty, bidItem()] })), false)
})

test('sala inválida: campo ausente, tipo errado e data sem fuso', () => {
  const missing = room()
  delete missing.phase
  assert.equal(isBidRoom(missing), false)
  assert.equal(isBidRoom(room({ bid_count: '1' })), false)
  assert.equal(isBidRoom(room({ as_of: '2026-10-26T14:30:00' })), false)
  assert.equal(isBidRoom(room({ phase: 'closed' })), false)
  assert.equal(isBidRoom(room({ bids: [bidItem({ bidder_alias: 'joao@x.com' })] })), false)
})

test('extras são ignorados na leitura e não quebram a guarda', () => {
  assert.equal(isBidRoom(room({ extra: 1 })), true)
})

test('/mine: alias, contagem e último valor anulável', () => {
  assert.equal(isMyBids({ bidder_alias: ALIAS, my_bid_count: 0, last_bid_cents: null }), true)
  assert.equal(isMyBids({ bidder_alias: ALIAS, my_bid_count: 2, last_bid_cents: 5 }), true)
  assert.equal(isMyBids({ bidder_alias: ALIAS, my_bid_count: -1, last_bid_cents: null }), false)
  assert.equal(isMyBids({ bidder_alias: 'x', my_bid_count: 0, last_bid_cents: null }), false)
})

test('201 válido e inválido (lance diferente do atual, carteira incoerente)', () => {
  assert.equal(isPlacedBidResponse(placed()), true)
  assert.equal(
    isPlacedBidResponse(
      placed({ lot: { current_bid_cents: 1, ends_at: '2026-10-26T15:02:00Z', anti_sniping_applied: false } }),
    ),
    false,
  )
  assert.equal(
    isPlacedBidResponse(
      placed({ wallet: { total_balance_cents: 1, committed_balance_cents: 0, available_balance_cents: 5 } }),
    ),
    false,
  )
})

test('POST: o 201 é o único aceite; corpo inválido é ambíguo', () => {
  assert.deepEqual(classifyBidResponse(201, placed()), { ok: true, placed: placed() })
  assert.deepEqual(classifyBidResponse(201, { bid: 1 }), { ok: false, failure: 'ambiguous' })
  assert.deepEqual(classifyBidResponse(201, null), { ok: false, failure: 'ambiguous' })
})

test('POST: as cinco recusas de negócio vêm do code, não da mensagem', () => {
  for (const code of [
    'below_minimum',
    'insufficient_balance',
    'already_winning',
    'lot_not_started',
    'lot_ended',
  ]) {
    assert.deepEqual(classifyBidResponse(422, { status: 422, code, message: '<b>x</b>' }), {
      ok: false,
      failure: code,
    })
  }
})

test('POST: validação, integridade, papel, sessão, 404 e outros 4xx', () => {
  const failure = (status: number, code: string) =>
    classifyBidResponse(status, { status, code, message: 'qualquer' })
  assert.deepEqual(failure(422, 'validation_error'), { ok: false, failure: 'validation' })
  assert.deepEqual(failure(409, 'lot_integrity_conflict'), { ok: false, failure: 'integrity' })
  assert.deepEqual(failure(401, 'unauthorized'), { ok: false, failure: 'unauthorized' })
  assert.deepEqual(failure(403, 'forbidden'), { ok: false, failure: 'forbidden' })
  assert.deepEqual(failure(403, 'csrf_origin_invalid'), { ok: false, failure: 'rejected' })
  assert.deepEqual(failure(404, 'not_found'), { ok: false, failure: 'not_found' })
  assert.deepEqual(failure(415, 'x'), { ok: false, failure: 'rejected' })
})

test('POST: 5xx e status inesperado são ambíguos', () => {
  assert.deepEqual(classifyBidResponse(500, null), { ok: false, failure: 'ambiguous' })
  assert.deepEqual(classifyBidResponse(503, { code: 'x' }), { ok: false, failure: 'ambiguous' })
  assert.deepEqual(classifyBidResponse(204, null), { ok: false, failure: 'ambiguous' })
})
