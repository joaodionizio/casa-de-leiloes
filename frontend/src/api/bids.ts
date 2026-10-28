// Contrato HTTP da sala do lote (Story 3.5). O servidor decide fase, mínimo e aceite:
// este módulo só lê, valida o formato e classifica respostas. Os textos nascem do
// status e do `code`, nunca do `message`. Sem retry: um lance nunca é reenviado
// automaticamente. Arquivo sem DOM, para o `node --test`.

import { isWalletResponse } from './wallet.ts'
import type { WalletResponse } from './wallet.ts'

export type RoomPhase = 'scheduled' | 'live' | 'ended'

export interface BidItem {
  sequence: number
  bidder_alias: string
  amount_cents: number
  placed_at: string
}

export interface BidRoom {
  as_of: string
  phase: RoomPhase
  ends_at: string
  current_bid_cents: number | null
  minimum_next_bid_cents: number | null
  bid_count: number
  bids: BidItem[]
  settlement_status: 'pending' | 'settled'
  settlement: PublicSettlement | null
}

export interface PublicSettlement {
  outcome: 'sold' | 'unsold'
  winner_alias: string | null
  final_amount_cents: number | null
  bid_count: number
  final_hash: string
  settled_at: string
}

export function publicSettlement(value: PublicSettlement): PublicSettlement {
  return { outcome: value.outcome, winner_alias: value.winner_alias,
    final_amount_cents: value.final_amount_cents, bid_count: value.bid_count,
    final_hash: value.final_hash, settled_at: value.settled_at }
}

export interface MyBids {
  bidder_alias: string
  my_bid_count: number
  last_bid_cents: number | null
}

export interface PlacedBidResponse {
  bid: BidItem
  lot: {
    current_bid_cents: number
    ends_at: string
    anti_sniping_applied: boolean
  }
  wallet: WalletResponse
}

export type ReadFailure = 'unauthorized' | 'forbidden' | 'not_found' | 'server'

export type ReadResult<T> = { ok: true; data: T } | { ok: false; failure: ReadFailure }

// Recusas que o servidor decidiu: o lance certamente não foi gravado.
export type KnownBidFailure =
  | 'below_minimum'
  | 'insufficient_balance'
  | 'already_winning'
  | 'lot_not_started'
  | 'lot_ended'
  | 'lot_cancelled' // Story 3.6
  | 'integrity' // 409 lot_integrity_conflict
  | 'validation' // 422 validation_error
  | 'forbidden' // 403 forbidden (papel)
  | 'unauthorized' // 401
  | 'not_found' // 404
  | 'rejected' // outro 4xx (403 csrf_*, 415...): o servidor não gravou

export type BidFailure = KnownBidFailure | 'ambiguous'

export type BidResult =
  | { ok: true; placed: PlacedBidResponse }
  | { ok: false; failure: BidFailure }

const MAX_WINDOW = 50
const ALIAS_PATTERN = /^Licitante-[0-9A-F]{16}$/
const TIMESTAMP_PATTERN =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function isTimestamp(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    TIMESTAMP_PATTERN.test(value) &&
    !Number.isNaN(Date.parse(value))
  )
}

function isCents(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 1
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
}

function isNullableCents(value: unknown): boolean {
  return value === null || isCents(value)
}

export function isBidItem(value: unknown): value is BidItem {
  if (!isRecord(value)) return false
  return (
    typeof value.sequence === 'number' &&
    Number.isSafeInteger(value.sequence) &&
    value.sequence >= 1 &&
    typeof value.bidder_alias === 'string' &&
    ALIAS_PATTERN.test(value.bidder_alias) &&
    isCents(value.amount_cents) &&
    isTimestamp(value.placed_at)
  )
}

export function isBidRoom(value: unknown): value is BidRoom {
  if (!isRecord(value)) return false
  return (
    isTimestamp(value.as_of) &&
    (value.phase === 'scheduled' || value.phase === 'live' || value.phase === 'ended') &&
    isTimestamp(value.ends_at) &&
    isNullableCents(value.current_bid_cents) &&
    isNullableCents(value.minimum_next_bid_cents) &&
    isCount(value.bid_count) &&
    Array.isArray(value.bids) &&
    value.bids.length <= MAX_WINDOW &&
    value.bids.every(isBidItem) &&
    ((value.settlement_status === 'pending' && value.settlement === null) ||
     (value.settlement_status === 'settled' && isPublicSettlement(value.settlement)))
  )
}

