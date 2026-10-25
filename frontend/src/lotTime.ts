// Horários do lote na interface (Story 2.4, P4, frontend-lot-creation §5). O
// navegador só traduz o horário de parede que a pessoa escolheu para ISO em UTC e
// formata o que o servidor devolveu. Quem decide se um horário vale é o servidor,
// com a hora do banco (AD-6). Este arquivo não compara com "agora"; a checagem
// preventiva, com `now` injetado, está em `lotDraft.ts`.

export function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone
}

const LOCAL_INPUT_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/

// "2026-10-25T13:00" (valor de um `datetime-local`, horário do navegador) → ISO em
// UTC com `Z`; null se o texto não for uma data e hora válidas.
export function localInputToIso(value: string): string | null {
  if (!LOCAL_INPUT_PATTERN.test(value)) return null
  const moment = new Date(value)
  if (Number.isNaN(moment.getTime())) return null
  return moment.toISOString()
}

// Campos explícitos (dia, mês abreviado, ano, hora e minuto) mais o nome do fuso: o
// mesmo texto que `dateStyle: 'medium'` e `timeStyle: 'short'` dariam, com o fuso. Não
// use `dateStyle`/`timeStyle` junto de `timeZoneName`: o `Intl` recusa a combinação com
// `TypeError: Invalid option : option`, e como isto roda na importação do módulo, a
// tela inteira ficava em branco (primeiro teste manual da Story 2.4).
const dateTimeFormat = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZoneName: 'short',
})

// Exibição, nunca decisão. Texto original se o servidor mandar algo ilegível.
export function formatDateTime(iso: string): string {
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return iso
  return dateTimeFormat.format(moment)
}
