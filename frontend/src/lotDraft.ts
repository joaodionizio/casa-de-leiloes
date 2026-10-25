// Rascunho do lote e sua checagem local (Story 2.4, frontend-lot-creation §4, §5, §8).
// A checagem é só PREVENTIVA: recebe `now` por parâmetro (o relógio do navegador, que
// aqui só evita ir à revisão com um horário que já passou) e nunca decide nada. A
// autoridade final é o servidor, com a hora do banco (AD-6), que repete as regras na
// publicação. O dinheiro vira centavos por texto (`money.ts`), nunca por ponto
// flutuante.

import type { CreateLotRequest, FieldProblem, LotField } from './api/lots.ts'
import { localInputToIso } from './lotTime.ts'
import { moneyErrorMessage, parseReaisToCents } from './money.ts'

export type StartMode = 'now' | 'scheduled'

export interface LotDraft {
  startingBid: string
  minIncrement: string
  startMode: StartMode
  // Valor do campo `datetime-local`, no horário do navegador.
  startsAtLocal: string
  endsAtLocal: string
}

// Mensagem por campo; ausente = sem erro.
export interface DraftErrors {
  starting_bid_cents?: string
  min_increment_cents?: string
  starts_at?: string
  ends_at?: string
}

export type DraftCheck =
  | { ok: true; request: CreateLotRequest }
  | { ok: false; errors: DraftErrors }

// Ordem visual dos campos: o primeiro com erro recebe o foco.
export const FIELD_ORDER: LotField[] = [
  'starting_bid_cents',
  'min_increment_cents',
  'starts_at',
  'ends_at',
]

export function emptyDraft(): LotDraft {
  return {
    startingBid: '',
    minIncrement: '',
    startMode: 'now',
    startsAtLocal: '',
    endsAtLocal: '',
  }
}

export function firstErrorField(errors: DraftErrors): LotField | null {
  return FIELD_ORDER.find((field) => errors[field] !== undefined) ?? null
}

const INVALID_DATE_TIME = 'Data e hora inválidas.'
const START_IN_PAST = 'O início agendado já passou. Escolha um horário futuro.'
const END_BEFORE_PUBLISH = 'O término precisa ser depois do momento da publicação.'
const END_BEFORE_START = 'O término precisa ser depois do início.'

type MomentField = 'starts_at' | 'ends_at'

// Erro de UM horário escolhido (sem a relação entre início e término), ou null.
export function momentError(
  field: MomentField,
  local: string,
  startMode: StartMode,
  now: Date,
): string | null {
  if (local === '') {
    return field === 'starts_at'
      ? 'Informe a data e a hora de início.'
      : 'Informe a data e a hora de término.'
  }
  const iso = localInputToIso(local)
  if (iso === null) return INVALID_DATE_TIME
  const moment = new Date(iso).getTime()
  if (field === 'starts_at' && moment <= now.getTime()) return START_IN_PAST
  // Com "assim que eu publicar" o início é "agora": o término tem de ser posterior.
  // Agendado, a relação com o início é checada no rascunho.
  if (field === 'ends_at' && startMode === 'now' && moment <= now.getTime()) {
    return END_BEFORE_PUBLISH
  }
  return null
}

export function checkDraft(externalId: number, draft: LotDraft, now: Date): DraftCheck {
  const errors: DraftErrors = {}

  const startingBid = parseReaisToCents(draft.startingBid)
  if (!startingBid.ok) errors.starting_bid_cents = moneyErrorMessage(startingBid.error, draft.startingBid)
  const minIncrement = parseReaisToCents(draft.minIncrement)
  if (!minIncrement.ok) errors.min_increment_cents = moneyErrorMessage(minIncrement.error, draft.minIncrement)

  // "Revisar lote" reexecuta tudo com o valor ATUAL do rascunho e com o `now` do
  // momento do clique: um rascunho inválido nunca vira `request`.
  const scheduled = draft.startMode === 'scheduled'
  if (scheduled) {
    const error = momentError('starts_at', draft.startsAtLocal, draft.startMode, now)
    if (error !== null) errors.starts_at = error
  }
  const endsError = momentError('ends_at', draft.endsAtLocal, draft.startMode, now)
  if (endsError !== null) errors.ends_at = endsError

  const startsAt = scheduled ? localInputToIso(draft.startsAtLocal) : null
  const endsAt = localInputToIso(draft.endsAtLocal)

  // Compara só as duas escolhas da pessoa entre si.
  if (
    scheduled &&
    errors.starts_at === undefined &&
    errors.ends_at === undefined &&
    startsAt !== null &&
    endsAt !== null &&
    new Date(endsAt).getTime() <= new Date(startsAt).getTime()
  ) {
    errors.ends_at = END_BEFORE_START
  }

  if (
    !startingBid.ok ||
    !minIncrement.ok ||
    endsAt === null ||
    (scheduled && startsAt === null) ||
    errors.starts_at !== undefined ||
    errors.ends_at !== undefined
  ) {
    return { ok: false, errors }
  }
  return {
    ok: true,
    request: {
      external_id: externalId,
      starting_bid_cents: startingBid.cents,
      min_increment_cents: minIncrement.cents,
      starts_at: startsAt,
      ends_at: endsAt,
    },
  }
}

// Erros do servidor (422) com campo → mensagem no campo (§8). Sem campo, ficam de fora.
export function serverProblemMessages(
  problems: FieldProblem[],
  startMode: StartMode,
): DraftErrors {
  const errors: DraftErrors = {}
  for (const problem of problems) {
    if (problem.field === null) continue
    if (problem.field === 'starting_bid_cents' || problem.field === 'min_increment_cents') {
      errors[problem.field] = 'Valor inválido.'
    } else if (problem.field === 'starts_at') {
      errors.starts_at =
        problem.type === 'starts_at_not_in_future'
          ? START_IN_PAST
          : INVALID_DATE_TIME
    } else if (problem.type === 'ends_at_not_after_start') {
      errors.ends_at = startMode === 'now' ? END_BEFORE_PUBLISH : END_BEFORE_START
    } else {
      errors.ends_at = INVALID_DATE_TIME
    }
  }
  return errors
}
