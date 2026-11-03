import type { BidRoom } from './api/bids.ts'

// The public settlement is authoritative, but personal ownership is only
// confirmed after reading the authenticated bidder's participation.
export type BidderSettlement =
  | 'won'
  | 'lost'
  | 'not_participated'
  | 'unsold'
  | 'unverified'

export function classifyBidderSettlement(
  room: Pick<BidRoom, 'phase' | 'settlement_status' | 'settlement'>,
  ownAlias: string | null,
  ownBidCount: number | null,
  participationVerified: boolean,
): BidderSettlement | null {
  if (room.phase !== 'ended' || room.settlement_status !== 'settled' || room.settlement === null) {
    return null
  }
  if (room.settlement.outcome === 'unsold') return 'unsold'
  if (!participationVerified || ownAlias === null || ownBidCount === null) return 'unverified'
  if (room.settlement.winner_alias === ownAlias) {
    return ownBidCount > 0 ? 'won' : 'unverified'
  }
  return ownBidCount > 0 ? 'lost' : 'not_participated'
}
