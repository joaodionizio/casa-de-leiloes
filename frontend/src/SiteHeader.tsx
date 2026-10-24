import { roleLabel, type CurrentUser } from './api/auth'

interface SiteHeaderProps {
  user: CurrentUser | null
  loggingOut: boolean
  logoutError: string | null
  onLogout: () => void
}

function SiteHeader({
  user,
  loggingOut,
  logoutError,
  onLogout,
}: SiteHeaderProps) {
  return (
    <header className="site-header">
      <div className="page-container site-header-inner">
        <div className="site-brand">
          <img src="/favicon.svg" alt="" width={24} height={24} />
          <span className="site-brand-name">Casa de Leilões</span>
        </div>
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
