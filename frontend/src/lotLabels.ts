// Textos de lote reaproveitados pela vitrine e pela página do lote (Story 2.5).
// Só apresentação: o dinheiro vem de `formatCents` (sem duplicar parser) e a fase vem
// pronta do servidor.

import type { PublicLotSummary } from './api/publicLots.ts'
import { phaseStatusText } from './lotPhase.ts'
import { formatCents } from './money.ts'

export const UNTITLED = 'Sem título'

export function lotTitleText(title: string | null): string {
  return title !== null && title.trim() !== '' ? title : UNTITLED
}

// A Vitrine recebe settlement explícito; outros contextos conservam o rótulo genérico.
export function publicLotStatusText(lot: PublicLotSummary): string {
  if (lot.phase === 'ended' && lot.settlement_status === 'settled') return 'Encerrado'
  return phaseStatusText(lot.phase)
}

// Nome acessível do link de um lote: começa pelo título, depois o estado em texto e o
// lance do snapshot. O encerrado não leva o valor, como a linha dele na tela:
// o último lance não representa necessariamente um resultado de liquidação.
export function lotLinkLabel(lot: PublicLotSummary): string {
  const base = `${lotTitleText(lot.title)}. ${publicLotStatusText(lot)}.`
  if (lot.phase === 'ended') return base
  const label = lot.current_bid_cents !== null ? 'Lance atual' : 'Lance inicial'
  return `${base} ${label} ${formatCents(lot.current_bid_cents ?? lot.starting_bid_cents)}.`
}
