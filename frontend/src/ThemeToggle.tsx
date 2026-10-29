import { useState } from 'react'

export default function ThemeToggle() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')
  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    setTheme(next)
    try { localStorage.setItem('atrio-theme', next) } catch { /* O tema ainda funciona sem persistência. */ }
  }
  return <button type="button" className="theme-toggle button button-secondary" aria-label={theme === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'} onClick={toggle}>
    <span aria-hidden="true">{theme === 'dark' ? '☼' : '☾'}</span>
  </button>
}
