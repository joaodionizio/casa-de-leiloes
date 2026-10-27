import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ambiguousNotice, refusalNotice, successText } from './bidFeedback.ts'

test('cada recusa tem o texto exato contratado', () => {
  assert.equal(
    refusalNotice('below_minimum').text,
    'Seu lance está abaixo do mínimo para este lote. Confira o valor mínimo acima.',
  )
  assert.equal(
    refusalNotice('insufficient_balance').text,
    'Saldo disponível insuficiente para este lance.',
  )
  assert.equal(refusalNotice('already_winning').text, 'Você já está ganhando este lote.')
  assert.equal(refusalNotice('lot_not_started').text, 'Este lote ainda não começou.')
  assert.equal(refusalNotice('lot_ended').text, 'Este lote já foi encerrado.')
  assert.equal(
    refusalNotice('integrity').text,
    'Não foi possível verificar a integridade deste lote. O lance não foi registrado.',
  )
})

test('só a recusa por saldo oferece o link da carteira', () => {
  assert.equal(refusalNotice('insufficient_balance').walletLink, true)
  assert.equal(refusalNotice('below_minimum').walletLink, false)
})

test('sucesso em reais e aviso de prorrogação', () => {
  assert.equal(successText(125000, false), 'Lance de R$ 1.250,00 registrado.')
  assert.equal(
    successText(125000, true),
    'Lance de R$ 1.250,00 registrado. Prazo prorrogado em 2 minutos.',
  )
})

test('erro ambíguo nunca afirma que o lance entrou ou não', () => {
  for (const sync of ['complete', 'partial', 'pending'] as const) {
    const notice = ambiguousNotice(sync)
    assert.equal(notice.kind, 'uncertain')
    assert.doesNotMatch(notice.text, /registrado|aceito|não foi gravado/i)
  }
  assert.match(ambiguousNotice('complete').text, /estado abaixo é o atual do servidor/)
  assert.match(ambiguousNotice('partial').text, /Atualizar sala/)
})
