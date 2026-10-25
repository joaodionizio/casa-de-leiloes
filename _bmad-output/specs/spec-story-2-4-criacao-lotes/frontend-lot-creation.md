# Front-end — criação de lote e "Meus lotes" (Story 2.4)

Autoridade: story > `docs/ARQUITETURA.md` > `DESIGN.md` + `EXPERIENCE.md`. Processo:
`docs/FRONTEND-WORKFLOW.md`. Não é a Vitrine (`VITRINE-BLUEPRINT.md` não se aplica).
Base: os componentes da 2.3 (`frontend-catalog.md` da 2.3) e o padrão de cliente de
`src/api/auth.ts`/`catalog.ts` (`fetch` same-origin, type guards, uniões de falha,
texto pelo `code`).

## 1. Regras aplicadas

| Fonte | Aplicação |
| --- | --- |
| DESIGN §1, §5 | Obra antes dos campos no formulário, na revisão e na confirmação; formulário como campos e divisores, sem card, sombra, pill ou badge. |
| DESIGN §10, EXPERIENCE §7, §16 | "Meus lotes" como lista densa; no mobile, blocos densos, não cards. |
| EXPERIENCE §2, CLAUDE.md | Só controles com função: sem "Vitrine", sem cancelar, sem editar, sem resultado, sem filtro, sem estado do lote. |
| EXPERIENCE §5 | Leiloeiro: "Criar lote" e "Meus lotes" ("Vitrine" só na 2.5). Licitante: nada novo. |
| EXPERIENCE §6 | buscar → escolher → conferir → início/fim → lance inicial → incremento → revisão → publicar. |
| DESIGN §14 | Erros por campo com `aria-describedby` e `aria-invalid`; estados nunca só por cor; foco visível. |
| AD-6, P4 | O navegador nunca é a autoridade sobre "agora": "começar agora" envia `starts_at: null` e quem decide é o servidor, com `clock_timestamp()`. A tela PODE comparar com `new Date()` (injetado como `now`) só como validação **preventiva** de UX, para não deixar um horário obviamente passado chegar à revisão; essa comparação não é regra de domínio e o servidor revalida tudo. |
| P5, D13 | Reais → centavos por texto; valores exibidos formatados a partir dos centavos. |
| 2.2 P15 | Texto pelo `code`/`details.type`, nunca pelo `message`. |

## 2. Estrutura

```text
App (authenticated)
├─ SiteHeader                 + <nav aria-label="Painel do leiloeiro"> só para AUCTIONEER:
│                               botões "Criar lote" | "Meus lotes" (aria-current="page" no ativo)
└─ main
   ├─ AUCTIONEER, view 'create': <LotCreation onSessionExpired onShowMyLots />
   │   ├─ etapa catalog  → <CatalogSearch onCreateLot> (sempre montado; `hidden` fora desta etapa)
   │   │                    └─ ArtworkDetailPanel: botão "Criar lote com esta obra" (só no estado pronto)
   │   ├─ etapa form     → <LotForm artwork draft onReview onBack>
   │   ├─ etapa review   → <LotReview artwork request onPublish onEdit>  (envio e erros)
   │   └─ etapa created  → <LotCreated lot onShowMyLots onCreateAnother>
   ├─ AUCTIONEER, view 'mine':   <MyLots onSessionExpired onCreateLot />  (montado ao abrir → refaz o GET)
   └─ BIDDER: como hoje
```

- `App.tsx` guarda `auctioneerView: 'create' | 'mine'` (padrão `'create'`, que preserva o
  pouso da 2.3). `LotCreation` fica montado e oculto (`hidden`) quando a vista é
  `'mine'`, para não perder busca nem rascunho; `MyLots` monta a cada abertura, então a
  lista é sempre relida (inclusive depois de criar).
- `LotCreation` guarda a etapa e o rascunho:
  `{kind:'catalog'} | {kind:'form'; artwork; draft} | {kind:'review'; artwork; draft; request} | {kind:'created'; lot}`.
  O rascunho sobrevive a form ↔ review e a qualquer erro do `POST`.
- "Ver meus lotes" (na confirmação) chama `onShowMyLots()`; `LotCreation` volta à etapa
  `catalog`, com a busca anterior intacta.
- Sem React Router; recarregar volta a "Criar lote" no estado inicial.

## 3. Arquivos

