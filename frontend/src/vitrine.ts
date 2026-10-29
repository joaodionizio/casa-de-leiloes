// Regras de tela da vitrine (Story 2.5, D12, D13, D14). Funções puras: nenhuma
// compara datas nem decide fase. O servidor já entrega os grupos classificados e
// ordenados; aqui só escolhemos o destaque e contamos quantos itens aparecem.

import type { PublicLotSummary, PublicLotsResponse } from './api/publicLots.ts'

// "Mostrar mais encerrados" revela de 6 em 6, só localmente, sem nova chamada.
export const ENDED_STEP = 6

export type VitrinePhaseFilter = 'all' | PublicLotSummary['phase']

function searchText(value: string): string {
  return value.normalize('NFD').replace(/\p{M}/gu, '').toLocaleLowerCase('pt-BR')
}

// Filtra somente os metadados da fotografia pública. Preserva grupos, ordem e
// estados recebidos; UUID e horários operacionais não entram na busca.
export function filterPublicLots(
  data: PublicLotsResponse,
  term: string,
  phase: VitrinePhaseFilter,
): PublicLotsResponse {
  const query = searchText(term.trim())
  function matching(group: PublicLotSummary[], kind: PublicLotSummary['phase']) {
    if (phase !== 'all' && phase !== kind) return []
    return group.filter((lot) => query === '' ||
      [lot.title, lot.artist_display, lot.date_display].some(
        (value) => value !== null && searchText(value).includes(query),
      ),
    )
  }
  return {
    as_of: data.as_of,
    live: matching(data.live, 'live'),
    scheduled: matching(data.scheduled, 'scheduled'),
    ended: matching(data.ended, 'ended'),
  }
}

export type Featured =
  | { kind: 'live'; lot: PublicLotSummary }
  | { kind: 'scheduled'; lot: PublicLotSummary }
  | { kind: 'none' }

// Primeiro ao vivo; sem ao vivo, o primeiro agendado; encerrado nunca é destaque.
export function selectFeatured(data: PublicLotsResponse): Featured {
  if (data.live.length > 0) return { kind: 'live', lot: data.live[0] }
  if (data.scheduled.length > 0) return { kind: 'scheduled', lot: data.scheduled[0] }
  return { kind: 'none' }
}

// O grupo sem o lote em destaque (por id), na mesma ordem. O destaque não se repete
// no rail da própria seção.
export function railItems(
  group: PublicLotSummary[],
  featured: Featured,
): PublicLotSummary[] {
  if (featured.kind === 'none') return group
  return group.filter((lot) => lot.id !== featured.lot.id)
}

export function nextEndedVisible(current: number, total: number): number {
  return Math.min(current + ENDED_STEP, total)
}

// Quantos encerrados aparecem de início. `restore` vem do `history.state` (quantos
// estavam visíveis ao sair da vitrine); só vale se for inteiro e múltiplo possível de
// um passo (>= ENDED_STEP), senão volta ao padrão.
export function initialEndedVisible(total: number, restore?: number): number {
  if (
    restore !== undefined &&
    Number.isInteger(restore) &&
    restore >= ENDED_STEP
  ) {
    return Math.min(restore, total)
  }
  return Math.min(ENDED_STEP, total)
}

export interface RailScrollState {
  overflow: boolean
  canPrev: boolean
  canNext: boolean
}

// Estado dos botões "Anterior"/"Próximo" do rail, com tolerância de 1 px nas pontas
// (a rolagem pode terminar em fração de pixel).
export function railScrollState(
  scrollLeft: number,
  clientWidth: number,
  scrollWidth: number,
): RailScrollState {
  const overflow = scrollWidth - clientWidth > 1
  return {
    overflow,
    canPrev: overflow && scrollLeft > 1,
    canNext: overflow && scrollLeft + clientWidth < scrollWidth - 1,
  }
}
