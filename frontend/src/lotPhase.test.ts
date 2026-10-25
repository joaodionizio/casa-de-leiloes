// Rótulos de fase (Story 2.5, P8, D15): só tradução de texto, nenhuma regra temporal.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { phaseLabel, phaseStatusText } from './lotPhase.ts'

test('phaseLabel traduz as três fases', () => {
  assert.equal(phaseLabel('scheduled'), 'Agendado')
  assert.equal(phaseLabel('live'), 'Ao vivo')
  assert.equal(phaseLabel('ended'), 'Encerrado')
})

test('phaseStatusText: só o encerrado diz "apurando resultado"', () => {
  assert.equal(phaseStatusText('ended'), 'Encerrado, apurando resultado')
  assert.equal(phaseStatusText('live'), phaseLabel('live'))
  assert.equal(phaseStatusText('scheduled'), phaseLabel('scheduled'))
})
