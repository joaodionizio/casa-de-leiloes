// Testes da checagem preventiva do rascunho (Story 2.4). `now` é sempre injetado: nada
// aqui depende da hora real. Nasceram do teste manual de 25/10/2026, em que um término
// de 23/10 passou pelo formulário, chegou à revisão e só o servidor o recusou.
import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import {
  checkDraft,
  emptyDraft,
  momentError,
  serverProblemMessages,
  type DraftCheck,
  type LotDraft,
} from './lotDraft.ts'

// 25/10/2026 12:00 UTC. Os valores `datetime-local` abaixo são horário de parede do
// fuso da máquina, então o teste fixa o fuso para ser determinístico.
const NOW = new Date('2026-10-25T12:00:00Z')

let originalTz: string | undefined
before(() => {
  originalTz = process.env.TZ
  process.env.TZ = 'UTC'
})
after(() => {
  if (originalTz === undefined) delete process.env.TZ
  else process.env.TZ = originalTz
})

// Rascunho com dinheiro válido; os horários vêm de `overrides`.
function draft(overrides: Partial<LotDraft> = {}): LotDraft {
  return { ...emptyDraft(), startingBid: '100', minIncrement: '10', ...overrides }
}

function errorsOf(check: DraftCheck): Record<string, string | undefined> {
  assert.equal(check.ok, false, 'o rascunho devia ser inválido')
  return check.ok ? {} : { ...check.errors }
}

test('"assim que eu publicar" com término no passado é inválido e não gera request', () => {
  const check = checkDraft(1, draft({ endsAtLocal: '2026-10-23T17:18' }), NOW)
  assert.deepEqual(errorsOf(check), {
    ends_at: 'O término precisa ser depois do momento da publicação.',
  })
})

test('"assim que eu publicar": término igual a agora é inválido; um minuto depois vale', () => {
  assert.equal(checkDraft(1, draft({ endsAtLocal: '2026-10-25T12:00' }), NOW).ok, false)
  const ok = checkDraft(1, draft({ endsAtLocal: '2026-10-25T12:01' }), NOW)
  assert.equal(ok.ok, true)
  if (ok.ok) {
    assert.equal(ok.request.starts_at, null)
    assert.equal(ok.request.ends_at, '2026-10-25T12:01:00.000Z')
  }
})

test('início agendado no passado é inválido', () => {
  const check = checkDraft(
    1,
    draft({
      startMode: 'scheduled',
      startsAtLocal: '2026-10-25T11:59',
      endsAtLocal: '2026-10-26T12:00',
    }),
    NOW,
  )
  assert.deepEqual(errorsOf(check), {
    starts_at: 'O início agendado já passou. Escolha um horário futuro.',
  })
})

test('início agendado igual a agora também é inválido', () => {
  const check = checkDraft(
    1,
    draft({
      startMode: 'scheduled',
      startsAtLocal: '2026-10-25T12:00',
      endsAtLocal: '2026-10-26T12:00',
    }),
    NOW,
  )
  assert.equal(errorsOf(check).starts_at !== undefined, true)
})

test('término menor ou igual ao início agendado é inválido', () => {
  for (const ends of ['2026-10-26T10:00', '2026-10-26T09:00']) {
    const check = checkDraft(
      1,
      draft({ startMode: 'scheduled', startsAtLocal: '2026-10-26T10:00', endsAtLocal: ends }),
      NOW,
    )
    assert.deepEqual(errorsOf(check), { ends_at: 'O término precisa ser depois do início.' }, ends)
  }
})

test('início futuro com término posterior é válido e usa os horários confirmados em UTC', () => {
  const check = checkDraft(
    27992,
    draft({
      startMode: 'scheduled',
      startsAtLocal: '2026-10-26T10:00',
      endsAtLocal: '2026-10-27T10:00',
    }),
    NOW,
  )
  assert.equal(check.ok, true)
  if (check.ok) {
    assert.deepEqual(check.request, {
      external_id: 27992,
      starting_bid_cents: 10000,
      min_increment_cents: 1000,
      starts_at: '2026-10-26T10:00:00.000Z',
      ends_at: '2026-10-27T10:00:00.000Z',
    })
  }
})

