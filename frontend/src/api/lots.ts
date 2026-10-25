// Contrato HTTP dos lotes (Story 2.4). O servidor é a única fonte do snapshot da
// obra: o corpo do POST leva só `external_id` e os termos. Os textos exibidos
// nascem do status, do `code` e do `details.type`, nunca do `message`.

export interface LotResponse {
  id: string
  external_id: number
  title: string | null
  artist_display: string | null
  date_display: string | null
  medium_display: string | null
  dimensions: string | null
  department_title: string | null
  artwork_type_title: string | null
  credit_line: string | null
  source_url: string
  image_id: string
  image_url: string
  starting_bid_cents: number
  min_increment_cents: number
  starts_at: string
  ends_at: string
  created_at: string
}

export interface CreateLotRequest {
  external_id: number
  starting_bid_cents: number
  min_increment_cents: number
  // null = "assim que eu publicar": o servidor usa a hora do banco.
  starts_at: string | null
  ends_at: string
}

export type LotField =
  | 'starting_bid_cents'
  | 'min_increment_cents'
  | 'starts_at'
  | 'ends_at'

export interface FieldProblem {
  field: LotField | null
  type: string
}

export type CreateLotFailure =
  | { kind: 'validation'; problems: FieldProblem[] }
  | { kind: 'not_eligible' }
  | { kind: 'unavailable' }
  | { kind: 'unauthorized' }
  | { kind: 'forbidden' }
  // Rede, 5xx, 403 de origem ou corpo fora do contrato: o resultado é incerto.
  | { kind: 'unknown' }

export type CreateLotResult =
  | { ok: true; lot: LotResponse }
  | { ok: false; failure: CreateLotFailure }

export type MyLotsFailure = 'unauthorized' | 'forbidden' | 'server'

export type MyLotsResult =
  | { ok: true; items: LotResponse[] }
  | { ok: false; failure: MyLotsFailure }

const LOT_FIELDS: LotField[] = [
  'starting_bid_cents',
  'min_increment_cents',
  'starts_at',
  'ends_at',
]

function isNullableString(value: unknown): boolean {
  return value === null || typeof value === 'string'
}

function isCents(value: unknown): boolean {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 1
}

function isLotResponse(value: unknown): value is LotResponse {
  if (typeof value !== 'object' || value === null) return false
  const lot = value as Record<string, unknown>
  return (
    typeof lot.id === 'string' &&
    typeof lot.external_id === 'number' &&
    isNullableString(lot.title) &&
    isNullableString(lot.artist_display) &&
    isNullableString(lot.date_display) &&
    isNullableString(lot.medium_display) &&
    isNullableString(lot.dimensions) &&
    isNullableString(lot.department_title) &&
    isNullableString(lot.artwork_type_title) &&
    isNullableString(lot.credit_line) &&
    typeof lot.source_url === 'string' &&
    typeof lot.image_id === 'string' &&
    typeof lot.image_url === 'string' &&
    isCents(lot.starting_bid_cents) &&
    isCents(lot.min_increment_cents) &&
    typeof lot.starts_at === 'string' &&
    typeof lot.ends_at === 'string' &&
    typeof lot.created_at === 'string'
  )
}

function isMyLotsBody(value: unknown): value is { items: LotResponse[] } {
  if (typeof value !== 'object' || value === null) return false
  const items = (value as { items?: unknown }).items
  return Array.isArray(items) && items.every(isLotResponse)
}

function errorCode(value: unknown): string | null {
  if (typeof value !== 'object' || value === null) return null
  const code = (value as { code?: unknown }).code
  return typeof code === 'string' ? code : null
}

// `details` do 422: `[{loc: ["body", "<campo>"], type}]`. Campo desconhecido → null.
function problemsFrom(value: unknown): FieldProblem[] {
  if (typeof value !== 'object' || value === null) return []
  const details = (value as { details?: unknown }).details
  if (!Array.isArray(details)) return []
  const problems: FieldProblem[] = []
  for (const detail of details) {
    if (typeof detail !== 'object' || detail === null) continue
    const { loc, type } = detail as { loc?: unknown; type?: unknown }
    if (typeof type !== 'string') continue
    let field: LotField | null = null
    if (Array.isArray(loc) && loc[0] === 'body') {
      field = LOT_FIELDS.find((name) => name === loc[1]) ?? null
    }
    problems.push({ field, type })
  }
  return problems
}

// Corpo JSON da resposta, ou null se não for JSON.
async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function createLot(request: CreateLotRequest): Promise<CreateLotResult> {
  let response: Response
  try {
    response = await fetch('/api/lots', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  } catch {
    return { ok: false, failure: { kind: 'unknown' } }
  }
  const body = await readJson(response)
  if (response.status === 201) {
    if (!isLotResponse(body)) return { ok: false, failure: { kind: 'unknown' } }
    return { ok: true, lot: body }
  }
  const code = errorCode(body)
  if (response.status === 422 && code === 'artwork_not_eligible') {
    return { ok: false, failure: { kind: 'not_eligible' } }
  }
  if (response.status === 422 && code === 'validation_error') {
    return { ok: false, failure: { kind: 'validation', problems: problemsFrom(body) } }
  }
  if (response.status === 503 && code === 'catalog_unavailable') {
    return { ok: false, failure: { kind: 'unavailable' } }
  }
  if (response.status === 401) return { ok: false, failure: { kind: 'unauthorized' } }
  if (response.status === 403 && code === 'forbidden') {
    return { ok: false, failure: { kind: 'forbidden' } }
  }
  return { ok: false, failure: { kind: 'unknown' } }
}

// Um `fetch` abortado cai no `catch` como qualquer falha de rede; quem chama
// descarta o resultado quando o próprio sinal foi abortado.
export async function fetchMyLots(signal: AbortSignal): Promise<MyLotsResult> {
  let response: Response
  try {
    response = await fetch('/api/lots/mine', { credentials: 'same-origin', signal })
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status === 401) return { ok: false, failure: 'unauthorized' }
  if (response.status === 403) return { ok: false, failure: 'forbidden' }
  if (response.status !== 200) return { ok: false, failure: 'server' }
  const body = await readJson(response)
  if (!isMyLotsBody(body)) return { ok: false, failure: 'server' }
  return { ok: true, items: body.items }
}
