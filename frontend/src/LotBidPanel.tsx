import type { RefObject } from 'react'
import type { BidRoom } from './api/bids'
import type { WalletResponse } from './api/wallet'
import AppLink from './AppLink'
import BidForm from './BidForm'
import type { BidNotice } from './bidFeedback'
import type { BidPosition } from './bidPosition'
import CountdownTimer from './CountdownTimer'
import type { CountdownAnchor } from './countdown'
import { formatDateTime, formatClock } from './lotTime'
import { formatCents } from './money'

export type Viewer = 'checking' | 'visitor' | 'auctioneer' | 'bidder'
export type Loadable<T> =
  | { status: 'loading' }
  | { status: 'failed' }
  | { status: 'ready'; data: T }

interface LotBidPanelProps {
  lotId: string
  viewer: Viewer
  startingBidCents: number
  startsAt: string
  room: BidRoom
  anchor: CountdownAnchor | null
  zeroConfirming: boolean
  zeroFailed: boolean
  // 201 aplicado, releitura pública ainda pendente ou falha: mínimo e posição ocultos.
  overlay: boolean
  syncFailed: boolean
  position: BidPosition
  wallet: Loadable<WalletResponse>
  // Participação ausente ou de outra rodada que a sala exibida: a posição não se calcula.
  participationUnavailable: boolean
  ownAlias: string | null
  // Último lance próprio, só com o lote encerrado.
  lastOwnBidCents: number | null
  notice: BidNotice | null
  acceptedSyncFailed: boolean
  refreshing: boolean
  submitting: boolean
  amountText: string
  fieldError: string | undefined
  inputRef: RefObject<HTMLInputElement | null>
  onAmountChange: (value: string) => void
  onSubmit: () => void
  onRefresh: () => void
  onZero: () => void
}

const POSITION_TEXT: Record<Exclude<BidPosition, 'hidden' | 'neutral'>, string> = {
  winning: '✓ Você está ganhando',
  outbid: '↑ Você foi superado',
}

