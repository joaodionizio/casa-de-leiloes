// Rotas do front (Story 2.5, P5, D7, D8). Navegação própria pela History API, sem
// React Router (AD-4). Este módulo é puro: sem DOM e sem `window`, para rodar no
// `node --test`. Os efeitos (`pushState`, eventos) ficam em `navigation.ts`.

import type { UserRole } from './api/auth.ts'

export type AppRoute =
  | { kind: 'vitrine' }
  | { kind: 'lot'; lotId: string }
  | { kind: 'login' }
  | { kind: 'create-lot' }
  | { kind: 'my-lots' }

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
  if (path === '/auctioneer/lots/new') return { kind: 'create-lot' }
  if (path === '/auctioneer/lots') return { kind: 'my-lots' }
  if (path.startsWith(LOT_PREFIX)) {
    const lotId = path.slice(LOT_PREFIX.length)
    if (UUID_PATTERN.test(lotId)) return { kind: 'lot', lotId }
  }
  return { kind: 'not-found' }
}

export function routePath(route: AppRoute): string {
  if (route.kind === 'lot') return `${LOT_PREFIX}${route.lotId}`
  if (route.kind === 'login') return '/login'
  if (route.kind === 'create-lot') return '/auctioneer/lots/new'
  if (route.kind === 'my-lots') return '/auctioneer/lots'
  return '/'
}

export function isAuctioneerRoute(
  route: Route,
): route is { kind: 'create-lot' } | { kind: 'my-lots' } {
  return route.kind === 'create-lot' || route.kind === 'my-lots'
}

// Destino seguro depois do login (D8): só rotas internas conhecidas (vitrine, lote e
// as áreas do leiloeiro). URL absoluta, `//host`, `/login`, texto livre ou qualquer
// valor que não seja string viram a vitrine. Área do leiloeiro só vale para quem
// entrou como `AUCTIONEER`. O resultado é sempre o caminho normalizado da rota, nunca
// o texto recebido (a query, por exemplo, é descartada).
export function safeReturnPath(value: unknown, role: UserRole): string {
  if (typeof value !== 'string') return '/'
  const route = parseRoute(value)
  if (route.kind === 'not-found' || route.kind === 'login') return '/'
  if (isAuctioneerRoute(route) && role !== 'AUCTIONEER') return '/'
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
  notice?: 'expired' // só na entrada /login
  fromVitrine?: boolean // entrada /lots/{id} aberta a partir da vitrine
  restoreLotId?: string // entrada /: lote a focar no Back
  endedVisible?: number // entrada /: quantos encerrados estavam visíveis
}

// Lê `history.state` desconhecido; campo inválido vira ausente.
export function readNavState(value: unknown): NavState {
  if (typeof value !== 'object' || value === null) return {}
  const raw = value as Record<string, unknown>
  const state: NavState = {}
  if (typeof raw.returnTo === 'string') state.returnTo = raw.returnTo
  if (raw.notice === 'expired') state.notice = 'expired'
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
