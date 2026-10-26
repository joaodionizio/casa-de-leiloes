// Textos e decisão pós-depósito (Story 3.1, P8): nenhum afirma que o depósito entrou
// sem confirmação do servidor.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { DepositFailure } from './api/wallet.ts'
import {
  depositFailureNotice,
  depositSuccessText,
  failureBelongsToField,
  rereadNotice,
} from './walletFeedback.ts'

test('depositSuccessText usa o dinheiro formatado pelo money.ts', () => {
  assert.equal(depositSuccessText(125000), 'Depósito de R$ 1.250,00 confirmado.')
  assert.equal(depositSuccessText(50), 'Depósito de R$ 0,50 confirmado.')
})

test('cada erro conhecido tem o texto combinado', () => {
  assert.deepEqual(depositFailureNotice('validation'), {
    kind: 'error',
    text: 'Informe um valor válido em reais.',
  })
  assert.deepEqual(depositFailureNotice('balance_limit'), {
    kind: 'error',
    text: 'O depósito ultrapassaria o limite de saldo da carteira.',
  })
  assert.deepEqual(depositFailureNotice('rejected'), {
    kind: 'error',
    text: 'Não foi possível concluir o depósito. Recarregue a página e tente novamente.',
  })
  assert.deepEqual(depositFailureNotice('forbidden'), {
    kind: 'error',
    text: 'Esta área é só para a conta de licitante.',
  })
})

test('só validação e teto aparecem no campo', () => {
  const failures: DepositFailure[] = [
    'validation',
    'balance_limit',
    'unauthorized',
    'forbidden',
    'rejected',
    'ambiguous',
  ]
  assert.deepEqual(
    failures.filter(failureBelongsToField),
    ['validation', 'balance_limit'],
  )
})

test('a releitura nunca afirma que o depósito entrou', () => {
  const ok = rereadNotice({
    ok: true,
    wallet: {
      total_balance_cents: 100,
      committed_balance_cents: 0,
      available_balance_cents: 100,
    },
  })
  const failed = rereadNotice({ ok: false, failure: 'server' })

  assert.equal(ok.kind, 'uncertain')
  assert.equal(failed.kind, 'uncertain')
  assert.match(ok.text, /Não foi possível confirmar o depósito/)
  assert.match(failed.text, /Não foi possível confirmar se o depósito foi feito/)
  for (const notice of [ok, failed]) {
    assert.doesNotMatch(notice.text, /confirmado\./)
    assert.doesNotMatch(notice.text, /foi realizado|entrou|com sucesso/i)
  }
})