// Painel operacional da sala (Story 3.5): lance atual, mínimo, tempo, posição, saldo e
// formulário. Tudo vem do read model e do 201; o painel não decide nada.
function LotBidPanel(props: LotBidPanelProps) {
  const { room, viewer, overlay } = props
  const live = room.phase === 'live'
  const minimumText = overlay
    ? props.syncFailed
      ? 'Mínimo indisponível'
      : 'Atualizando…'
    : room.minimum_next_bid_cents === null
      ? 'Sem valor possível'
      : formatCents(room.minimum_next_bid_cents)

  return (
    <section className="bid-panel" aria-labelledby="bid-panel-title">
      <h2 id="bid-panel-title">Sala do lote</h2>

      {room.phase === 'scheduled' && (
        <p className="room-phase-note">Os lances abrem em {formatDateTime(props.startsAt)}</p>
      )}
      {room.phase === 'ended' && (
        <p className="room-phase-note">Encerrado, apurando resultado</p>
      )}
      {live && <CountdownTimer anchor={props.anchor} onZero={props.onZero} />}
      {live && props.zeroConfirming && (
        <p role="status" className="muted">
          Confirmando encerramento com o servidor…
        </p>
      )}
      {live && props.zeroFailed && (
        <p role="alert" className="bid-notice bid-notice-uncertain">
          Não foi possível confirmar o encerramento com o servidor. Use Atualizar sala.
        </p>
      )}

      <dl className="bid-figures">
        <div>
          <dt>{room.current_bid_cents === null ? 'Lance inicial' : 'Lance atual'}</dt>
          <dd className="bid-current">
            {formatCents(room.current_bid_cents ?? props.startingBidCents)}
          </dd>
          {room.current_bid_cents === null && <dd className="muted">Sem lances ainda</dd>}
        </div>
        {room.phase !== 'ended' && (
          <div>
            <dt>Próximo lance mínimo</dt>
            <dd className="bid-minimum">{minimumText}</dd>
          </div>
        )}
      </dl>

      {viewer === 'bidder' && props.position === 'winning' && (
        <p className="bid-position bid-position-winning">{POSITION_TEXT.winning}</p>
      )}
      {viewer === 'bidder' && props.position === 'outbid' && (
        <p className="bid-position bid-position-outbid">{POSITION_TEXT.outbid}</p>
      )}
      {viewer === 'bidder' && props.participationUnavailable && (
        <p className="muted">Não foi possível carregar sua participação.</p>
      )}
      {viewer === 'bidder' && props.ownAlias !== null && (
        <p className="muted bid-own-alias">
          Seu pseudônimo neste lote: <strong>{props.ownAlias}</strong>
        </p>
      )}
      {viewer === 'bidder' && room.phase === 'ended' && props.lastOwnBidCents !== null && (
        <p className="bid-last-own">
          Seu último lance: <strong>{formatCents(props.lastOwnBidCents)}</strong>
        </p>
      )}

      {viewer === 'bidder' && (
        <div className="bid-wallet">
          {props.wallet.status === 'ready' && (
            <p>
              Saldo disponível:{' '}
              <strong>{formatCents(props.wallet.data.available_balance_cents)}</strong>
            </p>
          )}
          {props.wallet.status === 'failed' && (
            <p className="muted">Não foi possível carregar a carteira.</p>
          )}
        </div>
      )}

      {viewer === 'checking' && (
        <p role="status" className="muted">
          Verificando sua sessão…
        </p>
      )}
      {viewer === 'visitor' && live && (
        <AppLink
          to="/login"
          state={{ returnTo: `/lots/${props.lotId}` }}
          className="button button-primary"
        >
          Entrar para dar lance
        </AppLink>
      )}
      {viewer === 'auctioneer' && (
        <p className="muted">
          Sua conta é de leiloeiro: você acompanha o lote, mas não dá lances.
        </p>
      )}
      {viewer === 'bidder' && live && (
        <BidForm
          amountText={props.amountText}
          fieldError={props.fieldError}
          submitting={props.submitting}
          minimumCents={overlay ? null : room.minimum_next_bid_cents}
          updating={overlay}
          inputRef={props.inputRef}
          onChange={props.onAmountChange}
          onSubmit={props.onSubmit}
        />
      )}

      {/* Região sempre montada: o leitor de tela anuncia a mudança de conteúdo. */}
      <div className="bid-notices">
        <p role="status" className={`bid-notice bid-notice-${props.notice?.kind ?? 'none'}`}>
          {props.notice !== null && props.notice.kind !== 'error' && (
            <>
              <span aria-hidden="true">{props.notice.kind === 'success' ? '✓ ' : '! '}</span>
              {props.notice.text}
            </>
          )}
          {props.submitting && 'Enviando lance…'}
        </p>
        {props.notice !== null && props.notice.kind === 'error' && (
          <p role="alert" className="bid-notice bid-notice-error">
            <span aria-hidden="true">✕ </span>
            {props.notice.text}{' '}
            {props.notice.walletLink && (
              <AppLink to="/bidder/wallet">Ir para a carteira</AppLink>
            )}
          </p>
        )}
        {props.acceptedSyncFailed && (
          <p role="alert" className="bid-notice bid-notice-uncertain">
            Lance aceito, mas não foi possível atualizar a sala.
          </p>
        )}
      </div>

      <div className="room-refresh">
        <p className="as-of muted">Situação atualizada às {formatClock(room.as_of)}</p>
        <p className="muted">A sala não se atualiza sozinha; use Atualizar.</p>
        <button
          type="button"
          className="button button-secondary"
          onClick={props.onRefresh}
          disabled={props.submitting}
          aria-busy={props.refreshing}
        >
          {props.refreshing ? 'Atualizando…' : 'Atualizar sala'}
        </button>
      </div>
    </section>
  )
}

export default LotBidPanel
