import { useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { register, registrationErrors, registrationFailureMessage, type RegistrationErrors, type RegistrationField, type UserRole } from './api/auth'

interface RegisterFormProps {
  onRegistered: () => void
  children: (submitting: boolean) => ReactNode
}

function RegisterForm({ onRegistered, children }: RegisterFormProps) {
  const [role, setRole] = useState<UserRole | ''>('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [errors, setErrors] = useState<RegistrationErrors>({})
  const [error, setError] = useState<string | null>(null)
  const inFlight = useRef(false)
  const mounted = useRef(false)
  const focusTarget = useRef<RegistrationField | 'summary' | null>(null)
  const roleRef = useRef<HTMLInputElement>(null)
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const summaryRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  useEffect(() => {
    if (submitting || error === null) return
    const target = focusTarget.current
    if (target === 'role') roleRef.current?.focus()
    if (target === 'email') emailRef.current?.focus()
    if (target === 'password') passwordRef.current?.focus()
    if (target === 'summary') summaryRef.current?.focus()
    focusTarget.current = null
  }, [error, errors, submitting])

  function showErrors(nextErrors: RegistrationErrors, message: string) {
    focusTarget.current = nextErrors.role ? 'role' : nextErrors.email ? 'email' : nextErrors.password ? 'password' : 'summary'
    setErrors(nextErrors)
    setError(message)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    const nextErrors = registrationErrors(email, password, role)
    if (Object.keys(nextErrors).length > 0 || role === '') {
      showErrors(nextErrors, 'Confira os campos indicados para criar sua conta.')
      return
    }
    inFlight.current = true
    setSubmitting(true)
    setError(null)
    setErrors({})
    const result = await register(email.trim(), password, role)
    // The server may have committed even after navigation. Only this mounted
    // instance may handle its response, including errors and success navigation.
    if (!mounted.current) return
    if (result.ok) {
      setPassword('')
      onRegistered()
      return
    }
    inFlight.current = false
    setSubmitting(false)
    const fieldErrors: RegistrationErrors = {}
    if (result.fields.includes('role')) fieldErrors.role = 'Escolha como você quer participar.'
    if (result.fields.includes('email')) fieldErrors.email = result.failure === 'email_already_registered' ? 'Este e-mail já está cadastrado.' : 'Confira o e-mail informado.'
    if (result.fields.includes('password')) fieldErrors.password = 'Use uma senha de 8 a 1024 caracteres.'
    showErrors(fieldErrors, registrationFailureMessage(result.failure))
  }

  return (
    <form className="register-form" onSubmit={event => { void handleSubmit(event) }} noValidate aria-busy={submitting}>
      <fieldset className="register-roles" disabled={submitting} aria-describedby={errors.role ? 'register-role-error' : undefined} aria-invalid={Boolean(errors.role)}>
        <legend>Como você quer participar?</legend>
        <label className="register-role">
          <input ref={roleRef} type="radio" name="role" value="BIDDER" checked={role === 'BIDDER'} onChange={() => setRole('BIDDER')} aria-invalid={Boolean(errors.role)} aria-describedby={errors.role ? 'register-role-error' : undefined} />
          <span><strong>Licitante</strong><span>Deposite saldo simulado, dê lances e arremate obras.</span></span>
        </label>
        <label className="register-role">
          <input type="radio" name="role" value="AUCTIONEER" checked={role === 'AUCTIONEER'} onChange={() => setRole('AUCTIONEER')} aria-invalid={Boolean(errors.role)} aria-describedby={errors.role ? 'register-role-error' : undefined} />
          <span><strong>Leiloeiro</strong><span>Crie e gerencie seus lotes de arte.</span></span>
        </label>
        {errors.role && <p id="register-role-error" className="form-error">{errors.role}</p>}
      </fieldset>
      <div className="field">
        <label htmlFor="register-email">E-mail</label>
        <input ref={emailRef} id="register-email" name="email" type="email" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} readOnly={submitting} aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? 'register-email-error' : undefined} />
        {errors.email && <p id="register-email-error" className="form-error">{errors.email}</p>}
      </div>
      <div className="field">
        <label htmlFor="register-password">Senha</label>
        <input ref={passwordRef} id="register-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} readOnly={submitting} aria-invalid={Boolean(errors.password)} aria-describedby={`register-password-hint${errors.password ? ' register-password-error' : ''}`} />
        <div className="register-password-tools">
          <span id="register-password-hint" className="field-hint">Use pelo menos 8 caracteres.</span>
          <button type="button" className="password-toggle" disabled={submitting} aria-controls="register-password" aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Ocultar senha' : 'Mostrar senha'}</button>
        </div>
        {errors.password && <p id="register-password-error" className="form-error">{errors.password}</p>}
      </div>
      {error !== null && <p ref={summaryRef} id="register-error" className="form-error" role="alert" tabIndex={-1}>{error}</p>}
      <button className="button button-primary" type="submit" disabled={submitting}>{submitting ? 'Criando conta…' : 'Criar conta'}</button>
      {children(submitting)}
    </form>
  )
}

export default RegisterForm
