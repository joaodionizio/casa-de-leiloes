import type { PublicLotSummary } from './api/publicLots'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import LotState from './LotState'
import { getEndingSoonLabel } from './lotEndingSoon'
import { lotTitleText } from './lotLabels'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'
import { routePath } from './route'

interface FeaturedLotProps {
  lot: PublicLotSummary
  now: number
  onOpen: (lotId: string) => void
}

// Destaque image-led (blueprint §5, D12): a obra primeiro, só o necessário ao lado —
// estado, título, artista, lance, horário e um CTA. O lote em destaque não se
// repete no rail da própria seção. A transição desktop fica restrita à margem da arte.
function FeaturedLot({ lot, now, onOpen }: FeaturedLotProps) {
  const title = lotTitleText(lot.title)
  const endingSoonLabel = lot.phase === 'live' ? getEndingSoonLabel(lot.ends_at, now) : null
  return (
    <section className="featured" aria-labelledby="featured-heading">
      <h2 id="featured-heading" className="visually-hidden">
        Em destaque
      </h2>
      <div className="featured-art">
        <ArtworkImage
          key={lot.image_url}
          src={lot.image_url}
          alt={lot.title ?? 'Obra sem título'}
          variant="large"
        />
      </div>
      <div className="featured-info">
        <p className="featured-kicker">Leilões de Arte</p>
        <LotState phase={lot.phase} />
        {endingSoonLabel !== null && <p className="vitrine-ending-soon">{endingSoonLabel}</p>}
        <h3 className="featured-title" title={title}>
          {lot.title !== null ? title : <span className="untitled">{title}</span>}
        </h3>
        {lot.artist_display !== null && (
          <p className="featured-artist muted">{lot.artist_display}</p>
        )}
        <p className="featured-bid">
          <span className="featured-bid-label">
            {lot.current_bid_cents !== null ? 'Lance atual' : 'Lance inicial'}
          </span>
          <span className="featured-bid-value">
            {formatCents(lot.current_bid_cents ?? lot.starting_bid_cents)}
          </span>
        </p>
        <p className="featured-when">
          {lot.phase === 'live'
            ? `Termina ${formatDateTime(lot.ends_at)}`
            : `Começa ${formatDateTime(lot.starts_at)}`}
        </p>
        <AppLink
          to={routePath({ kind: 'lot', lotId: lot.id })}
          state={{ fromVitrine: true }}
          beforeNavigate={() => onOpen(lot.id)}
          className="button button-primary featured-cta"
          aria-label={`Ver lote: ${title}`}
          data-lot-id={lot.id}
        >
          Ver lote
        </AppLink>
      </div>
    </section>
  )
}

export default FeaturedLot
