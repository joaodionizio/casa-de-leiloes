const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const MAX_CENTS = Number.MAX_SAFE_INTEGER

export interface AuditBid {
  sequence: number
  bidder_alias: string
  amount_cents: number
  placed_at: string
  canonical_version: 1
  previous_hash: string
  current_hash: string
}
export interface AuditSettlement {
  outcome: 'sold' | 'unsold'
  winner_alias: string | null
  final_amount_cents: number | null
  bid_count: number
  final_hash: string
  settled_at: string
}
export interface Audit {
  lot_id: string
  as_of: string
  integrity: 'verified' | 'adulterated'
  phase: 'scheduled' | 'live' | 'ended' | 'cancelled' | null
  settlement_status: 'pending' | 'settled' | 'not_applicable' | null
  settlement: AuditSettlement | null
  bid_count: number | null
  final_hash: string | null
  bids: AuditBid[]
}
export type AuditResult = { ok: true; data: Audit } | { ok: false; failure: 'not_found' | 'server' }
const HASH = /^[0-9a-f]{64}$/
const ALIAS = /^Licitante-[0-9A-F]{16}$/
const GENESIS = '0'.repeat(64)
function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
function keys(value: Record<string, unknown>, expected: string): boolean {
  const names = expected.split(' ')
  return Object.keys(value).length === names.length && Object.keys(value).every(key => names.includes(key))
}
function integer(value: unknown, minimum = 0): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum && value <= MAX_CENTS
}
function timestamp(value: unknown): value is string {
  return typeof value === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{1,6})?Z$/.test(value) &&
    !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 19) === value.slice(0, 19)
}
function hash(value: unknown): value is string { return typeof value === 'string' && HASH.test(value) }
function alias(value: unknown): value is string { return typeof value === 'string' && ALIAS.test(value) }

export function isAudit(value: unknown, lotId: string): value is Audit {
  if (!object(value) || !keys(value, 'lot_id as_of integrity phase settlement_status settlement bid_count final_hash bids') ||
    value.lot_id !== lotId || !UUID_PATTERN.test(lotId) || !timestamp(value.as_of) || !Array.isArray(value.bids)) return false
  if (value.integrity === 'adulterated') {
    return value.phase === null && value.settlement_status === null && value.settlement === null &&
      value.bid_count === null && value.final_hash === null && value.bids.length === 0
  }
  if (value.integrity !== 'verified' || !integer(value.bid_count) || value.bid_count !== value.bids.length || !hash(value.final_hash)) return false
  let previous = GENESIS
  for (const [index, bid] of value.bids.entries()) {
    if (!object(bid) || !keys(bid, 'sequence bidder_alias amount_cents placed_at canonical_version previous_hash current_hash') ||
      bid.sequence !== index + 1 || !alias(bid.bidder_alias) || !integer(bid.amount_cents, 1) ||
      !timestamp(bid.placed_at) || Date.parse(bid.placed_at) > Date.parse(value.as_of) || bid.canonical_version !== 1 ||
      bid.previous_hash !== previous || !hash(bid.current_hash)) return false
    previous = bid.current_hash
  }
  if (value.final_hash !== previous) return false
  if (value.phase === 'cancelled') return value.settlement_status === 'not_applicable' && value.settlement === null
  if (!['scheduled', 'live', 'ended'].includes(String(value.phase))) return false
  if (value.settlement_status === 'pending') return value.settlement === null
  if (value.settlement_status !== 'settled' || value.phase !== 'ended' || !object(value.settlement)) return false
  const s = value.settlement
  if (!keys(s, 'outcome winner_alias final_amount_cents bid_count final_hash settled_at') ||
    s.bid_count !== value.bid_count || s.final_hash !== value.final_hash || !timestamp(s.settled_at) || Date.parse(s.settled_at) > Date.parse(value.as_of)) return false
  const last = value.bids.at(-1) as AuditBid | undefined
  if (s.outcome === 'unsold') return value.bid_count === 0 && s.winner_alias === null && s.final_amount_cents === null
  return s.outcome === 'sold' && last !== undefined && s.winner_alias === last.bidder_alias && s.final_amount_cents === last.amount_cents
}

export async function fetchAudit(lotId: string, signal: AbortSignal): Promise<AuditResult> {
  try {
    const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/audit`, { credentials: 'same-origin', cache: 'no-store', signal })
    if (response.status === 404) return { ok: false, failure: 'not_found' }
    if (response.status !== 200) return { ok: false, failure: 'server' }
    const data: unknown = await response.json()
    if (isAudit(data, lotId)) return { ok: true, data }
  } catch { /* Network, malformed JSON and abort are discarded by the caller. */ }
  return { ok: false, failure: 'server' }
}
