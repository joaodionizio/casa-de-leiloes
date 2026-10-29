// Contrato HTTP público dos lotes (Story 2.5). Sem sessão: a resposta não depende de
// quem pede. O front só apresenta o que o servidor classificou: `phase` chega pronta
// e nunca é recalculada aqui. Resposta fora do contrato vira falha `server`.

export type LotPhase = 'scheduled' | 'live' | 'ended'

export interface PublicLotSummary {
  id: string
  title: string | null
  artist_display: string | null
  date_display: string | null
  image_url: string
  starting_bid_cents: number
  starts_at: string
  ends_at: string
  phase: LotPhase
  settlement_status: 'pending' | 'settled'
}

export interface PublicLotDetail extends PublicLotSummary {
  external_id: number
  medium_display: string | null
  dimensions: string | null
  department_title: string | null
  artwork_type_title: string | null
  credit_line: string | null
  source_url: string
  min_increment_cents: number
}

export interface PublicLotsResponse {
  as_of: string
  live: PublicLotSummary[]
  scheduled: PublicLotSummary[]
  ended: PublicLotSummary[]
}

export interface PublicLotDetailResponse {
  as_of: string
  lot: PublicLotDetail
}

export type PublicLotsResult =
  | { ok: true; data: PublicLotsResponse }
  | { ok: false; failure: 'server' }

export type PublicLotResult =
  | { ok: true; data: PublicLotDetailResponse }
  | { ok: false; failure: 'not_found' | 'server' }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNullableString(value: unknown): boolean {
  return value === null || typeof value === 'string'
}

// Centavos válidos: inteiro seguro e >= 1 (a faixa da Story 2.4).
function isCents(value: unknown): boolean {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 1
}

function isLotPhase(value: unknown): value is LotPhase {
  return value === 'scheduled' || value === 'live' || value === 'ended'
}

export function isPublicLotSummary(value: unknown): value is PublicLotSummary {
  if (!isRecord(value)) return false
  return (
    typeof value.id === 'string' &&
    isNullableString(value.title) &&
    isNullableString(value.artist_display) &&
    isNullableString(value.date_display) &&
    typeof value.image_url === 'string' &&
    isCents(value.starting_bid_cents) &&
    typeof value.starts_at === 'string' &&
    typeof value.ends_at === 'string' &&
    isLotPhase(value.phase) &&
    (value.settlement_status === 'pending' || value.settlement_status === 'settled')
  )
}

export function isPublicLotDetail(value: unknown): value is PublicLotDetail {
  if (!isPublicLotSummary(value)) return false
  const candidate = value as unknown as Record<string, unknown>
  return (
    typeof candidate.external_id === 'number' &&
    Number.isSafeInteger(candidate.external_id) &&
    isNullableString(candidate.medium_display) &&
    isNullableString(candidate.dimensions) &&
    isNullableString(candidate.department_title) &&
    isNullableString(candidate.artwork_type_title) &&
    isNullableString(candidate.credit_line) &&
    typeof candidate.source_url === 'string' &&
    isCents(candidate.min_increment_cents)
  )
}

function isSummaryList(value: unknown): value is PublicLotSummary[] {
  return Array.isArray(value) && value.every(isPublicLotSummary)
}

export function isPublicLotsResponse(value: unknown): value is PublicLotsResponse {
  if (!isRecord(value)) return false
  return (
    typeof value.as_of === 'string' &&
    isSummaryList(value.live) &&
    isSummaryList(value.scheduled) &&
    isSummaryList(value.ended)
  )
}

export function isPublicLotDetailResponse(
  value: unknown,
): value is PublicLotDetailResponse {
  if (!isRecord(value)) return false
  return typeof value.as_of === 'string' && isPublicLotDetail(value.lot)
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

// Cada chamada é uma fotografia nova: a fase só muda num novo `GET` (P3). O chamador
// ignora o resultado quando o `signal` já foi abortado.
export async function fetchPublicLots(signal: AbortSignal): Promise<PublicLotsResult> {
  let response: Response
  try {
    response = await fetch('/api/lots', { credentials: 'same-origin', signal })
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status !== 200) return { ok: false, failure: 'server' }
  const body = await readJson(response)
  if (!isPublicLotsResponse(body)) return { ok: false, failure: 'server' }
  return { ok: true, data: body }
}

export async function fetchPublicLot(
  lotId: string,
  signal: AbortSignal,
): Promise<PublicLotResult> {
  let response: Response
  try {
    response = await fetch(`/api/lots/${encodeURIComponent(lotId)}`, {
      credentials: 'same-origin',
      signal,
    })
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status === 404 || response.status === 422) {
    return { ok: false, failure: 'not_found' }
  }
  if (response.status !== 200) return { ok: false, failure: 'server' }
  const body = await readJson(response)
  if (!isPublicLotDetailResponse(body)) return { ok: false, failure: 'server' }
  return { ok: true, data: body }
}
