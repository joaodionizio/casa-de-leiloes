import { useEffect, useRef, useState } from 'react'
import ArtworkImage from './ArtworkImage'
import { cancelLot, fetchMyLots } from './api/lots'
import type { CancelLotFailure, MyLotResponse, MyLotsFailure } from './api/lots'
import {
  bidCountText,
  canCancelLot,
  cancelFailureNotice,
  CANCEL_AMBIGUOUS_REFRESH_FAILED_TEXT,
  CANCEL_CONFIRM_TEXT,
  CANCEL_LIST_REFRESH_FAILED,
  CANCEL_SUCCESS_TEXT,
  shouldRefetch,
} from './lotCancellation'
import type { CancelNotice } from './lotCancellation'
import { lotTitleText } from './lotLabels'
import { phaseStatusText } from './lotPhase'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'

type ListState =
  | { status: 'loading' }
  | { status: 'ready'; items: MyLotResponse[]; asOf: string; totalReceivedCents: number }
  | { status: 'failed'; failure: MyLotsFailure }

// 'stale': a leitura foi substituída ou a tela desmontou; o resultado foi descartado.
type ReadOutcome = 'ok' | 'failed' | 'unauthorized' | 'stale'

interface MyLotsProps {
  onSessionExpired: () => void
  onCreateLot: () => void
}

function failureText(failure: MyLotsFailure): string {
  if (failure === 'forbidden') return 'Sua conta não tem acesso a esta lista.'
  return 'Não foi possível carregar seus lotes.'
}

