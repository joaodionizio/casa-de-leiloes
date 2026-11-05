import assert from 'node:assert/strict'
import test from 'node:test'
import { apiFetch, readJson } from './http.ts'

test('reads a valid JSON payload without changing it', async () => {
  const body = { status: 422, code: 'below_minimum', details: ['amount'] }
  const response = new Response(JSON.stringify(body), {
    status: 422, headers: { 'Content-Type': 'application/json' },
  })
  assert.deepEqual(await readJson(response), body)
})

test('returns null for invalid JSON instead of throwing', async () => {
  assert.equal(await readJson(new Response('not-json')), null)
})

test('returns null for an empty response body', async () => {
  assert.equal(await readJson(new Response(null, { status: 204 })), null)
})

test('apiFetch keeps the endpoint URL and enforces same-origin cookies', async (t) => {
  const calls: Array<{ input: Parameters<typeof fetch>[0]; init?: RequestInit }> = []
  t.mock.method(globalThis, 'fetch', async (input: Parameters<typeof fetch>[0], init?: RequestInit) => {
    calls.push({ input, init })
    return new Response(null, { status: 204 })
  })

  const signal = new AbortController().signal
  const headers = { 'Content-Type': 'application/json' }
  const response = await apiFetch('/api/wallet/deposit', {
    method: 'POST',
    headers,
    body: '{"amount_cents":10000}',
    signal,
    cache: 'no-store',
  })

  assert.equal(response.status, 204)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].input, '/api/wallet/deposit')
  assert.equal(calls[0].init?.credentials, 'same-origin')
  assert.equal(calls[0].init?.method, 'POST')
  assert.equal(calls[0].init?.body, '{"amount_cents":10000}')
  assert.equal(calls[0].init?.signal, signal)
  assert.equal(calls[0].init?.cache, 'no-store')
  assert.deepEqual(calls[0].init?.headers, headers)
})

test('apiFetch does not retry a network error (important for financial posts)', async (t) => {
  let attempts = 0
  t.mock.method(globalThis, 'fetch', async () => {
    attempts += 1
    throw new TypeError('connection lost')
  })

  await assert.rejects(() => apiFetch('/api/lots/lot-id/bids', {
    method: 'POST',
    body: '{"amount_cents":10000}',
  }), /connection lost/)
  assert.equal(attempts, 1)
})

test('apiFetch does not add a JSON body or headers to GET requests', async (t) => {
  const calls: RequestInit[] = []
  t.mock.method(globalThis, 'fetch', async (_input: Parameters<typeof fetch>[0], init?: RequestInit) => {
    calls.push(init ?? {})
    return new Response('{}', { status: 200 })
  })
  await apiFetch('/api/lots')
  assert.equal(calls.length, 1)
  assert.equal(calls[0].method, undefined)
  assert.equal(calls[0].headers, undefined)
  assert.equal(calls[0].body, undefined)
  assert.equal(calls[0].credentials, 'same-origin')
})
