import { useEffect, useRef, useState } from 'react'
import { fetchReceipt, type ReceiptResult } from './api/receipt'
import AppLink from './AppLink'
import ArtworkImage from './ArtworkImage'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'

export default function ReceiptPage({ lotId, navigated }: { lotId: string; navigated: boolean }) {
  const [result, setResult] = useState<ReceiptResult | null>(null)
  const [attempt, setAttempt] = useState(0)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    fetchReceipt(lotId, controller.signal).then(value => { if (!controller.signal.aborted) setResult(value) })
    return () => controller.abort()
  }, [lotId, attempt])
  useEffect(() => { if (navigated) heading.current?.focus() }, [navigated])
  return <article className="receipt-page" aria-labelledby="receipt-title">
    <AppLink to={`/lots/${lotId}`} className="back-link">← Sala do lote</AppLink>
    <h1 id="receipt-title" ref={heading} tabIndex={-1}>Comprovante de arremate</h1>
    <p className="muted">Lote {lotId}</p>
    {result === null && <p role="status">Carregando comprovante…</p>}
    {result && !result.ok && (result.failure === 'not_found'
      ? <p role="status">Comprovante não encontrado.</p>
      : <div role="alert"><p>{result.failure === 'conflict' ? 'Não foi possível confirmar a integridade deste comprovante.' : 'Não foi possível carregar o comprovante.'}</p><button className="button button-secondary" onClick={() => { setResult(null); setAttempt(n => n + 1) }}>Tentar novamente</button></div>)}
    {result?.ok && <>
      <div className="receipt-art"><ArtworkImage src={result.data.image_url} alt={result.data.title ?? 'Obra sem título'} variant="large" /></div>
      <h2>{result.data.title ?? 'Obra sem título'}</h2>
      {result.data.artist_display && <p>{result.data.artist_display}</p>}
      <p className="receipt-status">Arrematado</p>
      <dl className="receipt-details">
        <dt>Vencedor</dt><dd>{result.data.winner_alias}</dd>
        <dt>Valor final</dt><dd>{formatCents(result.data.final_amount_cents)}</dd>
        <dt>Data do arremate</dt><dd><time dateTime={result.data.settled_at}>{formatDateTime(result.data.settled_at)}</time></dd>
        <dt>Lances</dt><dd>{result.data.bid_count}</dd>
        <dt>Lance vencedor</dt><dd>#{result.data.winning_bid_sequence}</dd>
        <dt>Hash final</dt><dd><code>{result.data.final_hash}</code></dd>
      </dl>
      <p><AppLink to={`/lots/${lotId}/audit`}>Consultar auditoria pública</AppLink></p>
    </>}
  </article>
}
