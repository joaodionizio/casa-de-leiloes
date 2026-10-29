import { useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { register, registrationErrors, registrationFailureMessage, type RegistrationErrors, type UserRole } from './api/auth'

import { confirmationError, PASSWORD_RULE, passwordStrength } from './passwordStrength'

interface FormErrors extends RegistrationErrors { confirmation?: string }

interface RegisterFormProps {
  onRegistered: () => void
  children: (submitting: boolean) => ReactNode
}

function RegisterForm({ onRegistered, children }: RegisterFormProps) {
  const [role, setRole] = useState<UserRole | ''>('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const strength = passwordStrength(password)
  const valid = Object.keys(registrationErrors(email, password, role)).length === 0 && !confirmationError(password, confirmation)
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [errors, setErrors] = useState<FormErrors>({})
  const [error, setError] = useState<string | null>(null)
  const inFlight = useRef(false)
  const mounted = useRef(false)
  const focusTarget = useRef<keyof FormErrors | 'summary' | null>(null)
  const roleRef = useRef<HTMLInputElement>(null)
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const confirmationRef = useRef<HTMLInputElement>(null)
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
    if (target === 'confirmation') confirmationRef.current?.focus()
    if (target === 'summary') summaryRef.current?.focus()
    focusTarget.current = null
  }, [error, errors, submitting])

  function showErrors(nextErrors: FormErrors, message: string) {
    focusTarget.current = nextErrors.role ? 'role' : nextErrors.email ? 'email' : nextErrors.password ? 'password' : nextErrors.confirmation ? 'confirmation' : 'summary'
    setErrors(nextErrors)
    setError(message)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    const nextErrors: FormErrors = { ...registrationErrors(email, password, role), confirmation: confirmationError(password, confirmation) }
    if (!nextErrors.confirmation) delete nextErrors.confirmation
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
      setConfirmation('')
      onRegistered()
      return
    }
    inFlight.current = false
    setSubmitting(false)
    const fieldErrors: RegistrationErrors = {}
    if (result.fields.includes('role')) fieldErrors.role = 'Escolha como você quer participar.'
    if (result.fields.includes('email')) fieldErrors.email = result.failure === 'email_already_registered' ? 'Este e-mail já está cadastrado.' : 'Confira o e-mail informado.'
    if (result.fields.includes('password')) fieldErrors.password = PASSWORD_RULE
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
        <input ref={passwordRef} id="register-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" value={password} onChange={event => {
          const value = event.target.value
          setPassword(value)
          setErrors(current => ({
            ...current,
            password: passwordStrength(value).valid ? undefined : current.password,
            confirmation: confirmation !== '' || current.confirmation
              ? confirmationError(value, confirmation) : undefined,
          }))
        }} readOnly={submitting} aria-invalid={Boolean(errors.password)} aria-describedby={`register-password-hint${errors.password ? ' register-password-error' : ''}`} />
        <div className="register-password-tools">
          <span id="register-password-hint" className="field-hint">{PASSWORD_RULE}</span>
          <button type="button" className="password-toggle" disabled={submitting} aria-controls="register-password register-confirmation" aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Ocultar senhas' : 'Mostrar senhas'}</button>
        </div>
        <div className="password-requirements">
          <p>{strength.length >= 8 && strength.length <= 1024 ? '✓' : '○'} Comprimento: {strength.length} caracteres (8–1024).</p>
          <p>{strength.groupCount >= 3 ? '✓' : '○'} Grupos atendidos: {strength.groupCount} de 4; mínimo de 3.</p>
          <p>{strength.groups.map(group => `${group.met ? '✓' : '○'} ${group.label}`).join(' · ')}</p>
        </div>
        {errors.password && <p id="register-password-error" className="form-error">{errors.password}</p>}
      </div>
      <div className="field">
        <label htmlFor="register-confirmation">Confirmar senha</label>
        <input ref={confirmationRef} id="register-confirmation" name="password-confirmation" type={showPassword ? 'text' : 'password'} autoComplete="new-password" value={confirmation} onChange={event => {
          const value = event.target.value
          setConfirmation(value)
          setErrors(current => ({ ...current, confirmation: current.confirmation
            ? confirmationError(password, value) : undefined }))
        }} onBlur={() => setErrors(current => ({ ...current, confirmation: confirmationError(password, confirmation) }))} readOnly={submitting} aria-invalid={Boolean(errors.confirmation)} aria-describedby={errors.confirmation ? 'register-confirmation-error' : undefined} />
        {errors.confirmation && <p id="register-confirmation-error" className="form-error">{errors.confirmation}</p>}
      </div>
      {error !== null && <p ref={summaryRef} id="register-error" className="form-error" role="alert" tabIndex={-1}>{error}</p>}
      <button className="button button-primary" type="submit" disabled={submitting || !valid}>{submitting ? 'Criando conta…' : 'Criar conta'}</button>
      {children(submitting)}
    </form>
  )
}

export default RegisterForm