| Arquivo | Ação |
| --- | --- |
| `src/api/lots.ts` | novo: tipos e cliente (§6) |
| `src/money.ts` | novo: `parseReaisToCents`, `formatCents`, `MAX_CENTS` (§4) |
| `src/money.test.ts` | novo: `node:test` (Q1, §4.1) |
| `package.json` | script `"test"`; `"typecheck"` passa a checar também `tsconfig.node.json` |
| `tsconfig.app.json` | `"exclude": ["src/**/*.test.ts"]` |
| `tsconfig.node.json` | `"include"` ganha `"src/**/*.test.ts"` (já tem `types: ["node"]`) |
| `../verify.sh` | etapa "Frontend: test" entre "typecheck" e "build" |
| `src/lotTime.ts` | novo: `localInputToIso`, `formatDateTime`, `browserTimeZone` (§5) |
| `src/LotCreation.tsx` | novo: etapas e envio |
| `src/LotForm.tsx`, `src/LotReview.tsx`, `src/LotCreated.tsx`, `src/MyLots.tsx` | novos |
| `src/ArtworkDetailPanel.tsx` | prop opcional `onCreateLot?: (artwork: ArtworkDetail) => void` e o botão |
| `src/CatalogSearch.tsx` | repassa `onCreateLot` ao painel; nada mais muda |
| `src/SiteHeader.tsx` | navegação do leiloeiro (props `view`, `onNavigate`) |
| `src/App.tsx` | `auctioneerView`; renderiza `LotCreation`/`MyLots` |
| `src/App.css` | seções "Navegação do leiloeiro", "Criação de lote", "Meus lotes" |

## 4. Dinheiro (`money.ts`, D13)

```ts
export const MAX_CENTS = 9007199254740991          // igual ao back-end (D3)
export type MoneyError = 'empty' | 'format' | 'too_many_decimals' | 'not_positive' | 'too_large'
export type MoneyParse = { ok: true; cents: number } | { ok: false; error: MoneyError }
export function parseReaisToCents(input: string): MoneyParse
export function formatCents(cents: number): string   // "R$ 1.250,00"
```

`parseReaisToCents`, nesta ordem:

1. `s = input.trim()`; vazio → `empty`.
2. Se `s` casa `^[\d.]+,\d{3,}$` → `too_many_decimals`.
3. Se `s` não casa `^(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?$` → `format`.
4. `int = parte antes da vírgula sem pontos`; `frac = parte depois da vírgula` completada à
   direita com `0` até 2 dígitos (`""` → `"00"`, `"5"` → `"50"`).
5. `digits = (int + frac)` sem zeros à esquerda (`""` → `"0"`).
6. `digits === "0"` → `not_positive`.
7. `digits.length > 16` ou (`length === 16` e `digits > "9007199254740991"`, comparação de
   texto) → `too_large`.
8. `cents = Number(digits)` (inteiro ≤ 2^53 − 1: conversão exata).

Nenhum `parseFloat`, nenhuma multiplicação por 100, nenhum `Number` sobre texto com
vírgula ou ponto.

| Entrada | Resultado |
| --- | --- |
| `10` | 1000 |
| `10,5` | 1050 |
| `0,50` | 50 |
| `1.234,56` | 123456 |
| `1234,56` | 123456 |
| `  100,00  ` | 10000 |
| `90.071.992.547.409,91` | 9007199254740991 |
| `90.071.992.547.409,92` | `too_large` |
| (vazio), `   ` | `empty` |
| `0`, `0,00`, `000` | `not_positive` |
| `1,234`, `10,999` | `too_many_decimals` |
| `10.5`, `12.50`, `333.55` (ponto onde o pt-BR usa vírgula) | `dot_decimal` |
| `abc`, `-5`, `R$ 10`, `1.23,45`, `1.2345`, `,50`, `10,`, `1 000`, `10.000.0`, `1e3` | `format` |

`formatCents`: `s = String(cents).padStart(3, '0')`; reais = `s.slice(0, -2)` agrupado de 3
em 3 com `.` da direita para a esquerda; centavos = `s.slice(-2)`; `"R$ " + reais + "," +
centavos`. Exemplos: 50 → `R$ 0,50`; 123456 → `R$ 1.234,56`; 9007199254740991 →
`R$ 90.071.992.547.409,91`. Sem `Intl` e sem divisão.

Mensagens no campo:

| Erro | Texto |
| --- | --- |
| `empty` | "Informe o valor." |
| `format` | "Use só números, com vírgula para os centavos. Ex.: 1.250,00" |
| `dot_decimal` | "Use vírgula para os centavos. Ex.: 333,55." (o exemplo vem do que foi digitado) |
| `too_many_decimals` | "Use no máximo duas casas decimais." |
| `not_positive` | "O valor precisa ser maior que zero." |
| `too_large` | "Valor alto demais." |

