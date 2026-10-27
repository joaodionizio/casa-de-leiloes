import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { BidRoom, MyBids } from './api/bids.ts'
import { bidPosition, endedLastBid } from './bidPosition.ts'

const ME = 'Licitante-AAAAAAAAAAAAAAAA'
const OTHER = 'Licitante-BBBBBBBBBBBBBBBB'

function room(leader: string | null, phase: BidRoom['phase'] = 'live'): BidRoom {
  return {
    as_of: '2026-10-26T14:30:00Z',
    phase,
    ends_at: '2026-10-26T15:00:00Z',
    current_bid_cents: leader === null ? null : 5000,
    minimum_next_bid_cents: 6000,
    bid_count: leader === null ? 0 : 60,
    bids:
      leader === null
        ? []
        : [{ sequence: 60, bidder_alias: leader, amount_cents: 5000, placed_at: '2026-10-26T14:29:00Z' }],
  }
}

function mine(count: number, last: number | null = null): MyBids {
  return { bidder_alias: ME, my_bid_count: count, last_bid_cents: last }
}

test('ganhando: o alias próprio é o do lance atual', () => {
  assert.equal(bidPosition(room(ME), mine(1, 5000), false, true), 'winning')
})

test('superado, mesmo com o lance próprio fora dos 50 exibidos', () => {
  assert.equal(bidPosition(room(OTHER), mine(3, 1000), false, true), 'outbid')
})

test('neutro: nunca participou, com ou sem lances no lote', () => {
  assert.equal(bidPosition(room(OTHER), mine(0), false, true), 'neutral')
  assert.equal(bidPosition(room(null), mine(0), false, true), 'neutral')
})

test('só o último valor não decide a participação', () => {
  assert.equal(bidPosition(room(OTHER), mine(0, 1000), false, true), 'neutral')
})

test('oculta: encerrado, sem dado ou atualizando', () => {
  assert.equal(bidPosition(room(ME, 'ended'), mine(1, 5000), false, true), 'hidden')
  assert.equal(bidPosition(null, mine(1), false, true), 'hidden')
  assert.equal(bidPosition(room(ME), null, false, true), 'hidden')
  assert.equal(bidPosition(room(ME), mine(1), true, true), 'hidden')
})

test('oculta quando a participação é de outra rodada que a sala', () => {
  assert.equal(bidPosition(room(ME), mine(0), false, false), 'hidden')
  assert.equal(bidPosition(room(OTHER), mine(2, 1000), false, false), 'hidden')
})

test('último lance próprio: só encerrado, pareado e com participação', () => {
  assert.equal(endedLastBid(room(OTHER, 'ended'), mine(2, 1000), true), 1000)
  assert.equal(endedLastBid(room(OTHER, 'ended'), mine(0), true), null)
  assert.equal(endedLastBid(room(OTHER, 'ended'), mine(2, 1000), false), null)
  assert.equal(endedLastBid(room(OTHER, 'live'), mine(2, 1000), true), null)
  assert.equal(endedLastBid(null, mine(2, 1000), true), null)
})
