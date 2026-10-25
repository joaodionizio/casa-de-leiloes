# Front-end — vitrine e página do lote (Story 2.5)

Fontes vinculantes no escopo visual: `DESIGN.md`, `EXPERIENCE.md`,
`VITRINE-BLUEPRINT.md` (mesmo nível; subordinados à story e à ARQUITETURA). Regra
prática: roxo é assinatura, a obra é a protagonista; nenhum controle sem função.

## 1. Dados e cliente (`src/api/publicLots.ts`)

```ts
export type PublicLotsResult =
  | { ok: true; data: PublicLotsResponse } | { ok: false; failure: 'server' }
export type PublicLotResult =
  | { ok: true; data: PublicLotDetailResponse }
  | { ok: false; failure: 'not_found' | 'server' }

export function fetchPublicLots(signal: AbortSignal): Promise<PublicLotsResult>
export function fetchPublicLot(lotId: string, signal: AbortSignal): Promise<PublicLotResult>
```

- `GET /api/lots` e `GET /api/lots/{id}`, `credentials: 'same-origin'`. 200 que passa no
  guard → ok; 404 ou 422 → `not_found`; rede, 5xx, corpo fora do contrato → `server`;
  `AbortError` é ignorado pelo chamador.
- Os componentes públicos só chamam essas duas rotas e o `src` das imagens. Nunca
  `/api/catalog/artworks*`, nunca `CatalogSearch`.
- Cada montagem da vitrine ou da página do lote faz um `GET` novo (P3: a fase muda só
  aí). Sem temporizador, sem `Date.now()` para estado.

## 2. Lógica pura (`src/lotPhase.ts`, `src/vitrine.ts`, testadas)

```ts
// lotPhase.ts
export function phaseLabel(phase: LotPhase): string
  // 'scheduled' → 'Agendado'; 'live' → 'Ao vivo'; 'ended' → 'Encerrado'
export function phaseStatusText(phase: LotPhase): string
  // igual, exceto 'ended' → 'Encerrado, apurando resultado' (P8)

// vitrine.ts
export const ENDED_STEP = 6
export type Featured =
  | { kind: 'live'; lot: PublicLotSummary }
  | { kind: 'scheduled'; lot: PublicLotSummary }
  | { kind: 'none' }
export function selectFeatured(data: PublicLotsResponse): Featured // live[0] ?? scheduled[0]
export function railItems(group: PublicLotSummary[], featured: Featured): PublicLotSummary[]
  // o grupo sem o lote em destaque (compara por id)
export function nextEndedVisible(current: number, total: number): number
  // min(current + ENDED_STEP, total)
export function initialEndedVisible(total: number, restore?: number): number
  // restore válido (inteiro, ≥ ENDED_STEP) → min(restore, total); senão min(ENDED_STEP, total)
export function railScrollState(scrollLeft: number, clientWidth: number,
                                scrollWidth: number): { overflow: boolean; canPrev: boolean; canNext: boolean }
  // overflow = scrollWidth - clientWidth > 1; tolerância de 1 px nas pontas
```

Nenhuma função compara datas nem decide fase.

### 2.1 Indicador da situação (`src/asOf.ts`, D16, testado)

```ts
// "Situação atualizada às 14:30"                    (as_of no mesmo dia de `today`)
// "Situação atualizada em 25/10/2026 às 14:30"       (outro dia)
// null                                               (as_of ilegível: a linha não aparece)
export function asOfText(asOf: string, today: Date, timeZone?: string): string | null
```

- Fuso do navegador (ou `timeZone`, só nos testes); 24 h (`hourCycle: 'h23'`);
  `DD/MM/AAAA` por `Intl.DateTimeFormat('pt-BR', {day: '2-digit', month: '2-digit',
  year: 'numeric'})`. "Mesmo dia" = as duas datas formatadas no mesmo fuso são iguais
  (sem aritmética de datas). Nunca combinar `dateStyle`/`timeStyle` com
  `timeZoneName` (tela branca da 2.4).
- `today` só escolhe entre as duas formas do texto. A linha não se atualiza sozinha,
  não inicia relógio, não recalcula `phase` e não usa `Date.now()` para domínio: é a
  data da fotografia que o servidor produziu (P3).
- Visual: texto pequeno, `--color-muted`, sem ícone; vitrine abaixo do destaque; página
  do lote sob os termos do leilão.

## 3. Composição da vitrine (`Vitrine.tsx`)

Ordem (EXPERIENCE §3, blueprint §3): header → destaque → "Ao vivo" → "Próximos lotes"
→ "Encerrados". `h1` visualmente oculto "Vitrine"; cada seção um `h2`; títulos de lote
`h3`.

### 3.1 Destaque (`FeaturedLot.tsx`, D12)

- Seleção: `selectFeatured` (`live[0]`, senão `scheduled[0]`). `h2` visualmente oculto
  "Em destaque".
- Desktop ≥ 64rem: grade `3fr 2fr` (≈ 60/40); obra à esquerda, `ArtworkImage` `large`
  (eager, `alt` = título ou "Obra sem título"), caixa com `max-height: 70vh`,
  `object-fit: contain`, fundo `--color-surface-subtle`. Tablet: `11fr 9fr`. Mobile: obra
  em largura total, texto abaixo.
