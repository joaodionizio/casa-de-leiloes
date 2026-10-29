import { useEffect, useRef } from 'react'
import type { CurrentUser } from './api/auth'
import LoginForm from './LoginForm'
import AppLink from './AppLink'
import type { NavState } from './route'

interface LoginPageProps {
  focusHeading: boolean
  initialError: string | null
  registered: boolean
  authState: NavState
  onLoggedIn: (user: CurrentUser) => void
}

// Tela de login (CAP-8): só aparece pelo botão "Entrar" ou por `/login`. O destino
// depois do login é decidido pelo `App` (`returnTo` validado).
function LoginPage({ focusHeading, initialError, registered, authState, onLoggedIn }: LoginPageProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (focusHeading) headingRef.current?.focus()
  }, [focusHeading])

  return (
    <section aria-labelledby="login-title" className="login-section main-column">
      <h1 id="login-title" ref={headingRef} tabIndex={-1}>
        Entrar
      </h1>
      {registered && <p className="registration-confirmation" role="status">Conta criada com sucesso. Entre para continuar.</p>}
      <LoginForm
        initialError={initialError}
        focusEmail={false}
        onLoggedIn={onLoggedIn}
      />
      <p className="auth-switch">Não tem conta? <AppLink to="/register" state={authState}>Criar conta</AppLink></p>
    </section>
  )
}

export default LoginPage