test('o resultado não depende do fuso da máquina, só do instante', () => {
  // Mesmo instante de parede relativo a `now`: em cada fuso, "daqui a 1 dia" vale.
  for (const zone of ['UTC', 'America/Sao_Paulo', 'Asia/Tokyo']) {
    process.env.TZ = zone
    const wallClock = (offsetMs: number): string => {
      const moment = new Date(NOW.getTime() + offsetMs)
      const pad = (n: number) => String(n).padStart(2, '0')
      return `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}T${pad(moment.getHours())}:${pad(moment.getMinutes())}`
    }
    assert.equal(checkDraft(1, draft({ endsAtLocal: wallClock(86_400_000) }), NOW).ok, true, zone)
    assert.equal(checkDraft(1, draft({ endsAtLocal: wallClock(-86_400_000) }), NOW).ok, false, zone)
  }
  process.env.TZ = 'UTC'
})

test('"Revisar lote" revalida o valor ATUAL: corrigir para inválido volta a bloquear', () => {
  // Mesmo rascunho, editado em seguida: não há estado velho que deixe passar.
  const valid = draft({ endsAtLocal: '2026-10-27T10:00' })
  assert.equal(checkDraft(1, valid, NOW).ok, true)
  const edited = { ...valid, endsAtLocal: '2026-10-23T17:18' }
  assert.deepEqual(errorsOf(checkDraft(1, edited, NOW)), {
    ends_at: 'O término precisa ser depois do momento da publicação.',
  })
  // E a troca de modo também é revalidada: o mesmo término vale agendado só se for
  // posterior ao início.
  const toScheduled = { ...valid, startMode: 'scheduled' as const, startsAtLocal: '2026-10-28T10:00' }
  assert.deepEqual(errorsOf(checkDraft(1, toScheduled, NOW)), {
    ends_at: 'O término precisa ser depois do início.',
  })
})

test('o mesmo rascunho que valia deixa de valer quando o relógio avança', () => {
  // Escolhido quando ainda valia; ao clicar em revisar, o relógio avançou.
  const later = new Date('2026-10-27T10:00:01Z')
  const check = checkDraft(1, draft({ endsAtLocal: '2026-10-27T10:00' }), later)
  assert.equal(errorsOf(check).ends_at, 'O término precisa ser depois do momento da publicação.')
})

test('campos vazios e formatos inválidos', () => {
  const empty = checkDraft(1, draft({ endsAtLocal: '' }), NOW)
  assert.deepEqual(errorsOf(empty), { ends_at: 'Informe a data e a hora de término.' })
  const emptyStart = checkDraft(
    1,
    draft({ startMode: 'scheduled', startsAtLocal: '', endsAtLocal: '2026-10-27T10:00' }),
    NOW,
  )
  assert.deepEqual(errorsOf(emptyStart), { starts_at: 'Informe a data e a hora de início.' })
  const invalid = checkDraft(1, draft({ endsAtLocal: 'amanhã' }), NOW)
  assert.deepEqual(errorsOf(invalid), { ends_at: 'Data e hora inválidas.' })
})

test('os erros de dinheiro continuam e se somam aos de horário', () => {
  const check = checkDraft(
    1,
    draft({ startingBid: '0', minIncrement: '1,234', endsAtLocal: '2026-10-23T10:00' }),
    NOW,
  )
  assert.deepEqual(errorsOf(check), {
    starting_bid_cents: 'O valor precisa ser maior que zero.',
    min_increment_cents: 'Use no máximo duas casas decimais.',
    ends_at: 'O término precisa ser depois do momento da publicação.',
  })
})

test('momentError: o erro de um horário isolado', () => {
  assert.equal(momentError('ends_at', '2026-10-26T10:00', 'now', NOW), null)
  assert.equal(
    momentError('ends_at', '2026-10-24T10:00', 'now', NOW),
    'O término precisa ser depois do momento da publicação.',
  )
  // Agendado: a relação com o início fica para a checagem do rascunho.
  assert.equal(momentError('ends_at', '2026-10-24T10:00', 'scheduled', NOW), null)
  assert.equal(
    momentError('starts_at', '2026-10-24T10:00', 'scheduled', NOW),
    'O início agendado já passou. Escolha um horário futuro.',
  )
  assert.equal(momentError('starts_at', '', 'scheduled', NOW), 'Informe a data e a hora de início.')
})

test('mensagens do servidor por campo (volta da revisão)', () => {
  assert.deepEqual(
    serverProblemMessages(
      [
        { field: 'ends_at', type: 'ends_at_not_after_start' },
        { field: 'starts_at', type: 'starts_at_not_in_future' },
        { field: null, type: 'x' },
      ],
      'now',
    ),
    {
      ends_at: 'O término precisa ser depois do momento da publicação.',
      starts_at: 'O início agendado já passou. Escolha um horário futuro.',
    },
  )
})
