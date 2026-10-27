// Contagem regressiva da sala (Story 3.5). É só apresentação: estima o tempo restante a
// partir do último estado lido e de um relógio monotônico injetado. Pode superestimar
// (a âncora nasce antes de a resposta chegar), nunca é prova de lote aberto ou
// encerrado, e o próximo snapshot a corrige. Sem `Date.now()`, sem DOM.

export interface CountdownAnchor {
  endsAtMs: number
  referenceMs: number // `as_of` do /bids ou `placed_at` do 201
  receivedAt: number // relógio monotônico no instante da leitura
}

export function makeAnchor(
  endsAt: string,
  reference: string,
  monotonicNow: number,
): CountdownAnchor | null {
  const endsAtMs = Date.parse(endsAt)
  const referenceMs = Date.parse(reference)
  if (Number.isNaN(endsAtMs) || Number.isNaN(referenceMs)) return null
  return { endsAtMs, referenceMs, receivedAt: monotonicNow }
}

export function remainingMs(anchor: CountdownAnchor, monotonicNow: number): number {
  const elapsed = Math.max(0, monotonicNow - anchor.receivedAt)
  return Math.max(0, anchor.endsAtMs - anchor.referenceMs - elapsed)
}

function two(value: number): string {
  return String(value).padStart(2, '0')
}

// `ceil` evita mostrar zero com 1 ms restante. Abaixo de 1 h: M:SS (`0:00`, `00:01`,
// `02:00`); de 1 h a menos de 24 h: HH:MM:SS; 24 h ou mais: "{d} d {HH} h".
export function formatCountdown(ms: number): string {
  const total = Math.ceil(Math.max(0, ms) / 1000)
  if (total === 0) return '0:00'
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  if (days >= 1) return `${days} d ${two(hours)} h`
  if (hours >= 1) return `${two(hours)}:${two(minutes)}:${two(seconds)}`
  return `${two(minutes)}:${two(seconds)}`
}

// Chave de um fim: o instante, não o texto (o mesmo fim pode chegar com frações
// diferentes).
export function endsAtKey(endsAt: string): string {
  return String(Date.parse(endsAt))
}

// Consumo único por valor de `ends_at`: só a fase ao vivo arma a releitura em zero, e o
// valor é marcado ANTES de pedir a leitura. Mesmo fim nunca rearma; fim novo arma uma vez.
export function consumeZero(
  consumed: Set<string>,
  phase: string,
  endsAt: string,
  remaining: number,
): boolean {
  if (phase !== 'live' || remaining > 0) return false
  const key = endsAtKey(endsAt)
  if (consumed.has(key)) return false
  consumed.add(key)
  return true
}
