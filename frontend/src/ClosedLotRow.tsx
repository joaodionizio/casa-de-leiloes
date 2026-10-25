import type { PublicLotSummary } from './api/publicLots'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import LotState from './LotState'
import { lotLinkLabel, lotTitleText } from './lotLabels'
import { formatDateTime } from './lotTime'
import { routePath } from './route'

interface ClosedLotRowProps {
  lot: PublicLotSummary
  onOpen: (lotId: string) => void
}

// Encerrado na lista densa (blueprint §8): miniatura, título e artista, estado e
// quando terminou. Sem valor: não existe resultado ainda, e o lance inicial pareceria
// preço final. Um único link por linha.
function ClosedLotRow({ lot, onOpen }: ClosedLotRowProps) {
  const title = lotTitleText(lot.title)
  return (
    <li className="closed-row">
      <AppLink
        to={routePath({ kind: 'lot', lotId: lot.id })}
        state={{ fromVitrine: true }}
        beforeNavigate={() => onOpen(lot.id)}
        className="closed-link"
        aria-label={lotLinkLabel(lot)}
        data-lot-id={lot.id}
      >
        <ArtworkImage key={lot.image_url} src={lot.image_url} alt="" variant="thumb" />
        <div className="closed-text">
          <h3 className="closed-title" title={title}>
            {lot.title !== null ? title : <span className="untitled">{title}</span>}
          </h3>
          {lot.artist_display !== null && (
            <span className="closed-artist muted">{lot.artist_display}</span>
          )}
        </div>
        <div className="closed-status">
          <LotState phase={lot.phase} />
          <span className="muted">Terminou {formatDateTime(lot.ends_at)}</span>
        </div>
      </AppLink>
    </li>
  )
}

export default ClosedLotRow
