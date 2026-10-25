import { useEffect, useRef, useState } from 'react'
import type { ArtworkDetail } from './api/catalog'
import { createLot } from './api/lots'
import type { CreateLotFailure, CreateLotRequest, FieldProblem, LotResponse } from './api/lots'
import LotArtwork from './LotArtwork'
import { formatDateTime } from './lotTime'
import { formatCents } from './money'

interface LotReviewProps {
  artwork: ArtworkDetail
  request: CreateLotRequest
  onCreated: (lot: LotResponse) => void
  onEdit: () => void
  // Erros de campo do servidor: volta ao formulário com o rascunho mantido.
  onFieldProblems: (problems: FieldProblem[]) => void
  onBackToCatalog: () => void
  onShowMyLots: () => void
  onSessionExpired: () => void
}

// Mensagens de `frontend-lot-creation.md` §7.3, escolhidas pelo tipo da falha.
function failureMessage(failure: CreateLotFailure): string {
  if (failure.kind === 'not_eligible') {
    return 'Esta obra não pode virar lote: só obras de domínio público com imagem no acervo do museu.'
  }
  if (failure.kind === 'unavailable') {
    return 'O catálogo do museu não respondeu e o lote não foi criado. Seus dados foram mantidos; tente novamente em instantes.'
  }
  if (failure.kind === 'forbidden') return 'Sua conta não pode criar lotes.'
  if (failure.kind === 'validation') {
    return 'Não foi possível criar o lote com esses dados. Revise e tente de novo.'
  }
  // Rede, 5xx, corpo ilegível: o servidor pode ter criado o lote antes de a resposta
  // se perder, e não há chave de idempotência (P7).
  return 'Não foi possível confirmar se o lote foi criado. Confira em Meus lotes antes de tentar de novo.'
}

function LotReview({
  artwork,
  request,
  onCreated,
  onEdit,
  onFieldProblems,
  onBackToCatalog,
  onShowMyLots,
  onSessionExpired,
}: LotReviewProps) {
  const [submitting, setSubmitting] = useState(false)
  const [failure, setFailure] = useState<CreateLotFailure | null>(null)
  // O estado só atualiza depois da renderização; a referência barra o segundo clique
  // (ou Enter) que chega antes disso.
  const pending = useRef(false)
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  async function handlePublish() {
    if (pending.current) return
    pending.current = true
    setSubmitting(true)
    setFailure(null)
    const result = await createLot(request)
    pending.current = false
    setSubmitting(false)
    if (result.ok) {
      onCreated(result.lot)
      return
    }
    const problem = result.failure
    if (problem.kind === 'unauthorized') {
      onSessionExpired()
      return
    }
    if (
      problem.kind === 'validation' &&
      problem.problems.some((item) => item.field !== null)
    ) {
      onFieldProblems(problem.problems)
      return
    }
    setFailure(problem)
  }

  const startsNow = request.starts_at === null

  return (
    <section className="lot-step" aria-labelledby="lot-review-title" aria-busy={submitting}>
      <h2 id="lot-review-title" ref={headingRef} tabIndex={-1} className="lot-step-title">
        Revise o lote
      </h2>
      <div className="lot-layout">
        <div className="lot-layout-artwork">
          <LotArtwork artwork={artwork} size="compact" />
        </div>
        <div>
          <dl className="lot-terms">
            <div>
              <dt>Lance inicial</dt>
              <dd className="lot-money">{formatCents(request.starting_bid_cents)}</dd>
            </div>
            <div>
              <dt>Incremento mínimo</dt>
              <dd className="lot-money">{formatCents(request.min_increment_cents)}</dd>
            </div>
            <div>
              <dt>Início</dt>
              <dd>
                {request.starts_at === null
                  ? 'Assim que você publicar, pelo horário do servidor'
                  : formatDateTime(request.starts_at)}
              </dd>
            </div>
            <div>
              <dt>Término</dt>
              <dd>{formatDateTime(request.ends_at)}</dd>
            </div>
          </dl>
          <p className="muted">
            O servidor confere os horários no momento da publicação
            {startsNow ? ', inclusive o início.' : '.'}
          </p>

          {failure !== null && (
            <div className="lot-failure">
              <p role="alert" className="form-error">
                {failureMessage(failure)}
              </p>
              <div className="lot-actions">
                {failure.kind === 'not_eligible' ? (
                  <button
                    type="button"
                    className="button button-secondary"
                    onClick={onBackToCatalog}
                  >
                    Voltar à busca
                  </button>
                ) : null}
                {(failure.kind === 'unavailable' || failure.kind === 'unknown') && (
                  <button
                    type="button"
                    className="button button-secondary"
                    onClick={() => void handlePublish()}
                  >
                    Tentar novamente
                  </button>
                )}
                {failure.kind === 'unknown' && (
                  <button
                    type="button"
                    className="button button-secondary"
                    onClick={onShowMyLots}
                  >
                    Ver meus lotes
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="lot-actions">
            <button
              type="button"
              className="button button-primary"
              onClick={() => void handlePublish()}
              disabled={submitting}
            >
              {submitting ? 'Publicando…' : 'Publicar lote'}
            </button>
            <button
              type="button"
              className="button button-secondary"
              onClick={onEdit}
              disabled={submitting}
            >
              Editar
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

export default LotReview
