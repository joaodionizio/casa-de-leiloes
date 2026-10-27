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

// Sala do lote (Story 3.5). O mock serve o read model público e o `/mine` a partir de
// um estado simples por lote; não reimplementa o motor: aceita o valor enviado ou
// devolve a recusa pedida pelo teste. O `as_of` da sala difere do do detalhe, e avança
// 1 s a cada leitura de `/bids`.
export const ROOM_AS_OF = '2026-10-25T12:00:07.000000Z'
export const ALIASES: Record<string, string> = {
  'bidder1@example.com': 'Licitante-A83F19C2D4E5B601',
  'bidder2@example.com': 'Licitante-0B7E5A91C3D2F480',
}
export const OTHER_ALIAS = ALIASES['bidder2@example.com']
export const OWN_ALIAS = ALIASES['bidder1@example.com']

export interface MockBid {
  sequence: number
  bidder_alias: string
  amount_cents: number
  placed_at: string
}

export interface RoomSeed {
  bids?: MockBid[] // todos os lances, sequência crescente
  ends_at?: string
  // Sobrescritas aplicadas à N-ésima leitura de `/bids` (a última se repete).
  script?: Array<Partial<{ phase: Phase; ends_at: string; minimum_next_bid_cents: number | null }>>
}

// `count` lances alternando os dois licitantes, a partir do lance inicial.
export function makeBids(
  count: number,
  startingCents: number,
  aliases: string[] = [OTHER_ALIAS, OWN_ALIAS],
): MockBid[] {
  return Array.from({ length: count }, (_, index) => ({
    sequence: index + 1,
    bidder_alias: aliases[index % aliases.length],
    amount_cents: startingCents + index * 1_000,
    placed_at: new Date(BASE + index * 1_000).toISOString().replace('.000Z', '.000000Z'),
  }))
}

export type BidMode =
  | 'accepted'
  | 'anti_sniping'
  | 'below_minimum'
  | 'insufficient_balance'
  | 'already_winning'
  | 'lot_not_started'
  | 'lot_ended'
  | 'lot_cancelled'
  | 'integrity'
  | 'validation'
  | 'unauthorized'
  | 'forbidden'
  | 'server_error'
  | 'network'
  | 'invalid201'

// Lista do leiloeiro (Story 3.6): o item de `GET /api/lots/mine`. O mock guarda o estado
// por lote e o altera quando o cancelamento "grava"; não reimplementa as regras do servidor.
export interface MockMyLot {
  id: string
  title: string | null
  artist_display: string | null
  starts_at: string
  ends_at: string
  phase: Phase
  bid_count: number
  cancelled_at: string | null
}

export type CancelMode =
  | 'ok'
  | 'has_bids'
  | 'ended'
  | 'integrity'
  | 'forbidden'
  | 'not_found'
  | 'unauthorized'
  | 'server_error'
  | 'network'
  | 'invalid_body'

export const CANCELLED_AT = '2026-10-25T14:31:00.654321Z'

export interface MockOptions {
  // Lotes do leiloeiro em `GET /api/lots/mine` (padrão: nenhum).
  myLots?: MockMyLot[]
  // Resposta do `POST /api/lots/{id}/cancel`; `ok` grava `cancelled_at` no estado do mock.
  cancel?: CancelMode
  // Atraso do `POST`, para o teste do envio pendente.
  cancelDelayMs?: number
  // Nos erros ambíguos: o servidor chegou a gravar o cancelamento antes de falhar?
  cancelAppliedOnError?: boolean
  // Releituras `GET /api/lots/mine` depois do primeiro `POST`: 503.
  mineRereadFail?: boolean
  rooms?: Record<string, RoomSeed>
  bid?: BidMode
  // Atraso do `POST` do lance, para o teste do envio pendente.
  bidDelayMs?: number
  // Nos erros ambíguos: o servidor chegou a gravar o lance antes de falhar?
  bidAppliedOnError?: boolean
  // Depois do primeiro `POST`, as leituras indicadas respondem 503 (`all` = as três).
  rereadFail?: 'room' | 'mine' | 'wallet' | 'all'
  // Atraso das leituras `/bids` depois do primeiro `POST`.
  rereadDelayMs?: number
  // `/mine` ou a carteira respondem 401 (sessão expirada) em qualquer leitura.
  privateRead401?: 'mine' | 'wallet'

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
  // Ids dos lotes de cada `POST /api/lots/{id}/cancel` recebido.
  cancelPosts: string[]
  // Corpos dos `POST /api/lots/{id}/bids` recebidos.
  bidPosts: Array<{ lotId: string; body: unknown }>
  // Pedidos recebidos, no formato "GET /api/lots".
  requests: string[]
  count(request: string): number
  // Respostas de `POST /bids` já enviadas ao navegador.
  bidResponses: number
  // Segura os pedidos "GET /api/lots/..." iguais a `request` até `release()` (resposta
  // normal) ou `fail()` (503). Vale para todos os que chegarem antes disso.
  hold(request: string): { release: () => void; fail: () => void }
  // Troca os lances do lote no meio do teste (sequência crescente).
  setBids(lotId: string, bids: MockBid[]): void
  unexpected: string[]
}

