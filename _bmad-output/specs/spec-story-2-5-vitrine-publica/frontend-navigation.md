# Front-end — navegação, login e header (Story 2.5, P5)

Autoridade: story > `docs/ARQUITETURA.md` > `DESIGN.md` + `EXPERIENCE.md` +
`VITRINE-BLUEPRINT.md`. Processo: `docs/FRONTEND-WORKFLOW.md`. Sem React Router, sem
dependência de runtime nova (AD-4). (Playwright, de desenvolvimento, entrou depois: D21.)

## 1. Rotas (D7)

| Caminho | `Route` | Vista | Quem |
| --- | --- | --- | --- |
| `/` | `{kind: 'vitrine'}` | Vitrine | todos |
| `/lots/{uuid}` | `{kind: 'lot'; lotId}` | Página do lote | todos |
| `/login` | `{kind: 'login'}` | Entrar | anônimo (logado → destino) |
| `/auctioneer/lots/new` | `{kind: 'create-lot'}` | Criar lote (2.4) | `AUCTIONEER` |
| `/auctioneer/lots` | `{kind: 'my-lots'}` | Meus lotes (2.4) | `AUCTIONEER` |
| qualquer outro | `{kind: 'not-found'}` | Página não encontrada | todos |

`{uuid}` = `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$` (minúsculo,
como o servidor emite). Barra final, maiúsculas, `/lots/abc`, `/lots/<uuid>/x` →
`not-found`, sem chamar a API. Query e hash são ignorados.

## 2. Módulo puro `src/route.ts` (testado, D18)

```ts
export type AppRoute =
  | { kind: 'vitrine' }
  | { kind: 'lot'; lotId: string }
  | { kind: 'login' }
  | { kind: 'create-lot' }
  | { kind: 'my-lots' }
export type Route = AppRoute | { kind: 'not-found' }

export function parseRoute(pathname: string): Route
export function routePath(route: AppRoute): string      // ida e volta com parseRoute
export function isAuctioneerRoute(route: Route): boolean // create-lot | my-lots
// returnTo seguro: só caminhos que parseRoute aceita como vitrine, lot, create-lot ou
// my-lots; qualquer outra coisa (URL absoluta, '//evil.com', '/login', texto, não
// string) → '/'. Rota do leiloeiro com role !== 'AUCTIONEER' → '/'.
export function safeReturnPath(value: unknown, role: UserRole): string
// Clique que a SPA deve tratar: botão 0, sem meta/ctrl/shift/alt, não prevenido,
// sem target diferente de _self. Senão o navegador segue o link.
export function shouldHandleClick(event: ClickLike): boolean
export interface ClickLike {
  button: number; metaKey: boolean; ctrlKey: boolean; shiftKey: boolean
  altKey: boolean; defaultPrevented: boolean; target: string | null
}
// Lê history.state desconhecido; campos inválidos viram ausentes.
export function readNavState(value: unknown): NavState
export interface NavState {
  returnTo?: string        // só na entrada /login
  notice?: 'expired'       // só na entrada /login
  fromVitrine?: boolean    // entrada /lots/{id} aberta a partir da vitrine
  restoreLotId?: string    // entrada / : lote a focar no Back
  endedVisible?: number    // entrada / : quantos encerrados estavam visíveis
}
```

Sem DOM, sem `window`: roda no Node. `UserRole` vem de `./api/auth.ts` como `import
type` (apagável).

## 3. `src/navigation.ts` (efeitos, sem teste automatizado)

```ts
export const NAVIGATION_EVENT = 'app:navigation'
export function navigate(path: string, state?: NavState): void  // pushState + evento
export function replaceRoute(path: string, state?: NavState): void // replaceState + evento
export function patchCurrentState(patch: NavState): void       // replaceState do state atual, sem evento
```

`App` assina `popstate` e `NAVIGATION_EVENT`, lê `location.pathname` e `history.state`
e guarda `{route, navState, navigated}` (`navigated` = já houve navegação interna ou
`popstate`; o primeiro carregamento é `false`). `main.tsx` (ou o primeiro efeito do
`App`) define `history.scrollRestoration = 'manual'`. `navigate` rola ao topo; o
`popstate` deixa a rolagem para a regra de foco (D11).

`src/AppLink.tsx`: `<a href={to}>` real; `onClick` chama `shouldHandleClick` e, se
`true`, `preventDefault()` + `navigate(to, state)`. Ctrl/Cmd+clique, clique do meio e
"Abrir em nova aba" funcionam pelo navegador.

## 4. Login (`/login`, D8, D9)

- "Entrar" (header) = `AppLink` para `/login` com `state = {returnTo: <caminho atual>}`
  (push). Não aparece na própria `/login`.
- `LoginPage`: `h1` "Entrar" (foco ao navegar), `LoginForm` da 2.2 sem mudança;
  `notice: 'expired'` → `initialError` "Sua sessão expirou. Entre novamente.".
- Sucesso: `replaceRoute(safeReturnPath(navState.returnTo, user.role))`.
- `/login` aberto direto ou recarregado sem `state` → destino `/`. Recarregado com
  `state` → mesmo `returnTo` (o navegador guarda o `state` da entrada).
- Já logado e em `/login` → `replaceRoute(safeReturnPath(...))` assim que a sessão é
  conhecida.
- Nunca `?next=` na URL; nunca URL externa.

