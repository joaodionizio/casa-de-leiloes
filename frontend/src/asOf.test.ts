// Linha "Situação atualizada…" (Story 2.5, D16). O fuso é injetado: nada depende da
// hora nem do fuso real da máquina. Importar o módulo também prova que ele carrega no
// Node (lição do `Intl` da Story 2.4).
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { asOfText } from './asOf.ts'

const SAO_PAULO = 'America/Sao_Paulo'
const TODAY_25 = new Date('2026-10-25T15:00:00Z') // 25/10 12:00 em São Paulo
const TODAY_26 = new Date('2026-10-26T15:00:00Z')

test('mesmo dia: só a hora', () => {
  assert.equal(
    asOfText('2026-10-25T17:30:00Z', TODAY_25, SAO_PAULO),
    'Situação atualizada às 14:30',
  )
})

test('outro dia: data e hora', () => {
  assert.equal(
    asOfText('2026-10-25T17:30:00Z', TODAY_26, SAO_PAULO),
    'Situação atualizada em 25/10/2026 às 14:30',
  )
})

test('a virada de dia depende do fuso, não do UTC', () => {
  const asOf = '2026-10-26T02:30:00Z'
  // Em São Paulo ainda é 25/10, 23:30: mesmo dia de `TODAY_25`.
  assert.equal(
    asOfText(asOf, TODAY_25, SAO_PAULO),
    'Situação atualizada às 23:30',
  )
  // Em UTC já é 26/10: outro dia em relação a `TODAY_25`.
  assert.equal(
    asOfText(asOf, TODAY_25, 'UTC'),
    'Situação atualizada em 26/10/2026 às 02:30',
  )
})

test('relógio de 24 horas, com zero à esquerda', () => {
  assert.equal(
    asOfText('2026-10-25T12:05:00Z', TODAY_25, SAO_PAULO),
    'Situação atualizada às 09:05',
  )
  assert.equal(
    asOfText('2026-10-25T00:00:00Z', TODAY_25, 'UTC'),
    'Situação atualizada às 00:00',
  )
})

test('as_of com microssegundos e Z funciona', () => {
  assert.equal(
    asOfText('2026-10-25T17:30:00.123456Z', TODAY_25, SAO_PAULO),
    'Situação atualizada às 14:30',
  )
})

test('as_of ilegível: a linha não aparece', () => {
  assert.equal(asOfText('', TODAY_25, SAO_PAULO), null)
  assert.equal(asOfText('ontem', TODAY_25, SAO_PAULO), null)
  assert.equal(asOfText('2026-10-25T17:30:00Z', new Date('x'), SAO_PAULO), null)
})
