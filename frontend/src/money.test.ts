// Testes do conversor de dinheiro (Story 2.4, Q1): `node --test`, sem dependência.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import {
  formatCents,
  MAX_CENTS,
  moneyErrorMessage,
  parseReaisToCents,
  type MoneyError,
} from './money.ts'

function cents(input: string): number {
  const result = parseReaisToCents(input)
  assert.equal(result.ok, true, `"${input}" devia ser aceito`)
  return result.ok ? result.cents : -1
}

function error(input: string): MoneyError | 'ok' {
  const result = parseReaisToCents(input)
  return result.ok ? 'ok' : result.error
}

test('aceita inteiros, vírgula decimal e milhar com ponto', () => {
  const accepted: Array<[string, number]> = [
    ['10', 1000],
    ['10,5', 1050],
    ['0,50', 50],
    ['0,01', 1],
    ['1.234,56', 123456],
    ['1234,56', 123456],
    ['  100,00  ', 10000],
    ['1.000.000', 100000000],
    ['90.071.992.547.409,91', 9007199254740991],
  ]
  for (const [input, expected] of accepted) {
    assert.deepEqual(parseReaisToCents(input), { ok: true, cents: expected }, input)
  }
})

test('o máximo exato é aceito e um centavo acima é recusado', () => {
  assert.equal(cents('90.071.992.547.409,91'), MAX_CENTS)
  assert.equal(error('90.071.992.547.409,92'), 'too_large')
})

test('vazio e só espaços', () => {
  for (const input of ['', '   ', '\t']) {
    assert.deepEqual(parseReaisToCents(input), { ok: false, error: 'empty' }, input)
  }
})

test('zero em qualquer escrita não é positivo', () => {
  for (const input of ['0', '0,00', '000', '0,0', '0.000']) {
    assert.equal(error(input), 'not_positive', input)
  }
})

test('mais de duas casas decimais', () => {
  for (const input of ['1,234', '10,999', '1.234,567']) {
    assert.equal(error(input), 'too_many_decimals', input)
  }
})

test('ponto no lugar da vírgula tem mensagem própria e nunca é reinterpretado', () => {
  for (const input of ['655.3', '12.5', '12.50', '0.5', '1.23', ' 655.3 ']) {
    assert.equal(error(input), 'dot_decimal', input)
  }
  assert.equal(
    moneyErrorMessage('dot_decimal'),
    'Use vírgula para os centavos. Ex.: 655,30.',
  )
  // O que continua aceito não muda: milhar com três dígitos e a vírgula decimal.
  assert.equal(cents('655,30'), 65530)
  assert.equal(cents('1.234'), 123400)
  assert.equal(cents('5'), 500)
  assert.equal(cents('5,50'), 550)
  assert.equal(cents('1.250,00'), 125000)
  // Formatos ambíguos ou errados seguem recusados, cada um com a sua razão.
  assert.equal(error('1.5.3'), 'format')
  assert.equal(error('1.2345'), 'format')
  assert.equal(error('1.234.5'), 'format')
  assert.equal(error('1.23,45'), 'format')
  assert.equal(error('.5'), 'format')
  assert.equal(error('655.'), 'format')
})

test('ponto decimal: a mensagem sugere a escrita com vírgula a partir do que foi digitado', () => {
  const expected: Array<[string, string]> = [
    ['333.55', 'Use vírgula para os centavos. Ex.: 333,55.'],
    ['12.5', 'Use vírgula para os centavos. Ex.: 12,50.'],
    ['0.5', 'Use vírgula para os centavos. Ex.: 0,50.'],
    [' 655.3 ', 'Use vírgula para os centavos. Ex.: 655,30.'],
  ]
  for (const [input, message] of expected) {
    const result = parseReaisToCents(input)
    assert.equal(result.ok, false, input)
    assert.equal(result.ok ? '' : result.error, 'dot_decimal', input)
    assert.equal(moneyErrorMessage('dot_decimal', input), message, input)
  }
  // Os que não são ponto decimal NÃO ganham a dica da vírgula.
  for (const input of ['abc', '1,2,3', '10,999', '1.5.3', '-5']) {
    const result = parseReaisToCents(input)
    assert.equal(result.ok, false, input)
    const message = moneyErrorMessage(result.ok ? 'format' : result.error, input)
    assert.equal(message.includes('Use vírgula para os centavos'), false, input)
  }
  // O milhar válido segue válido: o ponto não vira erro automaticamente.
  assert.equal(cents('1.250,00'), 125000)
  assert.equal(cents('1.250'), 125000)
  assert.equal(cents('5'), 500)
  assert.equal(cents('5,50'), 550)
})

