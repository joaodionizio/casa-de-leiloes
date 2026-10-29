// Aviso de apresentação da Vitrine, sem relógio próprio. `now` é o as_of do
// snapshot, em milissegundos; a fase continua sendo a recebida do servidor.
export function getEndingSoonLabel(
  endsAt: string,
  now: number,
): 'Encerrando em breve' | 'Últimos 2 minutos' | null {
  const remaining = Date.parse(endsAt) - now
  if (!Number.isFinite(remaining) || remaining <= 0 || remaining > 10 * 60_000) return null
  return remaining <= 2 * 60_000 ? 'Últimos 2 minutos' : 'Encerrando em breve'
}
