// Dinheiro no front-end (Story 2.4, AD-3, P5, D13). O servidor só conhece centavos
// inteiros; aqui o texto digitado em reais vira centavos SEM aritmética de ponto
// flutuante: a conversão é feita sobre os dígitos, como texto. Este arquivo é
// TypeScript "apagável" e não usa DOM: o `node --test` o roda sem transpilador.

// Mesma faixa do back-end e do banco: Number.MAX_SAFE_INTEGER (limite técnico, não
// comercial). Um teste confere a igualdade.
export const MAX_CENTS = 9007199254740991
const MAX_CENTS_TEXT = '9007199254740991'

export type MoneyError =
  | 'empty'
  | 'format'
  | 'too_many_decimals'
  | 'dot_decimal'
  | 'not_positive'
  | 'too_large'

export type MoneyParse =
  | { ok: true; cents: number }
  | { ok: false; error: MoneyError }

// "1234", "1234,5", "1234,56", "1.234,56". Milhar só com ponto e grupos de três.
const AMOUNT_PATTERN = /^(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?$/
const TOO_MANY_DECIMALS_PATTERN = /^[\d.]+,\d{3,}$/
// "655.3" e "12.50": ponto onde o pt-BR usa vírgula. Nunca é reinterpretado em
// silêncio; a mensagem ensina a vírgula. ("1.234" tem três dígitos depois do ponto e é
// milhar válido, então não cai aqui.)
const DOT_DECIMAL_PATTERN = /^\d+\.\d{1,2}$/

export function parseReaisToCents(input: string): MoneyParse {
  const text = input.trim()
  if (text === '') return { ok: false, error: 'empty' }
  if (TOO_MANY_DECIMALS_PATTERN.test(text)) {
    return { ok: false, error: 'too_many_decimals' }
  }
  if (DOT_DECIMAL_PATTERN.test(text)) return { ok: false, error: 'dot_decimal' }
  if (!AMOUNT_PATTERN.test(text)) return { ok: false, error: 'format' }

  const [wholePart, fractionPart = ''] = text.split(',')
  const whole = wholePart.replaceAll('.', '')
  const fraction = fractionPart.padEnd(2, '0')
  // Concatenação de texto: "12" + "50" → "1250" centavos.
  const digits = (whole + fraction).replace(/^0+/, '') || '0'

  if (digits === '0') return { ok: false, error: 'not_positive' }
  // Mesma largura: a comparação de texto equivale à numérica.
  if (
    digits.length > MAX_CENTS_TEXT.length ||
    (digits.length === MAX_CENTS_TEXT.length && digits > MAX_CENTS_TEXT)
  ) {
    return { ok: false, error: 'too_large' }
  }
  // Só dígitos e no máximo 2^53 - 1: a conversão é exata.
  return { ok: true, cents: Number(digits) }
}

// Centavos → "R$ 1.234,56". Também textual: sem divisão e sem `Intl`.
export function formatCents(cents: number): string {
  if (!Number.isSafeInteger(cents) || cents < 0) {
    throw new RangeError('cents must be a non-negative safe integer')
  }
  const padded = String(cents).padStart(3, '0')
  const whole = padded.slice(0, -2)
  const fraction = padded.slice(-2)
  let grouped = ''
  for (let end = whole.length; end > 0; end -= 3) {
    const chunk = whole.slice(Math.max(0, end - 3), end)
    grouped = grouped === '' ? chunk : `${chunk}.${grouped}`
  }
  return `R$ ${grouped},${fraction}`
}

// Centavos → texto para o campo, sem "R$" nem milhar: 130000 → "1300,00". Só texto,
// sem divisão (usado pelo atalho "Usar o mínimo").
export function centsToInputText(cents: number): string {
  if (!Number.isSafeInteger(cents) || cents < 0) {
    throw new RangeError('cents must be a non-negative safe integer')
  }
  const padded = String(cents).padStart(3, '0')
  return `${padded.slice(0, -2)},${padded.slice(-2)}`
}

// Sugestão com vírgula para uma entrada com ponto decimal: "333.55" → "333,55",
// "12.5" → "12,50". Só texto, sem aritmética; sem entrada reconhecível, um exemplo.
function commaExample(input: string): string {
  const text = input.trim()
  if (!DOT_DECIMAL_PATTERN.test(text)) return '655,30'
  const [whole, fraction] = text.split('.')
  return `${whole},${fraction.padEnd(2, '0')}`
}

// Texto da mensagem no campo para cada erro de conversão. Para `dot_decimal`, o
// exemplo usa o que a pessoa digitou (`input`), quando disponível.
export function moneyErrorMessage(error: MoneyError, input: string = ''): string {
  if (error === 'empty') return 'Informe o valor.'
  if (error === 'too_many_decimals') return 'Use no máximo duas casas decimais.'
  if (error === 'dot_decimal') {
    return `Use vírgula para os centavos. Ex.: ${commaExample(input)}.`
  }
  if (error === 'not_positive') return 'O valor precisa ser maior que zero.'
  if (error === 'too_large') return 'Valor alto demais.'
  return 'Use só números, com vírgula para os centavos. Ex.: 1.250,00'
}
