# Front-end — busca e detalhe do catálogo (Story 2.3)

Autoridade: story > `docs/ARQUITETURA.md` > `DESIGN.md` + `EXPERIENCE.md`.
Processo: `docs/FRONTEND-WORKFLOW.md`. Não é a Vitrine: `VITRINE-BLUEPRINT.md`
não se aplica.

## 1. Base existente

- `App.tsx`: sessão `checking | anonymous | authenticated`; autenticado mostra só
  um `h1` oculto. `SiteHeader`: marca + e-mail + papel + "Sair".
- `src/api/auth.ts`: padrão de cliente (`fetch` com `credentials: 'same-origin'`,
  type guards, `readJson`, falha por união, texto em pt-BR pelo código).
- `index.css`: tokens de DESIGN §3–§4. `App.css`: `.page-container`, `.button*`,
  `.field`, `.form-error`, `.muted`, `.visually-hidden`, foco visível.
- `public/`: só `favicon.svg`. Sem roteador, sem testes de front.

## 2. Regras aplicadas

| Fonte | Aplicação |
| --- | --- |
| DESIGN §1, §5 | Obra protagonista no detalhe; roxo só em ação primária, foco e link; sem card, sombra, pill, badge, gradiente, ícone decorativo. |
| DESIGN §4 | `--font-display` em título da obra e artista; `--font-ui` no resto. |
| EXPERIENCE §6, DESIGN §10 | Resultado em lista visual compacta, não cards. |
| EXPERIENCE §2, CLAUDE.md, P10 | Sem botão "Criar lote", nem habilitado nem desabilitado; sem "Meus lotes", sem "Vitrine", sem filtros, sem paginação. Nada da 2.4. |
| EXPERIENCE §5 | `BIDDER` e visitante não veem a busca. |
| EXPERIENCE §17, DESIGN §11 | Espaço reservado → carga silenciosa → imagem → placeholder; `loading="lazy"` na lista; proporção fixa. A imagem vem do nosso proxy same-origin (`image_url`), nunca de `www.artic.edu` (P6.1). |
| DESIGN §13–§14, EXPERIENCE §18 | 320 px sem rolagem horizontal; desktop largo sem esticar; estado nunca só por cor; `aria-live`; foco visível. |
| 2.2 P15 | Texto exibido mapeado pelo `code`, nunca o `message`. |

## 3. Estados

| # | Estado | O que aparece |
| --- | --- | --- |
| 1 | Inicial | Formulário + texto de orientação (§5). Sem lista. |
| 2 | Buscando | Botão "Buscando…" desabilitado; região de resultados com `aria-busy="true"` e "Buscando obras…" (`role="status"`). Resultado anterior some. |
| 3 | Resultados | "N obras para “termo”"; lista; se N = 20, linha muted "Mostrando as 20 mais relevantes. Refine o termo para encontrar outras." |
| 4 | Nenhum resultado | 200 com `items: []` → "Nenhuma obra encontrada." (texto exato, `role="status"`) e, abaixo, muted: "Só aparecem obras em domínio público com imagem. Tente outro termo, em inglês." |
| 5 | Termo inválido | Sem requisição: `q.trim()` vazio → "Digite um termo para buscar." no campo (`aria-invalid`, foco no campo). Resposta 422 → mesma mensagem. Acima de 100: impedido por `maxLength={100}`. |
| 6 | Catálogo indisponível | 503 `catalog_unavailable` → "O catálogo do museu não respondeu. Tente novamente em instantes ou use outro termo." + botão "Tentar novamente" (repete a última busca). |
| 7 | Erro inesperado | Rede, 5xx, corpo fora do contrato → "Não foi possível falar com o servidor. Tente novamente." + "Tentar novamente". 403 → "Sua conta não tem acesso à busca de obras." 401 → sessão encerrada (§6). |
| 8 | Detalhe carregando | Painel do detalhe com "Carregando obra…" (`role="status"`), caixa de imagem reservada. |
| 9 | Detalhe disponível | Ficha completa (§4.3). |
| 10 | Detalhe indisponível | 404 → "Esta obra não está disponível para leilão: não foi encontrada ou não é de domínio público com imagem." 503 → texto do estado 6 + "Tentar novamente". Outros → texto do estado 7. Sempre com "Voltar aos resultados" (vista estreita). |

