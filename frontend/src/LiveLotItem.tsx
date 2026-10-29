import type { PublicLotSummary } from './api/publicLots'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import LotState from './LotState'
import { getEndingSoonLabel } from './lotEndingSoon'
import { lotLinkLabel, lotTitleText } from './lotLabels'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'
import { routePath } from './route'

interface LiveLotItemProps {
  lot: PublicLotSummary
  now: number
  onOpen: (lotId: string) => void
}

// Lote ao vivo no rail: a maior densidade (blueprint §9) — obra, estado, título,
// artista, lance e quando termina. Um único link; sem caixa nem sombra.
function LiveLotItem({ lot, now, onOpen }: LiveLotItemProps) {
  const title = lotTitleText(lot.title)
  const endingSoonLabel = lot.phase === 'live' ? getEndingSoonLabel(lot.ends_at, now) : null
  const linkLabel = lotLinkLabel(lot)
  return (
    <li className="rail-item rail-item-live">
      <AppLink
        to={routePath({ kind: 'lot', lotId: lot.id })}
        state={{ fromVitrine: true }}
        beforeNavigate={() => onOpen(lot.id)}
        className="rail-link"
        aria-label={endingSoonLabel === null ? linkLabel : `${linkLabel} ${endingSoonLabel}.`}
        data-lot-id={lot.id}
      >
        <ArtworkImage key={lot.image_url} src={lot.image_url} alt="" variant="card" />
        <div className="rail-body">
          <LotState phase={lot.phase} />
          {endingSoonLabel !== null && <p className="vitrine-ending-soon">{endingSoonLabel}</p>}
          <h3 className="rail-title" title={title}>
            {lot.title !== null ? title : <span className="untitled">{title}</span>}
          </h3>
          {lot.artist_display !== null && (
            <span className="rail-artist muted">{lot.artist_display}</span>
          )}
          <span className="rail-bid">
            <span className="rail-label">
              {lot.current_bid_cents !== null ? 'Lance atual' : 'Lance inicial'}
            </span>
            <span className="rail-value">
              {formatCents(lot.current_bid_cents ?? lot.starting_bid_cents)}
            </span>
          </span>
          <span className="rail-when muted">
            Termina {formatDateTime(lot.ends_at)}
          </span>
        </div>
      </AppLink>
    </li>
  )
}

export default LiveLotItem
