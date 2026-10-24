import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { failureMessage, login, type CurrentUser } from './api/auth'

interface LoginFormProps {
  initialError: string | null
  focusEmail: boolean
  onLoggedIn: (user: CurrentUser) => void
}

function LoginForm({ initialError, focusEmail, onLoggedIn }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(initialError)
  // Só validação e credenciais inválidas marcam os campos como inválidos; erro de
  // servidor ou recusa não dizem nada sobre o que foi digitado.
  const [fieldsInvalid, setFieldsInvalid] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (focusEmail) emailRef.current?.focus()
  }, [focusEmail])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return

    const trimmedEmail = email.trim()
    if (trimmedEmail === '' || password === '') {
      setError(failureMessage('validation'))
      setFieldsInvalid(true)
      if (trimmedEmail === '') emailRef.current?.focus()
      else passwordRef.current?.focus()
      return
    }

    setSubmitting(true)
    setError(null)
    setFieldsInvalid(false)
    const result = await login(trimmedEmail, password)
    if (result.ok) {
      setPassword('')
      onLoggedIn(result.user)
      return
    }
    setSubmitting(false)
    setPassword('')
    setError(failureMessage(result.failure))
    setFieldsInvalid(
      result.failure === 'invalid_credentials' || result.failure === 'validation',
    )
    passwordRef.current?.focus()
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
        {submitting ? 'Entrando…' : 'Entrar'}
      </button>
    </form>
  )
}

export default LoginForm
