import { useEffect, useRef } from 'react'
import type { PublicLotSummary } from './api/publicLots'
import ClosedLotRow from './ClosedLotRow'
import { nextEndedVisible } from './vitrine'

interface ClosedLotsProps {
  lots: PublicLotSummary[]
  visible: number
  onVisibleChange: (visible: number) => void
  onOpen: (lotId: string) => void
}

// "Encerrados" (D13): lista densa com os primeiros itens; "Mostrar mais encerrados"
// revela mais 6, só localmente — a resposta já trouxe todos, então nenhuma chamada nova.
function ClosedLots({ lots, visible, onVisibleChange, onOpen }: ClosedLotsProps) {
  const listRef = useRef<HTMLUListElement>(null)
  // Índice do primeiro item revelado, para devolver o foco a ele depois do clique.
  const focusIndexRef = useRef<number | null>(null)
  const total = lots.length

  useEffect(() => {
    const index = focusIndexRef.current
    if (index === null) return
    focusIndexRef.current = null
    const item = listRef.current?.children.item(index)
    item?.querySelector<HTMLElement>('a')?.focus()
  }, [visible])

  function showMore() {
    focusIndexRef.current = visible
    onVisibleChange(nextEndedVisible(visible, total))
  }

  return (
    <section className="vitrine-section" aria-labelledby="closed-heading">
      <div className="vitrine-section-head">
        <h2 id="closed-heading">Encerrados</h2>
      </div>
      {total === 0 ? (
        <p className="vitrine-empty muted">Nenhum lote encerrado ainda.</p>
      ) : (
        <>
          <ul className="closed-list" ref={listRef}>
            {lots.slice(0, visible).map((lot) => (
              <ClosedLotRow key={lot.id} lot={lot} onOpen={onOpen} />
            ))}
          </ul>
          <div className="closed-more">
            <p className="muted" role="status">
              Mostrando {Math.min(visible, total)} de {total}{' '}
              {total === 1 ? 'encerrado' : 'encerrados'}.
            </p>
            {visible < total && (
              <button
                type="button"
                className="button button-secondary"
                onClick={showMore}
              >
                Mostrar mais encerrados
              </button>
            )}
          </div>
        </>
      )}
    </section>
  )
}

export default ClosedLots
