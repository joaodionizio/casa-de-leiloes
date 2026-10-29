import type { RefObject } from 'react'
import { formatCents, moneyErrorMessage, parseReaisToCents } from './money'

interface MoneyFieldProps {
  id: string
  label: string
  description?: string
  value: string
  // Erro vindo do "Revisar lote" ou do servidor; tem prioridade sobre o feedback vivo.
  error: string | undefined
  inputRef: RefObject<HTMLInputElement | null>
  onChange: (value: string) => void
  // Enquanto um envio está pendente (carteira, Story 3.1): o valor fica visível e
  // focável, mas não muda.
  readOnly?: boolean
}

// Campo de reais em texto: o valor vira centavos por `money.ts`, nunca por
// `<input type="number">` (que passaria por ponto flutuante e pela localidade). O
// texto digitado não é reformatado.
//
// Há um único espaço de feedback, simétrico: valor válido → "✓ Valor reconhecido"
// (verde); valor inválido → "✕" e a mensagem (vermelho). O símbolo e o texto garantem
// que o estado não dependa só da cor. Campo vazio não mostra nada até o envio. Sem
// `aria-live`: o valor reconhecido muda a cada tecla e o leitor de tela reanunciaria
// "R$ 1,00", "R$ 12,00"... durante a digitação. O feedback continua ligado ao campo por
// `aria-describedby` e `aria-invalid`, e o erro do envio recebe o foco no campo.
function MoneyField({
  id,
  label,
  description,
  value,
  error,
  inputRef,
  onChange,
  readOnly = false,
}: MoneyFieldProps) {
  const descriptionId = `${id}-description`
  const hintId = `${id}-hint`
  const feedbackId = `${id}-feedback`
  const parsed = parseReaisToCents(value)

  let invalidMessage: string | undefined = error
  if (invalidMessage === undefined && !parsed.ok && parsed.error !== 'empty') {
    invalidMessage = moneyErrorMessage(parsed.error, value)
  }
  const recognized = invalidMessage === undefined && parsed.ok ? formatCents(parsed.cents) : null
  const hasFeedback = invalidMessage !== undefined || recognized !== null

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="money-input">
        <span className="money-prefix" aria-hidden="true">
          R$
        </span>
        <input
          id={id}
          ref={inputRef}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          value={value}
          readOnly={readOnly}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={invalidMessage !== undefined}
          aria-describedby={[description ? descriptionId : null, hintId, hasFeedback ? feedbackId : null].filter(Boolean).join(' ')}
        />
      </div>
      {description && <p id={descriptionId} className="field-hint muted">{description}</p>}
      <p id={hintId} className="field-hint muted">
        Digite o valor em reais. Use vírgula para centavos. Ex.: 5,50 ou 1.250,00.
      </p>
      <p
        id={feedbackId}
        className={invalidMessage !== undefined ? 'money-feedback money-invalid' : 'money-feedback money-recognized'}
      >
        {invalidMessage !== undefined && (
          <>
            <span aria-hidden="true">✕ </span>
            {invalidMessage}
          </>
        )}
        {recognized !== null && (
          <>
            <span aria-hidden="true">✓ </span>Valor reconhecido: {recognized}
          </>
        )}
      </p>
    </div>
  )
}

export default MoneyField
