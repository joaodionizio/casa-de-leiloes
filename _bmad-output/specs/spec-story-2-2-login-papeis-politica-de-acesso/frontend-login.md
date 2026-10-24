# Front-end — tela de login e conta (Story 2.2)

Autoridade: story/enunciado > `docs/ARQUITETURA.md` > `DESIGN.md` +
`EXPERIENCE.md` > referências. Processo: `docs/FRONTEND-WORKFLOW.md`. Não há
blueprint desta tela; `VITRINE-BLUEPRINT.md` não se aplica.

## 1. Estado atual

- `App.tsx`: título "Casa de Leilões", tagline e linha de estado do `GET /health` (critério da 1.3), estilo de pill em `App.css`.
- `src/api/health.ts`: `fetch` + type guard; padrão a seguir.
- `index.css`: fonte do sistema, sem tokens. Dependências: só `react`/`react-dom`. `tsconfig` com `strict` e `erasableSyntaxOnly` (sem parameter properties nem `enum` do TS).
- Vite: proxy de `/api` e `/health` para `127.0.0.1:8000`, porta fixa 5173.

## 2. O que os artefatos já decidiram (não reabrir)

| Fonte | Decisão aplicada aqui |
| --- | --- |
| AD-11, AD-29 | Sessão só no cookie HttpOnly; o JS nunca lê token; nada em `localStorage`/`sessionStorage`. |
| AD-4 | TypeScript simples: `interface`, `type`, unions simples, `Promise<T>`, contratos HTTP tipados; sem generics complexos. |
| AD-30, EXPERIENCE §5 | Interface "Leiloeiro"/"Licitante"; código `AUCTIONEER`/`BIDDER`. |
| EXPERIENCE §2, CLAUDE.md | Só controles que funcionam nesta story: sem link de Vitrine, Carteira, Meus lotes, Criar lote, Meus arremates, busca, cadastro, "esqueci a senha", "lembrar de mim", login social. |
| EXPERIENCE §3 Header | Header = marca + entrada/conta. "Vitrine" entra na 2.5. |
| EXPERIENCE §5 | Não promover ação proibida ao papel. |
| DESIGN §2–§3 | Tokens de cor exatos; roxo só em marca, ação primária, foco. |
| DESIGN §4 | `--font-ui` para formulário, botões, estados; `--font-display` só na marca. |
| DESIGN §5 | Formulário = campos e divisores, não card; sem sombra, pill, badge, gradiente, glow, ícone decorativo. |
| DESIGN §13, EXPERIENCE §18 | Sem rolagem horizontal em 320 px; desktop largo sem esticar campos. |
| DESIGN §14 | Foco visível, contraste, controles semânticos, `aria-live` onde necessário; estado nunca só por cor. |
| DESIGN §15–16 | Sem cara de SaaS/curso/fintech; nada de autenticação fake ou dados demo na tela. |
| FRONTEND-WORKFLOW §6–7 | `bmad-build` mostra plano em ≤ 8 linhas antes de editar; teste manual no navegador antes do review. |

## 3. O que esta spec decide (para não ficar ao implementador)

### Arquivos

- `src/index.css`: bloco `:root` com os tokens de cor de DESIGN §3 e `--font-ui`/`--font-display` de §4, exatamente com os valores dos artefatos; `body` com `background: var(--color-canvas)`, `color: var(--color-text)`, `font-family: var(--font-ui)`. Nenhum token novo além dos de DESIGN, salvo espaçamento se precisar (nome `--space-*`).
- `src/api/auth.ts` (novo): tipos e chamadas (§4).
- `src/App.tsx`: estado da sessão e composição.
- `src/LoginForm.tsx` e `src/SiteHeader.tsx` (novos): formulário e cabeçalho. Sem pasta de "design system".
- `src/App.css`: estilos da tela; remove o pill do health.

### Composição

- **Header** (sempre): à esquerda, `favicon.svg` (decorativo, `alt=""`) + "Casa de Leilões" em `--font-display`, texto simples (não link, não heading). À direita, só quando autenticado: e-mail, separador textual, papel ("Leiloeiro"/"Licitante") em texto simples (não badge), botão "Sair". Divisor inferior de 1 px `--color-border`. Em 320 px a conta quebra para a linha de baixo; e-mail longo trunca com reticências e mantém o valor completo em `title`.
- **Main, anônimo:** `<section>` com `<h1>Entrar</h1>`, formulário em coluna única: rótulo acima do campo, "E-mail", "Senha", botão primário "Entrar". Largura limitada para leitura no desktop, largura total menos as margens no mobile; alinhamento à esquerda dentro da coluna.
- **Main, autenticado:** `<h1>` visualmente oculto "Casa de Leilões"; nenhum conteúdo novo (a vitrine é a 2.5).
- **Sempre, depois do conteúdo principal:** tagline atual e linha de estado do `/health` em texto `--color-muted`, tamanho pequeno, sem borda, sem pill (mantém o critério da 1.3).
- **Visual:** fundo `--color-canvas`; campos com borda 1 px `--color-border`, raio 0–2 px, fundo `--color-surface`; botão primário fundo `--color-brand`, texto branco, raio 0–2 px, hover `--color-brand-strong`; "Sair" secundário (texto/sublinhado ou borda `--color-border`, nunca fundo roxo); foco `outline` 2 px `--color-brand-strong` com `offset`; erro em `--color-danger` sempre com o texto da mensagem.

