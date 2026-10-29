// Rotas do front (Story 2.5, P5, D7, D8). Navegação própria pela History API, sem
// React Router (AD-4). Este módulo é puro: sem DOM e sem `window`, para rodar no
// `node --test`. Os efeitos (`pushState`, eventos) ficam em `navigation.ts`.

import type { UserRole } from './api/auth.ts'

export type AppRoute =
  | { kind: 'vitrine' }
  | { kind: 'lot'; lotId: string }
  | { kind: 'audit'; lotId: string }
  | { kind: 'receipt'; lotId: string }
  | { kind: 'login' }
  | { kind: 'register' }
  | { kind: 'create-lot' }
  | { kind: 'my-lots' }
  | { kind: 'wallet' }
  | { kind: 'my-wins' }

export type Route = AppRoute | { kind: 'not-found' }

// UUID minúsculo com hífens, o formato que o servidor emite. Maiúsculas, barra final
// e qualquer outro texto viram "não encontrado", sem chamar a API.
export const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/

const LOT_PREFIX = '/lots/'

// Query e hash são ignorados.
function pathOnly(pathname: string): string {
  const cut = pathname.search(/[?#]/)
  return cut === -1 ? pathname : pathname.slice(0, cut)
}

export function parseRoute(pathname: string): Route {
  const path = pathOnly(pathname)
  if (path === '/') return { kind: 'vitrine' }
  if (path === '/login') return { kind: 'login' }
  if (path === '/register') return { kind: 'register' }
  if (path === '/auctioneer/lots/new') return { kind: 'create-lot' }
  if (path === '/auctioneer/lots') return { kind: 'my-lots' }
  if (path === '/bidder/wins') return { kind: 'my-wins' }
  if (path === '/bidder/wallet') return { kind: 'wallet' }
  if (path.startsWith(LOT_PREFIX)) {
    const suffix = path.slice(LOT_PREFIX.length)
    if (suffix.endsWith('/receipt')) {
      const lotId = suffix.slice(0, -8)
      if (UUID_PATTERN.test(lotId)) return { kind: 'receipt', lotId }
    }
    if (suffix.endsWith('/audit')) {
      const lotId = suffix.slice(0, -6)
      if (UUID_PATTERN.test(lotId)) return { kind: 'audit', lotId }
    }
    const lotId = suffix
    if (UUID_PATTERN.test(lotId)) return { kind: 'lot', lotId }
  }
  return { kind: 'not-found' }
}

export function routePath(route: AppRoute): string {
  if (route.kind === 'receipt') return `${LOT_PREFIX}${route.lotId}/receipt`
  if (route.kind === 'audit') return `${LOT_PREFIX}${route.lotId}/audit`
  if (route.kind === 'lot') return `${LOT_PREFIX}${route.lotId}`
  if (route.kind === 'login') return '/login'
  if (route.kind === 'register') return '/register'
  if (route.kind === 'create-lot') return '/auctioneer/lots/new'
  if (route.kind === 'my-lots') return '/auctioneer/lots'
  if (route.kind === 'my-wins') return '/bidder/wins'
  if (route.kind === 'wallet') return '/bidder/wallet'
  return '/'
}

export function isAuctioneerRoute(
  route: Route,
): route is { kind: 'create-lot' } | { kind: 'my-lots' } {
  return route.kind === 'create-lot' || route.kind === 'my-lots'
}

export function isBidderRoute(
  route: Route,
): route is { kind: 'wallet' } | { kind: 'my-wins' } {
  return route.kind === 'wallet' || route.kind === 'my-wins'
}

// Área restrita a um papel (Story 3.1): o anônimo vai ao login e guarda o retorno.
export function isRestrictedRoute(
  route: Route,
): route is
  | { kind: 'create-lot' }
  | { kind: 'my-lots' }
  | { kind: 'wallet' }
  | { kind: 'my-wins' } {
  return isAuctioneerRoute(route) || isBidderRoute(route)
}

// Destino seguro depois do login (D8): só rotas internas conhecidas (vitrine, lote, as
// áreas do leiloeiro e a carteira do licitante). URL absoluta, `//host`, `/login`,
// texto livre ou qualquer valor que não seja string viram a vitrine. Área do leiloeiro
// só vale para quem entrou como `AUCTIONEER`; a carteira, só para `BIDDER`. O
// resultado é sempre o caminho normalizado da rota, nunca o texto recebido (a query,
// por exemplo, é descartada).
export function safeReturnPath(value: unknown, role: UserRole): string {
  if (typeof value !== 'string') return '/'
  const route = parseRoute(value)
  if (route.kind === 'not-found' || route.kind === 'login' || route.kind === 'register') return '/'
  if (isAuctioneerRoute(route) && role !== 'AUCTIONEER') return '/'
  if (isBidderRoute(route) && role !== 'BIDDER') return '/'
  return routePath(route)
}

export interface ClickLike {
  button: number
  metaKey: boolean
  ctrlKey: boolean
  shiftKey: boolean
  altKey: boolean
  defaultPrevented: boolean
  target: string | null
}

// Só o clique simples vira navegação interna. Com modificador, botão do meio, alvo
// diferente de `_self` ou evento já tratado, o navegador segue o link (nova aba etc.).
export function shouldHandleClick(event: ClickLike): boolean {
  if (event.button !== 0) return false
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false
  if (event.defaultPrevented) return false
  return event.target === null || event.target === '' || event.target === '_self'
}

// O que guardamos em `history.state`, entrada por entrada (D8, D11).
export interface NavState {
  returnTo?: string // só na entrada /login
  notice?: 'expired' | 'registered' // só na entrada /login
  fromVitrine?: boolean // entrada /lots/{id} aberta a partir da vitrine
  restoreLotId?: string // entrada /: lote a focar no Back
  endedVisible?: number // entrada /: quantos encerrados estavam visíveis
  vitrineTerm?: string // entrada /: busca ao abrir o lote, para restaurar no Back
  vitrinePhase?: 'all' | 'live' | 'scheduled' | 'ended'
}

// Lê `history.state` desconhecido; campo inválido vira ausente.
export function readNavState(value: unknown): NavState {
  if (typeof value !== 'object' || value === null) return {}
  const raw = value as Record<string, unknown>
  const state: NavState = {}
  if (typeof raw.vitrineTerm === 'string') state.vitrineTerm = raw.vitrineTerm
  if (raw.vitrinePhase === 'all' || raw.vitrinePhase === 'live' ||
    raw.vitrinePhase === 'scheduled' || raw.vitrinePhase === 'ended') {
    state.vitrinePhase = raw.vitrinePhase
  }
  if (typeof raw.returnTo === 'string') state.returnTo = raw.returnTo
  if (raw.notice === 'expired' || raw.notice === 'registered') state.notice = raw.notice
  if (raw.fromVitrine === true) state.fromVitrine = true
  if (typeof raw.restoreLotId === 'string' && UUID_PATTERN.test(raw.restoreLotId)) {
    state.restoreLotId = raw.restoreLotId
  }
  if (
    typeof raw.endedVisible === 'number' &&
    Number.isSafeInteger(raw.endedVisible) &&
    raw.endedVisible >= 0
  ) {
    state.endedVisible = raw.endedVisible
  }
  return state
}

// Auth links carry only a known canonical destination. Role authorization is
// checked after the ordinary login, when the effective account is known.
export function authReturnState(value: unknown): NavState {
  if (typeof value !== 'string') return {}
  const route = parseRoute(value)
  if (route.kind === 'not-found' || route.kind === 'login' || route.kind === 'register') return {}
  return { returnTo: routePath(route) }
}
