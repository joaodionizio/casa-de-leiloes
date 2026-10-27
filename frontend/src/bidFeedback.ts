// Textos da sala do lote (Story 3.5). Puro e sem DOM, para o `node --test`. Os textos
// nascem do tipo da falha (status + `code` já classificados em `api/bids.ts`), nunca do
// `message` do servidor. Nenhum texto de erro ambíguo afirma que o lance entrou.

import type { KnownBidFailure } from './api/bids.ts'
import { formatCents } from './money.ts'

export type BidNoticeKind = 'success' | 'error' | 'uncertain'

export interface BidNotice {
  kind: BidNoticeKind
  text: string
  // Só a recusa por saldo oferece o caminho para a carteira.
  walletLink: boolean
}

const REFUSAL_TEXT: Record<KnownBidFailure, string> = {
  below_minimum:
    'Seu lance está abaixo do mínimo para este lote. Confira o valor mínimo acima.',
  insufficient_balance: 'Saldo disponível insuficiente para este lance.',
  already_winning: 'Você já está ganhando este lote.',
  lot_not_started: 'Este lote ainda não começou.',
  lot_ended: 'Este lote já foi encerrado.',
  integrity:
    'Não foi possível verificar a integridade deste lote. O lance não foi registrado.',
  validation: 'Informe um valor válido em reais.',
  forbidden: 'Esta área é só para a conta de licitante.',
  unauthorized: 'Sua sessão expirou. Entre novamente.',
  not_found: 'Lote não encontrado.',
  rejected: 'Não foi possível enviar o lance. Recarregue a página e tente novamente.',
}

export function refusalNotice(failure: KnownBidFailure): BidNotice {
  return {
    kind: 'error',
    text: REFUSAL_TEXT[failure],
    walletLink: failure === 'insufficient_balance',
  }
}

// A recusa de validação vai para o campo; as demais, para o aviso do formulário.
export function failureBelongsToField(failure: KnownBidFailure): boolean {
  return failure === 'validation'
}

export function successText(amountCents: number, antiSniping: boolean): string {
  const base = `Lance de ${formatCents(amountCents)} registrado.`
  return antiSniping ? `${base} Prazo prorrogado em 2 minutos.` : base
}

export type SyncOutcome = 'complete' | 'partial'

// Erro ambíguo: nunca diz se o lance entrou. Com a releitura completa, só aponta o
// estado atual do servidor.
export function ambiguousNotice(sync: SyncOutcome | 'pending'): BidNotice {
  const text =
    sync === 'complete'
      ? 'Não foi possível confirmar o lance. O estado abaixo é o atual do servidor; confira antes de tentar de novo.'
      : 'Não foi possível confirmar o lance nem atualizar todos os dados da sala. Use Atualizar sala e confira antes de tentar de novo.'
  return { kind: 'uncertain', text, walletLink: false }
}

export const ACCEPTED_SYNC_FAILED_TEXT =
  'Lance aceito, mas não foi possível atualizar a sala.'
