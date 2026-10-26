// Contrato HTTP da carteira (Story 3.1). O servidor é a única fonte dos saldos: este
// módulo só lê e classifica respostas. Os textos exibidos nascem do status e do `code`,
// nunca do `message`. Sem retry: um depósito nunca é reenviado automaticamente (P8).
// Arquivo sem DOM, para o `node --test`.

export interface WalletResponse {
  total_balance_cents: number
  committed_balance_cents: number
  available_balance_cents: number
}

export interface DepositRequest {
  amount_cents: number
}

export type WalletReadFailure = 'unauthorized' | 'forbidden' | 'server'

export type WalletReadResult =
  | { ok: true; wallet: WalletResponse }
  | { ok: false; failure: WalletReadFailure }

// Recusas que o servidor decidiu: o depósito certamente não foi gravado.
export type KnownDepositFailure =
  | 'validation' // 422 validation_error
  | 'balance_limit' // 422 balance_limit_exceeded
  | 'unauthorized' // 401
  | 'forbidden' // 403 forbidden
  | 'rejected' // outro 4xx (403 csrf_*, 415, 405...): o servidor não gravou

export type DepositFailure =
  | KnownDepositFailure
  | 'ambiguous' // rede, 5xx, 200 fora do contrato: o resultado é incerto

export type DepositResult =
  | { ok: true; wallet: WalletResponse }
  | { ok: false; failure: DepositFailure }

function isNonNegativeSafeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
}

// Os três valores são centavos inteiros seguros e a conta fecha: o disponível é
// exatamente total - comprometido. Resposta incoerente não é mostrada como saldo.
export function isWalletResponse(value: unknown): value is WalletResponse {
  if (typeof value !== 'object' || value === null) return false
  const wallet = value as Record<string, unknown>
  const total = wallet.total_balance_cents
  const committed = wallet.committed_balance_cents
  const available = wallet.available_balance_cents
  if (
    !isNonNegativeSafeInteger(total) ||
    !isNonNegativeSafeInteger(committed) ||
    !isNonNegativeSafeInteger(available)
  ) {
    return false
  }
  return committed <= total && available === total - committed
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

// Um `fetch` abortado cai no `catch` como qualquer falha de rede; quem chama descarta
// o resultado quando o próprio sinal foi abortado.
export async function fetchWallet(signal?: AbortSignal): Promise<WalletReadResult> {
  let response: Response
  try {
    response = await fetch('/api/wallet', { credentials: 'same-origin', signal })
  } catch {
    return { ok: false, failure: 'server' }
  }
  if (response.status === 401) return { ok: false, failure: 'unauthorized' }
  if (response.status === 403) return { ok: false, failure: 'forbidden' }
  if (response.status !== 200) return { ok: false, failure: 'server' }
  const body = await readJson(response)
  if (!isWalletResponse(body)) return { ok: false, failure: 'server' }
  return { ok: true, wallet: body }
}

export async function depositToWallet(amountCents: number): Promise<DepositResult> {
  const request: DepositRequest = { amount_cents: amountCents }
  let response: Response
  try {
    response = await fetch('/api/wallet/deposit', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  } catch {
    return { ok: false, failure: 'ambiguous' }
  }
  const body = await readJson(response)
  if (response.status === 200) {
    if (!isWalletResponse(body)) return { ok: false, failure: 'ambiguous' }
    return { ok: true, wallet: body }
  }
  // 5xx (ou qualquer resposta que não seja uma recusa conhecida do servidor): o
  // depósito pode ter sido gravado antes da falha.
  if (response.status >= 500) return { ok: false, failure: 'ambiguous' }
  const code = errorCode(body)
  if (response.status === 422 && code === 'balance_limit_exceeded') {
    return { ok: false, failure: 'balance_limit' }
  }
  if (response.status === 422 && code === 'validation_error') {
    return { ok: false, failure: 'validation' }
  }
  if (response.status === 401) return { ok: false, failure: 'unauthorized' }
  if (response.status === 403 && code === 'forbidden') {
    return { ok: false, failure: 'forbidden' }
  }
  if (response.status >= 400) return { ok: false, failure: 'rejected' }
  // 1xx/2xx/3xx inesperado: não dá para afirmar nada.
  return { ok: false, failure: 'ambiguous' }
}
