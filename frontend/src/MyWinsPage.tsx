import { useEffect, useRef, useState } from 'react'
import { fetchWins, type MyWin, type WinsResult } from './api/wins'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'

function stateText(item: MyWin): string {
  if (item.phase === 'cancelled') return 'Cancelado'
  if (item.phase === 'scheduled') return 'Agendado'
  if (item.phase === 'live') return 'Ao vivo'
  return item.settlement_status === 'pending' ? 'Encerrado, apurando resultado' : 'Encerrado'
}
function WinItem({ item }: { item: MyWin }) {
  const [copied, setCopied] = useState(false)
  const [failed, setFailed] = useState(false)
  const receiptPath = `/lots/${item.lot_id}/receipt`
  const absoluteUrl = new URL(receiptPath, window.location.origin).href
  async function copy() {
    setCopied(false)
    setFailed(false)
    try {
      await navigator.clipboard.writeText(absoluteUrl)
      setCopied(true)
    } catch { setFailed(true) }
  }
  return <li className="my-win">
    <ArtworkImage key={item.image_url} src={item.image_url} alt={item.title ?? 'Obra sem título'} variant="thumb" />
    <div className="my-win-details">
      <h2>{item.title ?? 'Obra sem título'}</h2>
      <p className="muted">{item.artist_display ?? 'Artista não informado'}</p>
      <p>{stateText(item)}{item.result === 'won' ? ' · Você arrematou' : item.result === 'not_won' ? ' · Não arrematado' : ''}</p>
      <p className="muted">{item.bid_count} {item.bid_count === 1 ? 'lance' : 'lances'}</p>
      {item.result === 'won' && <p>{formatCents(item.final_amount_cents!)} · {formatDateTime(item.settled_at!)} · {item.winner_alias}</p>}
      <div className="my-win-actions">
        <AppLink to={`/lots/${item.lot_id}`}>Abrir sala</AppLink>
        <AppLink to={`/lots/${item.lot_id}/audit`}>Auditoria</AppLink>
        {item.result === 'won' && <>
          <AppLink to={receiptPath}>Comprovante</AppLink>
          <button type="button" className="button button-secondary" onClick={copy}>Copiar link</button>
        </>}
      </div>
      <p role="status">{copied ? 'Link copiado.' : ''}</p>
      {failed && <div><p role="alert">Não foi possível copiar. Selecione e copie o link abaixo.</p>
        <input aria-label="Link do comprovante" readOnly value={absoluteUrl} onFocus={event => event.currentTarget.select()} />
      </div>}
    </div>
  </li>
}
export default function MyWinsPage({ focusHeading, onSessionExpired }: { focusHeading: boolean; onSessionExpired: () => void }) {
  const [read, setRead] = useState<WinsResult | null>(null)
  const [attempt, setAttempt] = useState(0)
  const heading = useRef<HTMLHeadingElement>(null)
  const expired = useRef(onSessionExpired)
  useEffect(() => { expired.current = onSessionExpired }, [onSessionExpired])
  useEffect(() => { if (focusHeading) heading.current?.focus() }, [focusHeading])
  useEffect(() => {
    const controller = new AbortController()
    fetchWins(controller.signal).then(result => {
      if (controller.signal.aborted) return
      if (!result.ok && result.failure === 'unauthorized') expired.current()
      else setRead(result)
    })
    return () => controller.abort()
  }, [attempt])
  return <section className="my-wins" aria-labelledby="wins-title">
    <h1 id="wins-title" tabIndex={-1} ref={heading}>Meus arremates</h1>
    <p className="muted">Acompanhe suas participações e os lotes que você arrematou.</p>
    {read === null && <p role="status">Carregando arremates…</p>}
    {read !== null && !read.ok && <div>
      <p role="alert">{read.failure === 'integrity' ? 'Não foi possível conferir os resultados por uma inconsistência no lote.' : read.failure === 'forbidden' ? 'Esta área é só para a conta de licitante.' : 'Não foi possível carregar seus arremates.'}</p>
      {read.failure !== 'forbidden' && <button className="button button-secondary" onClick={() => { setRead(null); setAttempt(value => value + 1) }}>Tentar novamente</button>}
    </div>}
    {read?.ok && (read.data.items.length === 0 ? <p>Você ainda não participou de nenhum lote. <AppLink to="/">Explorar a vitrine</AppLink></p> : <ul className="my-wins-list">{read.data.items.map(item => <WinItem key={item.lot_id} item={item} />)}</ul>)}
  </section>
}
