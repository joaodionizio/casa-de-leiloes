import type { PublicLotSummary } from './api/publicLots'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import LotState from './LotState'
import { lotLinkLabel, lotTitleText } from './lotLabels'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'
import { routePath } from './route'

interface UpcomingLotItemProps {
  lot: PublicLotSummary
  onOpen: (lotId: string) => void
}

// Próximo lote no rail: menos peso que o ao vivo (blueprint §7 e §9) — descoberta,
// não urgência. Mostra quando começa e, com peso menor, o lance inicial.
function UpcomingLotItem({ lot, onOpen }: UpcomingLotItemProps) {
  const title = lotTitleText(lot.title)
  return (
    <li className="rail-item rail-item-upcoming">
      <AppLink
        to={routePath({ kind: 'lot', lotId: lot.id })}
        state={{ fromVitrine: true }}
        beforeNavigate={() => onOpen(lot.id)}
        className="rail-link"
        aria-label={lotLinkLabel(lot)}
        data-lot-id={lot.id}
      >
        <ArtworkImage key={lot.image_url} src={lot.image_url} alt="" variant="card" />
        <div className="rail-body">
          <LotState phase={lot.phase} />
          <span className="rail-when">Começa {formatDateTime(lot.starts_at)}</span>
          <h3 className="rail-title" title={title}>
            {lot.title !== null ? title : <span className="untitled">{title}</span>}
          </h3>
          {lot.artist_display !== null && (
            <span className="rail-artist muted">{lot.artist_display}</span>
          )}
          <span className="rail-bid rail-bid-light muted">
            Lance inicial {formatCents(lot.starting_bid_cents)}
          </span>
        </div>
      </AppLink>
    </li>
  )
}

export default UpcomingLotItem
