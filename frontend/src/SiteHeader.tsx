import { roleLabel, type CurrentUser } from './api/auth'
import AppLink from './AppLink'
import AtrioMark from './AtrioMark'
import { PRODUCT_NAME, PRODUCT_TAGLINE } from './brand'
import { routePath, type Route } from './route'

interface SiteHeaderProps {
  // `null` = anônimo (ou ainda verificando a sessão, quando `checking`).
  user: CurrentUser | null
  checking: boolean
  route: Route
  loggingOut: boolean
  logoutError: string | null
  onLogout: () => void
}

function current(active: boolean): 'page' | undefined {
  return active ? 'page' : undefined
}

// Cabeçalho por papel (CAP-8): só há link para destino que existe. Anônimo: Vitrine e
// Entrar. `BIDDER`: Vitrine, Carteira e Meus arremates. `AUCTIONEER`: Vitrine,
// Criar lote e Meus lotes.
function SiteHeader({
  user,
  checking,
  route,
  loggingOut,
  logoutError,
  onLogout,
}: SiteHeaderProps) {
  const here = routePath(route.kind === 'not-found' ? { kind: 'vitrine' } : route)
  return (
    <header className="site-header">
      <div className="page-container site-header-inner">
        {/* Label in Name (WCAG 2.5.3): o nome acessível começa pelo texto visível do link
            ("ÁTRIO" e, no desktop, "Leilões de Arte") e só acrescenta o destino. */}
        <AppLink
          to="/"
          className="site-brand"
          aria-label={`${PRODUCT_NAME} — ${PRODUCT_TAGLINE} — ir para a vitrine`}
        >
          <AtrioMark />
          <span className="site-brand-text">
            <span className="site-brand-name">{PRODUCT_NAME}</span>
            <span className="site-brand-tagline">{PRODUCT_TAGLINE}</span>
          </span>
        </AppLink>
        <nav className="site-nav" aria-label="Principal">
          <AppLink
            to="/"
            className="site-nav-item"
            aria-current={current(route.kind === 'vitrine')}
          >
            Vitrine
          </AppLink>
          {user !== null && user.role === 'BIDDER' && (
            <>
              <AppLink
                to="/bidder/wallet"
                className="site-nav-item"
                aria-current={current(route.kind === 'wallet')}
              >
                Carteira
              </AppLink>
              <AppLink
                to="/bidder/wins"
                className="site-nav-item"
                aria-current={current(route.kind === 'my-wins')}
              >
                Meus arremates
              </AppLink>
            </>
          )}
          {user !== null && user.role === 'AUCTIONEER' && (
            <>
              <AppLink
                to="/auctioneer/lots/new"
                className="site-nav-item"
                aria-current={current(route.kind === 'create-lot')}
              >
                Criar lote
              </AppLink>
              <AppLink
                to="/auctioneer/lots"
                className="site-nav-item"
                aria-current={current(route.kind === 'my-lots')}
              >
                Meus lotes
              </AppLink>
            </>
          )}
        </nav>
        {user === null && !checking && route.kind !== 'login' && (
          <AppLink
            to="/login"
            state={{ returnTo: here }}
            className="button button-secondary site-login-link"
          >
            Entrar
          </AppLink>
        )}
        {user !== null && (
          <div className="account">
            <span className="account-email" title={user.email}>
              {user.email}
            </span>
            <span aria-hidden="true">·</span>
            <span className="account-role">{roleLabel(user.role)}</span>
            <button
              type="button"
              className="button button-secondary"
              onClick={onLogout}
              disabled={loggingOut}
            >
              {loggingOut ? 'Saindo…' : 'Sair'}
            </button>
            {logoutError !== null && (
              <p className="form-error account-error" role="alert">
                {logoutError}
              </p>
            )}
          </div>
        )}
      </div>
    </header>
  )
}

export default SiteHeader
