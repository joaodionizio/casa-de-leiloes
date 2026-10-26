// Guarda e classificação das respostas da carteira (Story 3.1, P8): uma resposta
// incoerente nunca vira saldo na tela, e só o servidor decide o que é erro conhecido.
import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { MAX_CENTS } from '../money.ts'
import { depositToWallet, fetchWallet, isWalletResponse } from './wallet.ts'

function wallet(total: number, committed: number, available: number) {
  return {
    total_balance_cents: total,
    committed_balance_cents: committed,
    available_balance_cents: available,
  }
}

test('isWalletResponse aceita respostas coerentes', () => {
  assert.equal(isWalletResponse(wallet(0, 0, 0)), true)
  assert.equal(isWalletResponse(wallet(1000, 400, 600)), true)
  assert.equal(isWalletResponse(wallet(MAX_CENTS, 0, MAX_CENTS)), true)
  assert.equal(isWalletResponse(wallet(MAX_CENTS, MAX_CENTS, 0)), true)
})

test('isWalletResponse recusa o que não é centavo inteiro seguro e não negativo', () => {
  assert.equal(isWalletResponse(wallet(1.5, 0, 1.5)), false)
  assert.equal(isWalletResponse(wallet(-1, 0, -1)), false)
  assert.equal(isWalletResponse(wallet(100, -1, 101)), false)
  assert.equal(isWalletResponse(wallet(MAX_CENTS + 1, 0, MAX_CENTS + 1)), false)
  assert.equal(isWalletResponse({ ...wallet(100, 0, 100), total_balance_cents: '100' }), false)
  assert.equal(isWalletResponse({ ...wallet(100, 0, 100), available_balance_cents: null }), false)
  assert.equal(isWalletResponse(wallet(Number.NaN, 0, Number.NaN)), false)
})

test('isWalletResponse recusa chave ausente, comprometido > total e disponível incoerente', () => {
  const missing: Record<string, unknown> = wallet(100, 0, 100)
  delete missing.committed_balance_cents
  assert.equal(isWalletResponse(missing), false)
  assert.equal(isWalletResponse(wallet(100, 200, 0)), false)
  assert.equal(isWalletResponse(wallet(1000, 400, 700)), false)
  assert.equal(isWalletResponse(wallet(1000, 400, 500)), false)
})

test('isWalletResponse recusa o que não é objeto', () => {
  for (const value of [null, undefined, 42, 'x', [], true]) {
    assert.equal(isWalletResponse(value), false, String(value))
  }
})

// --- classificação das respostas (fetch simulado) ---

const realFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = realFetch
})

function respondWith(status: number, body: unknown, calls: Request[] = []): void {
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push(new Request(new URL(String(input), 'http://localhost'), init))
    const text = typeof body === 'string' ? body : JSON.stringify(body)
    return new Response(status === 204 ? null : text, { status })
  }) as typeof fetch
}

function failWithNetworkError(): void {
  globalThis.fetch = (async () => {
    throw new TypeError('network down')
  }) as typeof fetch
}

function envelope(status: number, code: string) {
  return { status, code, message: 'texto do servidor, nunca exibido' }
}

test('fetchWallet: sucesso, 401, 403, 5xx, rede e corpo fora do contrato', async () => {
  respondWith(200, wallet(1000, 400, 600))
  assert.deepEqual(await fetchWallet(), { ok: true, wallet: wallet(1000, 400, 600) })

  respondWith(401, envelope(401, 'unauthorized'))
  assert.deepEqual(await fetchWallet(), { ok: false, failure: 'unauthorized' })

  respondWith(403, envelope(403, 'forbidden'))
  assert.deepEqual(await fetchWallet(), { ok: false, failure: 'forbidden' })

  respondWith(500, envelope(500, 'internal_error'))
  assert.deepEqual(await fetchWallet(), { ok: false, failure: 'server' })

  respondWith(200, wallet(1000, 400, 999))
  assert.deepEqual(await fetchWallet(), { ok: false, failure: 'server' })

  respondWith(200, 'não é json')
  assert.deepEqual(await fetchWallet(), { ok: false, failure: 'server' })

  failWithNetworkError()
  assert.deepEqual(await fetchWallet(), { ok: false, failure: 'server' })
})

