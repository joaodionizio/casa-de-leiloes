import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchBidRoom, fetchMyBids, publicSettlement, type BidRoom, type MyBids } from './api/bids'
import { fetchPublicLot, type PublicLotDetailResponse } from './api/publicLots'
import { fetchWallet, type WalletResponse } from './api/wallet'
import { ambiguousNotice, failureBelongsToField, refusalNotice, successText, type BidNotice } from './bidFeedback'
import { bidToFollow, pendingBidOf, startBid, type PendingBid } from './bidSubmission'
import { consumeZero, endsAtKey, makeAnchor, type CountdownAnchor } from './countdown'
import type { Loadable, Viewer } from './LotBidPanel'
import {
  roomSocketUrl, roomWithSettlement, sameRoomState, shouldApplyRoom,
  type ConnectionState,
} from './lotRoomSocket'
import { createLotConnection } from './lotConnection'
import { moneyErrorMessage, parseReaisToCents } from './money'

type LotPageState =
  | { status: 'loading' }
  | { status: 'not_found' }
  | { status: 'failed' }
  | { status: 'ready'; data: PublicLotDetailResponse }

type Sync = 'idle' | 'syncing' | 'failed'
type Channel = 'detail' | 'room' | 'priv'

interface LotRoomControllerProps {
  lotId: string
  viewer: Viewer
  owner: string | null
  onSessionExpired: () => void
}

// Leituras e envios disparados por efeitos começam fora do corpo do efeito: o resultado
// só chega a `setState` depois de uma resposta, nunca de forma síncrona.
function later(action: () => Promise<unknown>): void {
  void Promise.resolve().then(action)
}

// Leitura privada: `superseded` (outra leitura do canal tomou o lugar) nunca é sucesso.
type PrivateResult = 'ok' | 'failed' | 'superseded'

