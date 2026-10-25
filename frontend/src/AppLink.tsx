import type { AnchorHTMLAttributes, MouseEvent } from 'react'
import { navigate } from './navigation'
import { shouldHandleClick, type NavState } from './route'

interface AppLinkProps
  extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> {
  to: string
  state?: NavState
  // Roda antes da navegação interna (a vitrine guarda o lote aberto).
  beforeNavigate?: () => void
}

// Link de verdade (`<a href>`): Ctrl/Cmd+clique, clique do meio e "abrir em nova aba"
// funcionam pelo navegador. Só o clique simples vira `pushState` (P5).
function AppLink({ to, state, beforeNavigate, onClick, ...rest }: AppLinkProps) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    onClick?.(event)
    if (
      !shouldHandleClick({
        button: event.button,
        metaKey: event.metaKey,
        ctrlKey: event.ctrlKey,
        shiftKey: event.shiftKey,
        altKey: event.altKey,
        defaultPrevented: event.defaultPrevented,
        target: event.currentTarget.getAttribute('target'),
      })
    ) {
      return
    }
    event.preventDefault()
    beforeNavigate?.()
    navigate(to, state)
  }

  return <a href={to} onClick={handleClick} {...rest} />
}

export default AppLink
