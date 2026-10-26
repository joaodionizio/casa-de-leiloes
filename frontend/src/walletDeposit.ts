// Depósito em andamento da carteira (Story 3.1, P8; F-08 do code review). Vive fora da
// `WalletPage` porque a página remonta a cada navegação (`key={where.id}`): sem isto,
// voltar à carteira com o `POST` pendente traria o botão ativo de novo e permitiria um
// segundo depósito. Há no máximo um depósito por conta, identificada pelo e-mail da
// sessão: o depósito da conta A nunca bloqueia nem alimenta a tela da conta B, mesmo
// depois de sair e entrar com outra conta. Sem DOM, para o `node --test`.

import { depositToWallet, fetchWallet } from './api/wallet.ts'
import type {
  KnownDepositFailure,
  WalletReadResult,
  WalletResponse,
} from './api/wallet.ts'

export type DepositOutcome =
  | { kind: 'confirmed'; wallet: WalletResponse } // saldo da resposta do POST
  | { kind: 'refused'; failure: KnownDepositFailure } // o servidor recusou: nada gravado
  | { kind: 'uncertain'; reread: WalletReadResult } // erro ambíguo + a única releitura

export interface PendingDeposit {
  owner: string
  amountCents: number
  outcome: Promise<DepositOutcome>
}

// O envio e, só em erro ambíguo, uma única releitura. Nunca um segundo POST.
export async function sendDeposit(amountCents: number): Promise<DepositOutcome> {
  const result = await depositToWallet(amountCents)
  if (result.ok) return { kind: 'confirmed', wallet: result.wallet }
  if (result.failure !== 'ambiguous') return { kind: 'refused', failure: result.failure }
  return { kind: 'uncertain', reread: await fetchWallet() }
}

const pendingByOwner = new Map<string, PendingDeposit>()

export function pendingDepositOf(owner: string): PendingDeposit | null {
  return pendingByOwner.get(owner) ?? null
}

// Inicia o depósito, ou devolve `null` se a conta já tem um em andamento: a barreira
// contra duplo envio é síncrona e vale entre montagens da página. A entrada sai do
// registro quando o resultado fica pronto, antes de quem espera por ele recebê-lo.
export function startDeposit(
  owner: string,
  amountCents: number,
  send: (amountCents: number) => Promise<DepositOutcome> = sendDeposit,
): PendingDeposit | null {
  if (pendingByOwner.has(owner)) return null
  const outcome = send(amountCents)
    // Defesa: uma falha inesperada nunca deixa o botão preso nem afirma resultado.
    .catch((): DepositOutcome => ({
      kind: 'uncertain',
      reread: { ok: false, failure: 'server' },
    }))
    .finally(() => {
      if (pendingByOwner.get(owner) === entry) pendingByOwner.delete(owner)
    })
  const entry: PendingDeposit = { owner, amountCents, outcome }
  pendingByOwner.set(owner, entry)
  return entry
}