// Para as partes de uma rodada, quem substituiu a leitura responde pelo resultado.
function notFailed(read: Promise<PrivateResult>): Promise<boolean> {
  return read.then((result) => result !== 'failed')
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

// Owns data fetching, transport arbitration and bid submission for a single room.
// Components consume an immutable render snapshot and callbacks from the hook.
export function useLotRoomController({
  lotId,
  viewer,
  owner,
  onSessionExpired,
}: LotRoomControllerProps) {
  const [connection, setConnection] = useState<ConnectionState>('connecting')
  const connectionRef = useRef<ConnectionState>('connecting')
  const transportRef = useRef<ReturnType<typeof createLotConnection> | null>(null)
  const publicEpochRef = useRef(0)
  const publicReadRef = useRef<ReturnType<typeof fetchBidRoom> | null>(null)
  // Leitura manual bem-sucedida com o socket já indisponível: os dados estão atuais,
  // mas as atualizações ao vivo continuam fora.
  const [networkOffline, setNetworkOffline] = useState(false)
  const [manualFresh, setManualFresh] = useState(false)
  // Revalidação privada disparada por um evento do socket ainda em andamento: a
  // participação anterior fica oculta, mas isso é atualização, não falha.
  const [privatePending, setPrivatePending] = useState(false)
  // Aviso de POST ambíguo ainda sem desfecho; um evento do socket pode superar a rodada
  // pós-POST, e a revalidação coalescida então resolve o aviso.
  const ambiguousRef = useRef(false)
  const [cancelled, setCancelled] = useState(false)
  const cancelledRef = useRef(false)
  const privateRefresh = useRef({ running: false, dirty: false })
  const [detail, setDetail] = useState<LotPageState>({ status: 'loading' })
  const [room, setRoom] = useState<Loadable<BidRoom>>({ status: 'loading' })
  const [mine, setMine] = useState<Loadable<MyBids>>({ status: 'loading' })
  const [wallet, setWallet] = useState<Loadable<WalletResponse>>({ status: 'loading' })
  // Retained private data is not proof that the latest validation succeeded.
  const [mineFreshness, setMineFreshness] = useState<'unconfirmed' | 'confirmed' | 'stale'>('unconfirmed')
  const [walletStale, setWalletStale] = useState(false)
  const [anchor, setAnchor] = useState<CountdownAnchor | null>(null)
  const [zeroKey, setZeroKey] = useState<string | null>(null)
  const [overlay, setOverlay] = useState(false)
  const [sync, setSync] = useState<Sync>('idle')
  // Public freshness is independent of /mine and wallet failures in the round.
  const [publicStale, setPublicStale] = useState(false)
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
  const amountRef = useRef<HTMLInputElement>(null)
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

  const endTransport = useCallback(() => {
    cancelledRef.current = true
    transportRef.current?.stop('terminal')
    cancelRound()
    channels.current.detail.controller?.abort()
    channels.current.detail.generation += 1
  }, [cancelRound])

  const markNotFound = useCallback(() => {
    endTransport()
    setDetail({ status: 'not_found' })
  }, [endTransport])

  const markCancelled = useCallback(() => {
    endTransport()
    setCancelled(true)
  }, [endTransport])

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
    if (result.failure === 'not_found') { markNotFound(); return false }
    // Uma releitura que falha por rede ou servidor não derruba um lote já exibido.
    setDetail((current) =>
      result.failure === 'not_found'
        ? { status: 'not_found' }
        : current.status === 'ready'
          ? current
          : { status: 'failed' },
    )
    return false
  }, [begin, lotId, markNotFound])

  const applyRoom = useCallback((incoming: BidRoom, roundId: number, isOverlay = false): boolean => {
    const current = roomRef.current.status === 'ready' ? roomRef.current.data : null
    if (!shouldApplyRoom(current, incoming, cancelledRef.current, lotId, lotId)) return false
    if (incoming.settlement_status === 'settled') transportRef.current?.stop('terminal')
    roomRef.current = { status: 'ready', data: incoming }
    roomRoundRef.current = roundId
    setRoom(roomRef.current)
    setRoomRound(roundId)
    setAnchor(makeAnchor(incoming.ends_at, incoming.as_of, performance.now()))
    setOverlay(isOverlay)
    return true
  }, [lotId])

  const loadRoom = useCallback(
    async (roundId: number): Promise<boolean> => {
      const round = begin('room')
      const publicEpoch = publicEpochRef.current
      const reading = fetchBidRoom(lotId, round.signal)
      publicReadRef.current = reading
      const result = await reading
      if (publicReadRef.current === reading) publicReadRef.current = null
      if (!round.isCurrent()) return true
      if (result.ok) {
        setPublicStale(false)
        if (!applyRoom(result.data, roundId) && !cancelledRef.current) {
          // This round began after the retained newer room; its fresh private
          // read can pair with that authority without replacing public data.
          roomRoundRef.current = roundId
          setRoomRound(roundId)
        }
        return true
      }
      if (result.failure === 'not_found') {
        if (publicEpoch === publicEpochRef.current) markNotFound()
        return false
      }
      // Uma leitura que falha não apaga uma sala já carregada.
      if (publicEpoch === publicEpochRef.current) setPublicStale(true)
      setRoom((current) => (current.status === 'ready' ? current : { status: 'failed' }))
      return false
    },
    [begin, lotId, applyRoom, markNotFound],
  )

  const loadPrivate = useCallback(
    async (withWallet: boolean, roundId: number): Promise<PrivateResult> => {
      if (viewerRef.current !== 'bidder') return 'ok'
      const round = begin('priv')
      // Starting a read hides the previous position without clearing an existing error.
      setMineFreshness((current) => current === 'stale' ? current : 'unconfirmed')
      const [mineResult, walletResult] = await Promise.all([
        fetchMyBids(lotId, round.signal),
        withWallet ? fetchWallet(round.signal) : Promise.resolve(null),
      ])
      if (!round.isCurrent()) return 'superseded'
      if (
        (!mineResult.ok && mineResult.failure === 'unauthorized') ||
        (walletResult !== null && !walletResult.ok && walletResult.failure === 'unauthorized')
      ) {
        cancelRound()
        expiredRef.current()
        return 'failed'
      }
      if (mineResult.ok) {
        setMineFreshness('confirmed')
        setMine({ status: 'ready', data: mineResult.data })
        setMineRound(roundId)
      } else {
        setMineFreshness('stale')
        // Conserva a participação anterior para apresentação; ela não vale para a rodada.
        setMine((current) => (current.status === 'ready' ? current : { status: 'failed' }))
      }
      if (walletResult !== null) {
        setWalletStale(!walletResult.ok)
        if (walletResult.ok) setWallet({ status: 'ready', data: walletResult.wallet })
        else setWallet((current) => (current.status === 'ready' ? current : { status: 'failed' }))
      }
      return mineResult.ok && (walletResult === null || walletResult.ok) ? 'ok' : 'failed'
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
      if (privateFor !== null) parts.push(notFailed(loadPrivate(options.wallet, id)))
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
      setMineFreshness('unconfirmed')
      setWalletStale(false)
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
        running.parts.push(notFailed(loadPrivate(true, running.id)))
      }
    })
  }, [privateOwner, loadPrivate])

  // The connection owns only transport health; public arbitration stays here.
  useEffect(() => {
    let active = true
    let diagnosticEpoch = 0
    let diagnosticController: AbortController | null = null
    const invalidateDiagnostic = () => {
      diagnosticEpoch++
      diagnosticController?.abort()
      diagnosticController = null
    }
    const transport = createLotConnection(lotId, {
      socket: () => new WebSocket(roomSocketUrl(lotId, window.location.origin)),
      now: () => performance.now(),
      schedule: (callback, delay) => {
        const timer = window.setTimeout(callback, delay)
        return () => window.clearTimeout(timer)
      },
      random: Math.random,
      online: () => navigator.onLine,
      status: (state, offline = false) => {
        if (state === 'terminal' || state === 'disposed') invalidateDiagnostic()
        if (!active || cancelledRef.current) return
        connectionRef.current = state
        setConnection(state)
        setNetworkOffline(offline)
        if (state !== 'connected') setManualFresh(false)
      },
      recovered: invalidateDiagnostic,
      diagnose: () => {
        const epoch = ++diagnosticEpoch
        diagnosticController = new AbortController()
        const reading = publicReadRef.current ?? fetchBidRoom(lotId, diagnosticController.signal)
        void reading.then((result) => {
          if (!active || diagnosticEpoch !== epoch || cancelledRef.current) return
          if (!result.ok && result.failure === 'not_found') markNotFound()
        })
      },
      message: (event) => {
      if (!active || !mountedRef.current || cancelledRef.current) return
      if (event.type === 'lot_cancelled') {
        markCancelled()
        return
      }
      if (event.type === 'lot_closed') {
        const current = roomRef.current.status === 'ready' ? roomRef.current.data : null
        if (current === null) return
        const settlement = publicSettlement(event)
        const terminal = roomWithSettlement(current, settlement)
        if (!shouldApplyRoom(current, terminal, false, lotId, event.lot_id)) return
        publicEpochRef.current++
        applyRoom(terminal, roomRoundRef.current)
        // Revalida também a participação privada após a liquidação.
        // Um snapshot anterior não confirma o resultado pessoal do leilão.
        void runRound({ detail: false, wallet: true }, false)
        return
      }
      // A current connection's snapshot restores public freshness even when
      // arbitration retains newer data or the public state is unchanged.
      if (event.type === 'room_snapshot') {
        publicEpochRef.current++
        setPublicStale(false)
      }
      const current = roomRef.current.status === 'ready' ? roomRef.current.data : null
      if (!shouldApplyRoom(current, event.room, false, lotId, event.lot_id)) return
      setPublicStale(false)
      if (current !== null && sameRoomState(current, event.room)) {
        // Same public state, newer reading: only the clock is re-anchored. No round is
        // cancelled and no private read starts.
        roomRef.current = { status: 'ready', data: event.room }
        setRoom(roomRef.current)
        setAnchor(makeAnchor(event.room.ends_at, event.room.as_of, performance.now()))
        return
      }
      cancelRound()
      roundSeq.current += 1
      applyRoom(event.room, roundSeq.current)
      setSync('idle')
      if (viewerRef.current !== 'bidder') return
      setPrivatePending(true)
      const refresh = privateRefresh.current
      refresh.dirty = true
      if (refresh.running) return
      refresh.running = true
      later(async () => {
        let result: PrivateResult = 'superseded'
        try {
          while (active && refresh.dirty && !cancelledRef.current) {
            refresh.dirty = false
            result = await loadPrivate(true, roomRoundRef.current)
          }
        } finally {
          refresh.running = false
          if (active && mountedRef.current) {
            setPrivatePending(false)
            // Only this loop's own current, successful read resolves the notice. A
            // superseded read leaves it open for the round that replaced it.
            if (ambiguousRef.current && result !== 'superseded') {
              ambiguousRef.current = false
              if (result === 'ok') {
                setNotice((notice) =>
                  notice?.kind === 'uncertain' ? ambiguousNotice('complete') : notice,
                )
              }
            }
          }
        }
      })
      },
    })
    transportRef.current = transport
    if (cancelledRef.current) transport.stop()
    const goOffline = () => transport.offline()
    const goOnline = () => transport.online()
    const visible = () => { if (document.visibilityState === 'visible') transport.visible() }
    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    document.addEventListener('visibilitychange', visible)
    return () => {
      active = false
      invalidateDiagnostic()
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
      document.removeEventListener('visibilitychange', visible)
      transport.stop()
      if (transportRef.current === transport) transportRef.current = null
    }
  }, [lotId, applyRoom, cancelRound, loadRoom, loadPrivate, runRound, markNotFound, markCancelled])

  // Atualização explícita: pedidos durante outra rodada acompanham a mesma.
  function refreshRoom() {
    if (submittingRef.current) return
    setRefreshing(true)
    setAcceptedSyncFailed(false)
    void runRound({ detail: true, wallet: true }, true).then((result) => {
      if (!mountedRef.current) return
      setRefreshing(false)
      if (result === 'ok') setManualFresh(connectionRef.current !== 'connected')
      else if (result === 'failed') setManualFresh(false)
      // An ambiguous POST left open by a superseded revalidation is decided here.
      if (ambiguousRef.current && result !== 'superseded') {
        ambiguousRef.current = false
        setNotice((notice) =>
          notice?.kind === 'uncertain' ? ambiguousNotice(result === 'ok' ? 'complete' : 'partial') : notice,
        )
      }
    })
  }

  function retry() {
    setDetail({ status: 'loading' })
    // Retain public authority while retrying: lot_closed needs the known snapshot,
    // and arbitration must reject an older pending REST response after settlement.
    setRoom((current) => current.status === 'ready' ? current : { status: 'loading' })
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
      if (!mountedRef.current || cancelledRef.current || ownerRef.current !== entry.owner) return
      setSubmitting(false)
      submittingRef.current = false

      if (result.ok) {
        const { placed } = result
        cancelRound()
        // Success belongs to this attempt; only a newer bid may overlay the room.
        const current = roomRef.current.status === 'ready' ? roomRef.current.data : null
        if (current === null || placed.bid.sequence > current.bid_count) {
          roundSeq.current += 1
          applyRoom({
            as_of: placed.bid.placed_at,
            phase: 'live',
            ends_at: placed.lot.ends_at,
            current_bid_cents: placed.lot.current_bid_cents,
            minimum_next_bid_cents: null,
            bid_count: placed.bid.sequence,
            settlement_status: 'pending', settlement: null,
            bids: [placed.bid, ...(current?.bids ?? [])].slice(0, 50),
          }, roundSeq.current, true)
        }
        setWallet({ status: 'ready', data: placed.wallet })
        setAmountText('')
        setFieldError(undefined)
        setAcceptedSyncFailed(false)
        setNotice({
          kind: 'success',
          text: successText(placed.bid.amount_cents, placed.lot.anti_sniping_applied),
          walletLink: false,
        })
        const synced = await runRound({ detail: false, wallet: true }, false)
        if (!mountedRef.current || synced === 'superseded') return
        setAcceptedSyncFailed(synced === 'failed')
        return
      }

      if (result.failure === 'unauthorized') {
        expiredRef.current()
        return
      }
      if (result.failure === 'ambiguous') {
        ambiguousRef.current = true
        setNotice(ambiguousNotice('pending'))
        const synced = await runRound({ detail: false, wallet: true }, false)
        // Superada por um evento do socket: quem resolve o aviso é a revalidação dele.
        if (!mountedRef.current || synced === 'superseded') return
        ambiguousRef.current = false
        setNotice(ambiguousNotice(synced === 'ok' ? 'complete' : 'partial'))
        return
      }
      if (result.failure === 'not_found') {
        markNotFound()
        return
      }
      if (result.failure === 'lot_cancelled') {
        markCancelled()
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
    [cancelRound, runRound, applyRoom, markNotFound, markCancelled],
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
    ambiguousRef.current = false
    submittingRef.current = true
    setSubmitting(true)
    setNotice(null)
    setFieldError(undefined)
    setAcceptedSyncFailed(false)
    void handleOutcome(entry)
  }

  return {
    connection, networkOffline, manualFresh, privatePending, cancelled,
    detail, room, mine, wallet, mineFreshness, walletStale, anchor, zeroKey,
    overlay, sync, publicStale, refreshing, roomRound, mineRound,
    acceptedSyncFailed, notice, amountText, fieldError, submitting, amountRef,
    refreshRoom, retry, handleZero, handleAmountChange, handleSubmit,
  }
}
