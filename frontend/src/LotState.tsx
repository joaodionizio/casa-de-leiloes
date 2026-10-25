import type { LotPhase } from './api/publicLots'
import { phaseStatusText } from './lotPhase'

interface LotStateProps {
  phase: LotPhase
}

// Estado do lote (D15): texto sempre presente; a cor só reforça. O marcador "●" só
// existe no ao vivo e é decorativo (`aria-hidden`). Sem pill, badge nem fundo.
function LotState({ phase }: LotStateProps) {
  return (
    <p className={`lot-state lot-state-${phase}`}>
      {phase === 'live' && (
        <span className="lot-state-dot" aria-hidden="true">
          ●
        </span>
      )}
      {phaseStatusText(phase)}
    </p>
  )
}

export default LotState
