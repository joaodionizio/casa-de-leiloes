import type { PublicLotDetail } from './api/publicLots'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'

interface LotArtworkDetailsProps {
  lot: PublicLotDetail
  endsAt: string | null
}

// Static auction terms and artwork provenance; no network requests or business rules.
export default function LotArtworkDetails({ lot, endsAt }: LotArtworkDetailsProps) {
  const facts: Array<[string, string | null]> = [
    ['Técnica', lot.medium_display],
    ['Dimensões', lot.dimensions],
    ['Departamento', lot.department_title],
    ['Tipo', lot.artwork_type_title],
    ['Crédito', lot.credit_line],
    ['Nº no acervo', String(lot.external_id)],
  ]

  return (
      <div className="lot-page-details">
        <section aria-labelledby="lot-terms-title" className="lot-page-block">
          <h2 id="lot-terms-title">Leilão</h2>
          <dl className="lot-facts">
            <div>
              <dt>Lance inicial</dt>
              <dd className="lot-money">{formatCents(lot.starting_bid_cents)}</dd>
            </div>
            <div>
              <dt>Incremento mínimo</dt>
              <dd className="lot-money">{formatCents(lot.min_increment_cents)}</dd>
            </div>
            <div>
              <dt>Início</dt>
              <dd>{formatDateTime(lot.starts_at)}</dd>
            </div>
            {endsAt !== null && (
              <div>
                <dt>Término</dt>
                <dd>{formatDateTime(endsAt)}</dd>
              </div>
            )}
          </dl>
        </section>

        <section aria-labelledby="lot-work-title" className="lot-page-block">
          <h2 id="lot-work-title">Ficha da obra</h2>
          <dl className="lot-facts">
            {facts.map(([label, value]) =>
              value === null ? null : (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ),
            )}
          </dl>
          {lot.source_url.startsWith('https://') && (
            <a
              className="source-link"
              href={lot.source_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Ver a obra no site do Art Institute of Chicago
              <span className="visually-hidden"> (abre em nova aba)</span>
              <span aria-hidden="true"> ↗</span>
            </a>
          )}
        </section>
      </div>
  )
}