export function isPublicSettlement(value: unknown): value is PublicSettlement {
  if (!isRecord(value)) return false
  const keys = ['outcome', 'winner_alias', 'final_amount_cents', 'bid_count', 'final_hash', 'settled_at']
  if (Object.keys(value).length !== keys.length || !keys.every((key) => key in value) ||
      !isTimestamp(value.settled_at) || !value.settled_at.endsWith('Z') ||
      typeof value.final_hash !== 'string' || !/^[0-9a-f]{64}$/.test(value.final_hash) ||
      !isCount(value.bid_count)) return false
  return value.outcome === 'sold'
    ? value.bid_count > 0 && typeof value.winner_alias === 'string' &&
      ALIAS_PATTERN.test(value.winner_alias) && isCents(value.final_amount_cents)
    : value.outcome === 'unsold' && value.bid_count === 0 && value.winner_alias === null &&
      value.final_amount_cents === null && value.final_hash === '0'.repeat(64)
}

export function isMyBids(value: unknown): value is MyBids {
  if (!isRecord(value)) return false
  return (
    typeof value.bidder_alias === 'string' &&
    ALIAS_PATTERN.test(value.bidder_alias) &&
    isCount(value.my_bid_count) &&
    isNullableCents(value.last_bid_cents)
  )
}

// 201 seguro: formato completo, carteira coerente e o lance igual ao lance atual.
export function isPlacedBidResponse(value: unknown): value is PlacedBidResponse {
  if (!isRecord(value) || !isRecord(value.lot)) return false
  const lot = value.lot
  return (
    isBidItem(value.bid) &&
    isCents(lot.current_bid_cents) &&
    isTimestamp(lot.ends_at) &&
    typeof lot.anti_sniping_applied === 'boolean' &&
    isWalletResponse(value.wallet) &&
    value.bid.amount_cents === lot.current_bid_cents
  )
}

function errorCode(value: unknown): string | null {
  if (!isRecord(value)) return null
  return typeof value.code === 'string' ? value.code : null
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

async function fetchRead<T>(
  path: string,
  signal: AbortSignal | undefined,
  guard: (value: unknown) => value is T,
): Promise<ReadResult<T>> {
  let response: Response
  try {
    response = await fetch(path, { credentials: 'same-origin', signal })
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status === 401) return { ok: false, failure: 'unauthorized' }
  if (response.status === 403) return { ok: false, failure: 'forbidden' }
  if (response.status === 404 || response.status === 422) {
    return { ok: false, failure: 'not_found' }
  }
  if (response.status !== 200) return { ok: false, failure: 'server' }
  const body = await readJson(response)
  if (!guard(body)) return { ok: false, failure: 'server' }
  return { ok: true, data: body }
}

export function fetchBidRoom(lotId: string, signal?: AbortSignal): Promise<ReadResult<BidRoom>> {
  return fetchRead(`/api/lots/${encodeURIComponent(lotId)}/bids`, signal, isBidRoom)
}

export function fetchMyBids(lotId: string, signal?: AbortSignal): Promise<ReadResult<MyBids>> {
  return fetchRead(`/api/lots/${encodeURIComponent(lotId)}/bids/mine`, signal, isMyBids)
}

const BUSINESS_CODES: Record<string, KnownBidFailure> = {
  below_minimum: 'below_minimum',
  insufficient_balance: 'insufficient_balance',
  already_winning: 'already_winning',
  lot_not_started: 'lot_not_started',
  lot_ended: 'lot_ended',
  lot_cancelled: 'lot_cancelled',
}

// Classifica uma resposta já lida do POST. Separado do `fetch` para o teste puro.
export function classifyBidResponse(status: number, body: unknown): BidResult {
  if (status === 201) {
    if (!isPlacedBidResponse(body)) return { ok: false, failure: 'ambiguous' }
    return { ok: true, placed: body }
  }
  if (status >= 500) return { ok: false, failure: 'ambiguous' }
  const code = errorCode(body)
  if (status === 422 && code !== null && code in BUSINESS_CODES) {
    return { ok: false, failure: BUSINESS_CODES[code] }
  }
  if (status === 422 && code === 'validation_error') {
    return { ok: false, failure: 'validation' }
  }
  if (status === 409 && code === 'lot_integrity_conflict') {
    return { ok: false, failure: 'integrity' }
  }
  if (status === 401) return { ok: false, failure: 'unauthorized' }
  if (status === 403 && code === 'forbidden') return { ok: false, failure: 'forbidden' }
  if (status === 404) return { ok: false, failure: 'not_found' }
  if (status >= 400) return { ok: false, failure: 'rejected' }
  // 1xx/2xx/3xx inesperado: não dá para afirmar nada.
  return { ok: false, failure: 'ambiguous' }
}

export async function placeBid(lotId: string, amountCents: number): Promise<BidResult> {
  let response: Response
  try {
    response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/bids`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount_cents: amountCents }),
    })
  } catch {
    return { ok: false, failure: 'ambiguous' }
  }
  return classifyBidResponse(response.status, await readJson(response))
}
