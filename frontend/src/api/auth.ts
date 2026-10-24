// Contrato HTTP de autenticação (Story 2.2). O token vive só no cookie HttpOnly:
// este módulo nunca o lê, e nada de sessão vai para localStorage/sessionStorage.

export type UserRole = 'AUCTIONEER' | 'BIDDER'

export interface CurrentUser {
  email: string
  role: UserRole
}

export interface ApiErrorBody {
  status: number
  code: string
  message: string
}

export type AuthFailure =
  | 'invalid_credentials'
  | 'validation'
  | 'server'
  | 'rejected'

export type LoginResult =
  | { ok: true; user: CurrentUser }
  | { ok: false; failure: AuthFailure }

export type MeResult =
  | { ok: true; user: CurrentUser }
  | { ok: false; failure: 'anonymous' | 'server' }

export type LogoutResult =
  | { ok: true }
  | { ok: false; failure: 'server' | 'rejected' }

function isCurrentUser(value: unknown): value is CurrentUser {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as { email?: unknown; role?: unknown }
  return (
    typeof candidate.email === 'string' &&
    (candidate.role === 'AUCTIONEER' || candidate.role === 'BIDDER')
  )
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as { status?: unknown; code?: unknown }
  return typeof candidate.status === 'number' && typeof candidate.code === 'string'
}

// Corpo JSON da resposta, ou null se não for JSON.
async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function fetchCurrentUser(): Promise<MeResult> {
  let response: Response
  try {
    response = await fetch('/api/me', { credentials: 'same-origin' })
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status === 401) return { ok: false, failure: 'anonymous' }
  if (response.status !== 200) return { ok: false, failure: 'server' }
  const body = await readJson(response)
  if (!isCurrentUser(body)) return { ok: false, failure: 'server' }
  return { ok: true, user: body }
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResult> {
  let response: Response
  try {
    response = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status >= 500) return { ok: false, failure: 'server' }
  const body = await readJson(response)
  if (body === null) return { ok: false, failure: 'server' }
  if (response.status === 200) {
    if (!isCurrentUser(body)) return { ok: false, failure: 'server' }
    return { ok: true, user: body }
  }
  if (
    response.status === 401 &&
    isApiErrorBody(body) &&
    body.code === 'invalid_credentials'
  ) {
    return { ok: false, failure: 'invalid_credentials' }
  }
  if (response.status === 422) return { ok: false, failure: 'validation' }
  return { ok: false, failure: 'rejected' }
}

export async function logout(): Promise<LogoutResult> {
  let response: Response
  try {
    response = await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status === 204) return { ok: true }
  if (response.status >= 400 && response.status < 500) {
    return { ok: false, failure: 'rejected' }
  }
  return { ok: false, failure: 'server' }
}

// Textos exibidos (pt-BR). Nunca vêm do `message` do servidor: a interface
// controla o português.
export function failureMessage(failure: AuthFailure): string {
  if (failure === 'invalid_credentials') return 'E-mail ou senha inválidos.'
  if (failure === 'validation') return 'Informe e-mail e senha.'
  if (failure === 'rejected') {
    return 'Não foi possível concluir a operação. Recarregue a página e tente novamente.'
  }
  return 'Não foi possível falar com o servidor. Tente novamente.'
}

export function roleLabel(role: UserRole): string {
  return role === 'AUCTIONEER' ? 'Leiloeiro' : 'Licitante'
}
