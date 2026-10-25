import { useState } from 'react'
import type { ArtworkDetail } from './api/catalog'
import type { CreateLotRequest, FieldProblem, LotResponse } from './api/lots'
import CatalogSearch from './CatalogSearch'
import LotCreated from './LotCreated'
import LotForm from './LotForm'
import { emptyDraft, type LotDraft } from './lotDraft'
import LotReview from './LotReview'

type Stage =
  | { kind: 'catalog' }
  | { kind: 'form'; artwork: ArtworkDetail; draft: LotDraft; problems: FieldProblem[] }
  | { kind: 'review'; artwork: ArtworkDetail; draft: LotDraft; request: CreateLotRequest }
  | { kind: 'created'; lot: LotResponse }

interface LotCreationProps {
  onSessionExpired: () => void
  onShowMyLots: () => void
}

// Buscar → detalhe → formulário → revisão → confirmação (EXPERIENCE §6). A busca
// fica montada e oculta nas outras etapas, para não perder termo nem resultados. O
// rascunho sobrevive a formulário ↔ revisão e a qualquer erro do POST.
function LotCreation({ onSessionExpired, onShowMyLots }: LotCreationProps) {
  const [stage, setStage] = useState<Stage>({ kind: 'catalog' })
  // Contador: pede à busca que devolva o foco ao detalhe da obra ao reaparecer.
  const [returnFocus, setReturnFocus] = useState(0)

  function backToCatalog() {
    setStage({ kind: 'catalog' })
    setReturnFocus((count) => count + 1)
  }

  function showMyLots() {
    setStage({ kind: 'catalog' })
    onShowMyLots()
  }

  return (
    <>
      <div hidden={stage.kind !== 'catalog'}>
        <CatalogSearch
          onSessionExpired={onSessionExpired}
          onCreateLot={(artwork) =>
            setStage({ kind: 'form', artwork, draft: emptyDraft(), problems: [] })
          }
          returnFocus={returnFocus}
        />
      </div>

      {stage.kind === 'form' && (
        <LotForm
          artwork={stage.artwork}
          draft={stage.draft}
          serverProblems={stage.problems}
          onReview={(draft, request) =>
            setStage({ kind: 'review', artwork: stage.artwork, draft, request })
          }
          onBack={backToCatalog}
        />
      )}

      {stage.kind === 'review' && (
        <LotReview
          artwork={stage.artwork}
          request={stage.request}
          onCreated={(lot) => setStage({ kind: 'created', lot })}
          onEdit={() =>
            setStage({
              kind: 'form',
              artwork: stage.artwork,
              draft: stage.draft,
              problems: [],
            })
          }
          onFieldProblems={(problems) =>
            setStage({ kind: 'form', artwork: stage.artwork, draft: stage.draft, problems })
          }
          onBackToCatalog={backToCatalog}
          onShowMyLots={showMyLots}
          onSessionExpired={onSessionExpired}
        />
      )}

      {stage.kind === 'created' && (
        <LotCreated lot={stage.lot} onShowMyLots={showMyLots} onCreateAnother={backToCatalog} />
      )}
    </>
  )
}

export default LotCreation
