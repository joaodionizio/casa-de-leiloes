// Testes de lotTime.ts (Story 2.4). Existem porque o primeiro teste manual abriu uma
// tela branca: o `Intl.DateTimeFormat` do módulo tinha uma combinação inválida de
// opções e lançava na importação. Lint, tipos e build não pegam isso; só executar o
// módulo pega. Importar o módulo abaixo já é o teste principal.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { browserTimeZone, formatDateTime, localInputToIso } from './lotTime.ts'

test('importar o módulo e formatar uma data UTC não lança', () => {
  assert.doesNotThrow(() => formatDateTime('2026-10-25T16:00:00Z'))
})

test('uma data UTC válida vira texto não vazio com o ano e a hora', () => {
  const text = formatDateTime('2026-10-25T16:00:00.123456Z')
  assert.notEqual(text, '')
  assert.match(text, /2026/)
  // A hora depende do fuso da máquina, mas sempre aparecem minutos "00".
  assert.match(text, /\d{2}:00/)
})

test('o texto traz o nome do fuso (a spec pede o fuso indicado)', () => {
  // O nome varia por ICU e por fuso (BRT, GMT-3, UTC); só exijo algo depois da hora.
  assert.match(formatDateTime('2026-10-25T16:00:00Z'), /\d{2}:\d{2}\s+\S+/)
})

test('texto ilegível do servidor volta como veio, sem lançar', () => {
  assert.equal(formatDateTime('não é data'), 'não é data')
  assert.equal(formatDateTime(''), '')
})

test('o fuso do navegador é um identificador não vazio', () => {
  assert.notEqual(browserTimeZone(), '')
})

test('localInputToIso aceita datetime-local com e sem segundos e devolve UTC com Z', () => {
  for (const value of ['2026-10-25T13:00', '2026-10-25T13:00:30']) {
    const iso = localInputToIso(value)
    assert.notEqual(iso, null, value)
    assert.match(iso ?? '', /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
  }
})

// Observação: o `Date` do V8 faz rollover de "2026-02-30T10:00" para 2 de março em vez
// de recusar. O `<input type="datetime-local">` nunca emite uma data assim, então não
// é alcançável pela interface; por isso o caso não está na lista abaixo.
test('localInputToIso recusa o que não é data e hora válidas', () => {
  for (const value of [
    '',
    'amanhã',
    '2026-10-25',
    '2026-10-25 13:00',
    '2026-10-25T13:00Z',
    '2026-13-01T10:00',
  ]) {
    assert.equal(localInputToIso(value), null, value)
  }
})

test('localInputToIso traduz o horário de parede do fuso da máquina, sem regra própria', () => {
  const original = process.env.TZ
  try {
    process.env.TZ = 'UTC'
    assert.equal(localInputToIso('2026-10-25T13:00'), '2026-10-25T13:00:00.000Z')
    process.env.TZ = 'America/Sao_Paulo'
    assert.equal(localInputToIso('2026-10-25T13:00'), '2026-10-25T16:00:00.000Z')
    process.env.TZ = 'Asia/Tokyo'
    assert.equal(localInputToIso('2026-10-25T13:00'), '2026-10-25T04:00:00.000Z')
  } finally {
    if (original === undefined) delete process.env.TZ
    else process.env.TZ = original
  }
})
