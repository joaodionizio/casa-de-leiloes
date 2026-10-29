import { useEffect, useRef } from 'react'
import AppLink from './AppLink'
import RegisterForm from './RegisterForm'
import type { NavState } from './route'

interface RegisterPageProps {
  focusHeading: boolean
  authState: NavState
  onRegistered: () => void
}

function RegisterPage({ focusHeading, authState, onRegistered }: RegisterPageProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    if (focusHeading) headingRef.current?.focus()
  }, [focusHeading])

  return (
    <section className="register-section main-column" aria-labelledby="register-title">
      <p className="register-eyebrow">Nova conta</p>
      <h1 id="register-title" ref={headingRef} tabIndex={-1}>Cadastro</h1>
      <RegisterForm onRegistered={onRegistered}>
        {(submitting) => <p className="auth-switch">Já tem conta? <AppLink to="/login" state={authState} aria-disabled={submitting || undefined} onClick={event => { if (submitting) event.preventDefault() }}>Entrar</AppLink></p>}
      </RegisterForm>
    </section>
  )
}

export default RegisterPage