test('formatos que o campo recusa, cada um com o motivo certo', () => {
  assert.equal(error('1,2,3'), 'format')
  assert.equal(error('abc'), 'format')
  assert.equal(error('-5'), 'format')
  assert.equal(error('10,999'), 'too_many_decimals')
  assert.equal(error('0'), 'not_positive')
  assert.equal(error('0,00'), 'not_positive')
  assert.equal(error('90.071.992.547.409,92'), 'too_large')
})

test('formatos inválidos', () => {
  const invalid = [
    'abc',
    '-5',
    'R$ 10',
    '1.23,45',
    '1.2345',
    ',50',
    '10,',
    '1 000',
    '10.000.0',
    '1e3',
    '+10',
    '１０', // dígitos de largura total
    '10,5,0',
    '..',
  ]
  for (const input of invalid) {
    assert.equal(error(input), 'format', input)
  }
})

test('valores acima do limite', () => {
  for (const input of [
    '90.071.992.547.409,92',
    '100000000000000',
    '99999999999999999,99',
    '999.999.999.999.999.999',
  ]) {
    assert.equal(error(input), 'too_large', input)
  }
})

test('todo resultado aceito é um inteiro seguro e positivo', () => {
  for (const input of ['0,01', '1', '1.234,56', '90.071.992.547.409,91', '12345678,9']) {
    const value = cents(input)
    assert.equal(Number.isSafeInteger(value), true, input)
    assert.equal(value >= 1, true, input)
  }
})

test('formatCents', () => {
  const expected: Array<[number, string]> = [
    [1, 'R$ 0,01'],
    [50, 'R$ 0,50'],
    [100, 'R$ 1,00'],
    [123456, 'R$ 1.234,56'],
    [100000000, 'R$ 1.000.000,00'],
    [MAX_CENTS, 'R$ 90.071.992.547.409,91'],
  ]
  for (const [value, text] of expected) {
    assert.equal(formatCents(value), text)
  }
})

test('formatCents recusa o que não é centavo inteiro e seguro', () => {
  for (const value of [-1, 1.5, Number.NaN, Number.MAX_SAFE_INTEGER + 2]) {
    assert.throws(() => formatCents(value), RangeError)
  }
})

test('ida e volta: formatar e converter devolve os mesmos centavos', () => {
  for (const value of [1, 99, 100, 123456, 100000000, MAX_CENTS]) {
    const text = formatCents(value).slice('R$ '.length)
    assert.deepEqual(parseReaisToCents(text), { ok: true, cents: value }, text)
  }
})

test('os exemplos mostrados ao usuário: 5, 5,50 e 1.250,00 em reais e em centavos', () => {
  const examples: Array<[string, number, string]> = [
    ['5', 500, 'R$ 5,00'],
    ['5,50', 550, 'R$ 5,50'],
    ['1.250,00', 125000, 'R$ 1.250,00'],
  ]
  for (const [input, expectedCents, shown] of examples) {
    assert.equal(cents(input), expectedCents, input)
    // O "Valor reconhecido" da tela é o formatCents dos centavos calculados.
    assert.equal(formatCents(expectedCents), shown, input)
  }
})

test('o limite é o mesmo do back-end e do banco', () => {
  assert.equal(MAX_CENTS, Number.MAX_SAFE_INTEGER)
  assert.equal(MAX_CENTS, 9007199254740991)
})

test('toda falha tem mensagem em português', () => {
  const errors: MoneyError[] = [
    'empty',
    'format',
    'too_many_decimals',
    'dot_decimal',
    'not_positive',
    'too_large',
  ]
  for (const kind of errors) {
    assert.notEqual(moneyErrorMessage(kind), '')
  }
})

test('o fonte não usa conversão de ponto flutuante', () => {
  const source = readFileSync(new URL('./money.ts', import.meta.url), 'utf8')
  // Os testes acima provam o comportamento; aqui, a ausência das construções.
  for (const forbidden of ['parseFloat', 'parseInt', '* 100', '/ 100', 'toFixed']) {
    assert.equal(source.includes(forbidden), false, forbidden)
  }
})
