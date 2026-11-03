import type { RefObject } from 'react'
import AppLink from './AppLink'

interface LotPageFallbackProps {
  status: 'cancelled' | 'loading' | 'not_found' | 'failed'
  lotId: string
  headingRef: RefObject<HTMLHeadingElement | null>
  onRetry: () => void
}

// Display-only states. The room controller owns requests and navigation.
export default function LotPageFallback({ status, lotId, headingRef, onRetry }: LotPageFallbackProps) {
  if (status === 'cancelled') {
    return <section className="notice-page" aria-labelledby="lot-title">
      <h1 id="lot-title" ref={headingRef} tabIndex={-1}>Este lote foi cancelado</h1>
      <p><AppLink to={`/lots/${lotId}/audit`}>Consultar auditoria pública</AppLink></p>
      <AppLink to="/" className="button button-secondary">Ir para a vitrine</AppLink>
    </section>
  }

  if (status === 'loading') {
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

  if (status === 'not_found') {
    return (
      <section className="notice-page" aria-labelledby="lot-title">
        <h1 id="lot-title" ref={headingRef} tabIndex={-1}>
          Lote indisponível ou não encontrado
        </h1>
        <p>O lote pode ter sido removido ou o endereço está incompleto.</p>
        <p><AppLink to={`/lots/${lotId}/audit`}>Consultar auditoria pública</AppLink></p>
        <AppLink to="/" className="button button-secondary">
          Ir para a vitrine
        </AppLink>
      </section>
    )
  }

  if (status === 'failed') {
    return (
      <section className="notice-page" aria-labelledby="lot-title">
        <h1 id="lot-title" ref={headingRef} tabIndex={-1}>
          Não foi possível carregar o lote
        </h1>
        <p role="alert" className="form-error">
          O servidor não respondeu como esperado. Tente novamente em instantes.
        </p>
        <div className="notice-actions">
          <button type="button" className="button button-secondary" onClick={onRetry}>
            Tentar novamente
          </button>
          <AppLink to="/" className="button button-secondary">
            Ir para a vitrine
          </AppLink>
        </div>
      </section>
    )
  }
}