| Origem | Depois do login |
| --- | --- |
| Vitrine `/` | `/` |
| `/lots/{id}` | `/lots/{id}` |
| `/login` direto | `/` |
| Área do leiloeiro (redirecionado), entrou como `AUCTIONEER` | a mesma área |
| Área do leiloeiro, entrou como `BIDDER` | `/` |
| `state.returnTo` adulterado (`https://evil.com`, `//evil.com`, `/login`) | `/` |

## 5. Header (`SiteHeader.tsx`)

| Sessão | Itens |
| --- | --- |
| verificando | marca, "Vitrine"; área da conta vazia (sem piscar "Entrar") |
| anônimo | marca, "Vitrine", "Entrar" |
| `BIDDER` | marca, "Vitrine", e-mail · "Licitante", "Sair" |
| `AUCTIONEER` | marca, "Vitrine", "Criar lote", "Meus lotes", e-mail · "Leiloeiro", "Sair" |

- Marca: `AppLink` para `/` (logo + "Casa de Leilões").
- `<nav aria-label="Principal">` com `AppLink`s; `aria-current="page"` no item da rota
  atual ("Vitrine" na vitrine; nenhum na página do lote).
- Sem âncoras "Ao vivo"/"Próximos", busca, carteira, "Meus lances" (blueprint §4,
  links condicionais; story).
- "Sair": `logout()` da 2.2; sucesso → `navigate('/')`; erro → mensagem da 2.2.
- < 30rem: nav e conta quebram para linha própria; o e-mail trunca com `title`.

## 6. Áreas do leiloeiro (D9, D10)

- Sessão verificando: "Verificando sua sessão…" (`role="status"`).
- Anônimo: `replaceRoute('/login', {returnTo: <caminho>})`.
- `BIDDER`: vista com `h1` "Área do leiloeiro", texto "Esta área é só para a conta de
  leiloeiro." e `AppLink` "Ir para a vitrine".
- `AUCTIONEER`: `LotCreation` montado enquanto a sessão for `AUCTIONEER`, com
  `hidden` fora de `/auctioneer/lots/new`; `MyLots` montado só em `/auctioneer/lots`
  (refaz o GET a cada abertura, como na 2.4).
- `LotCreation.onShowMyLots` → `navigate('/auctioneer/lots')`; `MyLots.onCreateLot` →
  `navigate('/auctioneer/lots/new')`.
- `onSessionExpired` (401) → sessão anônima e
  `replaceRoute('/login', {returnTo: <caminho atual>, notice: 'expired'})`.
- Depois do login, o `AUCTIONEER` vai ao `returnTo` (a vitrine, se veio dela), não mais
  direto a "Criar lote" como na 2.4.

## 7. Foco, rolagem e título (D11)

- Cada vista tem um `h1` com `tabIndex={-1}`. Com `navigated === true`, a vista foca o
  seu `h1` ao montar; no primeiro carregamento, não.
- Página do lote: o mesmo `h1` existe em todos os estados ("Carregando lote…", o título,
  "Lote não encontrado", "Não foi possível carregar o lote"), então o foco não se perde
  quando o texto muda.
- Clique num lote na vitrine: antes do `navigate`, `patchCurrentState({restoreLotId,
  endedVisible})`; o `navigate` leva `{fromVitrine: true}`.
- `popstate` de volta à vitrine com `restoreLotId`: depois do `GET`, se o lote está em
  algum grupo, abre os encerrados até ele (`endedVisible`), foca o link
  (`[data-lot-id]`) e o põe na tela (`scrollIntoView({block: 'center'})`); senão foca o
  `h1` e rola ao topo.
- "← Vitrine" na página do lote: com `fromVitrine`, `history.back()` (dispara a regra
  acima); sem, `navigate('/')`.
- `document.title`: "Vitrine — Casa de Leilões", "{título ou Sem título} — Casa de
  Leilões", "Entrar — Casa de Leilões", "Página não encontrada — Casa de Leilões"; as
  áreas do leiloeiro: "Criar lote — …", "Meus lotes — …".

## 8. Página não encontrada

`h1` "Página não encontrada", "O endereço não corresponde a nenhuma página da Casa de
Leilões." e `AppLink` "Ir para a vitrine". Sem chamada à API.

## 9. Atualização de 25/10/2026: marca ÁTRIO

Esta spec foi escrita e aprovada com o nome de trabalho "Casa de Leilões"; o texto acima
fica como foi aprovado. Depois do teste manual, o nome do produto passou a **ÁTRIO — Leilões
de Arte**, e onde a spec diz "Casa de Leilões" vale hoje:

- §5 (marca do header): `AppLink` para `/` com o símbolo ÁTRIO (SVG inline, decorativo) e
  a palavra "ÁTRIO"; nome acessível "ÁTRIO — Leilões de Arte — ir para a vitrine" (contém o texto visível, WCAG 2.5.3); o descritor "Leilões de
  Arte" só a partir de 64 rem.
- §7 (`document.title`): "{página} — ÁTRIO" (`documentTitle` em `src/brand.ts`):
  "Vitrine — ÁTRIO", "{título ou Sem título} — ÁTRIO", "Entrar — ÁTRIO", "Página não
  encontrada — ÁTRIO", "Criar lote — ÁTRIO", "Meus lotes — ÁTRIO".
- §8: "O endereço não corresponde a nenhuma página do ÁTRIO."

Rotas, foco, `returnTo` e o resto da navegação não mudaram.
