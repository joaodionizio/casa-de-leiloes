import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { ArtworkDetail } from './api/catalog'
import type { CreateLotRequest, FieldProblem, LotField } from './api/lots'
import DateTimeField from './DateTimeField'
import LotArtwork from './LotArtwork'
import {
  checkDraft,
  firstErrorField,
  serverProblemMessages,
  type DraftErrors,
  type LotDraft,
  type StartMode,
} from './lotDraft'
import { browserTimeZone } from './lotTime'
import MoneyField from './MoneyField'

interface LotFormProps {
  artwork: ArtworkDetail
  draft: LotDraft
  // Erros que o servidor devolveu para campos deste formulário (volta da revisão).
  serverProblems: FieldProblem[]
  onReview: (draft: LotDraft, request: CreateLotRequest) => void
  onBack: () => void
}

function LotForm({ artwork, draft, serverProblems, onReview, onBack }: LotFormProps) {
  const [values, setValues] = useState<LotDraft>(draft)
  const [errors, setErrors] = useState<DraftErrors>(() =>
    serverProblemMessages(serverProblems, draft.startMode),
  )
  // Foco ao entrar: o título da etapa, ou o primeiro campo que o servidor recusou.
  const [initialFocus] = useState<LotField | null>(() =>
    firstErrorField(serverProblemMessages(serverProblems, draft.startMode)),
  )

  const headingRef = useRef<HTMLHeadingElement>(null)
  const startingRef = useRef<HTMLInputElement>(null)
  const incrementRef = useRef<HTMLInputElement>(null)
  const startsRef = useRef<HTMLInputElement>(null)
  const endsRef = useRef<HTMLInputElement>(null)

  function inputFor(field: LotField): HTMLInputElement | null {
    if (field === 'starting_bid_cents') return startingRef.current
    if (field === 'min_increment_cents') return incrementRef.current
    if (field === 'starts_at') return startsRef.current
    return endsRef.current
  }

  useEffect(() => {
    if (initialFocus === null) {
      headingRef.current?.focus()
      return
    }
    if (initialFocus === 'starting_bid_cents') startingRef.current?.focus()
    else if (initialFocus === 'min_increment_cents') incrementRef.current?.focus()
    else if (initialFocus === 'starts_at') startsRef.current?.focus()
    else endsRef.current?.focus()
  }, [initialFocus])

  function clearError(field: LotField) {
    if (errors[field] === undefined) return
    setErrors({ ...errors, [field]: undefined })
  }

  function handleStartMode(startMode: StartMode) {
    setValues({ ...values, startMode })
    setErrors({ ...errors, starts_at: undefined, ends_at: undefined })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    // "Revisar lote" é a confirmação do formulário: valida o valor ATUAL. O relógio do
    // navegador só evita ir à revisão com um horário que já passou; o servidor repete
    // a regra com a hora do banco.
    const check = checkDraft(artwork.external_id, values, new Date())
    if (!check.ok) {
      setErrors(check.errors)
      const first = firstErrorField(check.errors)
      if (first !== null) inputFor(first)?.focus()
      return
    }
    setErrors({})
    onReview(values, check.request)
  }

  const startsError = errors.starts_at
  const endsError = errors.ends_at

  return (
    <section className="lot-step" aria-labelledby="lot-form-title">
      <h2 id="lot-form-title" ref={headingRef} tabIndex={-1} className="lot-step-title">
        Criar lote
      </h2>
      <div className="lot-layout">
        <div className="lot-layout-artwork">
          <LotArtwork artwork={artwork} size="large" />
          <p className="muted lot-copy-note">
            Os dados da obra são copiados do acervo do museu no momento da publicação.
          </p>
        </div>

        <form className="lot-form" onSubmit={handleSubmit} noValidate>
          <fieldset className="lot-fieldset">
            <legend>Valores</legend>
            <MoneyField
              id="lot-starting-bid"
              label="Lance inicial"
              description="Valor mínimo aceito para o primeiro lance deste lote."
              value={values.startingBid}
              error={errors.starting_bid_cents}
              inputRef={startingRef}
              onChange={(startingBid) => {
                setValues({ ...values, startingBid })
                clearError('starting_bid_cents')
              }}
            />
            <MoneyField
              id="lot-min-increment"
              label="Incremento mínimo"
              description="Valor mínimo que cada novo lance deverá acrescentar ao lance atual."
              value={values.minIncrement}
              error={errors.min_increment_cents}
              inputRef={incrementRef}
              onChange={(minIncrement) => {
                setValues({ ...values, minIncrement })
                clearError('min_increment_cents')
              }}
            />
          </fieldset>

          <fieldset className="lot-fieldset">
            <legend>Período</legend>
            <fieldset className="lot-radio-group">
              <legend>Início</legend>
              <label className="lot-radio">
                <input
                  type="radio"
                  name="start-mode"
                  checked={values.startMode === 'now'}
                  onChange={() => handleStartMode('now')}
                />
                Assim que eu publicar
              </label>
              <label className="lot-radio">
                <input
                  type="radio"
                  name="start-mode"
                  checked={values.startMode === 'scheduled'}
                  onChange={() => handleStartMode('scheduled')}
                />
                Agendar
              </label>
            </fieldset>

            {values.startMode === 'scheduled' && (
              <DateTimeField
                id="lot-starts-at"
                label="Data e hora de início"
                value={values.startsAtLocal}
                error={startsError}
                inputRef={startsRef}
                onChange={(startsAtLocal) => {
                  setValues({ ...values, startsAtLocal })
                  clearError('starts_at')
                }}
              />
            )}

            <DateTimeField
              id="lot-ends-at"
              label="Término"
              value={values.endsAtLocal}
              error={endsError}
              inputRef={endsRef}
              onChange={(endsAtLocal) => {
                setValues({ ...values, endsAtLocal })
                clearError('ends_at')
              }}
            />
            <p className="muted field-hint">
              Horários no fuso deste navegador ({browserTimeZone()}).
            </p>
          </fieldset>

          <div className="lot-actions">
            <button type="submit" className="button button-primary">
              Revisar lote
            </button>
            <button type="button" className="button button-secondary" onClick={onBack}>
              Voltar à obra
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}

export default LotForm
