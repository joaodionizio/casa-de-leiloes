import { useEffect, useRef, useState } from 'react'
import { formatCountdown, remainingMs, type CountdownAnchor } from './countdown'

interface CountdownProps {
  anchor: CountdownAnchor | null
  // Chamado quando a estimativa chega a zero (a cada nova âncora que já está em zero);
  // quem decide se isso vira uma releitura é a página, que consome um disparo por fim.
  onZero: () => void
}

// Contagem regressiva: estimativa visual do último estado lido (Story 3.5). Só tick
// local, sem requisição. `aria-live="off"` para o leitor de tela não falar a cada
// segundo. Nunca é prova de lote aberto ou encerrado.
function CountdownTimer({ anchor, onZero }: CountdownProps) {
  const [now, setNow] = useState(() => performance.now())
  const zeroRef = useRef(onZero)

  useEffect(() => {
    zeroRef.current = onZero
  }, [onZero])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(performance.now()), 500)
    return () => window.clearInterval(timer)
  }, [anchor])

  const remaining = anchor === null ? null : remainingMs(anchor, now)
  const atZero = remaining === 0

  useEffect(() => {
    if (anchor !== null && atZero) zeroRef.current()
  }, [anchor, atZero])

  if (remaining === null) return null
  return (
    <p className="room-countdown">
      <span className="room-label">Tempo restante</span>
      <span role="timer" aria-live="off" className="room-countdown-value">
        {formatCountdown(remaining)}
      </span>
    </p>
  )
}

export default CountdownTimer
