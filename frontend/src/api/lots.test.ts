import assert from 'node:assert/strict'
import { test } from 'node:test'
import { classifyCancelResponse, isMyLotsBody } from './lots.ts'

const LOT_ID = '00000000-0000-4000-8000-000000000001'

function item(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: LOT_ID,
    external_id: 27992,
    title: 'Obra',
    artist_display: null,
    date_display: null,
    medium_display: null,
    dimensions: null,
    department_title: null,
    artwork_type_title: null,
    credit_line: null,
    source_url: 'https://www.artic.edu/artworks/27992',
    image_id: '2d484387-2509-5e8e-2c43-22f9981972eb',
    image_url: '/api/catalog/images/2d484387-2509-5e8e-2c43-22f9981972eb',
    starting_bid_cents: 10000,
    min_increment_cents: 1000,
    starts_at: '2026-10-26T12:00:00Z',
    ends_at: '2026-10-27T12:00:00Z',
    created_at: '2026-10-26T11:00:00Z',
    cancelled_at: null,
    bid_count: 0,
    phase: 'live',
    ...overrides,
  }
}

test('a lista do dono exige as_of e os três campos novos', () => {
  const body = { as_of: '2026-10-26T12:30:00.123456Z', items: [item()] }
  assert.equal(isMyLotsBody(body), true)
  assert.equal(isMyLotsBody({ items: [item()] }), false) // contrato antigo, sem as_of
  assert.equal(isMyLotsBody({ as_of: 'ontem', items: [] }), false)
  assert.equal(isMyLotsBody({ as_of: body.as_of, items: [] }), true)
  const without = (key: string) => {
    const copy = item()
    delete copy[key]
    return { as_of: body.as_of, items: [copy] }
  }
  for (const key of ['cancelled_at', 'bid_count', 'phase']) {
    assert.equal(isMyLotsBody(without(key)), false, key)
  }
})

test('a lista do dono recusa fase desconhecida, contagem inválida e data ilegível', () => {
  const asOf = '2026-10-26T12:30:00Z'
  assert.equal(isMyLotsBody({ as_of: asOf, items: [item({ phase: 'cancelled' })] }), false)
  assert.equal(isMyLotsBody({ as_of: asOf, items: [item({ bid_count: -1 })] }), false)
  assert.equal(isMyLotsBody({ as_of: asOf, items: [item({ bid_count: 1.5 })] }), false)
  assert.equal(isMyLotsBody({ as_of: asOf, items: [item({ cancelled_at: 'x' })] }), false)
  assert.equal(
    isMyLotsBody({ as_of: asOf, items: [item({ cancelled_at: '2026-10-26T12:00:00Z' })] }),
    true,
  )
})

test('POST: só o 200 com o id pedido e cancelled_at válido é sucesso', () => {
  assert.deepEqual(
    classifyCancelResponse(200, { id: LOT_ID, cancelled_at: '2026-10-26T12:00:00.5Z' }, LOT_ID),
    { ok: true, cancelledAt: '2026-10-26T12:00:00.5Z' },
  )
  const ambiguous = { ok: false, failure: 'ambiguous' }
  assert.deepEqual(classifyCancelResponse(200, { id: 'outro', cancelled_at: '2026-10-26T12:00:00Z' }, LOT_ID), ambiguous)
  assert.deepEqual(classifyCancelResponse(200, { id: LOT_ID, cancelled_at: null }, LOT_ID), ambiguous)
  assert.deepEqual(classifyCancelResponse(200, { id: LOT_ID }, LOT_ID), ambiguous)
  assert.deepEqual(classifyCancelResponse(200, null, LOT_ID), ambiguous)
})

test('POST: as falhas de negócio vêm do status e do code, nunca da mensagem', () => {
  const failure = (status: number, code: string) =>
    classifyCancelResponse(status, { status, code, message: 'qualquer <b>coisa</b>' }, LOT_ID)
  assert.deepEqual(failure(422, 'lot_has_bids'), { ok: false, failure: 'has_bids' })
  assert.deepEqual(failure(422, 'lot_ended'), { ok: false, failure: 'ended' })
  assert.deepEqual(failure(409, 'lot_integrity_conflict'), { ok: false, failure: 'integrity' })
  assert.deepEqual(failure(403, 'forbidden'), { ok: false, failure: 'forbidden' })
  assert.deepEqual(failure(404, 'not_found'), { ok: false, failure: 'not_found' })
  assert.deepEqual(classifyCancelResponse(401, null, LOT_ID), { ok: false, failure: 'unauthorized' })
})

test('POST: rede, 5xx, proteção CSRF, validação e código desconhecido são ambíguos', () => {
  const ambiguous = { ok: false, failure: 'ambiguous' }
  const failure = (status: number, code: string) =>
    classifyCancelResponse(status, { status, code, message: 'x' }, LOT_ID)
  assert.deepEqual(failure(500, 'internal_error'), ambiguous)
  assert.deepEqual(failure(502, 'x'), ambiguous)
  assert.deepEqual(failure(403, 'csrf_origin_mismatch'), ambiguous) // não é o `forbidden` do dono
  assert.deepEqual(failure(415, 'unsupported_media_type'), ambiguous)
  assert.deepEqual(failure(422, 'validation_error'), ambiguous)
  assert.deepEqual(failure(422, 'codigo_novo'), ambiguous)
  assert.deepEqual(classifyCancelResponse(500, 'texto', LOT_ID), ambiguous)
})