O campo é `<input type="text" inputMode="decimal" autoComplete="off">` com o prefixo
visível "R$" fora do input e a dica "Digite o valor em reais. Use vírgula para centavos. Ex.:
5,50 ou 1.250,00." ligada por `aria-describedby`. O
texto digitado não é reformatado; a revisão mostra o valor a partir dos centavos.

`money.ts` é TypeScript apagável (sem `enum`, sem `namespace`, sem parâmetro de
propriedade: o `tsconfig` já exige `erasableSyntaxOnly`), não usa DOM nem `import.meta`,
para rodar no Node sem transpilador.

### 4.1 Teste automatizado (Q1)

- **Arquivo:** `frontend/src/money.test.ts`, importando `./money.ts` (extensão
  explícita; `allowImportingTsExtensions` já está ligado) e `node:test` /
  `node:assert/strict`.
- **Comando:** `npm test` = `node --test "src/**/*.test.ts"` (Node 24, type stripping
  nativo; nenhuma dependência nova). Sai com código ≠ 0 em qualquer falha.
- **Tipos:** o arquivo fica fora do `tsconfig.app.json` (que só conhece `vite/client`) e
  dentro do `tsconfig.node.json` (que já tem `types: ["node"]`); `npm run typecheck` =
  `tsc --noEmit -p tsconfig.app.json && tsc --noEmit -p tsconfig.node.json`. O build do
  Vite não inclui o teste (nada o importa).
- **ESLint:** o arquivo entra no `eslint .` atual sem regra nova.
- **`verify.sh`:** depois de "Frontend: typecheck", `echo "=== Frontend: test ==="` e
  `npm test`; o `set -euo pipefail` já faz a etapa falhar o `verify`.
- **Casos:** `test-plan.md` §8.

## 5. Horários (`lotTime.ts`)

- "Início" é um `fieldset` com `legend` e dois rádios: **"Assim que eu publicar"**
  (padrão → `starts_at: null`) e **"Agendar"** (mostra
  `<input type="datetime-local">` "Data e hora de início").
- "Término": `<input type="datetime-local">` obrigatório.
- Nota sob o fieldset: "Horários no fuso deste navegador ({browserTimeZone()})."
  (`Intl.DateTimeFormat().resolvedOptions().timeZone`).
- `localInputToIso(value)`: exige `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$`; `new Date(value)`
  (sem offset = horário local, ECMAScript); inválido → `null`; senão `toISOString()` (UTC,
  `Z`). É só a tradução do horário de parede que o usuário escolheu; a validade é do
  servidor.
- `formatDateTime(iso)`: `Intl.DateTimeFormat('pt-BR', {day:'numeric', month:'short',
  year:'numeric', hour:'2-digit', minute:'2-digit', timeZoneName:'short'})`. Exibição,
  nunca decisão. Não combinar `dateStyle`/`timeStyle` com `timeZoneName`: o `Intl` lança
  `TypeError: Invalid option : option` (foi a tela branca do primeiro teste manual).
- Checagem local antes da revisão, **preventiva** (`checkDraft(externalId, draft, now)`,
  com `now` injetado; o formulário passa `new Date()`): agendado sem valor → "Informe a data
  e a hora de início."; término sem valor → "Informe a data e a hora de término."; valor que
  não converte → "Data e hora inválidas."; "assim que eu publicar" com término `<=` agora →
  "O término precisa ser depois do momento da publicação."; início agendado `<=` agora →
  "O início agendado já passou. Escolha um horário futuro."; agendado e término `<=` início →
  "O término precisa ser depois do início." Nenhum `min` no input. O servidor, com a hora do
  PostgreSQL, continua sendo a autoridade final e repete todas as regras.
  **Histórico:** a primeira versão desta spec não comparava com o relógio do navegador;
  o teste manual de 25/10/2026 mostrou um término passado chegando à revisão, e a regra foi
  revisada para a forma acima. O resto desta nota: "Revisar lote" revalida o valor atual; não há botão nem estado de
  confirmação (tentado e removido no último reteste). O `DateTimeField` é o `datetime-local`
  com um resumo do horário. O "Valor reconhecido" aparece sob o campo de dinheiro
  (`MoneyField`), e `655.3` dá a mensagem "Use vírgula para os centavos. Ex.: 655,30.".
