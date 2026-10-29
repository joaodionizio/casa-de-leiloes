// Textos de lote (Story 2.5): o nome acessível do link começa pelo título.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { PublicLotSummary } from './api/publicLots.ts'
import { lotLinkLabel, lotTitleText, publicLotStatusText, UNTITLED } from './lotLabels.ts'

function lot(overrides: Partial<PublicLotSummary> = {}): PublicLotSummary {
  return {
    id: '2d484387-2509-5e8e-2c43-22f9981972eb',
    title: 'Nighthawks',
    artist_display: null,
    date_display: null,
    image_url: '/api/catalog/images/x',
    starting_bid_cents: 1845000,
    starts_at: '2026-10-25T12:00:00Z',
    ends_at: '2026-10-26T12:00:00Z',
    phase: 'live',
    settlement_status: 'pending',
    ...overrides,
  }
}

test('título ausente ou vazio vira "Sem título"', () => {
  assert.equal(lotTitleText(null), UNTITLED)
  assert.equal(lotTitleText('   '), UNTITLED)
  assert.equal(lotTitleText('Nighthawks'), 'Nighthawks')
})

test('o nome do link começa pelo título e traz estado e lance inicial', () => {
  assert.equal(
    lotLinkLabel(lot()),
    'Nighthawks. Ao vivo. Lance inicial R$ 18.450,00.',
  )
  assert.equal(
    lotLinkLabel(lot({ title: null, phase: 'scheduled', starting_bid_cents: 85000 })),
    'Sem título. Agendado. Lance inicial R$ 850,00.',
  )
})

test('o encerrado não leva valor no nome do link', () => {
  assert.equal(
    lotLinkLabel(lot({ phase: 'ended' })),
    'Nighthawks. Encerrado, apurando resultado.',
  )
})

test('o nome do link nunca fala em "lance atual"', () => {
  assert.equal(lotLinkLabel(lot()).includes('atual'), false)
})


test('a Vitrine distingue pending/settled com o mesmo estado visual e acessível', () => {
  for (const [settlement_status, expected] of [
    ['pending', 'Encerrado, apurando resultado'],
    ['settled', 'Encerrado'],
  ] as const) {
    const item = lot({ phase: 'ended', settlement_status })
    assert.equal(publicLotStatusText(item), expected)
    assert.equal(lotLinkLabel(item), `Nighthawks. ${expected}.`)
  }
  for (const settlement_status of ['pending', 'settled'] as const) {
    assert.equal(publicLotStatusText(lot({ phase: 'live', settlement_status })), 'Ao vivo')
    assert.equal(publicLotStatusText(lot({ phase: 'scheduled', settlement_status })), 'Agendado')
  }
})
