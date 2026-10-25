// Contrato HTTP do catálogo do Art Institute of Chicago (Story 2.3). Leitura
// pura: o servidor devolve só estes campos, nunca o JSON da AIC. Os textos
// exibidos nascem do `code`/status, nunca do `message` do servidor.

export interface ArtworkSummary {
  external_id: number
  title: string | null
  artist_display: string | null
  date_display: string | null
  image_id: string
  image_url: string
}

export interface ArtworkDetail extends ArtworkSummary {
  medium_display: string | null
  dimensions: string | null
  department_title: string | null
  artwork_type_title: string | null
  credit_line: string | null
  source_url: string
}

export type CatalogFailure =
  | 'validation'
  | 'unavailable'
  | 'not_found'
  | 'unauthorized'
  | 'forbidden'
  | 'server'

export type SearchResult =
  | { ok: true; items: ArtworkSummary[] }
  | { ok: false; failure: CatalogFailure }

export type DetailResult =
  | { ok: true; artwork: ArtworkDetail }
  | { ok: false; failure: CatalogFailure }

function isNullableString(value: unknown): boolean {
  return value === null || typeof value === 'string'
}

function isArtworkSummary(value: unknown): value is ArtworkSummary {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.external_id === 'number' &&
    isNullableString(candidate.title) &&
    isNullableString(candidate.artist_display) &&
    isNullableString(candidate.date_display) &&
    typeof candidate.image_id === 'string' &&
    typeof candidate.image_url === 'string'
  )
}

function isArtworkDetail(value: unknown): value is ArtworkDetail {
  if (!isArtworkSummary(value)) return false
  const candidate = value as unknown as Record<string, unknown>
  return (
    isNullableString(candidate.medium_display) &&
    isNullableString(candidate.dimensions) &&
    isNullableString(candidate.department_title) &&
    isNullableString(candidate.artwork_type_title) &&
    isNullableString(candidate.credit_line) &&
    typeof candidate.source_url === 'string'
  )
}

function isSearchBody(value: unknown): value is { items: ArtworkSummary[] } {
  if (typeof value !== 'object' || value === null) return false
  const items = (value as { items?: unknown }).items
  return Array.isArray(items) && items.every(isArtworkSummary)
}

function errorCode(value: unknown): string | null {
  if (typeof value !== 'object' || value === null) return null
  const code = (value as { code?: unknown }).code
  return typeof code === 'string' ? code : null
}

// Corpo JSON da resposta, ou null se não for JSON.
async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

// Falha a partir do status e do código do erro. `not_found` só vale no detalhe.
async function failureFrom(
  response: Response,
  allowNotFound: boolean,
): Promise<CatalogFailure> {
  if (response.status === 401) return 'unauthorized'
  if (response.status === 403) return 'forbidden'
  if (response.status === 422) return 'validation'
  if (allowNotFound && response.status === 404) return 'not_found'
  if (response.status === 503) {
    const body = await readJson(response)
    if (errorCode(body) === 'catalog_unavailable') return 'unavailable'
  }
  return 'server'
}

// Um `fetch` abortado cai no `catch` como qualquer falha de rede; quem chama
// descarta o resultado quando o próprio sinal foi abortado.
export async function searchArtworks(
  term: string,
  signal: AbortSignal,
): Promise<SearchResult> {
  let response: Response
  try {
    response = await fetch(
      `/api/catalog/artworks?q=${encodeURIComponent(term)}`,
      { credentials: 'same-origin', signal },
    )
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status !== 200) {
    return { ok: false, failure: await failureFrom(response, false) }
  }
  const body = await readJson(response)
  if (!isSearchBody(body)) return { ok: false, failure: 'server' }
  return { ok: true, items: body.items }
}

export async function fetchArtwork(
  externalId: number,
  signal: AbortSignal,
): Promise<DetailResult> {
  let response: Response
  try {
    response = await fetch(
      `/api/catalog/artworks/${encodeURIComponent(String(externalId))}`,
      { credentials: 'same-origin', signal },
    )
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status !== 200) {
    return { ok: false, failure: await failureFrom(response, true) }
  }
  const body = await readJson(response)
  if (!isArtworkDetail(body)) return { ok: false, failure: 'server' }
  return { ok: true, artwork: body }
}

// Textos exibidos (pt-BR), escolhidos pela falha.
export function catalogFailureMessage(failure: CatalogFailure): string {
  if (failure === 'validation') return 'Digite um termo para buscar.'
  if (failure === 'unavailable') {
    return 'O catálogo do museu não respondeu. Tente novamente em instantes ou use outro termo.'
  }
  if (failure === 'not_found') {
    return 'Esta obra não está disponível para leilão: não foi encontrada ou não é de domínio público com imagem.'
  }
  if (failure === 'forbidden') {
    return 'Sua conta não tem acesso à busca de obras.'
  }
  return 'Não foi possível falar com o servidor. Tente novamente.'
}
