import assert from 'node:assert/strict'
import test from 'node:test'
import { confirmationError, passwordStrength } from './passwordStrength.ts'

test('senha: 3/4 grupos Unicode, espaços preservados e limites por code points', () => {
  for (const password of ['Abcdefg1', 'abcdef1!', 'ABCDEF1!', 'Abcdefg!', 'Abcdef1!', ' áÉ١    ', ' aaAA😀  ', ' aA1    ', 'Aa1' + '😀'.repeat(1021)]) assert.equal(passwordStrength(password).valid, true)
  for (const password of ['', 'Aa1abc!', 'abcdefgh', 'Abcdefgh', 'abcd1234', 'ABCD1234', '        ', 'aA      ', 'Aa1' + '😀'.repeat(1022)]) assert.equal(passwordStrength(password).valid, false)
})
test('confirmação literal não normaliza caixa ou espaços', () => {
  assert.equal(confirmationError(' Abcd123! ', ' Abcd123! '), undefined)
  assert.equal(confirmationError(' Abcd123! ', ''), 'Confirme sua senha.')
  for (const other of ['Abcd123!', ' abcd123! ', ' Abcd123!']) assert.equal(confirmationError(' Abcd123! ', other), 'As senhas não coincidem.')
})
