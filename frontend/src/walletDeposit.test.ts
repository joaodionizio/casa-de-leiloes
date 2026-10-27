// Depósito em andamento (Story 3.1, P8; F-08 do code review): um por conta, nunca
// compartilhado entre contas, e no máximo uma releitura depois de um erro ambíguo.
import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import type { WalletResponse } from './api/wallet.ts'
import {
  pendingDepositOf,
  sendDeposit,
  startDeposit,
  type DepositOutcome,
} from './walletDeposit.ts'

const WALLET: WalletResponse = {
  total_balance_cents: 1000,
  committed_balance_cents: 0,
  available_balance_cents: 1000,
}

// Um envio que só termina quando o teste manda.
function controlledSend() {
  const sent: number[] = []
  let finish: (outcome: DepositOutcome) => void = () => {}
  const send = (amountCents: number) => {
    sent.push(amountCents)
    return new Promise<DepositOutcome>((resolve) => {
      finish = resolve
    })
  }
  return { sent, send, finish: (outcome: DepositOutcome) => finish(outcome) }
}

test('um depósito por conta: o segundo envio da mesma conta não sai', async () => {
  const control = controlledSend()

  const first = startDeposit('a@example.com', 1000, control.send)
  const second = startDeposit('a@example.com', 1000, control.send)

  assert.notEqual(first, null)
  assert.equal(second, null)
  assert.deepEqual(control.sent, [1000])
  assert.equal(pendingDepositOf('a@example.com'), first)

  control.finish({ kind: 'confirmed', wallet: WALLET })
  assert.deepEqual(await first?.outcome, { kind: 'confirmed', wallet: WALLET })
  // Quem recebe o resultado já encontra a conta livre.
  assert.equal(pendingDepositOf('a@example.com'), null)
})

test('o depósito de uma conta não bloqueia nem aparece para outra', async () => {
  const control = controlledSend()
  const other = controlledSend()

  const fromA = startDeposit('a2@example.com', 500, control.send)
  assert.equal(pendingDepositOf('b2@example.com'), null)

  const fromB = startDeposit('b2@example.com', 700, other.send)
  assert.notEqual(fromB, null)
  assert.deepEqual(other.sent, [700])

  control.finish({ kind: 'confirmed', wallet: WALLET })
  await fromA?.outcome
  // O fim do depósito de A não libera nem apaga o de B.
  assert.equal(pendingDepositOf('b2@example.com'), fromB)
  other.finish({ kind: 'refused', failure: 'balance_limit' })
  await fromB?.outcome
  assert.equal(pendingDepositOf('b2@example.com'), null)
})

test('uma falha inesperada do envio libera a conta e não afirma resultado', async () => {
  const entry = startDeposit('c@example.com', 100, () => Promise.reject(new Error('x')))

  assert.deepEqual(await entry?.outcome, {
    kind: 'uncertain',
    reread: { ok: false, failure: 'server' },
  })
  assert.equal(pendingDepositOf('c@example.com'), null)
})

// --- sendDeposit (fetch simulado) ---

const realFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = realFetch
})

interface Reply {
  status: number
  body?: unknown
}

function serve(replies: Reply[], calls: string[]): void {
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push(`${init?.method ?? 'GET'} ${String(input)}`)
    const reply = replies.shift()
    if (reply === undefined) throw new TypeError('network down')
    return new Response(JSON.stringify(reply.body ?? {}), { status: reply.status })
  }) as typeof fetch
}

test('sendDeposit: sucesso usa a resposta do POST, sem releitura', async () => {
  const calls: string[] = []
  serve([{ status: 200, body: WALLET }], calls)

  assert.deepEqual(await sendDeposit(1000), { kind: 'confirmed', wallet: WALLET })
  assert.deepEqual(calls, ['POST /api/wallet/deposit'])
})

test('sendDeposit: recusa conhecida não relê', async () => {
  const calls: string[] = []
  serve([{ status: 422, body: { status: 422, code: 'balance_limit_exceeded', message: 'x' } }], calls)

  assert.deepEqual(await sendDeposit(1000), { kind: 'refused', failure: 'balance_limit' })
  assert.deepEqual(calls, ['POST /api/wallet/deposit'])
})

test('sendDeposit: erro ambíguo faz uma única releitura e nunca outro POST', async () => {
  const calls: string[] = []
  serve([{ status: 500 }, { status: 200, body: WALLET }], calls)

  assert.deepEqual(await sendDeposit(1000), {
    kind: 'uncertain',
    reread: { ok: true, wallet: WALLET },
  })
  assert.deepEqual(calls, ['POST /api/wallet/deposit', 'GET /api/wallet'])

  const failing: string[] = []
  serve([{ status: 503 }, { status: 503 }], failing)
  assert.deepEqual(await sendDeposit(1000), {
    kind: 'uncertain',
    reread: { ok: false, failure: 'server' },
  })
  assert.deepEqual(failing, ['POST /api/wallet/deposit', 'GET /api/wallet'])
})
