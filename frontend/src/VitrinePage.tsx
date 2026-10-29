import { useEffect, useRef, useState } from 'react'
import {
  fetchPublicLots,
  type PublicLotsResponse,
} from './api/publicLots'
import { asOfText } from './asOf'
import ClosedLots from './ClosedLots'
import FeaturedLot from './FeaturedLot'
import LotRail from './LotRail'
import { patchCurrentState } from './navigation'
import type { NavState } from './route'
import {
  filterPublicLots, initialEndedVisible, railItems, selectFeatured,
  type VitrinePhaseFilter,
} from './vitrine'

type VitrineState =
  | { status: 'loading' }
  | { status: 'failed' }
  // `today` é o dia do navegador no momento da carga: só escolhe o formato da linha
  // "Situação atualizada…" (D16), nunca decide fase.
  | { status: 'ready'; data: PublicLotsResponse; today: Date }

interface VitrineProps {
  navState: NavState
  // Já houve navegação interna (ou Back/Forward): só então movemos o foco (D11).
  navigated: boolean
}

interface VitrineContentProps {
  data: PublicLotsResponse
  today: Date
  endedRestore: number | undefined
  termRestore: string | undefined
  phaseRestore: VitrinePhaseFilter | undefined
}

const PHASE_FILTERS: { value: VitrinePhaseFilter; label: string }[] = [
  { value: 'all', label: 'Todos' },
  { value: 'live', label: 'Ao vivo' },
  { value: 'scheduled', label: 'Próximos' },
  { value: 'ended', label: 'Encerrados' },
]

function resultText(total: number) {
  return total === 0
    ? 'Nenhum lote encontrado com esses filtros.'
    : `${total} ${total === 1 ? 'lote encontrado' : 'lotes encontrados'}.`
}

