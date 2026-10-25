import type { RefObject } from 'react'
import ArtworkImage from './ArtworkImage'
import { catalogFailureMessage } from './api/catalog'
import type { ArtworkDetail, CatalogFailure } from './api/catalog'

export type DetailState =
  | { status: 'none' }
  | { status: 'loading' }
  | { status: 'ready'; artwork: ArtworkDetail }
  | { status: 'failed'; failure: CatalogFailure }

interface ArtworkDetailPanelProps {
  state: DetailState
  headingRef: RefObject<HTMLHeadingElement | null>
  onRetry: () => void
  onBack: () => void
  // Abre o formulário de lote com esta obra (Story 2.4); só no estado pronto.
  onCreateLot?: (artwork: ArtworkDetail) => void
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value ?? <span className="muted">Não informado</span>}</dd>
    </>
  )
}

function ArtworkDetailPanel({
  state,
  headingRef,
  onRetry,
  onBack,
  onCreateLot,
}: ArtworkDetailPanelProps) {
  const artwork = state.status === 'ready' ? state.artwork : null
  const title = artwork !== null ? (artwork.title ?? 'Sem título') : 'Detalhe da obra'

  return (
    <section className="artwork-panel" aria-labelledby="artwork-title">
      <button type="button" className="button button-secondary back-button" onClick={onBack}>
        ← Voltar aos resultados
      </button>

      {state.status === 'none' && (
        <p className="muted artwork-panel-hint">
          Selecione uma obra para ver o detalhe.
        </p>
      )}

      {/* A imagem vem antes do título (DESIGN §5). Os filhos têm posição fixa, então
          o `h2` não é remontado entre carregando, pronto e falha: o foco não se perde. */}
      {state.status === 'loading' && (
        <span className="artwork-image artwork-image-large artwork-image-reserved" />
      )}
      {artwork !== null && (
        <ArtworkImage
          key={artwork.image_url}
          src={artwork.image_url}
          alt={artwork.title ?? 'Obra sem título'}
          variant="large"
        />
      )}

      <h2
        id="artwork-title"
        ref={headingRef}
        tabIndex={-1}
        className={
          artwork !== null
            ? 'artwork-title'
            : state.status === 'none'
              ? 'visually-hidden'
              : 'artwork-title artwork-title-quiet'
        }
        title={artwork?.title ?? undefined}
      >
        {title}
      </h2>

      {state.status === 'loading' && (
        <p role="status" className="muted">
          Carregando obra…
        </p>
      )}

      {state.status === 'failed' && (
        <div className="artwork-failure">
          <p role="alert" className="form-error">
            {catalogFailureMessage(state.failure)}
          </p>
          {state.failure !== 'not_found' && (
            <button
              type="button"
              className="button button-secondary"
              onClick={onRetry}
            >
              Tentar novamente
            </button>
          )}
        </div>
      )}

      {artwork !== null && (
        <>
          {artwork.artist_display !== null && (
            <p className="artwork-artist">{artwork.artist_display}</p>
          )}
          <p className="artwork-public-domain">
            <span aria-hidden="true">✓ </span>Domínio público
          </p>
          {onCreateLot !== undefined && (
            <button
              type="button"
              className="button button-primary"
              onClick={() => onCreateLot(artwork)}
            >
              Criar lote com esta obra
            </button>
          )}
          <dl className="artwork-facts">
            <Field label="Data" value={artwork.date_display} />
            <Field label="Técnica" value={artwork.medium_display} />
            <Field label="Dimensões" value={artwork.dimensions} />
            <Field label="Departamento" value={artwork.department_title} />
            <Field label="Tipo" value={artwork.artwork_type_title} />
            <Field label="Crédito" value={artwork.credit_line} />
            <Field label="Nº no acervo" value={String(artwork.external_id)} />
          </dl>
          <p>
            <a
              className="source-link"
              href={artwork.source_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Ver no site do Art Institute of Chicago
              <span className="visually-hidden"> (abre em nova aba)</span>
            </a>
          </p>
        </>
      )}
    </section>
  )
}

export default ArtworkDetailPanel
