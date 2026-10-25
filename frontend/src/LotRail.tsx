import { useEffect, useRef, useState } from 'react'
import type { PublicLotSummary } from './api/publicLots'
import LiveLotItem from './LiveLotItem'
import UpcomingLotItem from './UpcomingLotItem'
import { railScrollState, type RailScrollState } from './vitrine'

interface LotRailProps {
  headingId: string
  title: string
  kind: 'live' | 'upcoming'
  lots: PublicLotSummary[]
  // Texto quando a seção não tem nenhum lote para mostrar (sem imagem, sem conteúdo
  // falso).
  emptyText: string
  onOpen: (lotId: string) => void
}

const NO_OVERFLOW: RailScrollState = {
  overflow: false,
  canPrev: false,
  canNext: false,
}

// Rail horizontal de "Ao vivo" e "Próximos lotes" (blueprint §6, §7, D14): sem limite
// de itens, `scroll-snap`, parte do próximo item visível. A classe `rail-n-N` (1, 2, 3 ou
// 4 = quatro ou mais) só ajusta a largura dos itens no desktop, para poucos lotes
// ocuparem a faixa em vez de deixar vazio à direita; o conteúdo não muda. "Anterior"/"Próximo" só
// existem no desktop (CSS) e só se há overflow de verdade; no toque e no teclado o
// rail rola sozinho (Tab pelos links).
function LotRail({ headingId, title, kind, lots, emptyText, onOpen }: LotRailProps) {
  const railRef = useRef<HTMLUListElement>(null)
  const [scroll, setScroll] = useState<RailScrollState>(NO_OVERFLOW)
  const hasItems = lots.length > 0

  useEffect(() => {
    const rail = railRef.current
    if (rail === null) return
    function update() {
      if (rail === null) return
      setScroll(railScrollState(rail.scrollLeft, rail.clientWidth, rail.scrollWidth))
    }
    // O observador dispara uma vez ao começar a observar e a cada mudança de tamanho.
    const observer = new ResizeObserver(update)
    observer.observe(rail)
    rail.addEventListener('scroll', update, { passive: true })
    return () => {
      observer.disconnect()
      rail.removeEventListener('scroll', update)
    }
  }, [hasItems, lots])

  function scrollBy(direction: 1 | -1) {
    const rail = railRef.current
    if (rail === null) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    rail.scrollBy({
      left: direction * rail.clientWidth * 0.9,
      behavior: reduced ? 'auto' : 'smooth',
    })
  }

  return (
    <section className="vitrine-section" aria-labelledby={headingId}>
      <div className="vitrine-section-head">
        <h2 id={headingId}>{title}</h2>
        {hasItems && scroll.overflow && (
          <div className="rail-controls">
            <button
              type="button"
              className="button button-secondary"
              aria-label={`Ver lotes anteriores de ${title}`}
              disabled={!scroll.canPrev}
              onClick={() => scrollBy(-1)}
            >
              Anterior
            </button>
            <button
              type="button"
              className="button button-secondary"
              aria-label={`Ver mais lotes de ${title}`}
              disabled={!scroll.canNext}
              onClick={() => scrollBy(1)}
            >
              Próximo
            </button>
          </div>
        )}
      </div>
      {hasItems ? (
        <ul
          className={`rail rail-${kind} rail-n-${Math.min(lots.length, 4)}`}
          ref={railRef}
        >
          {lots.map((lot) =>
            kind === 'live' ? (
              <LiveLotItem key={lot.id} lot={lot} onOpen={onOpen} />
            ) : (
              <UpcomingLotItem key={lot.id} lot={lot} onOpen={onOpen} />
            ),
          )}
        </ul>
      ) : (
        <p className="vitrine-empty muted">{emptyText}</p>
      )}
    </section>
  )
}

export default LotRail
