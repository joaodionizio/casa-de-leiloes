// Regras de tela da vitrine (Story 2.5, D12, D13, D14).
import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { PublicLotSummary, PublicLotsResponse } from './api/publicLots.ts'
import {
  ENDED_STEP,
  initialEndedVisible,
  nextEndedVisible,
  railItems,
  railScrollState,
  selectFeatured,
} from './vitrine.ts'

function lot(id: string, phase: PublicLotSummary['phase']): PublicLotSummary {
  return {
    id,
    title: `Obra ${id}`,
    artist_display: null,
    date_display: null,
    image_url: `/api/catalog/images/${id}`,
    starting_bid_cents: 10000,
    starts_at: '2026-10-25T12:00:00Z',
    ends_at: '2026-10-26T12:00:00Z',
    phase,
    settlement_status: 'pending',
  }
}

function response(
  live: PublicLotSummary[],
  scheduled: PublicLotSummary[],
  ended: PublicLotSummary[],
): PublicLotsResponse {
  return { as_of: '2026-10-25T14:00:00Z', live, scheduled, ended }
}

test('o destaque é o primeiro ao vivo', () => {
  const featured = selectFeatured(
    response([lot('a', 'live'), lot('b', 'live')], [lot('c', 'scheduled')], []),
  )
  assert.equal(featured.kind, 'live')
  assert.equal(featured.kind === 'live' && featured.lot.id, 'a')
})

test('sem ao vivo, o destaque é o primeiro agendado', () => {
  const featured = selectFeatured(
    response([], [lot('c', 'scheduled'), lot('d', 'scheduled')], [lot('e', 'ended')]),
  )
  assert.equal(featured.kind, 'scheduled')
  assert.equal(featured.kind === 'scheduled' && featured.lot.id, 'c')
})

test('só com encerrados (ou sem nada) não há destaque', () => {
  assert.deepEqual(selectFeatured(response([], [], [lot('e', 'ended')])), {
    kind: 'none',
  })
  assert.deepEqual(selectFeatured(response([], [], [])), { kind: 'none' })
})

test('railItems tira só o lote em destaque e preserva a ordem', () => {
  const group = [lot('a', 'live'), lot('b', 'live'), lot('c', 'live')]
  const featured = selectFeatured(response(group, [], []))

  assert.deepEqual(
    railItems(group, featured).map((item) => item.id),
    ['b', 'c'],
  )
})

test('railItems não toca em outro grupo nem sem destaque', () => {
  const scheduled = [lot('c', 'scheduled'), lot('d', 'scheduled')]
  const liveFeatured = selectFeatured(response([lot('a', 'live')], scheduled, []))
  assert.deepEqual(railItems(scheduled, liveFeatured), scheduled)
  assert.deepEqual(railItems(scheduled, { kind: 'none' }), scheduled)
})

test('o passo de "Mostrar mais encerrados" é 6', () => {
  assert.equal(ENDED_STEP, 6)
})

test('initialEndedVisible começa em 6 e respeita o total', () => {
  assert.equal(initialEndedVisible(0), 0)
  assert.equal(initialEndedVisible(4), 4)
  assert.equal(initialEndedVisible(6), 6)
  assert.equal(initialEndedVisible(50), 6)
})

test('initialEndedVisible restaura só um valor válido', () => {
  assert.equal(initialEndedVisible(50, 18), 18)
  assert.equal(initialEndedVisible(10, 18), 10)
  assert.equal(initialEndedVisible(50, 3), 6)
  assert.equal(initialEndedVisible(50, Number.NaN), 6)
  assert.equal(initialEndedVisible(50, 7.5), 6)
  assert.equal(initialEndedVisible(50, -12), 6)
})

test('nextEndedVisible soma 6 sem passar do total', () => {
  assert.equal(nextEndedVisible(6, 50), 12)
  assert.equal(nextEndedVisible(48, 50), 50)
  assert.equal(nextEndedVisible(50, 50), 50)
  assert.equal(nextEndedVisible(6, 8), 8)
})

test('railScrollState: sem overflow nenhum botão ativo', () => {
  assert.deepEqual(railScrollState(0, 800, 800), {
    overflow: false,
    canPrev: false,
    canNext: false,
  })
  // Diferença de 1 px ou menos não é overflow.
  assert.equal(railScrollState(0, 800, 801).overflow, false)
})

test('railScrollState: início, meio e fim com tolerância de 1 px', () => {
  assert.deepEqual(railScrollState(0, 800, 2000), {
    overflow: true,
    canPrev: false,
    canNext: true,
  })
  assert.deepEqual(railScrollState(1, 800, 2000), {
    overflow: true,
    canPrev: false,
    canNext: true,
  })
  assert.deepEqual(railScrollState(600, 800, 2000), {
    overflow: true,
    canPrev: true,
    canNext: true,
  })
  assert.deepEqual(railScrollState(1200, 800, 2000), {
    overflow: true,
    canPrev: true,
    canNext: false,
  })
  assert.equal(railScrollState(1199.5, 800, 2000).canNext, false)
})