test('fetchWallet faz um GET same-origin e nada mais', async () => {
  const calls: Request[] = []
  respondWith(200, wallet(0, 0, 0), calls)
  await fetchWallet()
  assert.equal(calls.length, 1)
  assert.equal(calls[0].method, 'GET')
  assert.equal(new URL(calls[0].url).pathname, '/api/wallet')
  assert.equal(calls[0].credentials, 'same-origin')
})

test('depositToWallet: sucesso usa a resposta do POST', async () => {
  const calls: Request[] = []
  respondWith(200, wallet(125000, 0, 125000), calls)

  const result = await depositToWallet(125000)

  assert.deepEqual(result, { ok: true, wallet: wallet(125000, 0, 125000) })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].method, 'POST')
  assert.equal(new URL(calls[0].url).pathname, '/api/wallet/deposit')
  assert.equal(calls[0].credentials, 'same-origin')
  assert.equal(calls[0].headers.get('content-type'), 'application/json')
  assert.deepEqual(await calls[0].json(), { amount_cents: 125000 })
})

test('depositToWallet: erros conhecidos pelo status e pelo code', async () => {
  respondWith(422, { ...envelope(422, 'validation_error'), details: [] })
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'validation' })

  respondWith(422, envelope(422, 'balance_limit_exceeded'))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'balance_limit' })

  respondWith(401, envelope(401, 'unauthorized'))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'unauthorized' })

  respondWith(403, envelope(403, 'forbidden'))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'forbidden' })
})

test('depositToWallet: 403 de origem, 415 e 405 são recusas que não gravaram', async () => {
  respondWith(403, envelope(403, 'csrf_origin_mismatch'))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'rejected' })

  respondWith(415, envelope(415, 'unsupported_media_type'))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'rejected' })

  respondWith(405, envelope(405, 'method_not_allowed'))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'rejected' })
})

test('depositToWallet: 4xx sem code conhecido ou sem corpo também é recusa', async () => {
  // Um 4xx é sempre uma recusa do servidor antes de gravar: sem code reconhecido, o
  // texto é o genérico de "não foi possível concluir", nunca o de resultado incerto.
  respondWith(422, envelope(422, 'some_future_code'))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'rejected' })

  respondWith(422, 'não é json')
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'rejected' })

  respondWith(403, '')
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'rejected' })
})

test('depositToWallet: 2xx diferente de 200 é ambíguo', async () => {
  respondWith(201, wallet(100, 0, 100))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'ambiguous' })

  respondWith(204, null)
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'ambiguous' })
})

test('depositToWallet: rede, 5xx e 200 fora do contrato são ambíguos', async () => {
  failWithNetworkError()
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'ambiguous' })

  for (const status of [500, 502, 503, 504]) {
    respondWith(status, envelope(status, 'internal_error'))
    assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'ambiguous' }, String(status))
  }

  respondWith(200, wallet(100, 0, 999))
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'ambiguous' })

  respondWith(200, 'não é json')
  assert.deepEqual(await depositToWallet(1), { ok: false, failure: 'ambiguous' })
})

test('depositToWallet nunca repete o POST sozinho, nem em erro ambíguo', async () => {
  for (const status of [500, 503]) {
    const calls: Request[] = []
    respondWith(status, envelope(status, 'internal_error'), calls)
    await depositToWallet(100)
    assert.equal(calls.length, 1, String(status))
  }
  let attempts = 0
  globalThis.fetch = (async () => {
    attempts += 1
    throw new TypeError('network down')
  }) as typeof fetch
  await depositToWallet(100)
  assert.equal(attempts, 1)
})
