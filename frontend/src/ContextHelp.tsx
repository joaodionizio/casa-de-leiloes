import { useEffect, useId, useRef, useSyncExternalStore } from 'react'

// Um único ID ativo para todas as instâncias, inclusive em áreas distintas.
let activeId: string | null = null
const listeners = new Set<() => void>()
function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}
function getActiveId() { return activeId }
function setActiveId(id: string | null) {
  if (activeId === id) return
  activeId = id
  listeners.forEach(listener => listener())
}

// Divulgação em fluxo: não depende de hover e não é recortada pelo viewport.
export default function ContextHelp({ label, text }: { label: string; text: string }) {
  const id = useId()
  const open = useSyncExternalStore(subscribe, getActiveId, () => null) === id
  const trigger = useRef<HTMLButtonElement>(null)

  useEffect(() => () => {
    if (activeId === id) setActiveId(null)
  }, [id])

  useEffect(() => {
    if (!open) return
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key !== 'Escape' || event.defaultPrevented || activeId !== id) return
      setActiveId(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [id, open])

  return <span className="context-help" onKeyDown={event => {
    if (event.key === 'Escape' && open) {
      event.stopPropagation()
      setActiveId(null)
      trigger.current?.focus()
    }
  }}>
    <button ref={trigger} type="button" className="context-help-trigger" aria-label={`Ajuda: ${label}`} aria-expanded={open} aria-controls={id} onClick={() => setActiveId(activeId === id ? null : id)}>?</button>
    <span id={id} className="context-help-text" hidden={!open}>{text}</span>
  </span>
}