Erros usam `role="alert"`; estados de progresso, `role="status"`. Nenhum estado
é indicado só por cor.

## 4. Estrutura

```text
App (authenticated, role AUCTIONEER)
└─ CatalogSearch            <section aria-labelledby="catalog-title">
   ├─ cabeçalho             h1 "Buscar obras" + linha muted de origem
   ├─ SearchForm            <form role="search"> label, input type="search", botão "Buscar"
   ├─ região de resultados  <div aria-live="polite"> status | erro | lista
   │  └─ ResultList         <ul> de <li><button> (ArtworkImage miniatura + textos)
   └─ ArtworkDetailPanel    <section aria-labelledby="artwork-title"> estados 8–10
      └─ ArtworkImage       imagem grande + placeholder
```

Arquivos: `src/api/catalog.ts`, `src/CatalogSearch.tsx` (estado, formulário,
lista), `src/ArtworkDetailPanel.tsx`, `src/ArtworkImage.tsx`; estilos numa seção
"Catálogo" em `src/App.css` (idioma atual: um só CSS de app). `App.tsx`
renderiza `<CatalogSearch onSessionExpired={...} />` quando
`session.user.role === 'AUCTIONEER'`; para `BIDDER`, mantém o `h1` oculto atual.

### 4.1 Cabeçalho e formulário

- `h1` "Buscar obras" (`--font-ui`, 1.5rem, como o login); abaixo, muted:
  "Acervo do Art Institute of Chicago. Só aparecem obras em domínio público com
  imagem."
- `label` visível "Termo de busca"; `input type="search"`, `maxLength={100}`,
  `placeholder="Ex.: Monet, water lilies, portrait"`, `autoComplete="off"`;
  botão primário "Buscar" à direita do campo (quebra para baixo em < 30rem).
  Enter envia. Largura do formulário ≤ 40rem.
- Orientação no estado inicial (muted, abaixo do formulário): "Pesquise por
  título, artista ou tema. O acervo do museu está em inglês."

### 4.2 Lista

- `<ul>` sem marcadores, itens separados por `border-bottom: 1px solid
  var(--color-border)`; cada `<li>` contém um `<button type="button">` que ocupa
  a linha toda (alvo de toque ≥ 44 px), alinhado à esquerda, sem fundo; hover e
  item selecionado com `background: var(--color-surface-subtle)`; selecionado
  também com `aria-current="true"` e barra de 3 px `--color-brand` à esquerda
  (não só cor: `aria-current` + barra).
- Conteúdo da linha: miniatura 4.5rem × 4.5rem (4rem em < 30rem) + bloco de
  texto: título (`--font-display`, 1.0625rem, até 2 linhas com
  `-webkit-line-clamp`, `title` com o nome completo), artista (muted,
  `white-space: pre-line`, 1 linha visível), data (muted, 0.875rem).
- Título `null` → "Sem título" em itálico muted. Artista ou data `null` → linha
  omitida.

### 4.3 Detalhe

Ordem (DESIGN §5: obra → título/artista → metadados):

1. `ArtworkImage` grande: caixa `aspect-ratio: 4 / 3`, `max-height: 70vh`,
   `object-fit: contain`, fundo `--color-surface-subtle`, `loading="eager"`.
2. `h2#artwork-title` (`--font-display`, 1.75rem desktop / 1.375rem mobile,
   `tabIndex={-1}` para receber foco); artista em `--font-display` 1.125rem,
   `pre-line`.
3. Linha de estado em texto: "Domínio público" (prefixo `✓` com
   `aria-hidden`) — informação, não decoração.
4. `<dl>` em duas colunas no desktop (termo muted / valor): Data, Técnica,
   Dimensões, Departamento, Tipo, Crédito, Nº no acervo (`external_id`). Valor
   `null` → "Não informado" muted (nunca inventado).
5. Link "Ver no site do Art Institute of Chicago" (`source_url`,
   `target="_blank"`, `rel="noopener noreferrer"`, texto visually-hidden
   "(abre em nova aba)").

Nenhum botão de ação de lote, nem desabilitado (P10).

### 4.4 `ArtworkImage`

Props: `src: string`, `alt: string`, `variant: 'thumb' | 'large'`.

