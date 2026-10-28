export interface Receipt {
  lot_id: string
  title: string | null
  artist_display: string | null
  image_url: string
  winner_alias: string
  winning_bid_sequence: number
  final_amount_cents: number
  settled_at: string
  bid_count: number
  final_hash: string
}
export type ReceiptResult = { ok: true; data: Receipt } | { ok: false; failure: 'not_found' | 'conflict' | 'server' }

export function isReceipt(value: unknown, lotId: string): value is Receipt {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false
  const v = value as Record<string, unknown>
  const fields = 'lot_id title artist_display image_url winner_alias winning_bid_sequence final_amount_cents settled_at bid_count final_hash'.split(' ')
  return Object.keys(v).length === fields.length && Object.keys(v).every(k => fields.includes(k)) &&
    v.lot_id === lotId && (v.title === null || typeof v.title === 'string') &&
    (v.artist_display === null || typeof v.artist_display === 'string') &&
    typeof v.image_url === 'string' && /^\/api\/catalog\/images\/[a-zA-Z0-9-]+$/.test(v.image_url) &&
    typeof v.winner_alias === 'string' && /^Licitante-[0-9A-F]{16}$/.test(v.winner_alias) &&
    typeof v.bid_count === 'number' && Number.isSafeInteger(v.bid_count) && v.bid_count > 0 &&
    v.winning_bid_sequence === v.bid_count && typeof v.final_amount_cents === 'number' &&
    Number.isSafeInteger(v.final_amount_cents) && v.final_amount_cents > 0 &&
    typeof v.settled_at === 'string' && !Number.isNaN(Date.parse(v.settled_at)) &&
    typeof v.final_hash === 'string' && /^[0-9a-f]{64}$/.test(v.final_hash)
}
export async function fetchReceipt(lotId: string, signal: AbortSignal): Promise<ReceiptResult> {
  try {
    const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/receipt`, { credentials: 'same-origin', cache: 'no-store', signal })
    if (response.status === 404) return { ok: false, failure: 'not_found' }
    if (response.status === 409) return { ok: false, failure: 'conflict' }
    if (response.status === 200) {
      const data: unknown = await response.json()
      if (isReceipt(data, lotId)) return { ok: true, data }
    }
  } catch { /* Request failure or abort. */ }
  return { ok: false, failure: 'server' }
}
