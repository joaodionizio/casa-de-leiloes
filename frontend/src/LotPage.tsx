import { useEffect, useRef } from 'react'
import type { MouseEvent } from 'react'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import LotArtworkDetails from './LotArtworkDetails'
import LotPageFallback from './LotPageFallback'
import BidHistory from './BidHistory'
import CountdownTimer from './CountdownTimer'
import { bidPosition, endedLastBid } from './bidPosition'
import { documentTitle } from './brand'
import { endsAtKey } from './countdown'
import LotBidPanel, { type Viewer } from './LotBidPanel'
import LotState from './LotState'
import { lotTitleText } from './lotLabels'
import { formatDateTime } from './lotTime'
import { navigate } from './navigation'
import { shouldHandleClick, type NavState } from './route'
import { useLotRoomController } from './useLotRoomController'

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

function LotPage({
  lotId,
  navState,
  navigated,
  viewer,
  owner,
  onSessionExpired,
}: LotPageProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const wasNavigatedRef = useRef(navigated)
  const {
    connection, networkOffline, manualFresh, privatePending, cancelled,
    detail, room, mine, wallet, mineFreshness, walletStale, anchor, zeroKey,
    overlay, sync, publicStale, refreshing, roomRound, mineRound,
    acceptedSyncFailed, notice, amountText, fieldError, submitting, amountRef,
    refreshRoom, retry, handleZero, handleAmountChange, handleSubmit,
  } = useLotRoomController({ lotId, viewer, owner, onSessionExpired })

  // Lote cancelado ao vivo: a tela inteira muda, então o foco vai para o título (que o
  // leitor de tela anuncia) em vez de cair no `body` quando o campo do lance desmonta.
  useEffect(() => {
    if (cancelled) headingRef.current?.focus()
  }, [cancelled])

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

  if (cancelled) {
    return <LotPageFallback status="cancelled" lotId={lotId} headingRef={headingRef} onRetry={retry} />
  }
  if (detail.status !== 'ready') {
    return <LotPageFallback status={detail.status} lotId={lotId} headingRef={headingRef} onRetry={retry} />
  }

  const { lot } = detail.data
  const title = lotTitleText(lot.title)
  const roomData = room.status === 'ready' ? room.data : null
  const mineData = mine.status === 'ready' ? mine.data : null
  // Participação só vale com a sala da mesma rodada; o pseudônimo, que não muda, sempre.
  const paired = roomRound === mineRound && mineFreshness === 'confirmed'
  const position = bidPosition(roomData, mineData, overlay, paired)
  const lastOwnBidCents = endedLastBid(roomData, mineData, paired)
  const participationUnavailable =
    mineFreshness === 'stale' ||
    mine.status === 'failed' ||
    (mine.status === 'ready' && !paired && mineFreshness !== 'unconfirmed' && sync !== 'syncing' && !privatePending)
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
  const roomStatus = roomData === null ? null : (
    <div className="lot-page-status">
      <LotState phase={roomData.phase} text={roomData.phase === 'ended' && roomData.settlement_status === 'settled' ? 'Encerrado' : undefined} />
      {roomData.phase === 'live' && roomData.settlement_status === 'pending' && (
        <CountdownTimer anchor={anchor} onZero={handleZero} />
      )}
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
      <p><AppLink to={`/lots/${lotId}/audit`}>Consultar auditoria pública</AppLink></p>
      {roomData?.settlement?.outcome === 'sold' && <p><AppLink to={`/lots/${lotId}/receipt`}>Ver comprovante de arremate</AppLink></p>}
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
              connection={connection}
              networkOffline={networkOffline}
              manualFresh={manualFresh}
              viewer={viewer}
              startingBidCents={lot.starting_bid_cents}
              startsAt={lot.starts_at}
              room={roomData}
              zeroConfirming={zeroReached && sync !== 'failed'}
              zeroFailed={zeroReached && sync === 'failed'}
              overlay={overlay}
              syncFailed={publicStale}
              position={position}
              wallet={wallet}
              walletStale={walletStale}
              participationUnavailable={participationUnavailable}
              ownAlias={mineData?.bidder_alias ?? null}
              ownBidCount={mineData?.my_bid_count ?? null}
              participationVerified={paired}
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
          outdated={publicStale}
        />
      )}

      <LotArtworkDetails lot={lot} endsAt={roomData?.ends_at ?? null} />
    </article>
  )
}

export default LotPage
