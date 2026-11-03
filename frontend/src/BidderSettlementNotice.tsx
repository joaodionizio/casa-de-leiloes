import type { BidRoom } from './api/bids'
import AppLink from './AppLink'
import { classifyBidderSettlement } from './bidderSettlement'
import { formatCents } from './money'

interface BidderSettlementNoticeProps {
  lotId: string
  room: BidRoom
  ownAlias: string | null
  ownBidCount: number | null
  participationVerified: boolean
  participationUnavailable: boolean
}

// The public result is never used to infer a private win without a verified alias.
export default function BidderSettlementNotice(props: BidderSettlementNoticeProps) {
  const outcome = classifyBidderSettlement(
    props.room,
    props.ownAlias,
    props.ownBidCount,
    props.participationVerified,
  )
  if (outcome === null) return null

  return (
    <section
      className={`bid-settlement-notice bid-settlement-${outcome}`}
      aria-label="Resultado do leilão"
      role="status"
    >
      {outcome === 'won' && (
        <>
          <h3>Você arrematou esta obra!</h3>
          {props.room.settlement?.final_amount_cents != null && (
            <p>Valor final: <strong>{formatCents(props.room.settlement.final_amount_cents)}</strong></p>
          )}
          <AppLink to={`/lots/${props.lotId}/receipt`}>Acessar seu comprovante</AppLink>
        </>
      )}
      {outcome === 'lost' && (
        <>
          <h3>Você não arrematou esta obra.</h3>
          <p>Outro licitante venceu a disputa.</p>
        </>
      )}
      {outcome === 'not_participated' && (
        <>
          <h3>Este lote foi arrematado.</h3>
          <p>Você não deu lances neste lote.</p>
        </>
      )}
      {outcome === 'unsold' && <h3>O leilão terminou sem arremate.</h3>}
      {outcome === 'unverified' && (
        <>
          <h3>O leilão foi encerrado.</h3>
          <p>
            {props.participationUnavailable
              ? 'Não foi possível confirmar sua participação. Use Atualizar sala para conferir o resultado.'
              : 'Confirmando o resultado da sua participação…'}
          </p>
        </>
      )}
    </section>
  )
}
