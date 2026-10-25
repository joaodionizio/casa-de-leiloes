import { useEffect, useState } from 'react'
import './App.css'
import {
  failureMessage,
  fetchCurrentUser,
  logout,
  type CurrentUser,
} from './api/auth'
import { fetchHealth } from './api/health'
import CatalogSearch from './CatalogSearch'
import LoginForm from './LoginForm'
import SiteHeader from './SiteHeader'

type HealthState = 'loading' | 'available' | 'unavailable'

type SessionState =
  | { status: 'checking' }
  | { status: 'anonymous' }
  | { status: 'authenticated'; user: CurrentUser }

function healthText(state: HealthState): string {
  if (state === 'loading') return 'Verificando o serviço…'
  if (state === 'available') return 'Serviço no ar'
  return 'Não foi possível falar com o servidor'
}

function App() {
  const [health, setHealth] = useState<HealthState>('loading')
  const [session, setSession] = useState<SessionState>({ status: 'checking' })
  const [sessionNotice, setSessionNotice] = useState<string | null>(null)
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)
  const [justLoggedOut, setJustLoggedOut] = useState(false)

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

  useEffect(() => {
    let cancelled = false
    fetchCurrentUser().then((result) => {
      if (cancelled) return
      if (result.ok) {
        setSession({ status: 'authenticated', user: result.user })
        return
      }
      setSession({ status: 'anonymous' })
      if (result.failure === 'server') setSessionNotice(failureMessage('server'))
    })
    return () => {
      cancelled = true
    }
  }, [])

  function handleLoggedIn(user: CurrentUser) {
    setSessionNotice(null)
    setJustLoggedOut(false)
    setSession({ status: 'authenticated', user })
  }

  // 401 numa rota do catálogo: a sessão acabou (o cookie venceu).
  function handleSessionExpired() {
    setSessionNotice('Sua sessão expirou. Entre novamente.')
    setJustLoggedOut(false)
    setSession({ status: 'anonymous' })
  }

  async function handleLogout() {
    setLoggingOut(true)
    setLogoutError(null)
    const result = await logout()
    setLoggingOut(false)
    if (result.ok) {
      setJustLoggedOut(true)
      setSession({ status: 'anonymous' })
      return
    }
    setLogoutError(failureMessage(result.failure))
  }

  return (
    <div className="app">
      <SiteHeader
        user={session.status === 'authenticated' ? session.user : null}
        loggingOut={loggingOut}
        logoutError={logoutError}
        onLogout={handleLogout}
      />
      <main className="app-main page-container">
        {session.status === 'checking' && (
          <p className="muted main-column" role="status">
            Verificando sua sessão…
          </p>
        )}
        {session.status === 'anonymous' && (
          <section
            aria-labelledby="login-title"
            className="login-section main-column"
          >
            <h1 id="login-title">Entrar</h1>
            <LoginForm
              initialError={sessionNotice}
              focusEmail={justLoggedOut}
              onLoggedIn={handleLoggedIn}
            />
          </section>
        )}
        {session.status === 'authenticated' &&
          (session.user.role === 'AUCTIONEER' ? (
            <CatalogSearch onSessionExpired={handleSessionExpired} />
          ) : (
            <h1 className="visually-hidden">Casa de Leilões</h1>
          ))}
      </main>
      <footer className="app-footnote page-container">
        <p>Leilões ao vivo de obras de arte em domínio público.</p>
        <p role="status">{healthText(health)}</p>
      </footer>
    </div>
  )
}

export default App
