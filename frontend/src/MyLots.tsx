import { useEffect, useRef, useState } from 'react'
import ArtworkImage from './ArtworkImage'
import { fetchMyLots } from './api/lots'
import type { LotResponse, MyLotsFailure } from './api/lots'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'

type ListState =
  | { status: 'loading' }
  | { status: 'ready'; items: LotResponse[] }
  | { status: 'failed'; failure: MyLotsFailure }

interface MyLotsProps {
  onSessionExpired: () => void
  onCreateLot: () => void
}

function failureText(failure: MyLotsFailure): string {
  if (failure === 'forbidden') return 'Sua conta não tem acesso a esta lista.'
  return 'Não foi possível carregar seus lotes.'
}

// Lista mínima dos lotes do leiloeiro (P9): só leitura, sem estado do lote (a fase
// depende da Q8, na 2.5), sem ações, sem filtro e sem paginação (A2: todos). Monta a
// cada abertura, então sempre relê o servidor.
function MyLots({ onSessionExpired, onCreateLot }: MyLotsProps) {
  const [state, setState] = useState<ListState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const headingRef = useRef<HTMLHeadingElement>(null)
  // O pai recria `onSessionExpired` a cada renderização; a referência evita que isso
  // dispare uma nova busca.
  const expiredRef = useRef(onSessionExpired)

  useEffect(() => {
    expiredRef.current = onSessionExpired
  }, [onSessionExpired])

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchMyLots(controller.signal).then((result) => {
      if (controller.signal.aborted) return
      if (result.ok) {
        setState({ status: 'ready', items: result.items })
      } else if (result.failure === 'unauthorized') {
        expiredRef.current()
      } else {
        setState({ status: 'failed', failure: result.failure })
      }
    })
    return () => controller.abort()
  }, [attempt])

  function retry() {
    setState({ status: 'loading' })
    setAttempt((count) => count + 1)
  }

  return (
    <section className="my-lots" aria-labelledby="my-lots-title">
      <h1 id="my-lots-title" ref={headingRef} tabIndex={-1}>
        Meus lotes
      </h1>

      {state.status === 'loading' && (
        <p role="status" className="muted">
          Carregando seus lotes…
        </p>
      )}

      {state.status === 'failed' && (
        <div className="catalog-failure">
          <p role="alert" className="form-error">
            {failureText(state.failure)}
          </p>
          {state.failure !== 'forbidden' && (
            <button type="button" className="button button-secondary" onClick={retry}>
              Tentar novamente
            </button>
          )}
        </div>
      )}

      {state.status === 'ready' && state.items.length === 0 && (
        <div>
          <p role="status" className="empty-title">
            Você ainda não criou lotes.
          </p>
          <button type="button" className="button button-primary" onClick={onCreateLot}>
            Criar lote
          </button>
        </div>
      )}

      {state.status === 'ready' && state.items.length > 0 && (
        <>
          <p className="muted my-lots-count">
            {state.items.length} {state.items.length === 1 ? 'lote' : 'lotes'}
          </p>
          <ul className="lot-list">
            {state.items.map((lot) => (
              <li key={lot.id} className="lot-row">
                <ArtworkImage key={lot.image_url} src={lot.image_url} alt="" variant="thumb" />
                <div className="lot-row-text">
                  {lot.title !== null ? (
                    <span className="lot-row-title" title={lot.title}>
                      {lot.title}
                    </span>
                  ) : (
                    <span className="lot-row-title untitled">Sem título</span>
                  )}
                  {lot.artist_display !== null && (
                    <span className="lot-row-artist muted">{lot.artist_display}</span>
                  )}
                </div>
                <dl className="lot-row-facts">
                  <div>
                    <dt>Início</dt>
                    <dd>{formatDateTime(lot.starts_at)}</dd>
                  </div>
                  <div>
                    <dt>Término</dt>
                    <dd>{formatDateTime(lot.ends_at)}</dd>
                  </div>
                  <div>
                    <dt>Lance inicial</dt>
                    <dd className="lot-money-small">{formatCents(lot.starting_bid_cents)}</dd>
                  </div>
                  <div>
                    <dt>Incremento</dt>
                    <dd className="lot-money-small">{formatCents(lot.min_increment_cents)}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

export default MyLots
