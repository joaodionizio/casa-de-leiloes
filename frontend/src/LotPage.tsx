import { useEffect, useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import {
  fetchPublicLot,
  type PublicLotDetailResponse,
} from './api/publicLots'
import { asOfText } from './asOf'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import { documentTitle } from './brand'
import LotState from './LotState'
import { lotTitleText } from './lotLabels'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'
import { navigate } from './navigation'
import { shouldHandleClick, type NavState } from './route'

type LotPageState =
  | { status: 'loading' }
  | { status: 'not_found' }
  | { status: 'failed' }
  | { status: 'ready'; data: PublicLotDetailResponse; today: Date }

interface LotPageProps {
  lotId: string
  navState: NavState
  navigated: boolean
}

// Página pública de um lote (CAP-11): a obra e os termos do leilão, sem antecipar a
// sala. Não há "Dar lance", campo de valor, carteira, histórico nem contagem
// regressiva — nem desabilitados. O estado do lote e o `as_of` vêm do servidor.
function LotPage({ lotId, navState, navigated }: LotPageProps) {
  const [state, setState] = useState<LotPageState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const wasNavigatedRef = useRef(navigated)

  useEffect(() => {
    const controller = new AbortController()
    fetchPublicLot(lotId, controller.signal).then((result) => {
      if (controller.signal.aborted) return
      if (result.ok) {
        setState({ status: 'ready', data: result.data, today: new Date() })
      } else {
        setState({ status: result.failure === 'not_found' ? 'not_found' : 'failed' })
      }
    })
    return () => controller.abort()
  }, [lotId, attempt])

  // Foco no `h1` ao navegar (D11). O `h1` existe em todos os estados, mas o layout
  // muda quando o lote carrega e o elemento é recriado: se o foco se perdeu (voltou
  // ao `body`), ele retorna ao `h1`; se a pessoa já foi para outro controle, fica.
  useEffect(() => {
    if (!wasNavigatedRef.current) return
    const active = document.activeElement
    if (active === null || active === document.body || active === headingRef.current) {
      headingRef.current?.focus()
    }
  }, [state.status])

  const readyTitle =
    state.status === 'ready' ? lotTitleText(state.data.lot.title) : null
  useEffect(() => {
    document.title = documentTitle(readyTitle ?? 'Lote')
  }, [readyTitle])

  function retry() {
    setState({ status: 'loading' })
    setAttempt((count) => count + 1)
  }

  // "← Vitrine": quem veio da vitrine volta com o Back do navegador (foco no lote);
  // quem abriu o link direto vai à vitrine.
  function handleBack(event: MouseEvent<HTMLAnchorElement>) {
    if (
      !shouldHandleClick({
        button: event.button,
        metaKey: event.metaKey,
        ctrlKey: event.ctrlKey,
        shiftKey: event.shiftKey,
        altKey: event.altKey,
        defaultPrevented: event.defaultPrevented,
        target: event.currentTarget.getAttribute('target'),
      })
    ) {
      return
    }
    event.preventDefault()
    if (navState.fromVitrine === true) window.history.back()
    else navigate('/')
  }

  if (state.status === 'loading') {
    return (
      <section className="notice-page" aria-labelledby="lot-title">
        <h1 id="lot-title" ref={headingRef} tabIndex={-1}>
          Carregando lote…
        </h1>
        <p role="status" className="muted">
          Buscando os dados do lote.
        </p>
        <div className="lot-page-reserve" aria-hidden="true" />
      </section>
    )
  }

  if (state.status === 'not_found') {
    return (
      <section className="notice-page" aria-labelledby="lot-title">
        <h1 id="lot-title" ref={headingRef} tabIndex={-1}>
          Lote não encontrado
        </h1>
        <p>O lote pode ter sido removido ou o endereço está incompleto.</p>
        <AppLink to="/" className="button button-secondary">
          Ir para a vitrine
        </AppLink>
      </section>
    )
  }

  if (state.status === 'failed') {
    return (
      <section className="notice-page" aria-labelledby="lot-title">
        <h1 id="lot-title" ref={headingRef} tabIndex={-1}>
          Não foi possível carregar o lote
        </h1>
        <p role="alert" className="form-error">
          O servidor não respondeu como esperado. Tente novamente em instantes.
        </p>
        <div className="notice-actions">
          <button type="button" className="button button-secondary" onClick={retry}>
            Tentar novamente
          </button>
          <AppLink to="/" className="button button-secondary">
            Ir para a vitrine
          </AppLink>
        </div>
      </section>
    )
  }

  const { lot, as_of: asOf } = state.data
  const title = lotTitleText(lot.title)
  const asOfLine = asOfText(asOf, state.today)
  const when =
    lot.phase === 'live'
      ? `Termina ${formatDateTime(lot.ends_at)}`
      : lot.phase === 'scheduled'
        ? `Começa ${formatDateTime(lot.starts_at)}`
        : `Terminou ${formatDateTime(lot.ends_at)}`
  const facts: Array<[string, string | null]> = [
    ['Técnica', lot.medium_display],
    ['Dimensões', lot.dimensions],
    ['Departamento', lot.department_title],
    ['Tipo', lot.artwork_type_title],
    ['Crédito', lot.credit_line],
    ['Nº no acervo', String(lot.external_id)],
  ]

  return (
    <article className="lot-page" aria-labelledby="lot-title">
      <p className="lot-page-back">
        <a href="/" className="back-link" onClick={handleBack}>
          <span aria-hidden="true">← </span>Vitrine
        </a>
      </p>
      <div className="lot-page-grid">
        <div className="lot-page-art">
          <ArtworkImage
            key={lot.image_url}
            src={lot.image_url}
            alt={lot.title ?? 'Obra sem título'}
            variant="large"
          />
        </div>
        <div className="lot-page-info">
          <LotState phase={lot.phase} />
          <p className="lot-page-when">{when}</p>
          <h1 id="lot-title" ref={headingRef} tabIndex={-1} className="lot-page-title">
            {lot.title !== null ? title : <span className="untitled">{title}</span>}
          </h1>
          {lot.artist_display !== null && (
            <p className="lot-page-artist muted">{lot.artist_display}</p>
          )}
          {lot.date_display !== null && (
            <p className="lot-page-date muted">{lot.date_display}</p>
          )}

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
              <div>
                <dt>Término</dt>
                <dd>{formatDateTime(lot.ends_at)}</dd>
              </div>
            </dl>
            {asOfLine !== null && <p className="as-of muted">{asOfLine}</p>}
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
      </div>
    </article>
  )
}

export default LotPage