- Texto, só: `LotState` (estado), título (`h3`, `--font-display`, até 3 linhas com
  `title`), artista (muted), "Lance inicial" + `formatCents(starting_bid_cents)` (valor
  grande, `tabular-nums`), horário ("Termina {data}" se ao vivo; "Começa {data}" se
  agendado), um CTA primário `AppLink` "Ver lote" (nome acessível "Ver lote: {título}").
- Sem nenhum ao vivo nem agendado: vazio editorial no lugar do destaque — `h2` "Nenhum
  lote em leilão agora" e "Novos lotes de obras em domínio público entram aqui assim que
  são publicados." Sem imagem falsa nem CTA.
- Encerrado nunca vai para o destaque.

### 3.2 Ao vivo e Próximos lotes (`LotRail.tsx`, `LiveLotItem.tsx`, `UpcomingLotItem.tsx`, D14)

- `LotRail`: `section` com `h2` e `<ul>` horizontal (`overflow-x: auto`,
  `scroll-snap-type: x mandatory`, `scroll-padding`), itens com `scroll-snap-align:
  start`; largura do item: ≥ 75rem ≈ 23% (4 visíveis + parte do 5º), 48–75rem ≈ 38%,
  < 48rem 80vw. Botões "Anterior"/"Próximo" (`aria-label` "Ver lotes anteriores de
  {seção}" / "Ver mais lotes de {seção}") só ≥ 64rem e só se `railScrollState().overflow`,
  recalculado em `scroll` e `resize` (`ResizeObserver`); desabilitados nas pontas;
  `scrollBy` de uma largura visível. Teclado: Tab pelos links já rola o rail.
- Itens: `railItems(group, featured)` (sem o destaque). Cada item é um `<li>` com um
  único `AppLink` envolvendo `ArtworkImage` `card` (`alt=""`), `LotState`, título (`h3`,
  2 linhas, `title`), artista (1 linha), e:
  - ao vivo: "Lance inicial" + valor; "Termina {data}";
  - próximo: "Começa {data}"; "Lance inicial" + valor, com peso menor.
  O `AppLink` leva `data-lot-id` e o clique grava `restoreLotId` (navegação §7).
- Densidade: ao vivo com imagem maior e valor em destaque; próximos com imagem menor
  (≈ 80% da largura do item ao vivo) e texto mais leve (blueprint §9).
- Vazios e "só o destaque":

| Grupo | Situação | Texto (sem imagem) |
| --- | --- | --- |
| Ao vivo | `live` vazio | "Nenhum lote ao vivo agora." |
| Ao vivo | só o lote em destaque | "O lote em destaque é o único ao vivo agora." |
| Próximos | `scheduled` vazio | "Nenhum lote agendado." |
| Próximos | só o lote em destaque | "O lote em destaque é o único agendado." |

### 3.3 Encerrados (`ClosedLotRow.tsx`, D13)

- Lista densa `<ul>` (blueprint §8): miniatura `ArtworkImage` `thumb` (lazy) | título e
  artista | "Encerrado, apurando resultado" + "Terminou {data}". Sem valor (não há
  resultado; o lance inicial pareceria preço final). Cada linha é um `AppLink`.
- Visíveis: `initialEndedVisible(total, navState.endedVisible)`; "Mostrando X de Y
  encerrados." (muted) e botão secundário "Mostrar mais encerrados" enquanto X < Y;
  clique → `nextEndedVisible`, sem chamada; o foco vai para o primeiro item revelado.
- Vazio: "Nenhum lote encerrado ainda."

### 3.4 Estados da vitrine

| Estado | Tela |
| --- | --- |
| carregando | `role="status"` "Carregando a vitrine…"; caixa do destaque reservada (sem shimmer) |
| erro (`server`) | `role="alert"` "Não foi possível carregar a vitrine." + botão "Tentar novamente" (novo `GET`) |
| carregada | §3.1 a §3.3 + linha `asOfText(as_of, new Date())` (muted, D16) abaixo do destaque |
| nada em nenhum grupo | vazio editorial do destaque + as três seções com o texto de vazio |
| imagem quebrada | placeholder da `ArtworkImage`; título, estado, valor e horário intactos |
| visitante / logado | mesma vitrine; muda só o header |

O lote demo aparece como qualquer lote, sem marca "DEMO".

## 4. `LotState.tsx` (D15)

`<p class="lot-state lot-state-{phase}">` com marcador e texto `phaseStatusText(phase)`.
Ao vivo: "●" `aria-hidden` em `--color-brand` + "Ao vivo" em peso forte. Agendado:
"Agendado" em `--color-text`. Encerrado: "Encerrado, apurando resultado" em
`--color-muted`. O texto sempre presente; a cor só reforça. Sem pill, badge nem fundo.

## 5. Página do lote (`LotPage.tsx`)

Ao montar: `fetchPublicLot(lotId)`. Um `h1` em todos os estados (navegação §7).

**Layout.** ≥ 64rem: grade `3fr 2fr`; obra à esquerda (`ArtworkImage` `large`,
`max-height: 80vh`, `contain`, sticky `top: 1rem`); ficha à direita. < 64rem: uma coluna,
na ordem abaixo.

**Ordem do conteúdo.**
1. "← Vitrine" (`AppLink`; com `fromVitrine`, `history.back()`).
2. Obra (imagem ou placeholder com "Imagem indisponível").
3. `LotState` + horário principal ("Termina {data}" / "Começa {data}" / "Terminou
   {data}").
4. `h1` título (`--font-display`; "Sem título" em itálico se `null`), artista (muted,
   `white-space: pre-line`), data da obra.
5. `<dl>` "Leilão": Lance inicial (`formatCents`), Incremento mínimo (`formatCents`),
   Início, Término (`formatDateTime`, com fuso). `dd` com `tabular-nums`.
6. Linha `asOfText(as_of, new Date())` (D16).
7. `<dl>` "Ficha da obra": Técnica, Dimensões, Departamento, Tipo, Crédito, Nº no
   acervo (`external_id`). Linha com valor `null` não é renderizada.
8. Link externo `<a href={source_url} target="_blank" rel="noopener noreferrer">` "Ver a
   obra no site do Art Institute of Chicago" + `<span class="visually-hidden"> (abre em
   nova aba)</span>` + "↗" `aria-hidden`.

Para `ended`: o estado diz "Encerrado, apurando resultado"; nenhuma frase sobre
vencedor, resultado ou valor final. Nenhum "Dar lance", campo de valor, carteira,
histórico ou countdown, nem desabilitado.

**Estados.**

| Estado | `h1` | Conteúdo |
| --- | --- | --- |
| carregando | "Carregando lote…" | `role="status"`; caixa da obra reservada |
| ok | título | §5 completo |
| `not_found` (404/422) | "Lote não encontrado" | "O lote pode ter sido removido ou o endereço está incompleto." + `AppLink` "Ir para a vitrine" |
| `server` | "Não foi possível carregar o lote" | `role="alert"` + "Tentar novamente" + `AppLink` "Ir para a vitrine" |

`/lots/<não-uuid>` não chega aqui: é "Página não encontrada" (navegação §8).

## 6. `ArtworkImage.tsx` (D17)

Nova variante `card`: `loading="lazy"`, `width`/`height` 843×632 só para reservar a
proporção, caixa `aspect-ratio: 4 / 3`, `object-fit: contain`, fundo
`--color-surface-subtle`; falha → placeholder com `alt=""`, sem legenda (vive dentro de
link). `thumb` e `large` mantêm o comportamento da 2.3/2.4. A `src` é sempre o
`image_url` do contrato (proxy da 2.3, P9).

## 7. Dinheiro e horários

`formatCents` de `money.ts` (sem duplicar lógica, sem float); `formatDateTime` de
`lotTime.ts` (fuso do navegador, com nome do fuso). Nenhuma comparação de horários no
front.

## 8. Responsividade

| Largura | Header | Destaque | Rails | Encerrados | Página do lote |
| --- | --- | --- | --- | --- | --- |
| ≥ 75rem | uma linha | 60/40 | ~4 itens + parte do 5º, botões | grade `4.5rem 1fr auto` | 3fr/2fr |
| 64–75rem | uma linha | 60/40 | ~2,5 itens, botões | idem | 3fr/2fr |
| 48–64rem | pode quebrar | 55/45 | ~2,5 itens, sem botões | idem | uma coluna |
| < 48rem (375, 320) | marca; nav e conta em linhas próprias | obra largura total, texto abaixo | 80vw, scroll-snap | miniatura + texto; estado abaixo | uma coluna |

Regras: nenhum elemento mais largo que a viewport (`min-width: 0` nos filhos de grid,
rails com `max-width: 100%`); `overflow-wrap: anywhere` em títulos, artistas e valores
(R$ 90.071.992.547.409,91 quebra); datas quebram entre data e hora; imagens nunca
cortadas (`contain`); "Mostrar mais" e CTAs com alvo ≥ 44px.

## 9. Acessibilidade

- Um `h1` por vista; `h2` por seção; `h3` por lote. Foco no `h1` ao navegar (D11).
- Lote = link com nome que começa pelo título; imagem dentro do link com `alt=""`.
- Foco visível (`:focus-visible` com `--color-brand`, contraste ≥ 3:1) em links, botões
  e itens de rail.
- `aria-current="page"` no header; `role="status"` em carregando; `role="alert"` em erro.
- Estado sempre em texto (D15); link externo anunciado como "abre em nova aba".
- Nada depende de hover: rails rolam por toque, teclado e botões.

## 10. Stress test (blueprint §15, roteiro manual)

Ao vivo 0/1/5/12; próximos 0/3/20; encerrados 0/8/50 (por SQL local); títulos curto, 2
linhas e excessivo; valores R$ 850, R$ 18.450, R$ 1.250.000 e o máximo; imagens paisagem,
retrato, quase quadrada e indisponível; 320 px e desktop largo.
