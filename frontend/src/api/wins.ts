import { UUID_PATTERN } from '../route.ts'

export interface MyWin {
  lot_id: string
  title: string | null
  artist_display: string | null
  image_url: string
  phase: 'scheduled' | 'live' | 'ended' | 'cancelled'
  settlement_status: 'pending' | 'settled' | 'not_applicable'
  result: 'won' | 'not_won' | null
  winner_alias: string | null
  final_amount_cents: number | null
  settled_at: string | null
  bid_count: number
}
export interface MyWinsResponse { as_of: string; items: MyWin[] }
export type WinsResult = { ok: true; data: MyWinsResponse } | {
  ok: false; failure: 'unauthorized' | 'forbidden' | 'integrity' | 'server'
}
const record = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)
const date = (v: unknown): v is string => typeof v === 'string' && /T.*(?:Z|[+-]\d\d:\d\d)$/.test(v) && Number.isFinite(Date.parse(v))
const nullableText = (v: unknown) => v === null || typeof v === 'string'
const count = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0
function isItem(v: unknown): v is MyWin {
  if (!record(v) || typeof v.lot_id !== 'string' || !UUID_PATTERN.test(v.lot_id) ||
    !nullableText(v.title) || !nullableText(v.artist_display) ||
    typeof v.image_url !== 'string' || !/^\/api\/catalog\/images\/[a-zA-Z0-9-]+$/.test(v.image_url) ||
    !['scheduled', 'live', 'ended', 'cancelled'].includes(String(v.phase)) ||
    !['pending', 'settled', 'not_applicable'].includes(String(v.settlement_status)) || !count(v.bid_count)) return false
  if (v.phase === 'cancelled') {
    if (v.settlement_status !== 'not_applicable' || v.result !== 'not_won') return false
  } else if (v.settlement_status === 'settled') {
    if (v.phase !== 'ended' || !['won', 'not_won'].includes(String(v.result))) return false
  } else if (v.settlement_status !== 'pending' || v.result !== null) return false
  if (v.result === 'won') return typeof v.winner_alias === 'string' && /^Licitante-[0-9A-F]{16}$/.test(v.winner_alias) && count(v.final_amount_cents) && v.final_amount_cents > 0 && date(v.settled_at) && v.bid_count > 0
  return v.winner_alias === null && v.final_amount_cents === null && v.settled_at === null
}
export function isMyWinsResponse(v: unknown): v is MyWinsResponse {
  return record(v) && date(v.as_of) && Array.isArray(v.items) && v.items.every(isItem) && new Set(v.items.map(item => item.lot_id)).size === v.items.length
}
export async function fetchWins(signal?: AbortSignal): Promise<WinsResult> {
  try {
    const response = await fetch('/api/me/wins', { credentials: 'same-origin', cache: 'no-store', signal })
    if (response.status === 401) return { ok: false, failure: 'unauthorized' }
    if (response.status === 403) return { ok: false, failure: 'forbidden' }
    const body: unknown = await response.json()
    if (response.status === 409 && record(body) && body.code === 'lot_integrity_conflict') return { ok: false, failure: 'integrity' }
    if (response.status !== 200 || !isMyWinsResponse(body)) return { ok: false, failure: 'server' }
    return { ok: true, data: body }
  } catch { return { ok: false, failure: 'server' } }
}
