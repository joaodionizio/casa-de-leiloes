// API simulada por interceptação de rede do Playwright. O front fala com `/api/...`
// como em produção; aqui as respostas vêm de dados controlados pelo teste. Nada toca o
// banco de desenvolvimento, a AIC ou o proxy de imagem real.

import type { Page, Route } from '@playwright/test'

export type Phase = 'scheduled' | 'live' | 'ended'
export type Role = 'AUCTIONEER' | 'BIDDER'

export interface MockLot {
  id: string
  title: string | null
  artist_display: string | null
  date_display: string | null
  image_url: string
  starting_bid_cents: number
  starts_at: string
  ends_at: string
  phase: Phase
  external_id: number
  medium_display: string | null
  dimensions: string | null
  department_title: string | null
  artwork_type_title: string | null
  credit_line: string | null
  source_url: string
  min_increment_cents: number
}

export const AS_OF = '2026-10-25T14:30:00.123456Z'
export const MAX_CENTS = 9007199254740991
export const LONG_TITLE =
  'Uma tarde de domingo na ilha de La Grande Jatte com um título excessivamente longo para testar a quebra de linha '.repeat(
    2,
  )

export function lotId(n: number): string {
  return `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
}

const BASE = Date.UTC(2026, 9, 25, 12, 0, 0)
const HOUR = 3_600_000

function iso(offsetHours: number): string {
  return new Date(BASE + offsetHours * HOUR).toISOString()
}

export function makeLot(
  n: number,
  phase: Phase,
  overrides: Partial<MockLot> = {},
): MockLot {
  // Ao vivo termina em horas diferentes (a ordem do servidor é ends_at crescente).
  const window =
    phase === 'live'
      ? { starts_at: iso(-3), ends_at: iso(1 + n) }
      : phase === 'scheduled'
        ? { starts_at: iso(2 + n), ends_at: iso(30 + n) }
        : { starts_at: iso(-80 - n), ends_at: iso(-30 - n) }
  return {
    id: lotId(n),
    title: `Obra de teste ${n}`,
    artist_display: `Artista ${n}\n(Francês, 1859–1891)`,
    date_display: '1884–86',
    image_url: `/api/catalog/images/2d484387-2509-5e8e-2c43-22f9981972${String(n % 100).padStart(2, '0')}`,
    starting_bid_cents: 10_000 + n * 1_000,
    ...window,
    phase,
    external_id: 27_000 + n,
    medium_display: 'Óleo sobre tela',
    dimensions: '207,5 × 308,1 cm',
    department_title: 'Pintura e Escultura da Europa',
    artwork_type_title: 'Pintura',
    credit_line: 'Coleção Helen Birch Bartlett',
    source_url: `https://www.artic.edu/artworks/${27_000 + n}`,
    min_increment_cents: 1_000,
    ...overrides,
  }
}

// Ao vivo: 1..live; agendados: 101..; encerrados: 201.. (a numeração só serve de id).
export function makeLots(count: {
  live?: number
  scheduled?: number
  ended?: number
}): MockLot[] {
  const lots: MockLot[] = []
  for (let i = 1; i <= (count.live ?? 0); i += 1) lots.push(makeLot(i, 'live'))
  for (let i = 1; i <= (count.scheduled ?? 0); i += 1) {
    lots.push(makeLot(100 + i, 'scheduled'))
  }
  for (let i = 1; i <= (count.ended ?? 0); i += 1) {
    lots.push(makeLot(200 + i, 'ended'))
  }
  return lots
}

const SUMMARY_KEYS = [
  'id',
  'title',
  'artist_display',
  'date_display',
  'image_url',
  'starting_bid_cents',
  'starts_at',
  'ends_at',
  'phase',
] as const

function summary(lot: MockLot): Record<string, unknown> {
  const picked: Record<string, unknown> = {}
  for (const key of SUMMARY_KEYS) picked[key] = lot[key]
  return picked
}

// PNG 1×1: o `<img>` do proxy de imagem decodifica de verdade.
const PIXEL = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
)

export interface MockOptions {
  lots?: MockLot[]
  // Sessão inicial: anônimo, ou já autenticado com o papel dado.
  session?: Role | null
  // `broken`: toda imagem responde 503, como a rota real quando o IIIF falha.
  images?: 'ok' | 'broken'
  // Carteira inicial de cada licitante (Story 3.1), em centavos. Padrão: zerada. Cada
  // conta tem a sua: o depósito de uma nunca aparece na outra.
  wallet?: { total: number; committed: number }
  // Resposta do `POST /api/wallet/deposit`. `ok` soma ao estado; `server_error` e
  // `network` são erros ambíguos (o depósito pode ou não ter entrado, ver abaixo).
  deposit?: 'ok' | 'limit' | 'validation' | 'server_error' | 'network'
  // Atraso do `POST`, para o teste do duplo envio.
  depositDelayMs?: number
  // Nos erros ambíguos: o servidor chegou a gravar o depósito antes de falhar?
  depositAppliedOnError?: boolean
  // Releituras `GET /api/wallet` depois do primeiro `POST`: `fail` responde 503.
  reread?: 'ok' | 'fail'
}

export interface MockApi {
  // Pedidos recebidos, no formato "GET /api/lots".
  requests: string[]
  count(request: string): number
  unexpected: string[]
}

