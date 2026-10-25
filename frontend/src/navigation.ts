// Efeitos da navegação própria (Story 2.5, P5). A parte pura, testada, está em
// `route.ts`. Aqui só `pushState`/`replaceState` e o evento que avisa o `App`; sem
// teste automatizado (precisa de `window`), coberto pelo roteiro manual.

import { readNavState, type NavState } from './route.ts'

export const NAVIGATION_EVENT = 'app:navigation'

// Navegação nova: entrada nova no histórico, volta ao topo. O `popstate` (Back/
// Forward) não passa por aqui; a rolagem dele é decidida pela regra de foco (D11).
// Ir para o caminho em que já estamos troca a entrada em vez de empilhar uma igual.
export function navigate(path: string, state?: NavState): void {
  if (window.location.pathname === path) {
    window.history.replaceState(state ?? null, '', path)
  } else {
    window.history.pushState(state ?? null, '', path)
  }
  window.dispatchEvent(new Event(NAVIGATION_EVENT))
  window.scrollTo(0, 0)
}

// Troca a entrada atual (redirecionamentos, destino depois do login).
export function replaceRoute(path: string, state?: NavState): void {
  window.history.replaceState(state ?? null, '', path)
  window.dispatchEvent(new Event(NAVIGATION_EVENT))
}

// Acrescenta campos ao `state` da entrada atual sem mudar a URL nem avisar o `App`:
// a vitrine guarda qual lote foi aberto para devolver o foco no Back (D11).
export function patchCurrentState(patch: NavState): void {
  window.history.replaceState(
    { ...readNavState(window.history.state), ...patch },
    '',
  )
}