// Lista dos lotes do leiloeiro (Story 2.4, P9; Story 3.6). Sem filtro e sem paginação
// (A2: todos). Monta a cada abertura, então sempre relê o servidor. O estado de cada
// lote vem pronto do servidor (`phase`, `cancelled_at`); "Cancelar lote" é só
// elegibilidade visual, e o servidor decide.
function MyLots({ onSessionExpired, onCreateLot }: MyLotsProps) {
  const [state, setState] = useState<ListState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [notice, setNotice] = useState<CancelNotice | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [stale, setStale] = useState(false)
  const headingRef = useRef<HTMLHeadingElement>(null)
  // O pai recria `onSessionExpired` a cada renderização; a referência evita que isso
  // dispare uma nova busca.
  const expiredRef = useRef(onSessionExpired)
  const mountedRef = useRef(true)
  // Só a leitura mais recente vale: um snapshot antigo nunca apaga um cancelamento.
  const readSeqRef = useRef(0)
  const readControllerRef = useRef<AbortController | null>(null)
  const readPromiseRef = useRef<Promise<ReadOutcome> | null>(null)
  const hasSnapshotRef = useRef(false)
  const blockedRef = useRef(false)
  // Marcado de forma síncrona, antes do primeiro `await`: clique e Enter repetidos não
  // iniciam um segundo POST.
  const submittingRef = useRef(false)
  const ctaRefs = useRef(new Map<string, HTMLButtonElement>())
  const pendingFocusRef = useRef<string | null>(null)

  useEffect(() => {
    expiredRef.current = onSessionExpired
  }, [onSessionExpired])

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  // Devolve o foco ao "Cancelar lote" da linha depois de "Voltar".
  useEffect(() => {
    const id = pendingFocusRef.current
    if (id === null) return
    pendingFocusRef.current = null
    ctaRefs.current.get(id)?.focus()
  })

  function invalidateReads() {
    readSeqRef.current += 1
    readControllerRef.current?.abort()
    readControllerRef.current = null
    readPromiseRef.current = null
  }

  function readList(mode: 'initial' | 'refresh', afterCancellation = false): Promise<ReadOutcome> {
    if (blockedRef.current || (submittingRef.current && !afterCancellation)) return Promise.resolve('stale')
    if (readPromiseRef.current !== null) return readPromiseRef.current
    const controller = new AbortController()
    readControllerRef.current = controller
    const seq = readSeqRef.current
    const pending = fetchMyLots(controller.signal).then((result): ReadOutcome => {
      if (controller.signal.aborted || seq !== readSeqRef.current || !mountedRef.current) {
        return 'stale'
      }
      if (result.ok) {
        hasSnapshotRef.current = true
        setState({ status: 'ready', items: result.items, asOf: result.asOf, totalReceivedCents: result.totalReceivedCents })
        setStale(false)
        return 'ok'
      }
      if (result.failure === 'unauthorized') {
        blockedRef.current = true
        hasSnapshotRef.current = false
        setState({ status: 'failed', failure: 'unauthorized' })
        expiredRef.current()
        return 'unauthorized'
      }
      // Na releitura a lista anterior continua na tela; só a carga inicial falha inteira.
      if (result.failure === 'forbidden') {
        blockedRef.current = true
        hasSnapshotRef.current = false
        setState({ status: 'failed', failure: 'forbidden' })
      } else if (mode === 'initial') setState({ status: 'failed', failure: result.failure })
      else setStale(true)
      return 'failed'
    }).finally(() => {
      if (seq === readSeqRef.current && mountedRef.current) {
        readPromiseRef.current = null
        readControllerRef.current = null
        setRefreshing(false)
      }
    })
    readPromiseRef.current = pending
    return pending
  }

  function refreshList() {
    if (blockedRef.current || submittingRef.current || readPromiseRef.current !== null) return
    setRefreshing(true)
    void readList(hasSnapshotRef.current ? 'refresh' : 'initial')
  }

  useEffect(() => {
    mountedRef.current = true
    void readList('initial')
    // Blur/hidden delimitam uma retomada; visible e focus da mesma retomada leem uma vez.
    let resumed = false
    const refreshOnReturn = () => {
      if (document.visibilityState === 'hidden' || resumed) return
      resumed = true
      refreshList()
    }
    const resetReturn = () => { resumed = false }
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') resetReturn()
      else refreshOnReturn()
    }
    window.addEventListener('focus', refreshOnReturn)
    window.addEventListener('blur', resetReturn)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      mountedRef.current = false
      invalidateReads()
      window.removeEventListener('focus', refreshOnReturn)
      window.removeEventListener('blur', resetReturn)
      document.removeEventListener('visibilitychange', onVisibility)
    }
    // `readList` só usa refs e setters estáveis; a carga reinicia apenas no `attempt`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt])

  function retry() {
    setState({ status: 'loading' })
    setAttempt((count) => count + 1)
  }

  function openConfirmation(lotId: string) {
    if (submittingRef.current) return
    setNotice(null)
    setConfirmingId(lotId)
  }

  function closeConfirmation(lotId: string) {
    if (submittingRef.current) return
    pendingFocusRef.current = lotId
    setConfirmingId(null)
  }

  async function confirmCancellation(lotId: string) {
    if (submittingRef.current) return
    submittingRef.current = true
    setSubmitting(true)
    setNotice(null)
    // Uma leitura em andamento mostraria o estado de antes do POST.
    invalidateReads()
    setRefreshing(false)
    try {
      const result = await cancelLot(lotId)
      if (!mountedRef.current) return
      let failure: Exclude<CancelLotFailure, 'unauthorized'> | null = null
      if (!result.ok) {
        if (result.failure === 'unauthorized') {
          blockedRef.current = true
          hasSnapshotRef.current = false
          setState({ status: 'failed', failure: 'unauthorized' })
          expiredRef.current()
          return
        }
        failure = result.failure
      }
      setConfirmingId(null)
      setNotice(
        failure === null
          ? { kind: 'success', text: CANCEL_SUCCESS_TEXT }
          : cancelFailureNotice(failure),
      )
      if (shouldRefetch(failure)) {
        setRefreshing(true)
        const outcome = await readList('refresh', true)
        if (outcome === 'failed') {
          // O resultado do POST não é invertido pela releitura que falhou.
          if (failure === null) {
            setNotice({
              kind: 'success',
              text: `${CANCEL_SUCCESS_TEXT} ${CANCEL_LIST_REFRESH_FAILED}`,
            })
          } else if (failure === 'ambiguous') {
            setNotice({ kind: 'uncertain', text: CANCEL_AMBIGUOUS_REFRESH_FAILED_TEXT })
          }
        }
      }
      headingRef.current?.focus()
    } finally {
      submittingRef.current = false
      if (mountedRef.current) setSubmitting(false)
    }
  }

  return (
    <section className="my-lots" aria-labelledby="my-lots-title">
      <h1 id="my-lots-title" ref={headingRef} tabIndex={-1}>
        Meus lotes
      </h1>

      {state.status === 'ready' && (
        <div className="my-lots-summary">
          <p className="my-lots-total">Total recebido <strong>{formatCents(state.totalReceivedCents)}</strong></p>
          <div className="my-lots-refresh">
            <p className="muted">Situação atualizada: {formatDateTime(state.asOf)}</p>
            <button type="button" className="button button-secondary" disabled={submitting} aria-disabled={refreshing || submitting}
              onClick={refreshList}>
              {refreshing ? 'Atualizando…' : 'Atualizar'}
            </button>
          </div>
        </div>
      )}
      <p role="status" className={refreshing || stale ? 'muted my-lots-read-status' : 'visually-hidden'}>
        {refreshing ? 'Atualizando…' : stale ? 'Não foi possível atualizar a lista. Os dados exibidos podem estar desatualizados.' : state.status === 'ready' ? 'Lista atualizada.' : ''}
      </p>

      {/* Sempre montada: o aviso de sucesso ou de incerteza não some com a releitura. */}
      <p
        role="status"
        className={notice !== null && notice.kind !== 'error' ? 'my-lots-notice' : 'visually-hidden'}
      >
        {notice !== null && notice.kind !== 'error' ? notice.text : ''}
      </p>
      {notice !== null && notice.kind === 'error' && (
        <p role="alert" className="form-error my-lots-notice">
          {notice.text}
        </p>
      )}

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
            {state.items.map((lot) => {
              const title = lotTitleText(lot.title)
              return (
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
                    {/* Estado sempre em texto. O cancelamento prevalece sobre a fase. */}
                    <span className="lot-row-status">
                      {lot.cancelled_at !== null ? (
                        <strong className="lot-cancelled-mark">Cancelado</strong>
                      ) : (
                        <strong>{lot.settlement?.outcome === 'sold' ? 'Vendido' : lot.settlement?.outcome === 'unsold' ? 'Sem arremate' : phaseStatusText(lot.phase)}</strong>
                      )}
                      <span className="muted"> · {bidCountText(lot.bid_count)}</span>
                    </span>
                    {lot.settlement !== null && (
                      <dl className="lot-row-result">
                        {lot.settlement.outcome === 'sold' && (<>
                          <div><dt>Valor final</dt><dd className="lot-money-small">{formatCents(lot.settlement.final_amount_cents)}</dd></div>
                          <div><dt>Vencedor</dt><dd>{lot.settlement.winner_alias}</dd></div>
                        </>)}
                        <div><dt>Apurado em</dt><dd>{formatDateTime(lot.settlement.settled_at)}</dd></div>
                      </dl>
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
                  {canCancelLot(lot) && (
                    <div className="lot-row-actions">
                      {confirmingId === lot.id ? (
                        <div className="lot-cancel-confirm" role="group" aria-label={`Cancelar ${title}`}>
                          <p>{CANCEL_CONFIRM_TEXT}</p>
                          <button
                            type="button"
                            className="button button-primary"
                            disabled={submitting}
                            autoFocus
                            onClick={() => void confirmCancellation(lot.id)}
                          >
                            {submitting ? 'Cancelando…' : 'Confirmar cancelamento'}
                          </button>
                          <button
                            type="button"
                            className="button button-secondary"
                            disabled={submitting}
                            onClick={() => closeConfirmation(lot.id)}
                          >
                            Voltar
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="button button-secondary"
                          disabled={submitting}
                          aria-label={`Cancelar lote: ${title}`}
                          ref={(element) => {
                            if (element === null) ctaRefs.current.delete(lot.id)
                            else ctaRefs.current.set(lot.id, element)
                          }}
                          onClick={() => openConfirmation(lot.id)}
                        >
                          Cancelar lote
                        </button>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}
    </section>
  )
}

export default MyLots