- `<img>` com `width`/`height` coerentes com a caixa, `decoding="async"`,
  `referrerPolicy="no-referrer"`, `loading="lazy"` (thumb) ou `"eager"` (large).
  `src` é o `image_url` do contrato, `/api/catalog/images/{image_id}` (revisão P6.1):
  URL relativa, mesma origem, sem `fetch`/blob manual e sem cabeçalho especial no
  navegador; o navegador não pede mais `default.jpg` ao domínio da AIC. A miniatura e
  o detalhe usam a mesma URL (843 px), então o servidor é chamado a cada carga
  (`no-store`).
- Estado `failed` em `onError` → troca para `/artwork-placeholder.svg`,
  `alt=""`; em `large`, legenda visível "Imagem indisponível" (muted) sob a
  caixa; em `thumb`, só o placeholder (sem texto oculto: ele viria antes do título no nome
  acessível do botão da linha; o título é o que o botão anuncia primeiro — review L2). `failed`
  reinicia quando `src` muda (`key={src}` no uso).
- `alt`: miniatura `""` (o título está no mesmo botão); grande = título ou
  "Obra sem título".
- A caixa tem dimensões fixas antes da carga: nenhuma mudança de layout ao
  carregar ou falhar. Sem shimmer.

### 4.5 Placeholder

`frontend/public/artwork-placeholder.svg`: asset estático local, sem texto,
`viewBox` quadrado, fundo `#f4f1f8` (`--color-surface-subtle`), moldura e
silhueta simples de quadro em `#ddd7e2`/`#716a78`, sem roxo, < 2 KB. Aparece só
quando a carga da imagem falha (o proxy responde 404 ou 503, ou a rede cai; P5: obra
sem `image_id` nem chega à tela). A falha é só visual: não muda dado, contrato nem
elegibilidade da obra. Testável manualmente bloqueando `/api/catalog/images/*` no
DevTools (`test-plan.md` §7, passo 8).

## 5. Responsividade

- ≥ 64rem: grade de duas colunas dentro de `.page-container`:
  lista `minmax(20rem, 2fr)` | detalhe `3fr`; detalhe `position: sticky; top: 1rem`
  com `max-height: calc(100dvh - 2rem)` e rolagem própria. Sem seleção, a
  coluna do detalhe mostra muted "Selecione uma obra para ver o detalhe."
- < 64rem: uma coluna. Selecionar item troca para o detalhe (lista oculta) com
  botão secundário "← Voltar aos resultados" no topo; voltar restaura a lista,
  a rolagem e o foco no item. O termo e os resultados ficam no estado.
- 320 px: nada com largura fixa maior que a viewport; `overflow-wrap: anywhere`
  em título, artista e valores do `<dl>`.

## 6. Comportamento

- `src/api/catalog.ts` (AD-4 simples): `ArtworkSummary`, `ArtworkDetail`
  (`extends ArtworkSummary`), `CatalogFailure = 'validation' | 'unavailable' |
  'not_found' | 'unauthorized' | 'forbidden' | 'server'`,
  `SearchResult`/`DetailResult` como uniões `{ ok: true; ... } | { ok: false;
  failure }`, type guards, `searchArtworks(term, signal)`,
  `fetchArtwork(externalId, signal)`, `catalogFailureMessage(failure)`. URL com
  `encodeURIComponent`. Status → falha: 422 `validation`; 503 com
  `code === 'catalog_unavailable'` `unavailable`; 404 `not_found` (só detalhe);
  401 `unauthorized`; 403 `forbidden`; demais e corpo inválido `server`.
- Cada busca e cada abertura de detalhe usa um `AbortController`; a anterior é
  abortada, e resposta de requisição abortada é ignorada (sem estado trocado
  fora de ordem). `AbortError` não vira mensagem.
- Nova busca limpa a seleção do detalhe.
- `unauthorized` chama `onSessionExpired()`; `App` volta a `anonymous` com o
  aviso "Sua sessão expirou. Entre novamente." no formulário de login.
- Foco: após resultados, o foco fica no campo; abrir detalhe move o foco para o
  `h2` do detalhe; voltar devolve ao botão do item.
- Teclado: Tab percorre campo → Buscar → itens (botões) → detalhe; Enter/Espaço
  abre; nada depende de hover.
- Nada em `localStorage`/`sessionStorage`; termo não vai para a URL.

## 7. Checagens

`npm run lint`, `npm run typecheck`, `npm run build` no `verify`; roteiro manual
em `test-plan.md` §7. Sem teste automatizado de front (P10).
