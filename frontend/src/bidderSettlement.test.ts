import assert from 'node:assert/strict'
import test from 'node:test'
import type { BidRoom } from './api/bids.ts'
import { classifyBidderSettlement } from './bidderSettlement.ts'

type State = Pick<BidRoom, 'phase' | 'settlement_status' | 'settlement'>
const OWN = 'Licitante-A83F19C2D4E5B601'
const OTHER = 'Licitante-0B7E5A91C3D2F480'

const sold: State = {
  phase: 'ended',
  settlement_status: 'settled',
  settlement: {
    outcome: 'sold',
    winner_alias: OWN,
    final_amount_cents: 12_000,
    bid_count: 2,
    final_hash: 'a'.repeat(64),
    settled_at: '2026-10-25T17:00:00.123456Z',
  },
}

test('does not claim a result while the lot is still being settled', () => {
  assert.equal(classifyBidderSettlement({ ...sold, settlement_status: 'pending', settlement: null }, OWN, 2, true), null)
  assert.equal(classifyBidderSettlement({ ...sold, phase: 'live' }, OWN, 2, true), null)
})

test('confirms the winner only with a verified authenticated alias and bids', () => {
  assert.equal(classifyBidderSettlement(sold, OWN, 2, true), 'won')
  assert.equal(classifyBidderSettlement(sold, OWN, 2, false), 'unverified')
  assert.equal(classifyBidderSettlement(sold, OWN, 0, true), 'unverified')
  assert.equal(classifyBidderSettlement(sold, null, null, false), 'unverified')
})

test('distinguishes a losing participant from an account that never bid', () => {
  assert.equal(classifyBidderSettlement(sold, OTHER, 1, true), 'lost')
  assert.equal(classifyBidderSettlement(sold, OTHER, 0, true), 'not_participated')
})

test('a settled lot without bids is unsold even when a private read is unavailable', () => {
  const unsold: State = {
    ...sold,
    settlement: {
      outcome: 'unsold',
      winner_alias: null,
      final_amount_cents: null,
      bid_count: 0,
      final_hash: '0'.repeat(64),
      settled_at: '2026-10-25T17:00:00.123456Z',
    },
  }
  assert.equal(classifyBidderSettlement(unsold, null, null, false), 'unsold')
})
