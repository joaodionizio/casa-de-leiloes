import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { register, registrationErrors, registrationFailureMessage } from './auth.ts'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })

test('cadastro manda somente e-mail/senha/papel por JSON same-origin e exige 201 válido', async () => {
  globalThis.fetch = async (input, init) => {
    assert.equal(input, '/api/auth/register')
    assert.equal(init?.method, 'POST')
    assert.equal(init?.credentials, 'same-origin')
    assert.deepEqual(init?.headers, { 'Content-Type': 'application/json' })
    assert.deepEqual(JSON.parse(String(init?.body)), { email: ' USER+tag@Example.com ', password: ' 123456 ', role: 'AUCTIONEER' })
    return Response.json({ email: 'user+tag@example.com', role: 'AUCTIONEER' }, { status: 201 })
  }
  assert.deepEqual(await register(' USER+tag@Example.com ', ' 123456 ', 'AUCTIONEER'), { ok: true, user: { email: 'user+tag@example.com', role: 'AUCTIONEER' } })
})

test('cadastro recusa sucesso malformado, papel/e-mail divergentes, dados extras ou status errado', async () => {
  for (const [status, body] of [
    [200, { email: 'u@e', role: 'BIDDER' }],
    [201, {}], [201, { email: 'u@e', role: 'ADMIN' }],
    [201, { email: 'u@e', role: 'AUCTIONEER' }],
    [201, { email: 'other@e', role: 'BIDDER' }],
    [201, { email: 'u@e', role: 'BIDDER', token: 'not-allowed' }],
  ] as const) {
    globalThis.fetch = async () => Response.json(body, { status })
    assert.equal((await register('u@e', '12345678', 'BIDDER')).ok, false)
  }
  globalThis.fetch = async () => new Response('html', { status: 201 })
  assert.deepEqual(await register('u@e', '12345678', 'BIDDER'), { ok: false, failure: 'server', fields: [] })
})

test('falhas usam code e campos sanitizados; nenhuma mensagem remota é exibida e não há retry', async () => {
  for (const [status, code, failure] of [
    [409, 'email_already_registered', 'email_already_registered'],
    [403, 'csrf_origin_mismatch', 'rejected'],
    [415, 'unsupported_media_type', 'rejected'],
    [500, 'internal_error', 'server'],
  ] as const) {
    let calls = 0
    globalThis.fetch = async () => { calls++; return Response.json({ status, code, message: 'REMOTE_SENTINEL' }, { status }) }
    const result = await register('u@e', '12345678', 'BIDDER')
    assert.equal(result.ok, false)
    if (!result.ok) {
      assert.equal(result.failure, failure)
      assert.ok(!registrationFailureMessage(result.failure).includes('REMOTE_SENTINEL'))
    }
    assert.equal(calls, 1)
  }
  globalThis.fetch = async () => Response.json({ status: 422, code: 'validation_error', details: [{ loc: ['body', 'password'] }, { loc: ['body', 'name'] }, { loc: ['body', 'password'] }] }, { status: 422 })
  assert.deepEqual(await register('u@e', '12345678', 'BIDDER'), { ok: false, failure: 'validation', fields: ['password'] })
  globalThis.fetch = async () => { throw new TypeError('network') }
  assert.deepEqual(await register('u@e', '12345678', 'BIDDER'), { ok: false, failure: 'server', fields: [] })
})

test('validação local exige composição por caracteres sem normalizar a senha', () => {
  assert.deepEqual(registrationErrors(' U.ser+tag@Example.com ', ' Aa1    ', 'BIDDER'), {})
  assert.deepEqual(registrationErrors('a'.repeat(252) + '@b', 'Aa1' + '😀'.repeat(1021), 'AUCTIONEER'), {})
  assert.ok(registrationErrors('a'.repeat(253) + '@b', '1234567', '').email)
  assert.ok(registrationErrors('a@b', 'Aa1' + '😀'.repeat(1022), '').password)
  for (const password of ['        ', 'abcdefgh', 'Abcdefgh', 'abcd1234']) assert.ok(registrationErrors('a@b', password, 'BIDDER').password)
  for (const email of ['', '@b', 'a@', 'a@@b', 'a b@c', 'a@b\nc']) assert.ok(registrationErrors(email, 'Abcdefg1', 'BIDDER').email)
  assert.ok(registrationErrors('a@b', 'Abcdefg1', '').role)
})
