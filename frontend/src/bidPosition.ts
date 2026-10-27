// Posição do licitante na sala (Story 3.5). Derivada dos dois read models, nunca de um
// campo `is_leading`. Puro e sem DOM, para o `node --test`.

import type { BidRoom, MyBids } from './api/bids.ts'

export type BidPosition = 'winning' | 'outbid' | 'neutral' | 'hidden'

// `hidden`: sem dado válido dos dois lados, lote encerrado ou atualização pendente.
// A contagem completa (`my_bid_count`) decide a participação; `last_bid_cents` sozinho
// nunca, e o lance próprio pode estar fora dos 50 exibidos.
export function bidPosition(
  room: BidRoom | null,
  mine: MyBids | null,
  updating: boolean,
  paired: boolean,
): BidPosition {
  // `paired`: a participação veio da mesma rodada de leitura que a sala. Sala nova com
  // participação antiga não é um snapshot válido.
  if (room === null || mine === null || updating || !paired) return 'hidden'
  if (room.phase === 'ended') return 'hidden'
  if (mine.my_bid_count === 0) return 'neutral'
  const leader = room.current_bid_cents !== null ? room.bids[0]?.bidder_alias : undefined
  if (leader !== undefined && leader === mine.bidder_alias) return 'winning'
  return 'outbid'
}

// Último lance próprio de um lote encerrado, vindo da participação completa (o lance pode
// estar fora dos 50 exibidos). Não afirma resultado: vencedor e liquidação são de outra story.
export function endedLastBid(
  room: BidRoom | null,
  mine: MyBids | null,
  paired: boolean,
): number | null {
  if (room === null || mine === null || !paired) return null
  if (room.phase !== 'ended' || mine.my_bid_count === 0) return null
  return mine.last_bid_cents
}
