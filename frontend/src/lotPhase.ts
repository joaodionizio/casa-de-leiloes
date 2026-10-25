// Rótulos do estado do lote (Story 2.5, P8, D15). O servidor classifica (`phase`); o
// front só traduz o valor recebido em texto. Nada aqui compara datas nem decide fase.
// "Encerrado, apurando resultado" é cópia de interface: não significa que exista
// liquidação (ela nasce na 4.3).

import type { LotPhase } from './api/publicLots.ts'

export function phaseLabel(phase: LotPhase): string {
  if (phase === 'live') return 'Ao vivo'
  if (phase === 'scheduled') return 'Agendado'
  return 'Encerrado'
}

export function phaseStatusText(phase: LotPhase): string {
  if (phase === 'ended') return 'Encerrado, apurando resultado'
  return phaseLabel(phase)
}
