import { useEffect, useRef } from 'react'
import type { CurrentUser } from './api/auth'
import LoginForm from './LoginForm'

interface LoginPageProps {
  focusHeading: boolean
  initialError: string | null
  onLoggedIn: (user: CurrentUser) => void
}

// Tela de login (CAP-8): só aparece pelo botão "Entrar" ou por `/login`. O destino
// depois do login é decidido pelo `App` (`returnTo` validado).
function LoginPage({ focusHeading, initialError, onLoggedIn }: LoginPageProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (focusHeading) headingRef.current?.focus()
  }, [focusHeading])

  return (
    <section aria-labelledby="login-title" className="login-section main-column">
      <h1 id="login-title" ref={headingRef} tabIndex={-1}>
        Entrar
      </h1>
      <LoginForm
        initialError={initialError}
        focusEmail={false}
        onLoggedIn={onLoggedIn}
      />
    </section>
  )
}

export default LoginPage
