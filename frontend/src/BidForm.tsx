import type { FormEvent, RefObject } from 'react'
import MoneyField from './MoneyField'
import { centsToInputText, formatCents, parseReaisToCents } from './money'

interface BidFormProps {
  amountText: string
  fieldError: string | undefined
  submitting: boolean
  // Mínimo atual do servidor; `null` quando não há valor possível ou ele está sendo
  // atualizado (`updating`).
  minimumCents: number | null
  updating: boolean
  inputRef: RefObject<HTMLInputElement | null>
  onChange: (value: string) => void
  onSubmit: () => void
}

// Formulário de lance (Story 3.5). O cliente valida só o formato (MoneyField e
// `parseReaisToCents` na página): mínimo e saldo ficam com o servidor, então nada aqui
// compara valores nem desabilita o envio por eles.
function BidForm({
  amountText,
  fieldError,
  submitting,
  minimumCents,
  updating,
  inputRef,
  onChange,
  onSubmit,
}: BidFormProps) {
  const parsed = parseReaisToCents(amountText)
  const showShortcut = minimumCents !== null && !submitting && !parsed.ok

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form className="bid-form" aria-busy={submitting} onSubmit={handleSubmit} noValidate>
      <MoneyField
        id="bid-amount"
        label="Valor do lance"
        value={amountText}
        error={fieldError}
        inputRef={inputRef}
        onChange={onChange}
        readOnly={submitting}
      />
      {showShortcut && (
        <button
          type="button"
          className="button button-secondary bid-shortcut"
          onClick={() => {
            onChange(centsToInputText(minimumCents))
            inputRef.current?.focus()
          }}
        >
          Usar o mínimo ({formatCents(minimumCents)})
        </button>
      )}
      {minimumCents === null && !updating && (
        <p className="muted">Não há valor possível acima do lance atual.</p>
      )}
      <button type="submit" className="button button-primary" disabled={submitting}>
        {submitting ? 'Enviando lance…' : 'Dar lance'}
      </button>
    </form>
  )
}

export default BidForm