function json(route: Route, status: number, body: unknown): Promise<void> {
  return route.fulfill({
    status,
    contentType: 'application/json',
    headers: { 'cache-control': 'no-store' },
    body: JSON.stringify(body),
  })
}

function errorBody(status: number, code: string): Record<string, unknown> {
  return { status, code, message: code }
}

export async function mockApi(
  page: Page,
  options: MockOptions = {},
): Promise<MockApi> {
  const lots = options.lots ?? []
  let session: { email: string; role: Role } | null =
    options.session === undefined || options.session === null
      ? null
      : {
          email:
            options.session === 'AUCTIONEER'
              ? 'auctioneer@example.com'
              : 'bidder1@example.com',
          role: options.session,
        }
  const wallets = new Map<string, { total: number; committed: number }>()
  const walletOf = (email: string) => {
    let state = wallets.get(email)
    if (state === undefined) {
      state = { total: options.wallet?.total ?? 0, committed: options.wallet?.committed ?? 0 }
      wallets.set(email, state)
    }
    return state
  }
  let depositAttempted = false
  const walletSnapshot = (email: string) => {
    const state = walletOf(email)
    return {
      total_balance_cents: state.total,
      committed_balance_cents: state.committed,
      available_balance_cents: state.total - state.committed,
    }
  }
  const api: MockApi = {
    requests: [],
    count: (request) => api.requests.filter((item) => item === request).length,
    unexpected: [],
  }

  await page.route('**/health', (route) => json(route, 200, { status: 'ok' }))

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())
    const method = request.method()
    api.requests.push(`${method} ${pathname}`)

    if (pathname.startsWith('/api/catalog/images/')) {
      if (options.images === 'broken') {
        return json(route, 503, errorBody(503, 'catalog_unavailable'))
      }
      return route.fulfill({ status: 200, contentType: 'image/png', body: PIXEL })
    }
    if (pathname === '/api/me' && method === 'GET') {
      return session === null
        ? json(route, 401, errorBody(401, 'unauthorized'))
        : json(route, 200, session)
    }
    if (pathname === '/api/auth/login' && method === 'POST') {
      const body = request.postDataJSON() as { email: string; password: string }
      if (body.password !== 'Demo123!') {
        return json(route, 401, errorBody(401, 'invalid_credentials'))
      }
      session = {
        email: body.email,
        role: body.email.startsWith('auctioneer') ? 'AUCTIONEER' : 'BIDDER',
      }
      return json(route, 200, session)
    }
    if (pathname === '/api/auth/logout' && method === 'POST') {
      session = null
      return route.fulfill({ status: 204 })
    }
    if (pathname === '/api/wallet' && method === 'GET') {
      if (session === null) return json(route, 401, errorBody(401, 'unauthorized'))
      if (session.role !== 'BIDDER') return json(route, 403, errorBody(403, 'forbidden'))
      if (depositAttempted && options.reread === 'fail') {
        return json(route, 503, errorBody(503, 'internal_error'))
      }
      return json(route, 200, walletSnapshot(session.email))
    }
    if (pathname === '/api/wallet/deposit' && method === 'POST') {
      if (session === null) return json(route, 401, errorBody(401, 'unauthorized'))
      if (session.role !== 'BIDDER') return json(route, 403, errorBody(403, 'forbidden'))
      depositAttempted = true
      // A conta é a da sessão no momento do pedido, como o cookie no servidor real:
      // sair e entrar com outra conta durante o atraso não muda o dono.
      const owner = session.email
      if (options.depositDelayMs !== undefined) {
        await new Promise((resolve) => setTimeout(resolve, options.depositDelayMs))
      }
      const mode = options.deposit ?? 'ok'
      const { amount_cents: amount } = request.postDataJSON() as { amount_cents: number }
      if (mode === 'limit') return json(route, 422, errorBody(422, 'balance_limit_exceeded'))
      if (mode === 'validation') {
        return json(route, 422, {
          ...errorBody(422, 'validation_error'),
          details: [{ loc: ['body', 'amount_cents'], type: 'greater_than' }],
        })
      }
      if (mode === 'server_error' || mode === 'network') {
        if (options.depositAppliedOnError === true) walletOf(owner).total += amount
        return mode === 'network'
          ? route.abort('failed')
          : json(route, 500, errorBody(500, 'internal_error'))
      }
      walletOf(owner).total += amount
      return json(route, 200, walletSnapshot(owner))
    }
    if (pathname === '/api/lots/mine' && method === 'GET') {
      return session?.role === 'AUCTIONEER'
        ? json(route, 200, { items: [] })
        : json(route, session === null ? 401 : 403, errorBody(403, 'forbidden'))
    }
    if (pathname === '/api/lots' && method === 'GET') {
      return json(route, 200, {
        as_of: AS_OF,
        live: lots.filter((lot) => lot.phase === 'live').map(summary),
        scheduled: lots.filter((lot) => lot.phase === 'scheduled').map(summary),
        ended: lots.filter((lot) => lot.phase === 'ended').map(summary),
      })
    }
    const detail = pathname.match(/^\/api\/lots\/([0-9a-f-]{36})$/)
    if (detail !== null && method === 'GET') {
      const found = lots.find((lot) => lot.id === detail[1])
      return found === undefined
        ? json(route, 404, errorBody(404, 'not_found'))
        : json(route, 200, { as_of: AS_OF, lot: found })
    }
    api.unexpected.push(`${method} ${pathname}`)
    return json(route, 404, errorBody(404, 'not_found'))
  })

  return api
}
