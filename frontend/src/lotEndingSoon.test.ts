import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getEndingSoonLabel } from './lotEndingSoon.ts'

const NOW = Date.parse('2026-10-29T12:00:00.000Z')
const endsIn = (milliseconds: number) => new Date(NOW + milliseconds).toISOString()

test('mais de 10 minutos não recebe aviso', () => {
  assert.equal(getEndingSoonLabel(endsIn(10 * 60_000 + 1), NOW), null)
})

test('exatamente 10 minutos recebe Encerrando em breve', () => {
  assert.equal(getEndingSoonLabel(endsIn(10 * 60_000), NOW), 'Encerrando em breve')
})

test('entre 10 e mais de 2 minutos recebe Encerrando em breve', () => {
  for (const remaining of [5 * 60_000, 2 * 60_000 + 1]) {
    assert.equal(getEndingSoonLabel(endsIn(remaining), NOW), 'Encerrando em breve')
  }
})

test('exatamente 2 minutos recebe Últimos 2 minutos', () => {
  assert.equal(getEndingSoonLabel(endsIn(2 * 60_000), NOW), 'Últimos 2 minutos')
})

test('menos de 2 minutos, até o último milissegundo, recebe Últimos 2 minutos', () => {
  for (const remaining of [60_000, 1]) {
    assert.equal(getEndingSoonLabel(endsIn(remaining), NOW), 'Últimos 2 minutos')
  }
})

test('prazo atingido ou passado não recebe aviso', () => {
  for (const remaining of [0, -1, -60_000]) {
    assert.equal(getEndingSoonLabel(endsIn(remaining), NOW), null)
  }
})

test('prorrogar ends_at recalcula a faixa e pode remover o aviso', () => {
  assert.equal(getEndingSoonLabel(endsIn(2 * 60_000), NOW), 'Últimos 2 minutos')
  assert.equal(getEndingSoonLabel(endsIn(4 * 60_000), NOW), 'Encerrando em breve')
  assert.equal(getEndingSoonLabel(endsIn(12 * 60_000), NOW), null)
})

test('novo instante injetado é usado e entradas inválidas não geram urgência', () => {
  assert.equal(getEndingSoonLabel(endsIn(12 * 60_000), NOW + 10 * 60_000), 'Últimos 2 minutos')
  for (const endsAt of ['', 'data inválida']) {
    assert.equal(getEndingSoonLabel(endsAt, NOW), null)
  }
  for (const now of [Number.NaN, Infinity, -Infinity]) {
    assert.equal(getEndingSoonLabel(endsIn(60_000), now), null)
  }
})
