import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import ArtworkDetailPanel from './ArtworkDetailPanel'
import type { DetailState } from './ArtworkDetailPanel'
import ArtworkImage from './ArtworkImage'
import { catalogFailureMessage, fetchArtwork, searchArtworks } from './api/catalog'
import type { ArtworkDetail, ArtworkSummary, CatalogFailure } from './api/catalog'

// Limite de resultados do servidor (P7): com 20, avisa que há mais para refinar.
const RESULT_LIMIT = 20

type SearchState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'results'; term: string; items: ArtworkSummary[] }
  | { status: 'failed'; failure: CatalogFailure }

type MobileView = 'list' | 'detail'

interface CatalogSearchProps {
  onSessionExpired: () => void
  // Abre o formulário de lote com a obra do detalhe (Story 2.4).
  onCreateLot: (artwork: ArtworkDetail) => void
  // Contador: quando aumenta, a busca (de volta à tela) devolve o foco ao detalhe.
  returnFocus: number
}

function CatalogSearch({ onSessionExpired, onCreateLot, returnFocus }: CatalogSearchProps) {
  const [term, setTerm] = useState('')
  const [termInvalid, setTermInvalid] = useState(false)
  const [search, setSearch] = useState<SearchState>({ status: 'idle' })
  const [detail, setDetail] = useState<DetailState>({ status: 'none' })
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [view, setView] = useState<MobileView>('list')
  // Contadores de pedido de foco: o efeito move o foco depois que a tela é
  // atualizada (o painel só aparece depois da troca de vista).
  const [detailFocus, setDetailFocus] = useState(0)
  const [listFocus, setListFocus] = useState(0)

  const inputRef = useRef<HTMLInputElement>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const itemRefs = useRef(new Map<number, HTMLButtonElement>())
  const searchAbort = useRef<AbortController | null>(null)
  const detailAbort = useRef<AbortController | null>(null)
  const lastTerm = useRef('')
  const scrollBeforeDetail = useRef(0)
  const selectedIdRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      searchAbort.current?.abort()
      detailAbort.current?.abort()
    }
  }, [])

  useEffect(() => {
    if (detailFocus > 0) headingRef.current?.focus()
  }, [detailFocus])

  useEffect(() => {
    if (returnFocus > 0) headingRef.current?.focus()
  }, [returnFocus])

  useEffect(() => {
    if (listFocus === 0) return
    window.scrollTo(0, scrollBeforeDetail.current)
    const id = selectedIdRef.current
    if (id !== null) itemRefs.current.get(id)?.focus({ preventScroll: true })
  }, [listFocus])

  function clearSelection() {
    detailAbort.current?.abort()
    selectedIdRef.current = null
    setSelectedId(null)
    setDetail({ status: 'none' })
    setView('list')
  }

  async function runSearch(rawTerm: string) {
    const trimmed = rawTerm.trim()
    if (trimmed === '') {
      setTermInvalid(true)
      inputRef.current?.focus()
      return
    }
    setTermInvalid(false)
    lastTerm.current = trimmed
    clearSelection()
    searchAbort.current?.abort()
    const controller = new AbortController()
    searchAbort.current = controller
    setSearch({ status: 'loading' })
    // O botão fica desabilitado durante a busca; o foco permanece no campo.
    inputRef.current?.focus()

    const result = await searchArtworks(trimmed, controller.signal)
    if (controller.signal.aborted) return
    if (result.ok) {
      setSearch({ status: 'results', term: trimmed, items: result.items })
      return
    }
    if (result.failure === 'unauthorized') {
      onSessionExpired()
      return
    }
    if (result.failure === 'validation') {
      setSearch({ status: 'idle' })
      setTermInvalid(true)
      inputRef.current?.focus()
      return
    }
    setSearch({ status: 'failed', failure: result.failure })
  }

  async function openArtwork(externalId: number) {
    scrollBeforeDetail.current = window.scrollY
    detailAbort.current?.abort()
    const controller = new AbortController()
    detailAbort.current = controller
    selectedIdRef.current = externalId
    setSelectedId(externalId)
    setDetail({ status: 'loading' })
    setView('detail')
    setDetailFocus((count) => count + 1)

    const result = await fetchArtwork(externalId, controller.signal)
    if (controller.signal.aborted) return
    if (result.ok) {
      setDetail({ status: 'ready', artwork: result.artwork })
      return
    }
    if (result.failure === 'unauthorized') {
      onSessionExpired()
      return
    }
    setDetail({ status: 'failed', failure: result.failure })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (search.status === 'loading') return
    void runSearch(term)
  }

  function handleBack() {
    setView('list')
    setListFocus((count) => count + 1)
  }

  function handleRetryDetail() {
    if (selectedId !== null) void openArtwork(selectedId)
  }

  const loading = search.status === 'loading'
  const results = search.status === 'results' ? search : null

  return (
    <section
      className="catalog"
      aria-labelledby="catalog-title"
      data-view={view}
    >
      <div className="catalog-intro">
        <h1 id="catalog-title">Buscar obras</h1>
        <p className="muted">
          Acervo do Art Institute of Chicago. Só aparecem obras em domínio público
          com imagem.
        </p>
        <form role="search" className="catalog-form" onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="catalog-term">Termo de busca</label>
            <div className="catalog-search-row">
              <input
                id="catalog-term"
                ref={inputRef}
                type="search"
                maxLength={100}
                autoComplete="off"
                placeholder="Ex.: Monet, water lilies, portrait"
                value={term}
                onChange={(event) => {
                  setTerm(event.target.value)
                  setTermInvalid(false)
                }}
                aria-invalid={termInvalid}
                aria-describedby={termInvalid ? 'catalog-term-error' : undefined}
              />
              <button
                type="submit"
                className="button button-primary"
                disabled={loading}
              >
                {loading ? 'Buscando…' : 'Buscar'}
              </button>
            </div>
          </div>
          {termInvalid && (
            <p id="catalog-term-error" className="form-error" role="alert">
              {catalogFailureMessage('validation')}
            </p>
          )}
        </form>
        {search.status === 'idle' && (
          <p className="muted">
            Pesquise por título, artista ou tema. O acervo do museu está em inglês.
          </p>
        )}
      </div>

      <div className="catalog-layout">
        <div className="result-region" aria-live="polite" aria-busy={loading}>
          {loading && (
            <p role="status" className="muted">
              Buscando obras…
            </p>
          )}

          {search.status === 'failed' && (
            <div className="catalog-failure">
              <p role="alert" className="form-error">
                {catalogFailureMessage(search.failure)}
              </p>
              {search.failure !== 'forbidden' && (
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => void runSearch(lastTerm.current)}
                >
                  Tentar novamente
                </button>
              )}
            </div>
          )}

          {results !== null && results.items.length === 0 && (
            <div>
              <p role="status" className="empty-title">
                Nenhuma obra encontrada.
              </p>
              <p className="muted">
                Só aparecem obras em domínio público com imagem. Tente outro termo,
                em inglês.
              </p>
            </div>
          )}

          {results !== null && results.items.length > 0 && (
            <>
              <p className="result-count">
                {results.items.length}{' '}
                {results.items.length === 1 ? 'obra' : 'obras'} para “{results.term}”
              </p>
              {results.items.length === RESULT_LIMIT && (
                <p className="muted">
                  Mostrando as {RESULT_LIMIT} mais relevantes. Refine o termo para
                  encontrar outras.
                </p>
              )}
              <ul className="result-list">
                {results.items.map((item) => (
                  <li key={item.external_id}>
                    <button
                      type="button"
                      className="result-item"
                      aria-current={item.external_id === selectedId ? 'true' : undefined}
                      ref={(node) => {
                        if (node === null) itemRefs.current.delete(item.external_id)
                        else itemRefs.current.set(item.external_id, node)
                      }}
                      onClick={() => void openArtwork(item.external_id)}
                    >
                      <ArtworkImage
                        key={item.image_url}
                        src={item.image_url}
                        alt=""
                        variant="thumb"
                      />
                      <span className="result-text">
                        {item.title !== null ? (
                          <span className="result-title" title={item.title}>
                            {item.title}
                          </span>
                        ) : (
                          <span className="result-title untitled">Sem título</span>
                        )}
                        {item.artist_display !== null && (
                          <span className="result-artist muted">
                            {item.artist_display}
                          </span>
                        )}
                        {item.date_display !== null && (
                          <span className="result-date muted">
                            {item.date_display}
                          </span>
                        )}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <ArtworkDetailPanel
          state={detail}
          headingRef={headingRef}
          onRetry={handleRetryDetail}
          onBack={handleBack}
          onCreateLot={onCreateLot}
        />
      </div>
    </section>
  )
}

export default CatalogSearch
