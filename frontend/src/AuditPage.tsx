import { useEffect, useRef, useState } from 'react'
import { fetchAudit, type AuditResult } from './api/audit'
import AppLink from './AppLink'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'

export default function AuditPage({ lotId, navigated }: { lotId: string; navigated: boolean }) {
  const [result, setResult] = useState<AuditResult | null>(null)
  const [attempt, setAttempt] = useState(0)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    fetchAudit(lotId, controller.signal).then(value => {
      if (!controller.signal.aborted) setResult(value)
    })
    return () => controller.abort()
  }, [lotId, attempt])
  useEffect(() => { if (navigated) heading.current?.focus() }, [navigated])
  const data = result?.ok ? result.data : null
  const phases = { scheduled: 'Agendado', live: 'Ao vivo', ended: 'Encerrado', cancelled: 'Cancelado' }
  return <article className="audit-page" aria-labelledby="audit-title">
    <AppLink to={`/lots/${lotId}`} className="back-link">← Sala do lote</AppLink>
    <h1 id="audit-title" ref={heading} tabIndex={-1}>Auditoria pública do lote</h1>
    <p className="audit-lot-id">Lote {lotId}</p>
    {result === null && <p role="status">Carregando auditoria…</p>}
    {result && !result.ok && (result.failure === 'not_found'
      ? <p role="status">Lote não encontrado.</p>
      : <div role="alert"><p>Não foi possível carregar a auditoria.</p><button className="button button-secondary" onClick={() => { setResult(null); setAttempt(value => value + 1) }}>Tentar novamente</button></div>)}
    {data && <>
      <p className="muted">Consulta em <time dateTime={data.as_of}>{formatDateTime(data.as_of)}</time></p>
      <h2>{data.integrity === 'verified' ? 'Integridade verificada' : 'Integridade adulterada'}</h2>
      {data.integrity === 'adulterated'
        ? <p role="alert">Foram encontradas inconsistências. O estado, o resultado e o histórico foram retidos porque os dados não são confiáveis.</p>
        : <>
          <p className="audit-state">{data.phase && phases[data.phase]}{data.phase === 'ended' && data.settlement_status === 'pending' ? ', apurando resultado' : ''}</p>
          {data.phase === 'cancelled' && <p>Lote cancelado, sem apuração de resultado.</p>}
          {data.settlement?.outcome === 'sold' && <p>Arrematado por {data.settlement.winner_alias} por {formatCents(data.settlement.final_amount_cents!)}.</p>}
          {data.settlement?.outcome === 'unsold' && <p>Encerrado sem vencedor.</p>}
          <p>{data.bid_count} {data.bid_count === 1 ? 'lance registrado' : 'lances registrados'}.</p>
          <h2>Histórico completo</h2>
          {data.bids.length === 0 ? <p>Nenhum lance registrado.</p> : <ol className="audit-events">
            {data.bids.map(bid => <li key={bid.sequence}>
              <div className="audit-event-summary"><strong>Lance {bid.sequence}</strong><span>{bid.bidder_alias}</span><strong>{formatCents(bid.amount_cents)}</strong></div>
              <time dateTime={bid.placed_at}>{formatDateTime(bid.placed_at)}</time>
              <details><summary>Detalhes técnicos do lance {bid.sequence}</summary>
                <dl><dt>Versão canônica</dt><dd>{bid.canonical_version}</dd><dt>Timestamp canônico (UTC)</dt><dd>{bid.placed_at}</dd><dt>Hash anterior</dt><dd><code>{bid.previous_hash}</code></dd><dt>Hash atual</dt><dd><code>{bid.current_hash}</code></dd></dl>
              </details>
            </li>)}
          </ol>}
          <details className="audit-method"><summary>Como a integridade é verificada</summary>
            <p>A representação canônica v1 usa JSON UTF-8, com chaves ordenadas e sem espaços: amount_cents, bidder_alias, lot_id, previous_hash, sequence, timestamp e v. placed_at é o timestamp canônico em UTC, com seis casas decimais e Z; canonical_version corresponde a v.</p>
            <p>Cada hash é o SHA-256 dos bytes desse JSON. O hash anterior do primeiro lance contém 64 zeros. Os pseudônimos são os persistidos em cada lance.</p>
            <p>O servidor também valida a âncora HMAC, a quantidade, o hash final e os vínculos com o resultado e o comprovante persistidos. HMAC é uma validação interna do servidor, não uma prova pública independente.</p>
            <p>Hash final: <code>{data.final_hash}</code></p>
          </details>
        </>}
    </>}
  </article>
}
