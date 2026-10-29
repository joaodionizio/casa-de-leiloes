// Cancelamento de lote na lista do leiloeiro (Story 3.6). Puro e sem DOM, para o
// `node --test`. Os textos nascem do tipo da falha (status + `code` já classificados em
// `api/lots.ts`), nunca do `message` do servidor. O servidor é a autoridade: a
// elegibilidade daqui é só UX, e um estado antigo pode resultar em recusa.

import type { CancelLotFailure, MyLotResponse } from './api/lots.ts'

export type CancelNoticeKind = 'success' | 'error' | 'uncertain'

export interface CancelNotice {
  kind: CancelNoticeKind
  text: string
}

// Aparentemente elegível: não cancelado e ainda não encerrado. A fase vem do
// servidor (`as_of`), o navegador não calcula nada.
export function canCancelLot(lot: Pick<MyLotResponse, 'cancelled_at' | 'bid_count' | 'phase'>): boolean {
  return lot.cancelled_at === null && lot.phase !== 'ended'
}

export const CANCEL_CONFIRM_TEXT = 'O lote sai da vitrine e não pode ser reaberto.'
export const CANCEL_WITH_BIDS_CONFIRM_TEXT =
  'Este lote possui lances. Ao cancelar, o saldo comprometido do licitante líder será liberado automaticamente.'
export const CANCEL_SUCCESS_TEXT = 'Lote cancelado.'
export const CANCEL_LIST_REFRESH_FAILED = 'Não foi possível atualizar a lista.'

const FAILURE_TEXT: Record<Exclude<CancelLotFailure, 'unauthorized' | 'ambiguous'>, string> = {
  ended: 'Este lote já foi encerrado.',
  integrity:
    'Não foi possível concluir a operação porque a integridade do lote não pôde ser confirmada.',
  forbidden: 'Você não pode cancelar este lote.',
  not_found: 'Lote não encontrado.',
}

export const CANCEL_AMBIGUOUS_TEXT =
  'Não foi possível confirmar o cancelamento. Confira a lista atualizada antes de tentar novamente.'
export const CANCEL_AMBIGUOUS_REFRESH_FAILED_TEXT =
  'Não foi possível confirmar o cancelamento nem atualizar a lista. Recarregue Meus lotes e confira antes de tentar novamente.'

// `unauthorized` não tem texto: quem chama aciona o callback de sessão expirada.
export function cancelFailureNotice(failure: Exclude<CancelLotFailure, 'unauthorized'>): CancelNotice {
  if (failure === 'ambiguous') return { kind: 'uncertain', text: CANCEL_AMBIGUOUS_TEXT }
  return { kind: 'error', text: FAILURE_TEXT[failure] }
}

// Depois de qualquer resposta que não seja a 401, a lista é relida uma vez. Só a recusa
// por papel/dono, a inexistência e o conflito de integridade não mudam a lista; todas as
// demais (sucesso, encerrado, ambíguo) podem ter mudado.
export function shouldRefetch(failure: CancelLotFailure | null): boolean {
  return failure === null || failure === 'ended' || failure === 'ambiguous'
}

export function bidCountText(count: number): string {
  return count === 1 ? '1 lance' : `${count} lances`
}