function VitrineContent({ data, today, endedRestore, termRestore, phaseRestore }: VitrineContentProps) {
  const [term, setTerm] = useState(termRestore ?? '')
  const [phase, setPhase] = useState<VitrinePhaseFilter>(phaseRestore ?? 'all')
  const [endedVisible, setEndedVisible] = useState(() => initialEndedVisible(
    filterPublicLots(data, termRestore ?? '', phaseRestore ?? 'all').ended.length,
    endedRestore,
  ))
  const [announcement, setAnnouncement] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)
  const filtered = filterPublicLots(data, term, phase)
  const featured = selectFeatured(filtered)
  const total = filtered.live.length + filtered.scheduled.length + filtered.ended.length
  const hasFilters = term.trim() !== '' || phase !== 'all'
  const asOfLine = asOfText(data.as_of, today)
  // Avisos usam a mesma fotografia da fase e do ends_at, sem relógio em execução.
  const snapshotTime = Date.parse(data.as_of)

  function changeFilters(nextTerm: string, nextPhase: VitrinePhaseFilter, announce: boolean) {
    const next = filterPublicLots(data, nextTerm, nextPhase)
    setTerm(nextTerm)
    setPhase(nextPhase)
    setEndedVisible(initialEndedVisible(next.ended.length))
    // Digitar atualiza imediatamente. Leitores de tela recebem o resumo ao sair
    // do campo, ou ao selecionar/limpar, sem um anúncio por tecla.
    setAnnouncement(announce
      ? resultText(next.live.length + next.scheduled.length + next.ended.length)
      : '')
  }

  // Antes de sair para um lote, guarda qual foi e quantos encerrados estavam à
  // mostra, para o Back devolver o foco ao mesmo lugar (D11).
  function rememberLot(lotId: string) {
    patchCurrentState({ restoreLotId: lotId, endedVisible, vitrineTerm: term, vitrinePhase: phase })
  }

  const liveRail = railItems(filtered.live, featured)
  const scheduledRail = railItems(filtered.scheduled, featured)

  return (
    <>
      <form className="vitrine-filters" role="search" aria-label="Buscar lotes" onSubmit={(event) => {
        event.preventDefault()
        setAnnouncement(resultText(total))
      }}>
        <div className="field vitrine-search">
          <label htmlFor="vitrine-search">Buscar obras</label>
          <input
            ref={searchRef}
            id="vitrine-search"
            type="search"
            value={term}
            placeholder="Título, artista ou data da obra"
            onChange={(event) => changeFilters(event.target.value, phase, false)}
            onBlur={() => setAnnouncement(resultText(total))}
          />
        </div>
        <div className="field vitrine-phase-select">
          <label htmlFor="vitrine-phase-select">Estado do lote</label>
          <select id="vitrine-phase-select" value={phase} onChange={(event) => {
            const option = PHASE_FILTERS.find(item => item.value === event.target.value)
            if (option) changeFilters(term, option.value, true)
          }}>
            {PHASE_FILTERS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </div>
        <fieldset className="vitrine-phase-filters">
          <legend>Estado do lote</legend>
          <div className="vitrine-phase-options">
            {PHASE_FILTERS.map((option) => (
              <label className="vitrine-phase-option" key={option.value}>
                <input type="radio" name="vitrine-phase" value={option.value}
                  checked={phase === option.value}
                  onChange={() => changeFilters(term, option.value, true)} />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="vitrine-filter-summary">
          <p className="muted">{total === 0 ? '0 lotes encontrados.' : resultText(total)}</p>
          {hasFilters && (
            <button type="button" className="vitrine-clear" onClick={() => {
              changeFilters('', 'all', true)
              searchRef.current?.focus()
            }}>Limpar filtros</button>
          )}
        </div>
        <p role="status" aria-atomic="true" className="visually-hidden">{announcement}</p>
      </form>

      {total === 0 && hasFilters ? (
        <section className="featured-empty" aria-labelledby="filter-empty-title">
          <h2 id="filter-empty-title">Nenhum lote encontrado com esses filtros.</h2>
        </section>
      ) : featured.kind === 'none' && !hasFilters ? (
        <section className="featured-empty" aria-labelledby="featured-empty-title">
          <h2 id="featured-empty-title">Nenhum lote em leilão agora</h2>
          <p className="muted">
            Novos lotes de obras em domínio público entram aqui assim que são
            publicados.
          </p>
        </section>
      ) : featured.kind !== 'none' ? (
        <FeaturedLot lot={featured.lot} now={snapshotTime} onOpen={rememberLot} />
      ) : null}
      {asOfLine !== null && <p className="as-of muted">{asOfLine}</p>}

      {(phase === 'all' || phase === 'live') && (total > 0 || !hasFilters) && <LotRail
        headingId="live-heading"
        title="Ao vivo"
        kind="live"
        lots={liveRail}
        now={snapshotTime}
        emptyText={
          filtered.live.length === 0
            ? 'Nenhum lote ao vivo agora.'
            : 'O lote em destaque é o único ao vivo agora.'
        }
        onOpen={rememberLot}
      />}
      {(phase === 'all' || phase === 'scheduled') && (total > 0 || !hasFilters) && <LotRail
        headingId="upcoming-heading"
        title="Próximos lotes"
        kind="upcoming"
        lots={scheduledRail}
        now={snapshotTime}
        emptyText={
          filtered.scheduled.length === 0
            ? 'Nenhum lote agendado.'
            : 'O lote em destaque é o único agendado.'
        }
        onOpen={rememberLot}
      />}
      {(phase === 'all' || phase === 'ended') && (total > 0 || !hasFilters) && <ClosedLots
        lots={filtered.ended}
        announceCount={!hasFilters}
        visible={endedVisible}
        onVisibleChange={setEndedVisible}
        onOpen={rememberLot}
      />}
    </>
  )
}

// Vitrine pública (CAP-10): destaque, ao vivo, próximos lotes e encerrados, tudo vindo
// classificado do servidor numa fotografia só (`as_of`). Cada montagem faz um GET novo;
// a fase não muda sozinha com a página aberta (P3): sem polling, sem contagem
// regressiva, sem relógio do navegador no estado do lote.
function VitrinePage({ navState, navigated }: VitrineProps) {
  const [state, setState] = useState<VitrineState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const rootRef = useRef<HTMLDivElement>(null)
  // O que o Back guardou na entrada: lido uma vez, na montagem.
  const restoreRef = useRef({
    navigated,
    lotId: navState.restoreLotId,
  })

  useEffect(() => {
    if (restoreRef.current.navigated) headingRef.current?.focus()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchPublicLots(controller.signal).then((result) => {
      if (controller.signal.aborted) return
      if (result.ok) {
        setState({ status: 'ready', data: result.data, today: new Date() })
      } else {
        setState({ status: 'failed' })
      }
    })
    return () => controller.abort()
  }, [attempt])

  // Back: com a vitrine pronta, o foco volta ao link do lote aberto (e o põe na
  // tela); sem ele, ao título da vista, no topo.
  useEffect(() => {
    if (state.status !== 'ready') return
    const { navigated: wasNavigated, lotId } = restoreRef.current
    if (!wasNavigated || lotId === undefined) return
    const link = rootRef.current?.querySelector<HTMLElement>(
      `[data-lot-id="${lotId}"]`,
    )
    if (link) {
      link.focus()
      link.scrollIntoView({ block: 'center' })
    } else {
      headingRef.current?.focus()
      window.scrollTo(0, 0)
    }
  }, [state.status])

  function retry() {
    setState({ status: 'loading' })
    setAttempt((count) => count + 1)
  }

  return (
    <div className="vitrine" ref={rootRef}>
      <h1 className="visually-hidden" ref={headingRef} tabIndex={-1}>
        Vitrine
      </h1>

      {state.status === 'loading' && (
        <>
          <p role="status" className="muted">
            Carregando a vitrine…
          </p>
          <div className="featured-reserve" aria-hidden="true" />
        </>
      )}

      {state.status === 'failed' && (
        <div className="vitrine-failure">
          <p role="alert" className="form-error">
            Não foi possível carregar a vitrine.
          </p>
          <button type="button" className="button button-secondary" onClick={retry}>
            Tentar novamente
          </button>
        </div>
      )}

      {state.status === 'ready' && (
        <VitrineContent
          data={state.data}
          today={state.today}
          endedRestore={navState.endedVisible}
          termRestore={navState.vitrineTerm}
          phaseRestore={navState.vitrinePhase}
        />
      )}
    </div>
  )
}

export default VitrinePage
