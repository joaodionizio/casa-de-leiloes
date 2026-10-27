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

// Item da lista do leiloeiro (Story 3.6, D7): o `LotResponse` mais o cancelamento, a
// contagem persistida (dica de UX, não autenticada) e a fase temporal que o servidor
// calculou com o `as_of`. O 201 da criação continua devolvendo `LotResponse`.
export type MyLotPhase = 'scheduled' | 'live' | 'ended'

export interface MyLotResponse extends LotResponse {
  cancelled_at: string | null
  bid_count: number
  phase: MyLotPhase
}

export interface MyLotsBody {
  as_of: string
  items: MyLotResponse[]
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
  | { ok: true; asOf: string; items: MyLotResponse[] }
  | { ok: false; failure: MyLotsFailure }

// Falhas do POST de cancelamento. As de negócio (`has_bids`, `ended`, `integrity`,
// `forbidden`, `not_found`, `unauthorized`) o servidor decidiu; `ambiguous` é rede, 5xx,
// corpo fora do contrato ou código desconhecido: o resultado é incerto.
export type CancelLotFailure =
  | 'has_bids'
  | 'ended'
  | 'integrity'
  | 'forbidden'
  | 'not_found'
  | 'unauthorized'
  | 'ambiguous'

export type CancelLotResult =
  | { ok: true; cancelledAt: string }
  | { ok: false; failure: CancelLotFailure }

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

// ISO 8601 com fuso, como o servidor serializa (a fração pode faltar quando é zero).
const TIMESTAMP_PATTERN =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/

function isTimestamp(value: unknown): value is string {
  return (
    typeof value === 'string' && TIMESTAMP_PATTERN.test(value) && !Number.isNaN(Date.parse(value))
  )
}

function isMyLot(value: unknown): value is MyLotResponse {
  if (!isLotResponse(value)) return false
  const lot = value as unknown as Record<string, unknown>
  return (
    (lot.cancelled_at === null || isTimestamp(lot.cancelled_at)) &&
    typeof lot.bid_count === 'number' &&
    Number.isSafeInteger(lot.bid_count) &&
    lot.bid_count >= 0 &&
    (lot.phase === 'scheduled' || lot.phase === 'live' || lot.phase === 'ended')
  )
}

// Uma lista sem `as_of` (contrato antigo) não é sucesso nem lista vazia.
export function isMyLotsBody(value: unknown): value is MyLotsBody {
  if (typeof value !== 'object' || value === null) return false
  const body = value as { as_of?: unknown; items?: unknown }
  return isTimestamp(body.as_of) && Array.isArray(body.items) && body.items.every(isMyLot)
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
  return { ok: true, asOf: body.as_of, items: body.items }
}

// Classifica uma resposta já lida do POST. Separado do `fetch` para o teste puro. Só o
// `code` decide; o `message` do servidor nunca é lido. Só o 200 com `id` do lote pedido
// e `cancelled_at` válido é sucesso.
export function classifyCancelResponse(
  status: number,
  body: unknown,
  lotId: string,
): CancelLotResult {
  if (status === 200) {
    const data = (typeof body === 'object' && body !== null ? body : {}) as {
      id?: unknown
      cancelled_at?: unknown
    }
    if (data.id !== lotId || !isTimestamp(data.cancelled_at)) {
      return { ok: false, failure: 'ambiguous' }
    }
    return { ok: true, cancelledAt: data.cancelled_at }
  }
  const code = errorCode(body)
  if (status === 422 && code === 'lot_has_bids') return { ok: false, failure: 'has_bids' }
  if (status === 422 && code === 'lot_ended') return { ok: false, failure: 'ended' }
  if (status === 409 && code === 'lot_integrity_conflict') {
    return { ok: false, failure: 'integrity' }
  }
  if (status === 403 && code === 'forbidden') return { ok: false, failure: 'forbidden' }
  if (status === 404 && code === 'not_found') return { ok: false, failure: 'not_found' }
  if (status === 401) return { ok: false, failure: 'unauthorized' }
  // Rede, 5xx, 403/415 de proteção (csrf_*), 422 de validação, código desconhecido ou
  // qualquer outra coisa: não dá para afirmar o resultado.
  return { ok: false, failure: 'ambiguous' }
}

// Um único `fetch`, sem corpo, sem retry: o servidor é a autoridade e idempotente, mas o
// cliente nunca reenvia sozinho.
export async function cancelLot(lotId: string): Promise<CancelLotResult> {
  let response: Response
  try {
    response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/cancel`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    return { ok: false, failure: 'ambiguous' }
  }
  return classifyCancelResponse(response.status, await readJson(response), lotId)
}
