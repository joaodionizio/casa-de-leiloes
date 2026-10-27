// Textos e decisão pós-depósito da carteira (Story 3.1, P8). Puro e sem DOM, para o
// `node --test`. As mensagens nascem do tipo da falha, nunca do `message` do servidor.
// Nenhum texto daqui afirma que o depósito entrou sem confirmação do servidor.

import type {
  DepositFailure,
  KnownDepositFailure,
  WalletReadResult,
} from './api/wallet.ts'
import { formatCents } from './money.ts'

export type WalletNotice =
  | { kind: 'success'; text: string }
  | { kind: 'error'; text: string } // erro conhecido; o saldo mostrado não muda
  | { kind: 'uncertain'; text: string } // erro ambíguo

export function depositSuccessText(amountCents: number): string {
  return `Depósito de ${formatCents(amountCents)} confirmado.`
}

// Texto de uma recusa conhecida. O erro ambíguo não passa por aqui: ele leva à única
// releitura (`walletDeposit.ts`) e ao texto de `rereadNotice`. `balance_limit` e
// `validation` aparecem no campo; os demais, no formulário. Ambos usam o mesmo
// `error`; quem renderiza decide o lugar pela falha.
export function depositFailureNotice(failure: KnownDepositFailure): WalletNotice {
  if (failure === 'validation') {
    return { kind: 'error', text: 'Informe um valor válido em reais.' }
  }
  if (failure === 'balance_limit') {
    return {
      kind: 'error',
      text: 'O depósito ultrapassaria o limite de saldo da carteira.',
    }
  }
  if (failure === 'forbidden') {
    return { kind: 'error', text: 'Esta área é só para a conta de licitante.' }
  }
  if (failure === 'unauthorized') {
    // Não vira texto: a tela chama `onSessionExpired()`. Texto defensivo, caso alguém
    // o mostre por engano.
    return { kind: 'error', text: 'Sua sessão expirou. Entre novamente.' }
  }
  return {
    kind: 'error',
    text: 'Não foi possível concluir o depósito. Recarregue a página e tente novamente.',
  }
}

// Depois de um erro ambíguo a tela faz UMA releitura. Se ela funcionar, mostra o
// saldo real do servidor sem dizer se o depósito entrou; se falhar, não afirma nada.
export function rereadNotice(reread: WalletReadResult): WalletNotice {
  if (reread.ok) {
    return {
      kind: 'uncertain',
      text:
        'Não foi possível confirmar o depósito. O saldo abaixo é o atual do servidor; ' +
        'confira antes de tentar de novo.',
    }
  }
  return {
    kind: 'uncertain',
    text:
      'Não foi possível confirmar se o depósito foi feito. Recarregue a página e ' +
      'confira o saldo antes de tentar de novo.',
  }
}

// Onde o erro conhecido aparece: no campo (valor) ou no formulário (o resto).
export function failureBelongsToField(failure: DepositFailure): boolean {
  return failure === 'validation' || failure === 'balance_limit'
}