- Horário inexistente no fuso local (mudança de horário de verão) é ajustado pelo
  navegador; a revisão mostra o horário resultante.

## 6. Cliente (`api/lots.ts`)

```ts
export interface LotResponse { id: string; external_id: number; title: string | null;
  artist_display: string | null; date_display: string | null; medium_display: string | null;
  dimensions: string | null; department_title: string | null; artwork_type_title: string | null;
  credit_line: string | null; source_url: string; image_id: string; image_url: string;
  starting_bid_cents: number; min_increment_cents: number;
  starts_at: string; ends_at: string; created_at: string }

export interface CreateLotRequest { external_id: number; starting_bid_cents: number;
  min_increment_cents: number; starts_at: string | null; ends_at: string }

export type LotField = 'starting_bid_cents' | 'min_increment_cents' | 'starts_at' | 'ends_at'
export interface FieldProblem { field: LotField | null; type: string }

export type CreateLotFailure =
  | { kind: 'validation'; problems: FieldProblem[] }
  | { kind: 'not_eligible' } | { kind: 'unavailable' }
  | { kind: 'unauthorized' } | { kind: 'forbidden' }
  | { kind: 'unknown' }                 // rede, 5xx, 403 csrf, corpo fora do contrato
export type CreateLotResult = { ok: true; lot: LotResponse } | { ok: false; failure: CreateLotFailure }

export type MyLotsFailure = 'unauthorized' | 'forbidden' | 'server'
export type MyLotsResult = { ok: true; items: LotResponse[] } | { ok: false; failure: MyLotsFailure }

export function createLot(request: CreateLotRequest): Promise<CreateLotResult>
export function fetchMyLots(signal: AbortSignal): Promise<MyLotsResult>
```

`createLot`: `POST /api/lots`, `credentials: 'same-origin'`, `Content-Type:
application/json` (o `Origin` o navegador envia). Mapeamento: 201 com `isLotResponse` →
ok; 422 `validation_error` → `validation` com `details` (`loc[0] === 'body'` e `loc[1]`
em `LotField` → `field`; senão `field: null`); 422 `artwork_not_eligible` →
`not_eligible`; 503 `catalog_unavailable` → `unavailable`; 401 → `unauthorized`; 403
`forbidden` → `forbidden`; todo o resto → `unknown`.
`fetchMyLots`: `GET /api/lots/mine`; 200 com `items` válidos → ok; 401/403; resto →
`server`. Lote nunca vai a `localStorage`/`sessionStorage`.

## 7. Telas e estados

### 7.1 Detalhe da obra (2.3, alterado)
No estado "pronto", depois da linha "Domínio público", botão primário **"Criar lote com
esta obra"** → etapa `form` com o `ArtworkDetail` exibido. Em carregando/falha, o botão
não existe.

### 7.2 Formulário (`LotForm`)
- `h2` "Criar lote" (`tabIndex={-1}`, recebe o foco ao entrar).
- Obra, só leitura: imagem (`ArtworkImage` `large`, `max-height` 40vh no mobile), título
  (`--font-display`), artista, data, "Nº no acervo". Muted: "Os dados da obra são
  copiados do acervo do museu no momento da publicação."
- `fieldset` "Valores": "Lance inicial" e "Incremento mínimo" (§4).
- `fieldset` "Período": "Início" e "Término" (§5).
- Ações: **"Revisar lote"** (primário) e "Voltar à obra" (secundário; volta ao detalhe
  com a busca intacta).
- "Revisar lote" valida tudo localmente; com erro, marca os campos (`aria-invalid`,
  mensagem por `aria-describedby`) e foca o primeiro inválido; sem erro, monta o
  `CreateLotRequest` e vai para `review`.
- Erros de servidor que voltam para cá (de §7.3) aparecem nos campos com os textos de §8.

