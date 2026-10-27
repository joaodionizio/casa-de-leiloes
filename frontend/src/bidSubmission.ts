// Lance em andamento (Story 3.5, espelho de `walletDeposit.ts`). Vive fora da página
// porque ela remonta ao navegar: sem isto, voltar à sala com o `POST` pendente traria o
// botão ativo e permitiria um segundo lance. Há no máximo um lance por conta e lote; a
// conta é identificada pelo e-mail da sessão (chave interna, nunca enviada). Nunca há
// retry: o `POST` não é idempotente. Sem DOM, para o `node --test`.

import { placeBid } from './api/bids.ts'
import type { BidResult } from './api/bids.ts'

export interface PendingBid {
  owner: string
  lotId: string
  amountCents: number
  amountText: string
  outcome: Promise<BidResult>
}

const pending = new Map<string, PendingBid>()

function keyOf(owner: string, lotId: string): string {
  return `${owner}\n${lotId}`
}

export function pendingBidOf(owner: string, lotId: string): PendingBid | null {
  return pending.get(keyOf(owner, lotId)) ?? null
}

// Inicia o lance, ou devolve `null` se esta conta já tem um pendente neste lote: a
// barreira é síncrona (antes de qualquer `await`) e vale entre montagens. A entrada sai
// do registro quando o resultado fica pronto.
export function startBid(
  owner: string,
  lotId: string,
  amountCents: number,
  amountText: string,
  send: (lotId: string, amountCents: number) => Promise<BidResult> = placeBid,
): PendingBid | null {
  const key = keyOf(owner, lotId)
  if (pending.has(key)) return null
  const outcome = send(lotId, amountCents)
    // Defesa: uma falha inesperada nunca deixa o botão preso nem afirma resultado.
    .catch((): BidResult => ({ ok: false, failure: 'ambiguous' }))
    .finally(() => {
      if (pending.get(key) === entry) pending.delete(key)
    })
  const entry: PendingBid = { owner, lotId, amountCents, amountText, outcome }
  pending.set(key, entry)
  return entry
}
