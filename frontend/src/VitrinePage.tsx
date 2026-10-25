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
import { initialEndedVisible, railItems, selectFeatured } from './vitrine'

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
}

function VitrineContent({ data, today, endedRestore }: VitrineContentProps) {
  const [endedChoice, setEndedChoice] = useState<number | null>(null)
  const featured = selectFeatured(data)
  const endedVisible =
    endedChoice ?? initialEndedVisible(data.ended.length, endedRestore)
  const asOfLine = asOfText(data.as_of, today)

  // Antes de sair para um lote, guarda qual foi e quantos encerrados estavam à
  // mostra, para o Back devolver o foco ao mesmo lugar (D11).
  function rememberLot(lotId: string) {
    patchCurrentState({ restoreLotId: lotId, endedVisible })
  }

  const liveRail = railItems(data.live, featured)
  const scheduledRail = railItems(data.scheduled, featured)

  return (
    <>
      {featured.kind === 'none' ? (
        <section className="featured-empty" aria-labelledby="featured-empty-title">
          <h2 id="featured-empty-title">Nenhum lote em leilão agora</h2>
          <p className="muted">
            Novos lotes de obras em domínio público entram aqui assim que são
            publicados.
          </p>
        </section>
      ) : (
        <FeaturedLot lot={featured.lot} onOpen={rememberLot} />
      )}
      {asOfLine !== null && <p className="as-of muted">{asOfLine}</p>}

      <LotRail
        headingId="live-heading"
        title="Ao vivo"
        kind="live"
        lots={liveRail}
        emptyText={
          data.live.length === 0
            ? 'Nenhum lote ao vivo agora.'
            : 'O lote em destaque é o único ao vivo agora.'
        }
        onOpen={rememberLot}
      />
      <LotRail
        headingId="upcoming-heading"
        title="Próximos lotes"
        kind="upcoming"
        lots={scheduledRail}
        emptyText={
          data.scheduled.length === 0
            ? 'Nenhum lote agendado.'
            : 'O lote em destaque é o único agendado.'
        }
        onOpen={rememberLot}
      />
      <ClosedLots
        lots={data.ended}
        visible={endedVisible}
        onVisibleChange={setEndedChoice}
        onOpen={rememberLot}
      />
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
        />
      )}
    </div>
  )
}

export default VitrinePage
