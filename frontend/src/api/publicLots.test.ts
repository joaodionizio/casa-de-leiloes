// Guards das respostas públicas (Story 2.5): uma resposta fora do contrato nunca
// chega à tela.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  isPublicLotDetailResponse,
  isPublicLotsResponse,
} from './publicLots.ts'

function summary(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: '2d484387-2509-5e8e-2c43-22f9981972eb',
    title: 'A Sunday on La Grande Jatte — 1884',
    artist_display: 'Georges Seurat (French, 1859–1891)',
    date_display: '1884–86, border added 1888–89',
    image_url: '/api/catalog/images/2d484387-2509-5e8e-2c43-22f9981972eb',
    starting_bid_cents: 10000,
    current_bid_cents: null,
    starts_at: '2026-10-25T12:00:00.481203Z',
    ends_at: '2026-10-28T12:00:00.481203Z',
    phase: 'live',
    settlement_status: 'pending',
    ...overrides,
  }
}

function without(
  value: Record<string, unknown>,
  key: string,
): Record<string, unknown> {
  const copy = { ...value }
  delete copy[key]
  return copy
}

function list(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    as_of: '2026-10-25T14:30:00.123456Z',
    live: [summary()],
    scheduled: [],
    ended: [],
    ...overrides,
  }
}

function detail(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    as_of: '2026-10-25T14:30:00.123456Z',
    lot: {
      ...summary(),
      external_id: 27992,
      medium_display: 'Oil on canvas',
      dimensions: '207.5 × 308.1 cm',
      department_title: 'Painting and Sculpture of Europe',
      artwork_type_title: 'Painting',
      credit_line: 'Helen Birch Bartlett Memorial Collection',
      source_url: 'https://www.artic.edu/artworks/27992',
      min_increment_cents: 1000,
    },
    ...overrides,
  }
}

test('a vitrine do exemplo do contrato é aceita', () => {
  assert.equal(isPublicLotsResponse(list()), true)
  assert.equal(
    isPublicLotsResponse(list({ live: [], scheduled: [], ended: [] })),
    true,
  )
})

test('campos de texto podem ser null', () => {
  const nulls = summary({ title: null, artist_display: null, date_display: null })
  assert.equal(isPublicLotsResponse(list({ live: [nulls] })), true)
})

test('lance atual obrigatório aceita null ou centavos inteiros no resumo e no detalhe', () => {
  const base = detail().lot as Record<string, unknown>
  for (const current_bid_cents of [null, 100000, 150000, 9007199254740991]) {
    assert.equal(isPublicLotsResponse(list({ live: [summary({ current_bid_cents })] })), true)
    assert.equal(isPublicLotDetailResponse({ ...detail(), lot: { ...base, current_bid_cents } }), true)
  }
  for (const current_bid_cents of [undefined, 100.5, 0, -1, '100', Number.NaN, 2 ** 53]) {
    assert.equal(isPublicLotsResponse(list({ live: [summary({ current_bid_cents })] })), false)
    assert.equal(isPublicLotDetailResponse({ ...detail(), lot: { ...base, current_bid_cents } }), false)
  }
  assert.equal(isPublicLotsResponse(list({ live: [without(summary(), 'current_bid_cents')] })), false)
  assert.equal(isPublicLotDetailResponse({ ...detail(), lot: without(base, 'current_bid_cents') }), false)
})

test('a vitrine recusa phase fora dos três valores', () => {
  for (const phase of ['cancelled', 'pending', 'LIVE', '', null, 1]) {
    assert.equal(
      isPublicLotsResponse(list({ live: [summary({ phase })] })),
      false,
      String(phase),
    )
  }
})

test('a vitrine recusa centavos fora do contrato', () => {
  for (const cents of [100.5, 0, -1, '100', null, Number.NaN, 2 ** 53]) {
    assert.equal(
      isPublicLotsResponse(list({ live: [summary({ starting_bid_cents: cents })] })),
      false,
      String(cents),
    )
  }
})

test('a vitrine recusa tipo errado e campo ausente', () => {
  assert.equal(isPublicLotsResponse(list({ live: [summary({ title: 42 })] })), false)
  assert.equal(isPublicLotsResponse(list({ live: [summary({ id: 7 })] })), false)
  assert.equal(
    isPublicLotsResponse(list({ live: [summary({ image_url: undefined })] })),
    false,
  )
  assert.equal(isPublicLotsResponse(without(list(), 'live')), false)
  assert.equal(isPublicLotsResponse(without(list(), 'as_of')), false)
  assert.equal(isPublicLotsResponse(list({ ended: 'nenhum' })), false)
  assert.equal(isPublicLotsResponse(list({ scheduled: [null] })), false)
})

test('a vitrine recusa o que não é objeto', () => {
  for (const value of [null, undefined, 'texto', 3, []]) {
    assert.equal(isPublicLotsResponse(value), false)
  }
})

test('o detalhe do exemplo do contrato é aceito', () => {
  assert.equal(isPublicLotDetailResponse(detail()), true)
})

test('o detalhe recusa campo ausente ou fora do contrato', () => {
  assert.equal(isPublicLotDetailResponse(without(detail(), 'lot')), false)
  assert.equal(isPublicLotDetailResponse(without(detail(), 'as_of')), false)

  const base = detail().lot as Record<string, unknown>
  for (const bad of [
    { external_id: '27992' },
    { source_url: null },
    { min_increment_cents: 0 },
    { min_increment_cents: 10.5 },
    { medium_display: 5 },
    { phase: 'cancelled' },
    { starting_bid_cents: '100' },
  ]) {
    assert.equal(
      isPublicLotDetailResponse({ ...detail(), lot: { ...base, ...bad } }),
      false,
      JSON.stringify(bad),
    )
  }
})


test('settlement_status é obrigatório em resumo e detalhe e aceita só pending/settled', () => {
  for (const status of ['pending', 'settled']) {
    assert.equal(isPublicLotsResponse(list({ ended: [summary({ phase: 'ended', settlement_status: status })] })), true)
    const base = detail().lot as Record<string, unknown>
    assert.equal(isPublicLotDetailResponse({ ...detail(), lot: { ...base, settlement_status: status } }), true)
  }
  for (const status of [undefined, null, '', 'sold', 'unsold', true, 1]) {
    const invalid = summary({ settlement_status: status })
    assert.equal(isPublicLotsResponse(list({ ended: [invalid] })), false)
    const base = detail().lot as Record<string, unknown>
    assert.equal(isPublicLotDetailResponse({ ...detail(), lot: { ...base, settlement_status: status } }), false)
  }
  assert.equal(isPublicLotsResponse(list({ ended: [without(summary(), 'settlement_status')] })), false)
  const base = detail().lot as Record<string, unknown>
  assert.equal(isPublicLotDetailResponse({ ...detail(), lot: without(base, 'settlement_status') }), false)
})
