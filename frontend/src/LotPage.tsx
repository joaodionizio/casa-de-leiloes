import { useCallback, useEffect, useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import { fetchBidRoom, fetchMyBids, type BidRoom, type MyBids } from './api/bids'
import {
  fetchPublicLot,
  type PublicLotDetailResponse,
} from './api/publicLots'
import { fetchWallet, type WalletResponse } from './api/wallet'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import BidHistory from './BidHistory'
import {
  ambiguousNotice,
  failureBelongsToField,
  refusalNotice,
  successText,
  type BidNotice,
} from './bidFeedback'
import { bidPosition, endedLastBid } from './bidPosition'
import { bidToFollow, pendingBidOf, startBid, type PendingBid } from './bidSubmission'
import { documentTitle } from './brand'
import { consumeZero, endsAtKey, makeAnchor, type CountdownAnchor } from './countdown'
import LotBidPanel, { type Loadable, type Viewer } from './LotBidPanel'
import LotState from './LotState'
import { lotTitleText } from './lotLabels'
import { formatDateTime } from './lotTime'
import { formatCents, moneyErrorMessage, parseReaisToCents } from './money'
import { navigate } from './navigation'
import { shouldHandleClick, type NavState } from './route'

type LotPageState =
  | { status: 'loading' }
  | { status: 'not_found' }
  | { status: 'failed' }
  | { status: 'ready'; data: PublicLotDetailResponse }

type Sync = 'idle' | 'syncing' | 'failed'
type Channel = 'detail' | 'room' | 'priv'

interface LotPageProps {
  lotId: string
  navState: NavState
  navigated: boolean
  viewer: Viewer
  // E-mail da sessão do licitante: só chave interna do envio pendente, nunca exibida
  // nem enviada.
  owner: string | null
  onSessionExpired: () => void
}

// Leituras e envios disparados por efeitos começam fora do corpo do efeito: o resultado
// só chega a `setState` depois de uma resposta, nunca de forma síncrona.
function later(action: () => Promise<unknown>): void {
  void Promise.resolve().then(action)
}

interface ReadRound {
  signal: AbortSignal
  isCurrent: () => boolean
}

// Uma rodada lógica de sincronização: detalhe (se preciso), sala pública e, para o
// licitante, participação e carteira. Só uma roda por vez; o resultado final só vale
// para a rodada vigente. `superseded`: outra rodada (ou o envio) tomou o lugar dela.
type RoundResult = 'ok' | 'failed' | 'superseded'

interface Round {
  id: number
  parts: Array<Promise<boolean>>
  // Conta cuja leitura privada já faz parte da rodada.
  privateFor: string | null
  done: Promise<RoundResult>
}

interface RoundOptions {
  detail: boolean
  wallet: boolean
  // Carga inicial ou nova tentativa: uma falha não marca o histórico como desatualizado.
  quiet?: boolean
}

// Sala do lote (CAP-11 da 2.5, Story 3.5): a obra, os termos e, agora, a disputa. O
// detalhe (2.5) só fornece o que é estático; fase, fim, lance atual, mínimo e histórico
// vêm do `GET /bids`. Não há polling nem atualização entre clientes (Épico 4): a sala
// muda numa leitura explícita, no zero da contagem ou depois do próprio lance.
function LotPage({
  lotId,
  navState,
  navigated,
  viewer,
  owner,
  onSessionExpired,
}: LotPageProps) {
  const [detail, setDetail] = useState<LotPageState>({ status: 'loading' })
  const [room, setRoom] = useState<Loadable<BidRoom>>({ status: 'loading' })
  const [mine, setMine] = useState<Loadable<MyBids>>({ status: 'loading' })
  const [wallet, setWallet] = useState<Loadable<WalletResponse>>({ status: 'loading' })
  const [anchor, setAnchor] = useState<CountdownAnchor | null>(null)
  const [zeroKey, setZeroKey] = useState<string | null>(null)
  const [overlay, setOverlay] = useState(false)
  const [sync, setSync] = useState<Sync>('idle')
  const [refreshing, setRefreshing] = useState(false)
  // Rodada que produziu a sala e a participação exibidas: só pares da mesma rodada
  // formam um snapshot válido para a posição.
  const [roomRound, setRoomRound] = useState(0)
  const [mineRound, setMineRound] = useState(0)
  const [acceptedSyncFailed, setAcceptedSyncFailed] = useState(false)
  const [notice, setNotice] = useState<BidNotice | null>(null)
  const [amountText, setAmountText] = useState(
    () => (owner === null ? null : pendingBidOf(owner, lotId)?.amountText) ?? '',
  )
  const [fieldError, setFieldError] = useState<string | undefined>(undefined)
  // Envio pendente desta conta e lote na primeira renderização: o efeito acompanha esta
  // entrada, não uma segunda consulta ao registro (ela pode já ter saído dele).
  const [capturedBid] = useState<PendingBid | null>(() =>
    owner === null ? null : pendingBidOf(owner, lotId),
  )
  const [submitting, setSubmitting] = useState(() => capturedBid !== null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const amountRef = useRef<HTMLInputElement>(null)
  const wasNavigatedRef = useRef(navigated)
  const mountedRef = useRef(true)
  const roomRef = useRef(room)
  const submittingRef = useRef(submitting)
  const ownerRef = useRef(viewer === 'bidder' ? owner : null)
  const viewerRef = useRef(viewer)
  const expiredRef = useRef(onSessionExpired)
  // Fins (`ends_at`) cuja chegada a zero já gerou a releitura nesta visita.
  const consumedRef = useRef(new Set<string>())
  const channels = useRef<Record<Channel, { generation: number; controller: AbortController | null }>>({
    detail: { generation: 0, controller: null },
    room: { generation: 0, controller: null },
    priv: { generation: 0, controller: null },
  })
  const roundRef = useRef<Round | null>(null)
  const roundSeq = useRef(0)
  const roomRoundRef = useRef(0)

  useEffect(() => {
    roomRef.current = room
    submittingRef.current = submitting
    viewerRef.current = viewer
    expiredRef.current = onSessionExpired
  })

  const privateOwner = viewer === 'bidder' ? owner : null

  // Cada canal de leitura tem a sua geração e o seu `AbortController`: uma leitura nova
  // invalida a anterior do mesmo canal, e só a leitura atual aplica o resultado.
  const begin = useCallback((channel: Channel): ReadRound => {
    const state = channels.current[channel]
    state.controller?.abort()
    const controller = new AbortController()
    state.controller = controller
    state.generation += 1
    const generation = state.generation
    return {
      signal: controller.signal,
      isCurrent: () =>
        mountedRef.current &&
        !controller.signal.aborted &&
        channels.current[channel].generation === generation,
    }
  }, [])

  // Cancela a rodada vigente e as leituras da sala e da participação. O detalhe é
  // estático e fica de fora: abortá-lo sem reiniciá-lo deixaria a página em `loading`.
  const cancelRound = useCallback(() => {
    roundRef.current = null
    for (const channel of ['room', 'priv'] as const) {
      channels.current[channel].controller?.abort()
      channels.current[channel].generation += 1
    }
  }, [])

  // As leituras devolvem `false` só numa falha real; uma leitura substituída por outra do
  // mesmo canal devolve `true` (quem a substituiu responde pelo resultado).
  const loadDetail = useCallback(async (): Promise<boolean> => {
    const round = begin('detail')
    const result = await fetchPublicLot(lotId, round.signal)
    if (!round.isCurrent()) return true
    if (result.ok) {
      setDetail({ status: 'ready', data: result.data })
      return true
    }
    setDetail({ status: result.failure === 'not_found' ? 'not_found' : 'failed' })
    return false
  }, [begin, lotId])

  const loadRoom = useCallback(
    async (roundId: number): Promise<boolean> => {
      const round = begin('room')
      const result = await fetchBidRoom(lotId, round.signal)
      if (!round.isCurrent()) return true
      if (result.ok) {
        roomRoundRef.current = roundId
        setRoom({ status: 'ready', data: result.data })
        setRoomRound(roundId)
        setAnchor(makeAnchor(result.data.ends_at, result.data.as_of, performance.now()))
        setOverlay(false)
        return true
      }
      // Uma leitura que falha não apaga uma sala já carregada.
      setRoom((current) => (current.status === 'ready' ? current : { status: 'failed' }))
      return false
    },
    [begin, lotId],
  )

  const loadPrivate = useCallback(
    async (withWallet: boolean, roundId: number): Promise<boolean> => {
      if (viewerRef.current !== 'bidder') return true
      const round = begin('priv')
      const [mineResult, walletResult] = await Promise.all([
        fetchMyBids(lotId, round.signal),
        withWallet ? fetchWallet(round.signal) : Promise.resolve(null),
      ])
      if (!round.isCurrent()) return true
      if (
        (!mineResult.ok && mineResult.failure === 'unauthorized') ||
        (walletResult !== null && !walletResult.ok && walletResult.failure === 'unauthorized')
      ) {
        cancelRound()
        expiredRef.current()
        return false
      }
      if (mineResult.ok) {
        setMine({ status: 'ready', data: mineResult.data })
        setMineRound(roundId)
      } else {
        // Conserva a participação anterior para apresentação; ela não vale para a rodada.
        setMine((current) => (current.status === 'ready' ? current : { status: 'failed' }))
      }
      if (walletResult !== null) {
        if (walletResult.ok) setWallet({ status: 'ready', data: walletResult.wallet })
        else setWallet((current) => (current.status === 'ready' ? current : { status: 'failed' }))
      }
      return mineResult.ok && (walletResult === null || walletResult.ok)
    },
    [begin, cancelRound, lotId],
  )

  // Espera as partes da rodada (inclusive as que entram enquanto ela roda) e só aplica o
  // resultado final se ela ainda for a vigente.
  const settleRound = useCallback(async (round: Round, quiet: boolean): Promise<RoundResult> => {
    let seen = 0
    let ok = true
    while (seen < round.parts.length) {
      const batch = round.parts.slice(seen)
      seen = round.parts.length
      const results = await Promise.all(batch)
      ok = ok && results.every(Boolean)
    }
    if (roundRef.current !== round) return 'superseded'
    roundRef.current = null
    if (mountedRef.current) setSync(ok || quiet ? 'idle' : 'failed')
    return ok ? 'ok' : 'failed'
  }, [])

  // Todo gatilho de leitura passa por aqui. `join`: se já há uma rodada, acompanha a
  // mesma em vez de abrir outra.
  const runRound = useCallback(
    (options: RoundOptions, join: boolean): Promise<RoundResult> => {
      const running = roundRef.current
      if (join && running !== null) return running.done
      roundSeq.current += 1
      const id = roundSeq.current
      const quiet = options.quiet === true
      const privateFor = viewerRef.current === 'bidder' ? ownerRef.current : null
      const parts: Array<Promise<boolean>> = [
        options.detail ? loadDetail() : Promise.resolve(true),
        loadRoom(id),
      ]
      if (privateFor !== null) parts.push(loadPrivate(options.wallet, id))
      const round: Round = { id, parts, privateFor, done: Promise.resolve('failed') }
      roundRef.current = round
      setSync(quiet ? 'idle' : 'syncing')
      round.done = settleRound(round, quiet)
      return round.done
    },
    [loadDetail, loadRoom, loadPrivate, settleRound],
  )

  useEffect(() => {
    mountedRef.current = true
    const state = channels.current
    return () => {
      mountedRef.current = false
      for (const channel of ['detail', 'room', 'priv'] as const) {
        state[channel].controller?.abort()
      }
    }
  }, [])

  // Abertura do lote: uma rodada (detalhe, sala e, se já for licitante, participação).
  useEffect(() => {
    later(() => runRound({ detail: true, wallet: true, quiet: true }, true))
  }, [runRound])

  // A parte privada pertence à conta atual: ao trocar de conta (ou sair), some; quando a
  // sessão resolve como licitante, carrega participação e carteira.
  useEffect(() => {
    ownerRef.current = privateOwner
    channels.current.priv.controller?.abort()
    channels.current.priv.generation += 1
    later(async () => {
      setMine({ status: 'loading' })
      setWallet({ status: 'loading' })
      if (privateOwner === null) {
        setNotice(null)
        setAcceptedSyncFailed(false)
        return
      }
      // Com uma rodada em andamento, a leitura privada entra nela. Sem rodada, a
      // participação é pareada com a sala já aplicada.
      const running = roundRef.current
      if (running === null) {
        await loadPrivate(true, roomRoundRef.current)
      } else if (running.privateFor !== privateOwner) {
        running.privateFor = privateOwner
        running.parts.push(loadPrivate(true, running.id))
      }
    })
  }, [privateOwner, loadPrivate])

  // Foco no `h1` ao navegar (D11).
  useEffect(() => {
    if (!wasNavigatedRef.current) return
    const active = document.activeElement
    if (active === null || active === document.body || active === headingRef.current) {
      headingRef.current?.focus()
    }
  }, [detail.status])

  const readyTitle = detail.status === 'ready' ? lotTitleText(detail.data.lot.title) : null
  useEffect(() => {
    document.title = documentTitle(readyTitle ?? 'Lote')
  }, [readyTitle])

  // Atualização explícita: pedidos durante outra rodada acompanham a mesma.
  function refreshRoom() {
    if (submittingRef.current) return
    setRefreshing(true)
    setAcceptedSyncFailed(false)
    void runRound({ detail: true, wallet: true }, true).then(() => {
      if (mountedRef.current) setRefreshing(false)
    })
  }

  function retry() {
    setDetail({ status: 'loading' })
    setRoom({ status: 'loading' })
    void runRound({ detail: true, wallet: true, quiet: true }, false)
  }

  // Zero da estimativa: no máximo uma releitura por valor de `ends_at`. O valor é
  // consumido antes de pedir a leitura. Durante um envio, a rodada pós-POST já cobre; com
  // outra rodada em andamento, acompanha a mesma. Uma falha vira aviso, nunca repetição.
  const handleZero = useCallback(() => {
    const current = roomRef.current
    if (current.status !== 'ready') return
    setZeroKey(endsAtKey(current.data.ends_at))
    if (!consumeZero(consumedRef.current, current.data.phase, current.data.ends_at, 0)) return
    if (submittingRef.current) return
    void runRound({ detail: false, wallet: true }, true)
  }, [runRound])

  // Resultado do envio desta conta e deste lote (também depois de uma remontagem).
  const handleOutcome = useCallback(
    async (entry: PendingBid) => {
      const result = await entry.outcome
      if (!mountedRef.current || ownerRef.current !== entry.owner) return
      setSubmitting(false)
      submittingRef.current = false

      if (result.ok) {
        const { placed } = result
        cancelRound()
        // O 201 vale mesmo sem sala carregada (remontagem): sem sala, ela nasce dele.
        setRoom((current) =>
          current.status === 'ready'
            ? {
                status: 'ready',
                data: {
                  ...current.data,
                  current_bid_cents: placed.lot.current_bid_cents,
                  ends_at: placed.lot.ends_at,
                  minimum_next_bid_cents: null,
                },
              }
            : {
                status: 'ready',
                data: {
                  as_of: placed.bid.placed_at,
                  phase: 'live',
                  ends_at: placed.lot.ends_at,
                  current_bid_cents: placed.lot.current_bid_cents,
                  minimum_next_bid_cents: null,
                  bid_count: placed.bid.sequence,
                  bids: [placed.bid],
                },
              },
        )
        setAnchor(makeAnchor(placed.lot.ends_at, placed.bid.placed_at, performance.now()))
        setWallet({ status: 'ready', data: placed.wallet })
        setAmountText('')
        setFieldError(undefined)
        setOverlay(true)
        setAcceptedSyncFailed(false)
        setNotice({
          kind: 'success',
          text: successText(placed.bid.amount_cents, placed.lot.anti_sniping_applied),
          walletLink: false,
        })
        const synced = await runRound({ detail: false, wallet: false }, false)
        if (!mountedRef.current || synced === 'superseded') return
        setAcceptedSyncFailed(synced === 'failed')
        return
      }

      if (result.failure === 'unauthorized') {
        expiredRef.current()
        return
      }
      if (result.failure === 'ambiguous') {
        setNotice(ambiguousNotice('pending'))
        const synced = await runRound({ detail: false, wallet: true }, false)
        if (!mountedRef.current || synced === 'superseded') return
        setNotice(ambiguousNotice(synced === 'ok' ? 'complete' : 'partial'))
        return
      }
      if (result.failure === 'not_found') {
        setDetail({ status: 'not_found' })
        return
      }
      const refusal = refusalNotice(result.failure)
      if (failureBelongsToField(result.failure)) {
        setFieldError(refusal.text)
      } else {
        setNotice(refusal)
      }
      amountRef.current?.focus()
      await runRound({ detail: false, wallet: true }, false)
    },
    [cancelRound, runRound],
  )

  // Remontagem durante um envio pendente: acompanha o mesmo `POST`, sem outro.
  useEffect(() => {
    if (privateOwner === null) return
    const entry = bidToFollow(capturedBid, privateOwner, lotId)
    if (entry === null) return
    later(() => handleOutcome(entry))
  }, [capturedBid, privateOwner, lotId, handleOutcome])

  function handleAmountChange(value: string) {
    setAmountText(value)
    setFieldError(undefined)
    setNotice((current) => (current?.kind === 'success' ? null : current))
  }

  function handleSubmit() {
    if (privateOwner === null || submittingRef.current) return
    const parsed = parseReaisToCents(amountText)
    if (!parsed.ok) {
      setNotice(null)
      setFieldError(moneyErrorMessage(parsed.error, amountText))
      amountRef.current?.focus()
      return
    }
    const entry = startBid(privateOwner, lotId, parsed.cents, amountText)
    if (entry === null) return
    // Só o formato foi validado aqui: mínimo e saldo são do servidor.
    cancelRound()
    submittingRef.current = true
    setSubmitting(true)
    setNotice(null)
    setFieldError(undefined)
    setAcceptedSyncFailed(false)
    void handleOutcome(entry)
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

  if (detail.status === 'loading') {
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

  if (detail.status === 'not_found') {
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

  if (detail.status === 'failed') {
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

  const { lot } = detail.data
  const title = lotTitleText(lot.title)
  const roomData = room.status === 'ready' ? room.data : null
  const mineData = mine.status === 'ready' ? mine.data : null
  // Participação só vale com a sala da mesma rodada; o pseudônimo, que não muda, sempre.
  const paired = roomRound === mineRound
  const position = bidPosition(roomData, mineData, overlay, paired)
  const lastOwnBidCents = endedLastBid(roomData, mineData, paired)
  const participationUnavailable =
    mine.status === 'failed' || (mine.status === 'ready' && !paired && sync !== 'syncing')
  const zeroReached =
    roomData !== null &&
    roomData.phase === 'live' &&
    zeroKey === endsAtKey(roomData.ends_at)
  const when =
    roomData === null
      ? null
      : roomData.phase === 'live'
        ? `Termina ${formatDateTime(roomData.ends_at)}`
        : roomData.phase === 'scheduled'
          ? `Começa ${formatDateTime(lot.starts_at)}`
          : `Terminou ${formatDateTime(roomData.ends_at)}`
  const facts: Array<[string, string | null]> = [
    ['Técnica', lot.medium_display],
    ['Dimensões', lot.dimensions],
    ['Departamento', lot.department_title],
    ['Tipo', lot.artwork_type_title],
    ['Crédito', lot.credit_line],
    ['Nº no acervo', String(lot.external_id)],
  ]

  const roomStatus = roomData === null ? null : (
    <div className="lot-page-status">
      <LotState phase={roomData.phase} />
      {when !== null && <p className="lot-page-when">{when}</p>}
    </div>
  )

  return (
    <article className="lot-page" aria-labelledby="lot-title">
      <p className="lot-page-back">
        <a href="/" className="back-link" onClick={handleBack}>
          <span aria-hidden="true">← </span>Vitrine
        </a>
      </p>
      <div className="lot-page-grid">
        {roomStatus}
        <div className="lot-page-art">
          <ArtworkImage
            key={lot.image_url}
            src={lot.image_url}
            alt={lot.title ?? 'Obra sem título'}
            variant="large"
          />
        </div>
        <div className="lot-page-info">
          <h1 id="lot-title" ref={headingRef} tabIndex={-1} className="lot-page-title">
            {lot.title !== null ? title : <span className="untitled">{title}</span>}
          </h1>
          {lot.artist_display !== null && (
            <p className="lot-page-artist muted">{lot.artist_display}</p>
          )}
          {lot.date_display !== null && (
            <p className="lot-page-date muted">{lot.date_display}</p>
          )}

          {room.status === 'loading' && (
            <p role="status" className="muted">
              Carregando sala…
            </p>
          )}
          {room.status === 'failed' && (
            <div className="catalog-failure">
              <p role="alert" className="form-error">
                Não foi possível carregar a sala do lote.
              </p>
              <button type="button" className="button button-secondary" onClick={retry}>
                Tentar novamente
              </button>
            </div>
          )}
          {roomData !== null && (
            <LotBidPanel
              lotId={lotId}
              viewer={viewer}
              startingBidCents={lot.starting_bid_cents}
              startsAt={lot.starts_at}
              room={roomData}
              anchor={anchor}
              zeroConfirming={zeroReached && sync !== 'failed'}
              zeroFailed={zeroReached && sync === 'failed'}
              overlay={overlay}
              syncFailed={sync === 'failed'}
              position={position}
              wallet={wallet}
              participationUnavailable={participationUnavailable}
              ownAlias={mineData?.bidder_alias ?? null}
              lastOwnBidCents={lastOwnBidCents}
              notice={notice}
              acceptedSyncFailed={acceptedSyncFailed}
              refreshing={refreshing}
              submitting={submitting}
              amountText={amountText}
              fieldError={fieldError}
              inputRef={amountRef}
              onAmountChange={handleAmountChange}
              onSubmit={handleSubmit}
              onRefresh={refreshRoom}
              onZero={handleZero}
            />
          )}
        </div>
      </div>

      {roomData !== null && (
        <BidHistory
          bids={roomData.bids}
          bidCount={roomData.bid_count}
          myAlias={mineData?.bidder_alias ?? null}
          updating={sync === 'syncing' && overlay}
          outdated={sync === 'failed'}
        />
      )}

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
            {roomData !== null && (
              <div>
                <dt>Término</dt>
                <dd>{formatDateTime(roomData.ends_at)}</dd>
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
    </article>
  )
}

export default LotPage
