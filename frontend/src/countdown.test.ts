import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  consumeZero,
  endsAtKey,
  formatCountdown,
  makeAnchor,
  remainingMs,
} from './countdown.ts'

const AS_OF = '2026-10-26T14:00:00.000000Z'

test('formatos nos limites', () => {
  assert.equal(formatCountdown(0), '0:00')
  assert.equal(formatCountdown(1), '00:01')
  assert.equal(formatCountdown(120_000), '02:00')
  assert.equal(formatCountdown(3_600_000), '01:00:00')
  assert.equal(formatCountdown((2 * 86400 + 4 * 3600) * 1000), '2 d 04 h')
  assert.equal(formatCountdown(-5), '0:00')
})

test('o restante usa o relógio monotônico injetado e nunca fica negativo', () => {
  const anchor = makeAnchor('2026-10-26T14:02:00Z', AS_OF, 1000)
  assert.ok(anchor)
  assert.equal(remainingMs(anchor, 1000), 120_000)
  assert.equal(remainingMs(anchor, 31_000), 90_000)
  assert.equal(remainingMs(anchor, 500_000), 0)
})

test('Date.now é ignorado no cálculo', () => {
  const real = Date.now
  Date.now = () => {
    throw new Error('Date.now não deve ser usado')
  }
  try {
    const anchor = makeAnchor('2026-10-26T14:02:00Z', AS_OF, 0)
    assert.ok(anchor)
    assert.equal(remainingMs(anchor, 60_000), 60_000)
  } finally {
    Date.now = real
  }
})

test('trocar o fim muda a contagem; datas ilegíveis não geram âncora', () => {
  const first = makeAnchor('2026-10-26T14:02:00Z', AS_OF, 0)
  const extended = makeAnchor('2026-10-26T14:04:00Z', AS_OF, 0)
  assert.ok(first && extended)
  assert.equal(remainingMs(extended, 0) - remainingMs(first, 0), 120_000)
  assert.equal(makeAnchor('x', AS_OF, 0), null)
})

test('a âncora só pode superestimar: resposta atrasada não reduz o restante', () => {
  // O instante do servidor nasce antes da chegada: contar desde o recebimento dá mais.
  const anchor = makeAnchor('2026-10-26T14:01:00Z', AS_OF, 5000)
  assert.ok(anchor)
  assert.equal(remainingMs(anchor, 5000), 60_000)
})

test('zero consome o fim antes de pedir a leitura e não rearma', () => {
  const consumed = new Set<string>()
  const end = '2026-10-26T14:02:00Z'
  assert.equal(consumeZero(consumed, 'live', end, 1), false)
  assert.equal(consumeZero(consumed, 'live', end, 0), true)
  assert.equal(consumeZero(consumed, 'live', end, 0), false)
  // O mesmo instante com outra grafia é o mesmo fim.
  assert.equal(consumeZero(consumed, 'live', '2026-10-26T14:02:00.000000Z', 0), false)
  assert.equal(endsAtKey(end), endsAtKey('2026-10-26T14:02:00.000000Z'))
})

test('fim novo arma uma vez; fases agendada e encerrada não disparam', () => {
  const consumed = new Set<string>()
  assert.equal(consumeZero(consumed, 'scheduled', '2026-10-26T14:02:00Z', 0), false)
  assert.equal(consumeZero(consumed, 'ended', '2026-10-26T14:02:00Z', 0), false)
  assert.equal(consumeZero(consumed, 'live', '2026-10-26T14:02:00Z', 0), true)
  assert.equal(consumeZero(consumed, 'live', '2026-10-26T14:04:00Z', 0), true)
  assert.equal(consumeZero(consumed, 'live', '2026-10-26T14:04:00Z', 0), false)
})
