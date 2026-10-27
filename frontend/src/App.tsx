import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import {
  failureMessage,
  fetchCurrentUser,
  logout,
  type CurrentUser,
} from './api/auth'
import { fetchHealth } from './api/health'
import AppLink from './AppLink'
import { documentTitle } from './brand'
import LoginPage from './LoginPage'
import LotCreation from './LotCreation'
import LotPage from './LotPage'
import type { Viewer } from './LotBidPanel'
import MyLots from './MyLots'
import { NAVIGATION_EVENT, navigate, replaceRoute } from './navigation'
import NotFoundPage from './NotFoundPage'
import {
  isRestrictedRoute,
  parseRoute,
  readNavState,
  routePath,
  safeReturnPath,
} from './route'
import SiteHeader from './SiteHeader'
import VitrinePage from './VitrinePage'
import WalletPage from './WalletPage'

type HealthState = 'loading' | 'available' | 'unavailable'

type SessionState =
  | { status: 'checking' }
  | { status: 'anonymous' }
  | { status: 'authenticated'; user: CurrentUser }

// Onde estamos, lido de `window.location` e `history.state`. `navigated` fica falso no
// primeiro carregamento e vira verdadeiro com qualquer navegação interna ou Back/
// Forward: só então movemos o foco para o título da vista (D11). `id` muda a cada
// navegação e remonta a vitrine, para cada visita fazer um GET novo (P3).
interface Where {
  pathname: string
  state: unknown
  navigated: boolean
  id: number
}

function readWhere(previous: Where | null): Where {
  return {
    pathname: window.location.pathname,
    state: window.history.state as unknown,
    navigated: previous !== null,
    id: previous === null ? 0 : previous.id + 1,
  }
}

function pageTitle(kind: string): string | null {
  if (kind === 'vitrine') return documentTitle('Vitrine')
  if (kind === 'login') return documentTitle('Entrar')
  if (kind === 'create-lot') return documentTitle('Criar lote')
  if (kind === 'my-lots') return documentTitle('Meus lotes')
  if (kind === 'wallet') return documentTitle('Carteira')
  if (kind === 'not-found') return documentTitle('Página não encontrada')
  return null // a página do lote usa o título da obra
}

function healthText(state: HealthState): string {
  if (state === 'loading') return 'Verificando o serviço…'
  if (state === 'available') return 'Serviço no ar'
  return 'Não foi possível falar com o servidor'
}

interface AuctioneerOnlyProps {
  focusHeading: boolean
}

// Licitante numa área do leiloeiro (D9): sem 404 e sem formulário; o caminho de volta.
function AuctioneerOnly({ focusHeading }: AuctioneerOnlyProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    if (focusHeading) headingRef.current?.focus()
  }, [focusHeading])
  return (
    <section className="notice-page" aria-labelledby="auctioneer-only-title">
      <h1 id="auctioneer-only-title" ref={headingRef} tabIndex={-1}>
        Área do leiloeiro
      </h1>
      <p>Esta área é só para a conta de leiloeiro.</p>
      <AppLink to="/" className="button button-secondary">
        Ir para a vitrine
      </AppLink>
    </section>
  )
}

// Leiloeiro numa área do licitante (Story 3.1, D13): espelho da vista acima. Esta vista
// não monta a carteira, então nenhuma chamada à API sai.
interface BidderOnlyProps {
  focusHeading: boolean
}

function BidderOnly({ focusHeading }: BidderOnlyProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    if (focusHeading) headingRef.current?.focus()
  }, [focusHeading])
  return (
    <section className="notice-page" aria-labelledby="bidder-only-title">
      <h1 id="bidder-only-title" ref={headingRef} tabIndex={-1}>
        Área do licitante
      </h1>
      <p>Esta área é só para a conta de licitante.</p>
      <AppLink to="/" className="button button-secondary">
        Ir para a vitrine
      </AppLink>
    </section>
  )
}