// Um pedido abortado pelo navegador (leitura substituída) não tem mais rota para responder.
function json(route: Route, status: number, body: unknown): Promise<void> {
  return route
    .fulfill({
      status,
      contentType: 'application/json',
      headers: { 'cache-control': 'no-store' },
      body: JSON.stringify(body),
    })
    .catch(() => undefined)
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
  const rooms = new Map<
    string,
    { bids: MockBid[]; endsAt: string; reads: number }
  >()
  const roomOf = (id: string) => {
    let state = rooms.get(id)
    if (state === undefined) {
      const lot = lots.find((item) => item.id === id)
      const seed = options.rooms?.[id]
      state = {
        bids: [...(seed?.bids ?? [])],
        endsAt: seed?.ends_at ?? lot?.ends_at ?? '',
        reads: 0,
      }
      rooms.set(id, state)
    }
    return state
  }
  let bidAttempted = false
  // O 401 simulado vale uma vez: depois do novo login a sessão volta a ser válida.
  let expiredOnce = false
  const expires = (what: 'mine' | 'wallet') => {
    if (options.privateRead401 !== what || expiredOnce) return false
    expiredOnce = true
    return true
  }
  const failsAfterPost = (what: 'room' | 'mine' | 'wallet') =>
    bidAttempted && (options.rereadFail === what || options.rereadFail === 'all')
  const holds = new Map<string, Promise<boolean>>()
  const myLots = (options.myLots ?? []).map((lot) => ({ ...lot }))
  let cancelAttempted = false
  const api: MockApi = {
    cancelPosts: [],
    bidPosts: [],
    requests: [],
    count: (request) => api.requests.filter((item) => item === request).length,
    bidResponses: 0,
    hold: (request) => {
      let settle: (ok: boolean) => void = () => undefined
      holds.set(
        request,
        new Promise<boolean>((resolve) => {
          settle = resolve
        }),
      )
      return {
        release: () => {
          holds.delete(request)
          settle(true)
        },
        fail: () => {
          holds.delete(request)
          settle(false)
        },
      }
    },
    setBids: (id, bids) => {
      roomOf(id).bids = [...bids]
    },
    unexpected: [],
  }

  await page.route('**/health', (route) => json(route, 200, { status: 'ok' }))

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())
    const method = request.method()
    api.requests.push(`${method} ${pathname}`)
    const held = holds.get(`${method} ${pathname}`)
    if (held !== undefined && !(await held)) {
      return json(route, 503, errorBody(503, 'internal_error'))
    }

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
      if (expires('wallet')) {
        return json(route, 401, errorBody(401, 'unauthorized'))
      }
      if (failsAfterPost('wallet')) return json(route, 503, errorBody(503, 'internal_error'))
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
      if (session?.role !== 'AUCTIONEER') {
        return json(route, session === null ? 401 : 403, errorBody(403, 'forbidden'))
      }
      if (cancelAttempted && options.mineRereadFail === true) {
        return json(route, 503, errorBody(503, 'internal_error'))
      }
      return json(route, 200, {
        as_of: AS_OF,
        items: myLots.map((lot) => ({
          id: lot.id,
          external_id: 27_000,
          title: lot.title,
          artist_display: lot.artist_display,
          date_display: null,
          medium_display: null,
          dimensions: null,
          department_title: null,
          artwork_type_title: null,
          credit_line: null,
          source_url: 'https://www.artic.edu/artworks/27000',
          image_id: '2d484387-2509-5e8e-2c43-22f9981972eb',
          image_url: '/api/catalog/images/2d484387-2509-5e8e-2c43-22f9981972eb',
          starting_bid_cents: 10_000,
          min_increment_cents: 1_000,
          starts_at: lot.starts_at,
          ends_at: lot.ends_at,
          created_at: lot.starts_at,
          cancelled_at: lot.cancelled_at,
          bid_count: lot.bid_count,
          phase: lot.phase,
        })),
      })
    }
    const cancelPath = pathname.match(/^\/api\/lots\/([0-9a-f-]{36})\/cancel$/)
    if (cancelPath !== null && method === 'POST') {
      api.cancelPosts.push(cancelPath[1])
      cancelAttempted = true
      if (options.cancelDelayMs !== undefined) {
        await new Promise((resolve) => setTimeout(resolve, options.cancelDelayMs))
      }
      const target = myLots.find((lot) => lot.id === cancelPath[1])
      const mode = options.cancel ?? 'ok'
      const refusals: Partial<Record<CancelMode, [number, string]>> = {
        has_bids: [422, 'lot_has_bids'],
        ended: [422, 'lot_ended'],
        integrity: [409, 'lot_integrity_conflict'],
        forbidden: [403, 'forbidden'],
        not_found: [404, 'not_found'],
        unauthorized: [401, 'unauthorized'],
      }
      const refusal = refusals[mode]
      if (refusal !== undefined) {
        return json(route, refusal[0], {
          status: refusal[0],
          code: refusal[1],
          message: 'MENSAGEM DO SERVIDOR QUE A TELA NÃO DEVE USAR',
        })
      }
      const record = () => {
        if (target !== undefined) target.cancelled_at = CANCELLED_AT
      }
      if (mode === 'server_error' || mode === 'network') {
        if (options.cancelAppliedOnError === true) record()
        return mode === 'network'
          ? route.abort('failed')
          : json(route, 500, errorBody(500, 'internal_error'))
      }
      record()
      if (mode === 'invalid_body') return json(route, 200, { id: 'outro', cancelled_at: null })
      return json(route, 200, { id: cancelPath[1], cancelled_at: CANCELLED_AT })
    }
    if (pathname === '/api/lots' && method === 'GET') {
      return json(route, 200, {
        as_of: AS_OF,
        live: lots.filter((lot) => lot.phase === 'live').map(summary),
        scheduled: lots.filter((lot) => lot.phase === 'scheduled').map(summary),
        ended: lots.filter((lot) => lot.phase === 'ended').map(summary),
      })
    }
    const bidsPath = pathname.match(/^\/api\/lots\/([0-9a-f-]{36})\/bids(\/mine)?$/)
    if (bidsPath !== null) {
      const lot = lots.find((item) => item.id === bidsPath[1])
      if (lot === undefined) return json(route, 404, errorBody(404, 'not_found'))
      const state = roomOf(lot.id)
      if (bidsPath[2] === '/mine' && method === 'GET') {
        if (session === null || expires('mine')) {
          return json(route, 401, errorBody(401, 'unauthorized'))
        }
        if (session.role !== 'BIDDER') return json(route, 403, errorBody(403, 'forbidden'))
        if (failsAfterPost('mine')) return json(route, 503, errorBody(503, 'internal_error'))
        const alias = ALIASES[session.email] ?? OWN_ALIAS
        const own = state.bids.filter((bid) => bid.bidder_alias === alias)
        return json(route, 200, {
          bidder_alias: alias,
          my_bid_count: own.length,
          last_bid_cents: own.length === 0 ? null : own[own.length - 1].amount_cents,
        })
      }
      if (bidsPath[2] === undefined && method === 'GET') {
        if (bidAttempted && options.rereadDelayMs !== undefined) {
          await new Promise((resolve) => setTimeout(resolve, options.rereadDelayMs))
        }
        if (failsAfterPost('room')) return json(route, 503, errorBody(503, 'internal_error'))
        const script = options.rooms?.[lot.id]?.script
        const step = script === undefined ? {} : script[Math.min(state.reads, script.length - 1)]
        state.reads += 1
        const latest = state.bids[state.bids.length - 1]
        // A read after an accepted POST cannot predate that bid's server clock.
        const asOf = new Date(Math.max(
          Date.parse(ROOM_AS_OF) + (state.reads - 1) * 1000,
          bidAttempted && latest !== undefined ? Date.parse(latest.placed_at) + 1 : 0,
        )).toISOString()
        const current = latest === undefined ? null : latest.amount_cents
        return json(route, 200, {
          as_of: asOf.replace('.000Z', '.000000Z'),
          phase: step.phase ?? lot.phase,
          ends_at: step.ends_at ?? state.endsAt,
          current_bid_cents: current,
          minimum_next_bid_cents:
            step.minimum_next_bid_cents !== undefined
              ? step.minimum_next_bid_cents
              : current === null
                ? lot.starting_bid_cents
                : current + lot.min_increment_cents,
          bid_count: state.bids.length,
          bids: state.bids.slice(-50).reverse(),
        })
      }
      if (bidsPath[2] === undefined && method === 'POST') {
        if (session === null) return json(route, 401, errorBody(401, 'unauthorized'))
        const owner = session.email
        const body = request.postDataJSON() as { amount_cents: number }
        api.bidPosts.push({ lotId: lot.id, body })
        bidAttempted = true
        if (options.bidDelayMs !== undefined) {
          await new Promise((resolve) => setTimeout(resolve, options.bidDelayMs))
        }
        const mode = options.bid ?? 'accepted'
        const refusals: Partial<Record<BidMode, [number, string]>> = {
          below_minimum: [422, 'below_minimum'],
          insufficient_balance: [422, 'insufficient_balance'],
          already_winning: [422, 'already_winning'],
          lot_not_started: [422, 'lot_not_started'],
          lot_ended: [422, 'lot_ended'],
          lot_cancelled: [422, 'lot_cancelled'],
          integrity: [409, 'lot_integrity_conflict'],
          validation: [422, 'validation_error'],
          unauthorized: [401, 'unauthorized'],
          forbidden: [403, 'forbidden'],
        }
        const refusal = refusals[mode]
        if (refusal !== undefined) {
          return json(route, refusal[0], {
            status: refusal[0],
            code: refusal[1],
            message: 'MENSAGEM DO SERVIDOR QUE A TELA NÃO DEVE USAR',
          })
        }
        const record = () => {
          const sequence = state.bids.length + 1
          state.bids.push({
            sequence,
            bidder_alias: ALIASES[owner] ?? OWN_ALIAS,
            amount_cents: body.amount_cents,
            placed_at: '2026-10-25T12:00:09.000000Z',
          })
          walletOf(owner).committed = body.amount_cents
          return state.bids[state.bids.length - 1]
        }
        if (mode === 'server_error' || mode === 'network') {
          if (options.bidAppliedOnError === true) record()
          return mode === 'network'
            ? route.abort('failed')
            : json(route, 500, errorBody(500, 'internal_error'))
        }
        if (mode === 'invalid201') {
          record()
          api.bidResponses += 1
          return json(route, 201, { bid: null })
        }
        const placed = record()
        api.bidResponses += 1
        const extended = mode === 'anti_sniping'
        if (extended) {
          // AD-5 (revisada em 27/10/2026): o novo fim é `placed_at` + 2 min.
          state.endsAt = new Date(Date.parse(placed.placed_at) + 120_000)
            .toISOString()
            .replace('.000Z', 'Z')
        }
        return json(route, 201, {
          bid: placed,
          lot: {
            current_bid_cents: placed.amount_cents,
            ends_at: state.endsAt,
            anti_sniping_applied: extended,
          },
          wallet: walletSnapshot(owner),
        })
      }
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
