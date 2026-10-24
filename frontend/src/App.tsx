import { useEffect, useState } from 'react'
import './App.css'
import { fetchHealth } from './api/health'

type HealthState = 'loading' | 'available' | 'unavailable'

function healthText(state: HealthState): string {
  if (state === 'loading') return 'Verificando o serviço…'
  if (state === 'available') return 'Serviço no ar'
  return 'Não foi possível falar com o servidor'
}

function App() {
  const [health, setHealth] = useState<HealthState>('loading')

  useEffect(() => {
    let cancelled = false
    fetchHealth()
      .then(() => {
        if (!cancelled) setHealth('available')
      })
      .catch(() => {
        if (!cancelled) setHealth('unavailable')
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="app">
      <h1 className="brand">Casa de Leilões</h1>
      <p className="tagline">
        Leilões ao vivo de obras de arte em domínio público.
      </p>
      <p className={`health health-${health}`} role="status">
        {healthText(health)}
      </p>
    </main>
  )
}

export default App
