import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { CancelLotFailure } from './api/lots.ts'
import {
  bidCountText,
  canCancelLot,
  cancelFailureNotice,
  CANCEL_AMBIGUOUS_TEXT,
  CANCEL_WITH_BIDS_CONFIRM_TEXT,
  shouldRefetch,
} from './lotCancellation.ts'

const base = { cancelled_at: null, bid_count: 0, phase: 'live' } as const

test('o CTA só aparece para lote não cancelado e não encerrado, com ou sem lances', () => {
  assert.equal(canCancelLot(base), true)
  assert.equal(canCancelLot({ ...base, phase: 'scheduled' }), true)
  assert.equal(canCancelLot({ ...base, phase: 'ended' }), false)
  assert.equal(canCancelLot({ ...base, bid_count: 1 }), true)
  assert.equal(canCancelLot({ ...base, cancelled_at: '2026-10-26T12:00:00Z' }), false)
  assert.equal(
    canCancelLot({ cancelled_at: '2026-10-26T12:00:00Z', bid_count: 0, phase: 'ended' }),
    false,
  )
})

test('cada falha de negócio tem o texto contratado', () => {
  assert.equal(cancelFailureNotice('ended').text, 'Este lote já foi encerrado.')
  assert.equal(cancelFailureNotice('forbidden').text, 'Você não pode cancelar este lote.')
  assert.equal(cancelFailureNotice('not_found').text, 'Lote não encontrado.')
  assert.equal(
    cancelFailureNotice('integrity').text,
    'Não foi possível concluir a operação porque a integridade do lote não pôde ser confirmada.',
  )
  for (const failure of ['ended', 'forbidden', 'not_found', 'integrity'] as const) {
    assert.equal(cancelFailureNotice(failure).kind, 'error')
  }
})

test('o 409 de integridade não afirma cancelamento nem fala em lance, hash ou HMAC', () => {
  assert.doesNotMatch(cancelFailureNotice('integrity').text, /cancelado com|lance|hash|HMAC|âncora/i)
})

test('o erro ambíguo nunca afirma sucesso nem falha', () => {
  const notice = cancelFailureNotice('ambiguous')
  assert.equal(notice.kind, 'uncertain')
  assert.equal(notice.text, CANCEL_AMBIGUOUS_TEXT)
  assert.doesNotMatch(notice.text, /Lote cancelado\.|não foi cancelado|foi cancelado com sucesso/i)
})

test('a lista é relida no sucesso, encerrado e ambíguo', () => {
  assert.equal(shouldRefetch(null), true)
  const failures: CancelLotFailure[] = ['ended', 'integrity', 'forbidden', 'not_found', 'unauthorized', 'ambiguous']
  assert.deepEqual(
    failures.filter((failure) => shouldRefetch(failure)),
    ['ended', 'ambiguous'],
  )
})

test('contagem de lances no singular e no plural', () => {
  assert.equal(bidCountText(0), '0 lances')
  assert.equal(bidCountText(1), '1 lance')
  assert.equal(bidCountText(2), '2 lances')
})

test('a confirmação com lances explica a liberação sem identificar o líder', () => {
  assert.equal(CANCEL_WITH_BIDS_CONFIRM_TEXT, 'Este lote possui lances. Ao cancelar, o saldo comprometido do licitante líder será liberado automaticamente.')
})
