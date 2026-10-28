import { isBidRoom, isPublicSettlement, isTimestamp, publicSettlement, type BidRoom, type PublicSettlement } from './api/bids.ts'

export type ConnectionState = 'connecting' | 'connected' | 'unavailable' | 'reconnecting' | 'terminal' | 'disposed'
export type RoomMessage =
  | { type: 'room_snapshot' | 'bid_accepted'; lot_id: string; room: BidRoom }
  | { type: 'lot_cancelled'; lot_id: string; cancelled_at: string }
  | ({ type: 'lot_closed'; lot_id: string; as_of: string } & PublicSettlement)

function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).length === keys.length && keys.every((key) => key in value)
}

export function parseRoomMessage(data: unknown): RoomMessage | null {
  if (typeof data !== 'string') return null
  let value: unknown
  try { value = JSON.parse(data) } catch { return null }
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null
  const event = value as Record<string, unknown>
  if (typeof event.lot_id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(event.lot_id)) return null
  if (event.type === 'lot_cancelled') {
    return exactKeys(event, ['type', 'lot_id', 'cancelled_at']) && isTimestamp(event.cancelled_at)
      ? event as unknown as RoomMessage : null
  }
  if (event.type === 'lot_closed') {
    const settlement = publicSettlement(event as unknown as PublicSettlement)
    return exactKeys(event, ['type', 'lot_id', 'outcome', 'winner_alias', 'final_amount_cents', 'bid_count', 'final_hash', 'settled_at', 'as_of']) &&
      isPublicSettlement(settlement) && event.as_of === settlement.settled_at
      ? event as unknown as RoomMessage : null
  }
  if ((event.type === 'room_snapshot' || event.type === 'bid_accepted') &&
      exactKeys(event, ['type', 'lot_id', 'room']) && isBidRoom(event.room)) {
    return event as unknown as RoomMessage
  }
  return null
}

// Preserve PostgreSQL's microseconds, including equivalent UTC offset spellings.
function timestampMicros(value: string): bigint {
  const fraction = /\.(\d{1,6})/.exec(value)?.[1] ?? ''
  return BigInt(Math.floor(Date.parse(value) / 1000)) * 1_000_000n +
    BigInt(fraction.padEnd(6, '0'))
}

export function shouldApplyRoom(
  current: BidRoom | null,
  incoming: BidRoom,
  cancelled = false,
  currentLotId?: string,
  incomingLotId = currentLotId,
): boolean {
  if (cancelled || incomingLotId !== currentLotId) return false
  if (current === null) return true
  if (current.settlement_status === 'settled') {
    if (incoming.settlement_status !== 'settled' ||
        !sameSettlement(current.settlement, incoming.settlement)) return false
  } else if (incoming.settlement_status === 'settled') return true
  if (incoming.bid_count !== current.bid_count) return incoming.bid_count > current.bid_count
  return timestampMicros(incoming.as_of) >= timestampMicros(current.as_of)
}

// Mesmo estado público, ignorando só o `as_of`: o servidor produz um `as_of` novo em
// cada releitura, então comparar a sala inteira nunca acharia um duplicado.
export function sameRoomState(a: BidRoom, b: BidRoom): boolean {
  return (
    a.settlement_status === b.settlement_status &&
    sameSettlement(a.settlement, b.settlement) &&
    a.phase === b.phase &&
    a.ends_at === b.ends_at &&
    a.current_bid_cents === b.current_bid_cents &&
    a.minimum_next_bid_cents === b.minimum_next_bid_cents &&
    a.bid_count === b.bid_count &&
    a.bids.length === b.bids.length &&
    a.bids.every(
      (bid, index) =>
        bid.sequence === b.bids[index].sequence &&
        bid.bidder_alias === b.bids[index].bidder_alias &&
        bid.amount_cents === b.bids[index].amount_cents &&
        bid.placed_at === b.bids[index].placed_at,
    )
  )
}

export function sameSettlement(a: PublicSettlement | null, b: PublicSettlement | null): boolean {
  if (a === null || b === null) return a === b
  return timestampMicros(a.settled_at) === timestampMicros(b.settled_at) &&
    a.outcome === b.outcome && a.final_hash === b.final_hash &&
    a.bid_count === b.bid_count && a.winner_alias === b.winner_alias &&
    a.final_amount_cents === b.final_amount_cents
}

// A sparse terminal frame retains the known history; a pure REST read can fill
// missed bids afterwards without delaying terminal transport cleanup.
export function roomWithSettlement(current: BidRoom, result: PublicSettlement): BidRoom {
  return { ...current, phase: 'ended', settlement_status: 'settled', settlement: result }
}

export function roomSocketUrl(lotId: string, origin: string): string {
  const url = new URL(`/ws/lots/${encodeURIComponent(lotId)}`, origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.href
}
