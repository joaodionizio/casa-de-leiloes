import type { BidItem } from './api/bids'
import { formatCents } from './money'
import { formatClock } from './lotTime'

interface BidHistoryProps {
  bids: BidItem[]
  bidCount: number
  myAlias: string | null
  updating: boolean
  outdated: boolean
}

// Histórico da sala (Story 3.5): só pseudônimos, mais recente primeiro, no máximo 50
// linhas. A auditoria completa é da 5.1; nenhum link falso para ela.
function BidHistory({ bids, bidCount, myAlias, updating, outdated }: BidHistoryProps) {
  const summary =
    bidCount > bids.length
      ? `${bids.length} mais recentes de ${bidCount}`
      : `${bidCount} ${bidCount === 1 ? 'lance' : 'lances'}`
  return (
    <section className="bid-history" aria-labelledby="bid-history-title">
      <h2 id="bid-history-title">Histórico de lances</h2>
      {bidCount > 0 && <p className="muted bid-history-count">{summary}</p>}
      {updating && <p className="muted">Atualizando histórico…</p>}
      {outdated && (
        <p className="bid-history-outdated">Histórico possivelmente desatualizado.</p>
      )}
      {bids.length === 0 ? (
        <p className="muted">Nenhum lance ainda.</p>
      ) : (
        <ol className="bid-history-list">
          {bids.map((bid) => (
            <li key={bid.sequence}>
              <span className="bid-seq">#{bid.sequence}</span>
              <span className="bid-alias">
                {bid.bidder_alias}
                {bid.bidder_alias === myAlias && <strong> (Você)</strong>}
              </span>
              <span className="bid-amount">{formatCents(bid.amount_cents)}</span>
              <time className="bid-time muted" dateTime={bid.placed_at}>
                {formatClock(bid.placed_at)}
              </time>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export default BidHistory
