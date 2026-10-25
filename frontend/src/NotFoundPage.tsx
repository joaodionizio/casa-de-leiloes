import { useEffect, useRef } from 'react'
import AppLink from './AppLink'
import { PRODUCT_NAME } from './brand'

interface NotFoundPageProps {
  focusHeading: boolean
}

// Rota do front desconhecida (soft 404 consciente: o servidor devolve a SPA e a tela
// avisa). Não chama a API.
function NotFoundPage({ focusHeading }: NotFoundPageProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (focusHeading) headingRef.current?.focus()
  }, [focusHeading])

  return (
    <section className="notice-page" aria-labelledby="not-found-title">
      <h1 id="not-found-title" ref={headingRef} tabIndex={-1}>
        Página não encontrada
      </h1>
      <p>O endereço não corresponde a nenhuma página do {PRODUCT_NAME}.</p>
      <AppLink to="/" className="button button-secondary">
        Ir para a vitrine
      </AppLink>
    </section>
  )
}

export default NotFoundPage
