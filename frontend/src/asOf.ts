// Linha "Situação atualizada…" (Story 2.5, D16). Mostra a data da fotografia que o
// servidor produziu (`as_of`), em horário do navegador. É só apresentação: não inicia
// relógio, não se atualiza sozinha, não recalcula `phase` e não usa `Date.now()`.
// `today` só escolhe entre as duas formas do texto. Não combine `dateStyle`/
// `timeStyle` com `timeZoneName`: o `Intl` recusa (tela branca da Story 2.4).

function formatParts(
  moment: Date,
  timeZone: string | undefined,
): { date: string; time: string } {
  const date = new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone,
  }).format(moment)
  const time = new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone,
  }).format(moment)
  return { date, time }
}

// "Situação atualizada às 14:30" (mesmo dia de `today`) ou "Situação atualizada em
// 25/10/2026 às 14:30"; `null` se o `as_of` for ilegível (a linha não aparece).
export function asOfText(
  asOf: string,
  today: Date,
  timeZone?: string,
): string | null {
  const moment = new Date(asOf)
  if (Number.isNaN(moment.getTime()) || Number.isNaN(today.getTime())) return null
  const shot = formatParts(moment, timeZone)
  const now = formatParts(today, timeZone)
  if (shot.date === now.date) return `Situação atualizada às ${shot.time}`
  return `Situação atualizada em ${shot.date} às ${shot.time}`
}