### Comportamento

- Estado da sessão: `type SessionState = { status: 'checking' } | { status: 'anonymous' } | { status: 'authenticated'; user: CurrentUser }`.
- Ao montar: `fetchCurrentUser()` → `checking` mostra "Verificando sua sessão…" (`role="status"`); 200 → `authenticated`; 401 → `anonymous`; falha → `anonymous` + mensagem de servidor indisponível.
- Formulário: `noValidate` (mensagens nativas do navegador podem sair em outra língua); `type="email"` + `autoComplete="username"`; `type="password"` + `autoComplete="current-password"`; `<label htmlFor>` em cada campo.
- Envio: e-mail vazio (após `trim`) ou senha vazia → "Informe e-mail e senha." sem requisição. Senão botão desabilitado com "Entrando…", campos `readOnly`, uma requisição por vez.
- Sucesso: usa o `CurrentUser` da resposta do login (sem chamar `/api/me` de novo) → `authenticated`; limpa a senha da memória do estado.
- Falha: mensagem num elemento com `role="alert"` ligado ao formulário (`aria-describedby`); mantém o e-mail, limpa a senha e devolve o foco ao campo de senha.
- "Sair": botão desabilitado com "Saindo…"; 204 → `anonymous`, campos vazios, foco no campo de e-mail; falha → continua `authenticated` e mostra a mensagem ao lado do botão (`role="alert"`).
- Enter envia; ordem de Tab: e-mail, senha, Entrar; no header, Sair.
- O papel exibido vem só da resposta do servidor; o cliente não deduz permissões.

## 4. Contrato tipado (`src/api/auth.ts`)

```ts
export type UserRole = 'AUCTIONEER' | 'BIDDER'
export interface CurrentUser { email: string; role: UserRole }
export interface ApiErrorBody { status: number; code: string; message: string }
export type AuthFailure = 'invalid_credentials' | 'validation' | 'server' | 'rejected'
export type LoginResult = { ok: true; user: CurrentUser } | { ok: false; failure: AuthFailure }
export type MeResult = { ok: true; user: CurrentUser } | { ok: false; failure: 'anonymous' | 'server' }
export type LogoutResult = { ok: true } | { ok: false; failure: 'server' | 'rejected' }
```

- `fetchCurrentUser(): Promise<MeResult>`, `login(email, password): Promise<LoginResult>`, `logout(): Promise<LogoutResult>`; nunca lançam para o componente.
- `fetch` relativo (`/api/...`), `credentials: 'same-origin'`, `Content-Type: application/json` no login (corpo `JSON.stringify({ email, password })`) e no logout (sem corpo).
- Type guards como em `health.ts` (`isCurrentUser`, `isApiErrorBody`); corpo inesperado → `server`.
- Mapeamento: `fetch` rejeitado, corpo não JSON ou status ≥ 500 → `server`; 401 com `code === 'invalid_credentials'` → `invalid_credentials`; 422 → `validation`; demais 4xx (`csrf_*`, 415, 405) → `rejected`; em `/api/me`, 401 → `anonymous`. O texto exibido nunca vem do `message` do servidor.
- Nada de `document.cookie`, `localStorage` ou `sessionStorage`.

## 5. Textos (pt-BR)

| Situação | Texto |
| --- | --- |
| Verificando sessão | Verificando sua sessão… |
| Título do formulário / botão | Entrar |
| Enviando | Entrando… |
| Rótulos | E-mail · Senha |
| Campo vazio / `validation` | Informe e-mail e senha. |
| `invalid_credentials` | E-mail ou senha inválidos. |
| `server` | Não foi possível falar com o servidor. Tente novamente. |
| `rejected` | Não foi possível concluir a operação. Recarregue a página e tente novamente. |
| Papel | Leiloeiro · Licitante |
| Botão de saída / saindo | Sair · Saindo… |

## 6. Proibido improvisar

Card/caixa com sombra ou cantos arredondados em volta do formulário; fundo ou
hero roxo; gradiente; ilustração; ícones decorativos; "Bem-vindo de volta"; badge
ou pill de papel; credenciais demo na tela; botão de mostrar senha; links ou
itens de menu sem rota; spinner chamativo; fontes externas; biblioteca de UI;
React Router; biblioteca de testes; qualquer persistência no cliente.
