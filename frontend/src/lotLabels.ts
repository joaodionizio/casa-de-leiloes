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

// Nome acessível do link de um lote: começa pelo título, depois o estado em texto e o
// lance inicial (nunca "lance atual": ainda não existe lance). O encerrado não leva o
// valor, como a linha dele na tela: sem resultado, o lance inicial pareceria preço final.
export function lotLinkLabel(lot: PublicLotSummary): string {
  const base = `${lotTitleText(lot.title)}. ${phaseStatusText(lot.phase)}.`
  if (lot.phase === 'ended') return base
  return `${base} Lance inicial ${formatCents(lot.starting_bid_cents)}.`
}
