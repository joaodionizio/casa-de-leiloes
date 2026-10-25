import type { RefObject } from 'react'
import { formatDateTime, localInputToIso } from './lotTime'

interface DateTimeFieldProps {
  id: string
  label: string
  value: string
  error: string | undefined
  inputRef: RefObject<HTMLInputElement | null>
  onChange: (value: string) => void
}

// Campo `datetime-local` nativo, mais alto que o padrão para facilitar o toque, com um
// resumo discreto do horário escolhido e o fuso. Não há etapa de confirmação: "Revisar
// lote" é que valida o valor atual (um botão dentro do seletor nativo não existe, e uma
// confirmação separada era uma etapa artificial).
function DateTimeField({ id, label, value, error, inputRef, onChange }: DateTimeFieldProps) {
  const errorId = `${id}-error`
  const summaryId = `${id}-summary`
  const chosenIso = value === '' ? null : localInputToIso(value)
  const describedBy =
    error !== undefined ? errorId : chosenIso !== null ? summaryId : undefined

  return (
    <div className="field datetime-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        ref={inputRef}
        type="datetime-local"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error !== undefined}
        aria-describedby={describedBy}
      />
      {error !== undefined && (
        <p id={errorId} className="form-error">
          {error}
        </p>
      )}
      {error === undefined && chosenIso !== null && (
        <p id={summaryId} className="datetime-chosen">
          {formatDateTime(chosenIso)}
        </p>
      )}
    </div>
  )
}

export default DateTimeField
