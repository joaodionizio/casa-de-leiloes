import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { failureMessage, login, type CurrentUser } from './api/auth'

// Contas públicas documentadas no README; não são credenciais privadas.
const DEMO_ACCOUNTS = [
  { label: 'Leiloeiro', email: 'auctioneer@example.com' },
  { label: 'Licitante 1', email: 'bidder1@example.com' },
  { label: 'Licitante 2', email: 'bidder2@example.com' },
]

interface LoginFormProps {
  initialError: string | null
  focusEmail: boolean
  onLoggedIn: (user: CurrentUser) => void
}

function LoginForm({ initialError, focusEmail, onLoggedIn }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const inFlight = useRef(false)
  const [activeDemo, setActiveDemo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(initialError)
  // Só validação e credenciais inválidas marcam os campos como inválidos; erro de
  // servidor ou recusa não dizem nada sobre o que foi digitado.
  const [fieldsInvalid, setFieldsInvalid] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const demoRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    if (focusEmail) emailRef.current?.focus()
  }, [focusEmail])

  useEffect(() => {
    if (error !== null && !submitting) demoRef.current?.focus()
  }, [error, submitting])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    demoRef.current = null

    const trimmedEmail = email.trim()
    if (trimmedEmail === '' || password === '') {
      setError(failureMessage('validation'))
      setFieldsInvalid(true)
      if (trimmedEmail === '') emailRef.current?.focus()
      else passwordRef.current?.focus()
      return
    }

    void submitLogin(trimmedEmail, password, null)
  }

  async function submitLogin(loginEmail: string, loginPassword: string, demo: string | null) {
    if (inFlight.current) return
    inFlight.current = true
    setActiveDemo(demo)
    setSubmitting(true)
    setError(null)
    setFieldsInvalid(false)
    const result = await login(loginEmail, loginPassword)
    if (result.ok) {
      setPassword('')
      onLoggedIn(result.user)
      return
    }
    inFlight.current = false
    setSubmitting(false)
    setActiveDemo(null)
    setPassword('')
    setError(failureMessage(result.failure))
    setFieldsInvalid(
      demo === null && (result.failure === 'invalid_credentials' || result.failure === 'validation'),
    )
    if (demo === null) passwordRef.current?.focus()
  }

  return (
    <form className="login-form" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor="login-email">E-mail</label>
        <input
          id="login-email"
          ref={emailRef}
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          readOnly={submitting}
          aria-invalid={fieldsInvalid}
          aria-describedby={error !== null ? 'login-error' : undefined}
        />
      </div>
      <div className="field">
        <label htmlFor="login-password">Senha</label>
        <input
          id="login-password"
          ref={passwordRef}
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          readOnly={submitting}
          aria-invalid={fieldsInvalid}
          aria-describedby={error !== null ? 'login-error' : undefined}
        />
      </div>
      {error !== null && (
        <p id="login-error" className="form-error" role="alert">
          {error}
        </p>
      )}
      <button
        type="submit"
        className="button button-primary"
        disabled={submitting}
      >
        {submitting && activeDemo === null ? 'Entrando…' : 'Entrar'}
      </button>
      <fieldset className="login-demo" disabled={submitting}>
        <legend>Contas públicas de demonstração</legend>
        <div className="login-demo-actions">
          {DEMO_ACCOUNTS.map(account => (
            <button key={account.email} type="button" className="button button-secondary"
              onClick={(event) => {
                demoRef.current = event.currentTarget
                void submitLogin(account.email, 'Demo123!', account.email)
              }}>
              {activeDemo === account.email ? 'Entrando…' : `Entrar como ${account.label}`}
            </button>
          ))}
        </div>
      </fieldset>
    </form>
  )
}

export default LoginForm
