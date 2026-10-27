# Front-end — carteira (Story 3.1, P7, P8)

Autoridade: story > `docs/ARQUITETURA.md` > `DESIGN.md` + `EXPERIENCE.md`. Processo:
`docs/FRONTEND-WORKFLOW.md`. Navegação: `../spec-story-2-5-vitrine-publica/frontend-navigation.md`
(adotado; esta spec só acrescenta). Sem React Router, sem dependência nova (AD-4).

## 1. Rota (`src/route.ts`)

| Caminho | `Route` | Quem |
| --- | --- | --- |
| `/bidder/wallet` | `{kind: 'wallet'}` | `BIDDER` |

```ts
export type AppRoute = ... | { kind: 'wallet' }
export function isBidderRoute(route: Route): route is { kind: 'wallet' }
export function isRestrictedRoute(route: Route): boolean   // isAuctioneerRoute || isBidderRoute
// safeReturnPath: rota de BIDDER com role !== 'BIDDER' → '/'
```

`/bidder/wallet/`, `/bidder`, `/bidder/x` → `not-found`. Ida e volta `parseRoute(routePath(r))`.

## 2. `App.tsx`

- Redirecionamento: `isRestrictedRoute(route) && anônimo` → `replaceRoute('/login',
  {returnTo: routePath(route)})` (o `returnTo` vai no `history.state`, nunca na URL).
- Depois do login: `safeReturnPath(navState.returnTo, user.role)` (já existente): `BIDDER`
  volta a `/bidder/wallet`; `AUCTIONEER` vai a `/`.
- `handleSessionExpired`: `returnTo` = `routePath(route)` se `isRestrictedRoute(route)`,
  senão `/`, com `notice: 'expired'`.
- `pageTitle('wallet')` = `documentTitle('Carteira')` ("Carteira — ÁTRIO").
- Vista `wallet`: sessão verificando → "Verificando sua sessão…"; anônimo → `null`
  (redirecionando); `AUCTIONEER` → `BidderOnly`; `BIDDER` → `<WalletPage key={where.id}
  focusHeading={navigated} onSessionExpired={handleSessionExpired} />` (remonta e relê a
  cada navegação).
- `BidderOnly` (espelho de `AuctioneerOnly`): `h1` "Área do licitante" (`tabIndex=-1`,
  focado em navegação), "Esta área é só para a conta de licitante.", `AppLink` "Ir para a
  vitrine". **Não monta `WalletPage`**, então nenhum `GET /api/wallet` sai.

## 3. Header (`SiteHeader.tsx`)

| Sessão | Itens |
| --- | --- |
| verificando | marca, "Vitrine" |
| anônimo | marca, "Vitrine", "Entrar" |
| `BIDDER` | marca, "Vitrine", **"Carteira"** (`/bidder/wallet`, `aria-current` em `wallet`), e-mail · "Licitante", "Sair" |
| `AUCTIONEER` | marca, "Vitrine", "Criar lote", "Meus lotes", e-mail · "Leiloeiro", "Sair" |

O comentário "Nada de carteira…" é atualizado. "Carteira" usa `site-nav-item` (mesmo alvo
de ~44 px por pseudo-elemento). A 375 e 320 px o header do `BIDDER` não pode sobrepor nem
criar rolagem horizontal; se faltar espaço, a regra `< 30rem` existente (nav e conta em
linha própria) resolve, sem esconder "Carteira".

## 4. Cliente (`src/api/wallet.ts`)

```ts
export interface WalletResponse {
  total_balance_cents: number
  committed_balance_cents: number
  available_balance_cents: number
}
export interface DepositRequest { amount_cents: number }

export function isWalletResponse(value: unknown): value is WalletResponse
// os três são inteiros seguros >= 0; committed <= total; available === total - committed

export type WalletReadResult =
  | { ok: true; wallet: WalletResponse }
  | { ok: false; failure: 'unauthorized' | 'forbidden' | 'server' }

export type DepositFailure =
  | 'validation'        // 422 validation_error
  | 'balance_limit'     // 422 balance_limit_exceeded
  | 'unauthorized'      // 401
  | 'forbidden'         // 403 forbidden
  | 'rejected'          // outro 4xx (403 csrf_*, 415, 405…): não chegou a gravar
  | 'ambiguous'         // rede, 5xx, 200 fora do contrato: resultado incerto
export type DepositResult =
  | { ok: true; wallet: WalletResponse }
  | { ok: false; failure: DepositFailure }

export async function fetchWallet(): Promise<WalletReadResult>          // GET /api/wallet
export async function depositToWallet(amountCents: number): Promise<DepositResult>
// POST /api/wallet/deposit, credentials same-origin, Content-Type: application/json
```

Nunca usa o `message` do servidor. Sem retry.

## 5. Textos e decisão pós-depósito (`src/walletFeedback.ts`, puro)

```ts
export type WalletNotice =
  | { kind: 'success'; text: string }      // role="status"
  | { kind: 'error'; text: string }        // erro conhecido; o saldo mostrado não muda
  | { kind: 'uncertain'; text: string }    // erro ambíguo

export function depositSuccessText(amountCents: number): string
//  "Depósito de R$ 1.250,00 confirmado."   (formatCents)
export function depositFailureNotice(failure: KnownDepositFailure): WalletNotice
//  só recusas conhecidas → error com o texto da tabela. (Correção do review, F-08: a
//  decisão "ambíguo → uma releitura" saiu daqui para `walletDeposit.ts`; antes a
//  função devolvia 'reread' para 'ambiguous'.)
export function rereadNotice(reread: WalletReadResult): WalletNotice
//  ok → uncertain "Não foi possível confirmar o depósito. O saldo abaixo é o atual
//        do servidor; confira antes de tentar de novo."
//  falha → uncertain "Não foi possível confirmar se o depósito foi feito. Recarregue a
//        página e confira o saldo antes de tentar de novo."
```

