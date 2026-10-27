import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { BidResult } from './api/bids.ts'
import { bidToFollow, pendingBidOf, startBid } from './bidSubmission.ts'
import { parseReaisToCents } from './money.ts'

const LOT = '2d484387-2509-5e8e-2c43-22f9981972eb'
const OTHER_LOT = '3d484387-2509-5e8e-2c43-22f9981972eb'

function deferred() {
  let resolve!: (result: BidResult) => void
  const promise = new Promise<BidResult>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

test('valores abaixo do mínimo ou acima do saldo têm formato válido e seguem para o POST', () => {
  // O front só valida o formato: 0,01 e 99.999.999,99 são aceitos pelo parser.
  assert.deepEqual(parseReaisToCents('0,01'), { ok: true, cents: 1 })
  assert.deepEqual(parseReaisToCents('99.999.999,99'), { ok: true, cents: 9999999999 })
  assert.equal(parseReaisToCents('').ok, false)
  assert.equal(parseReaisToCents('abc').ok, false)
})

test('a barreira é síncrona por conta e lote, e sobrevive à remontagem', async () => {
  const gate = deferred()
  let sends = 0
  const send = () => {
    sends += 1
    return gate.promise
  }
  const first = startBid('a@x', LOT, 5000, '50,00', send)
  assert.ok(first)
  assert.equal(startBid('a@x', LOT, 5000, '50,00', send), null)
  assert.equal(pendingBidOf('a@x', LOT), first)
  assert.equal(sends, 1)

  gate.resolve({ ok: false, failure: 'below_minimum' })
  assert.deepEqual(await first.outcome, { ok: false, failure: 'below_minimum' })
  assert.equal(pendingBidOf('a@x', LOT), null)
})

test('contas e lotes são independentes', async () => {
  const gate = deferred()
  const send = () => gate.promise
  const mineEntry = startBid('a@x', LOT, 1, '0,01', send)
  const otherAccount = startBid('b@x', LOT, 1, '0,01', send)
  const otherLot = startBid('a@x', OTHER_LOT, 1, '0,01', send)
  assert.ok(mineEntry && otherAccount && otherLot)
  assert.equal(pendingBidOf('b@x', OTHER_LOT), null)
  gate.resolve({ ok: false, failure: 'ambiguous' })
  await Promise.all([mineEntry.outcome, otherAccount.outcome, otherLot.outcome])
})

test('erro ambíguo é devolvido uma vez, sem novo envio', async () => {
  let sends = 0
  const entry = startBid('c@x', LOT, 5000, '50,00', async () => {
    sends += 1
    return { ok: false, failure: 'ambiguous' }
  })
  assert.ok(entry)
  assert.deepEqual(await entry.outcome, { ok: false, failure: 'ambiguous' })
  assert.equal(sends, 1)
})

test('uma falha inesperada do envio vira ambígua e libera a barreira', async () => {
  const entry = startBid('d@x', LOT, 5000, '50,00', () => Promise.reject(new Error('boom')))
  assert.ok(entry)
  assert.deepEqual(await entry.outcome, { ok: false, failure: 'ambiguous' })
  assert.equal(pendingBidOf('d@x', LOT), null)
})

test('a montagem acompanha a entrada capturada mesmo depois de o registro liberá-la', async () => {
  const gate = deferred()
  let sends = 0
  const entry = startBid('r@x', LOT, 5000, '50,00', () => {
    sends += 1
    return gate.promise
  })
  assert.ok(entry)
  // Renderização: captura. O POST termina antes do efeito e o registro libera a entrada.
  const captured = pendingBidOf('r@x', LOT)
  gate.resolve({ ok: false, failure: 'below_minimum' })
  await entry.outcome
  assert.equal(pendingBidOf('r@x', LOT), null)
  // Efeito: a consulta ao registro sozinha abandonaria o resultado.
  const followed = bidToFollow(captured, 'r@x', LOT)
  assert.equal(followed, entry)
  assert.deepEqual(await followed.outcome, { ok: false, failure: 'below_minimum' })
  assert.equal(sends, 1)
})

test('a entrada capturada nunca vale para outra conta ou outro lote', () => {
  const entry = startBid('s@x', LOT, 1, '0,01', () => new Promise<BidResult>(() => {}))
  assert.ok(entry)
  assert.equal(bidToFollow(entry, 's@x', LOT), entry)
  assert.equal(bidToFollow(entry, 't@x', LOT), null)
  assert.equal(bidToFollow(entry, 's@x', OTHER_LOT), null)
  assert.equal(bidToFollow(null, 's@x', LOT), entry)
})