function App() {
  const [where, setWhere] = useState<Where>(() => readWhere(null))
  const [health, setHealth] = useState<HealthState>('loading')
  const [session, setSession] = useState<SessionState>({ status: 'checking' })
  const [sessionNotice, setSessionNotice] = useState<string | null>(null)
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)

  const route = useMemo(() => parseRoute(where.pathname), [where.pathname])
  const navState = useMemo(() => readNavState(where.state), [where.state])
  const navigated = where.navigated

  useEffect(() => {
    function sync() {
      setWhere((previous) => readWhere(previous))
    }
    window.addEventListener('popstate', sync)
    window.addEventListener(NAVIGATION_EVENT, sync)
    return () => {
      window.removeEventListener('popstate', sync)
      window.removeEventListener(NAVIGATION_EVENT, sync)
    }
  }, [])

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

  // Redirecionamentos (D8, D9): quem já está logado não fica em `/login`; anônimo numa
  // área restrita (leiloeiro ou carteira do licitante) vai ao login e volta para ela
  // depois, se o papel permitir.
  useEffect(() => {
    if (route.kind === 'login' && session.status === 'authenticated') {
      replaceRoute(safeReturnPath(navState.returnTo, session.user.role))
    } else if (isRestrictedRoute(route) && session.status === 'anonymous') {
      replaceRoute('/login', { returnTo: routePath(route) })
    }
  }, [route, session, navState])

  const title = pageTitle(route.kind)
  useEffect(() => {
    if (title !== null) document.title = title
  }, [title])

  const isAuctioneer =
    session.status === 'authenticated' && session.user.role === 'AUCTIONEER'

  // "Criar lote" fica montado e oculto fora da sua rota; ao navegar para ela, o foco
  // vai para o título da busca (D11).
  useEffect(() => {
    if (navigated && isAuctioneer && route.kind === 'create-lot') {
      document.getElementById('catalog-title')?.focus()
    }
  }, [navigated, isAuctioneer, route.kind])

  function handleLoggedIn(user: CurrentUser) {
    setSessionNotice(null)
    setSession({ status: 'authenticated', user })
    replaceRoute(safeReturnPath(navState.returnTo, user.role))
  }

  // 401 numa rota restrita ou na sala de um lote: a sessão acabou (o cookie venceu).
  // Volta ao login com o aviso e, depois de entrar, à mesma área ou ao mesmo lote.
  function handleSessionExpired() {
    setSession({ status: 'anonymous' })
    setSessionNotice(null)
    const returnTo =
      isRestrictedRoute(route) || route.kind === 'lot' ? routePath(route) : '/'
    replaceRoute('/login', { returnTo, notice: 'expired' })
  }

  async function handleLogout() {
    setLoggingOut(true)
    setLogoutError(null)
    const result = await logout()
    setLoggingOut(false)
    if (result.ok) {
      setSession({ status: 'anonymous' })
      if (window.location.pathname === '/') replaceRoute('/')
      else navigate('/')
      return
    }
    setLogoutError(failureMessage(result.failure))
  }

  const lotViewer: Viewer =
    session.status === 'checking'
      ? 'checking'
      : session.status === 'anonymous'
        ? 'visitor'
        : session.user.role === 'AUCTIONEER'
          ? 'auctioneer'
          : 'bidder'

  function renderView() {
    if (route.kind === 'vitrine') {
      return <VitrinePage key={where.id} navState={navState} navigated={navigated} />
    }
    if (route.kind === 'lot') {
      return (
        <LotPage
          key={route.lotId}
          lotId={route.lotId}
          navState={navState}
          navigated={navigated}
          viewer={lotViewer}
          owner={session.status === 'authenticated' ? session.user.email : null}
          onSessionExpired={handleSessionExpired}
        />
      )
    }
    if (route.kind === 'not-found') return <NotFoundPage focusHeading={navigated} />
    if (session.status === 'checking') {
      return (
        <p className="muted main-column" role="status">
          Verificando sua sessão…
        </p>
      )
    }
    if (route.kind === 'login') {
      if (session.status === 'authenticated') return null // redirecionando
      return (
        <LoginPage
          focusHeading={navigated}
          initialError={
            navState.notice === 'expired'
              ? 'Sua sessão expirou. Entre novamente.'
              : sessionNotice
          }
          onLoggedIn={handleLoggedIn}
        />
      )
    }
    // Carteira do licitante (Story 3.1). O leiloeiro vê só a vista de papel errado:
    // a página da carteira nem monta, então não há `GET /api/wallet`.
    if (route.kind === 'wallet') {
      if (session.status === 'anonymous') return null // redirecionando para /login
      if (session.user.role !== 'BIDDER') return <BidderOnly focusHeading={navigated} />
      return (
        <WalletPage
          key={where.id}
          owner={session.user.email}
          focusHeading={navigated}
          onSessionExpired={handleSessionExpired}
        />
      )
    }
    // Áreas do leiloeiro.
    if (session.status === 'anonymous') return null // redirecionando para /login
    if (session.user.role !== 'AUCTIONEER') {
      return <AuctioneerOnly focusHeading={navigated} />
    }
    if (route.kind === 'my-lots') {
      return (
        <MyLots
          onSessionExpired={handleSessionExpired}
          onCreateLot={() => navigate(routePath({ kind: 'create-lot' }))}
        />
      )
    }
    return null // "Criar lote": já montado abaixo
  }

  return (
    <div className="app">
      <SiteHeader
        user={session.status === 'authenticated' ? session.user : null}
        checking={session.status === 'checking'}
        route={route}
        loggingOut={loggingOut}
        logoutError={logoutError}
        onLogout={handleLogout}
      />
      <main className="app-main page-container">
        {renderView()}
        {/* "Criar lote" fica montado e oculto fora da sua rota, para não perder a
            busca nem o rascunho (2.4, D10); "Meus lotes" monta a cada abertura. */}
        {isAuctioneer && (
          <div hidden={route.kind !== 'create-lot'}>
            <LotCreation
              onSessionExpired={handleSessionExpired}
              onShowMyLots={() => navigate(routePath({ kind: 'my-lots' }))}
            />
          </div>
        )}
      </main>
      <footer className="app-footnote page-container">
        <p>Leilões ao vivo de obras de arte em domínio público.</p>
        <p role="status">{healthText(health)}</p>
      </footer>
    </div>
  )
}

export default App