| Falha | Texto |
| --- | --- |
| `validation` | "Informe um valor válido em reais." (no campo, `MoneyField.error`) |
| `balance_limit` | "O depósito ultrapassaria o limite de saldo da carteira." (no campo) |
| `rejected` | "Não foi possível concluir o depósito. Recarregue a página e tente novamente." |
| `forbidden` | "Esta área é só para a conta de licitante." |
| `unauthorized` | não vira texto: `onSessionExpired()` |

Importa `formatCents` de `./money.ts` (extensão `.ts`, para o `node --test`).

## 6. `WalletPage.tsx`

**Estrutura** (`DESIGN.md` §10, `EXPERIENCE.md` §8): `section` com `h1` "Carteira"
(`tabIndex=-1`, foco em navegação interna); `dl` com:

1. "Disponível para lances" — o valor maior, em `--font-display`, o mais acionável;
2. "Saldo total";
3. "Comprometido em lances", com a nota "Reservado nos lotes em que você lidera."

Depois, o formulário "Depósito simulado" com a nota "Valor fictício, sem dinheiro
real.", `MoneyField` (`id="deposit-amount"`, rótulo "Valor do depósito") e botão
primário "Depositar". Sem gráfico, sem card dentro de card, sem movimentos.

**Estados da leitura:** carregando → "Carregando carteira…" (`role="status"`); `server` →
"Não foi possível carregar a carteira." + "Tentar novamente" (novo `GET`); `unauthorized`
→ `onSessionExpired()`; `forbidden` → texto da área do licitante.

**Depósito (P8):**

```text
submit:
  if pending → ignora                         (nunca dois POSTs)
  parseReaisToCents(texto) inválido → erro no campo (moneyErrorMessage), sem POST
  pending = true; botão disabled, rótulo "Depositando…"
  result = await depositToWallet(cents)
  ok        → saldos = result.wallet; campo limpo; notice success
  ambiguous → reread = await fetchWallet()   (uma vez; nunca outro POST)
              reread ok → saldos = reread.wallet
              notice = rereadNotice(reread)
  outro     → depositFailureNotice → erro no campo/formulário; saldos inalterados
  pending = false
```

**Correções do code review (F-01, F-02, F-08, F-12), que valem sobre o texto acima:**

- **Depósito em andamento fora da página (F-08).** O envio e a releitura única vivem em
  `src/walletDeposit.ts` (`startDeposit`, `pendingDepositOf`, `sendDeposit`), num
  registro por conta (o e-mail da sessão), não no estado da `WalletPage`. A página
  remonta a cada navegação (`key={where.id}`); ao montar com um depósito da mesma
  conta pendente, ela nasce com "Depositando…" e o campo travado e mostra o resultado
  daquele mesmo `POST` quando ele termina. O "if pending → ignora" é essa barreira por
  conta, síncrona. O depósito de uma conta nunca bloqueia nem alimenta a tela de outra.
  Uma leitura iniciada antes de um saldo vindo do depósito não o sobrescreve.
- **Campo travado durante o envio (F-01).** `MoneyField` ganha `readOnly` opcional;
  com o `POST` pendente o valor não muda. Ao editar o valor, um aviso de sucesso
  anterior some; o aviso de resultado incerto fica.
- **Regiões vivas (F-02).** Sucesso e resultado incerto vão para um `p role="status"`
  sempre montado dentro do formulário (muda só o conteúdo); erro conhecido do
  formulário usa `role="alert"`.
- **Lista de saldos (F-12).** `dl` com um nível só: cada `div` agrupa diretamente o seu
  `dt`/`dd`; o total e o comprometido ficam lado a lado pelo grid do próprio `dl`.

Erro com "✕ " e sucesso com "✓ " em `aria-hidden` mais o texto (estado nunca só por
cor). Os valores sempre vêm do servidor (resposta do `POST` ou do `GET`), nunca de uma
soma no front.

**Responsivo:** a 375 e 320 px os três números empilham (disponível primeiro), o valor
máximo quebra sem estourar (`overflow-wrap: anywhere` no valor), formulário em coluna,
botão com largura total no celular. Sem rolagem horizontal.

## 7. Arquivos

Novos: `src/api/wallet.ts`, `src/api/wallet.test.ts`, `src/walletFeedback.ts`,
`src/walletFeedback.test.ts`, `src/WalletPage.tsx`. Alterados: `src/route.ts`,
`src/route.test.ts`, `src/App.tsx`, `src/SiteHeader.tsx`, `src/App.css` (seção
"Carteira"). Intocados: `money.ts`, `MoneyField.tsx`, `navigation.ts`, `AppLink.tsx`,
`api/auth.ts`, telas da 2.4 e 2.5. *(Correções do review: nasceram
`src/walletDeposit.ts` e `src/walletDeposit.test.ts` (F-08), e `MoneyField.tsx` ganhou
só a prop opcional `readOnly` (F-01), sem efeito no formulário de lote da 2.4.)*
