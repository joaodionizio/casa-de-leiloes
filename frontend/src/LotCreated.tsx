import { useEffect, useRef } from 'react'
import type { LotResponse } from './api/lots'
import LotArtwork from './LotArtwork'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'

interface LotCreatedProps {
  lot: LotResponse
  onShowMyLots: () => void
  onCreateAnother: () => void
}

// Confirmação: mostra o que o SERVIDOR gravou (a resposta do POST), não o que a
// pessoa digitou. Sem vitrine, sala nem cancelar (2.5, 4.1 e 3.6).
function LotCreated({ lot, onShowMyLots, onCreateAnother }: LotCreatedProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return (
    <section className="lot-step" aria-labelledby="lot-created-title">
      <h2 id="lot-created-title" ref={headingRef} tabIndex={-1} className="lot-step-title">
        <span aria-hidden="true">✓ </span>Lote criado
      </h2>
      <div className="lot-layout">
        <div className="lot-layout-artwork">
          <LotArtwork artwork={lot} size="compact" />
        </div>
        <div>
          <dl className="lot-terms">
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
            <div>
              <dt>Término</dt>
              <dd>{formatDateTime(lot.ends_at)}</dd>
            </div>
            <div>
              <dt>Criado em</dt>
              <dd>{formatDateTime(lot.created_at)}</dd>
            </div>
          </dl>
          <div className="lot-actions">
            <button type="button" className="button button-primary" onClick={onShowMyLots}>
              Ver meus lotes
            </button>
            <button type="button" className="button button-secondary" onClick={onCreateAnother}>
              Criar outro lote
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

export default LotCreated