### 7.3 Revisão (`LotReview`)
- `h2` "Revise o lote" (foco ao entrar); obra (miniatura, título, artista).
- `<dl>`: Lance inicial `formatCents`, Incremento mínimo `formatCents`, Início ("Assim que
  você publicar, pelo horário do servidor" ou `formatDateTime`), Término.
- Muted: "O servidor confere os horários no momento da publicação."
- Ações: **"Publicar lote"** (primário) e "Editar" (volta ao `form` com o rascunho).
- Envio: `submitting` por `useRef` **e** estado; um segundo clique ou Enter enquanto
  pendente não chama `createLot` de novo; o botão vira "Publicando…" desabilitado e a
  região tem `aria-busy="true"`; "Editar" também fica desabilitado.
- Resultados:

| Resultado | Comportamento |
| --- | --- |
| ok | etapa `created` |
| `validation` com `field` | volta ao `form` com os erros nos campos (§8); rascunho mantido |
| `validation` sem `field` | `role="alert"`: "Não foi possível criar o lote com esses dados. Revise e tente de novo." + "Editar" |
| `not_eligible` | `role="alert"`: "Esta obra não pode virar lote: só obras de domínio público com imagem no acervo do museu." + "Voltar à busca" (sem "Tentar novamente") |
| `unavailable` | `role="alert"`: "O catálogo do museu não respondeu e o lote não foi criado. Seus dados foram mantidos; tente novamente em instantes." + **"Tentar novamente"** (reenvia o mesmo pedido) + "Editar" |
| `unauthorized` | `onSessionExpired()` ("Sua sessão expirou. Entre novamente.") |
| `forbidden` | `role="alert"`: "Sua conta não pode criar lotes." |
| `unknown` | `role="alert"`: "Não foi possível confirmar se o lote foi criado. Confira em Meus lotes antes de tentar de novo." + "Ver meus lotes" + "Tentar novamente" (P7) |

### 7.4 Confirmação (`LotCreated`)
- `h2` "Lote criado" (foco), com `✓` `aria-hidden`; texto, não só cor.
- Resumo **do que o servidor gravou** (`LotResponse`): obra, lance inicial, incremento,
  início (`starts_at` do servidor), término, "Criado em".
- Ações: **"Ver meus lotes"** (primário) e "Criar outro lote" (volta à busca).
- Nenhum link de vitrine, sala ou cancelar.

### 7.5 Meus lotes (`MyLots`)
- `h1` "Meus lotes" (foco ao abrir pela navegação); muted "N lotes" (o servidor devolve
  todos, sem limite nem paginação, A2).
- Estados: carregando ("Carregando seus lotes…", `role="status"`); vazio ("Você ainda não
  criou lotes." + botão "Criar lote", que muda a vista); falha ("Não foi possível carregar
  seus lotes." + "Tentar novamente"); 401 → `onSessionExpired`; 403 → "Sua conta não tem
  acesso a esta lista."
- Linha (`<ul>` sem marcadores, divisor `1px var(--color-border)`): miniatura (`ArtworkImage`
  `thumb`, `loading="lazy"`), título (`--font-display`, até 2 linhas, `title` com o nome
  completo; `null` → "Sem título" itálico muted), artista (muted, 1 linha) e `<dl>` com
  Início, Término, Lance inicial, Incremento (`dt` muted pequeno, `dd` com
  `font-variant-numeric: tabular-nums`).
- Ordem do servidor (mais recente primeiro). Sem estado, sem ação por linha, sem filtro.
- Com a AIC fora, só as miniaturas caem no placeholder (CA9).

## 8. Erros de servidor nos campos

| `field` / `type` | Texto |
| --- | --- |
| `starts_at` / `starts_at_not_in_future` | "O início agendado já passou. Escolha um horário futuro." |
| `ends_at` / `ends_at_not_after_start` | "O término precisa ser depois do início." (com "Assim que eu publicar": "…depois do momento da publicação.") |
| `starts_at`/`ends_at` / `datetime_format`, `timezone_aware`, outro | "Data e hora inválidas." |
| `starting_bid_cents`/`min_increment_cents` / qualquer | "Valor inválido." |

## 9. Responsividade

- ≥ 64rem: formulário e revisão em duas colunas (obra `2fr`, sticky `top: 1rem` | campos
  `3fr`); "Meus lotes" com a linha em grade: miniatura 4.5rem | obra `minmax(14rem, 2fr)`
  | quatro colunas `minmax(8rem, 1fr)` para o `<dl>`.
- < 64rem: uma coluna; obra compacta no topo; "Meus lotes" com miniatura + textos e o
  `<dl>` em grade 2 × 2 abaixo.
- 320 px: sem rolagem horizontal; inputs `width: 100%`; `overflow-wrap: anywhere` em
  títulos e valores; R$ 90.071.992.547.409,91 cabe quebrando.
- Navegação do header: os dois botões quebram para linha própria em < 30rem.

## 10. Checagens

`npm run lint`, `npm run typecheck`, `npm test` (`money.ts`, Q1) e `npm run build` no
`verify`, nessa ordem; roteiro manual em `test-plan.md` §9. Componentes sem teste
automatizado.
