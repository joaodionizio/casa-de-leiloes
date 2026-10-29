# Estado atual e evidências — 28/10/2026

## Base e limites

Auditei os arquivos vivos, sem Git, e o build atual no Chromium com a API simulada
existente. Descartei tomar protótipos e registros históricos como prova do estado
atual. Li CLAUDE, arquitetura, enunciado, Story 6.2, DESIGN, EXPERIENCE, blueprint,
workflow frontend, fechamento de épico e `implementation-artifacts/deferred-work.md`.

Confrontei as telas com os artefatos de implementação 2.2 (login/marca), 2.3
(catálogo/imagem), 2.4 (criação/painel), 2.5 (Vitrine/navegação), 3.1 (carteira),
3.5/3.6 (lance/cancelamento), 4.1/4.2/4.4 (WS/recuperação/terminal), 4.5
(resultado/total), 5.1 (auditoria), 5.2 (comprovante) e 5.3 (arremates).
O pedido atual confirma a aprovação técnica da 6.1 após o re-review R6.1-01;
não sincronizei seus registros históricos nem executei seus gates publicados.

`App.tsx`, `route.ts`, `navigation.ts`, `AppLink.tsx` e `SiteHeader.tsx` são a base
comum. O frontend usa React/Vite/TypeScript, History API própria e CSS próprio;
nenhum UI kit. O catálogo de criação fica montado/oculto ao sair da rota, preservando
rascunho; isso não deve mudar por CSS ou reorganização de componentes.

## Inventário real por tela

| Tela, rota e raiz | Filhos e CSS/tokens | Responsividade e estados existentes | O que preservo / gap concreto |
| --- | --- | --- | --- |
| Vitrine `/` — `VitrinePage` | `FeaturedLot`, `LotRail`, `LiveLotItem`, `UpcomingLotItem`, `ClosedLots`/`ClosedLotRow`, `ArtworkImage`, `LotState`; `.featured`, `.rail-*`, `.closed-*` em `App.css` | Hero 1 coluna; 48 rem: 55/45; 64 rem: 60/40, arte à esquerda. Rails internos, snap, largura por quantidade e 75 rem; próximos mais leves. Encerrados: 6 iniciais, +6 local. Loading/reserva, vazio, erro/retry, sem grupos, imagem falha e sessão pública/autenticada | Já tem obra cedo, serif, densidades distintas, fallback e ausência de controles mortos. Hero não corresponde à composição adicional; com título longo+valor máximo a 320 CTA começa em y830,45, além de 812. Não há countdown/preço atual no DTO público |
| Sala `/lots/{id}` — `LotPage` | `LotState`, `ArtworkImage`, `LotBidPanel`, `CountdownTimer`, `BidForm`/`MoneyField`, `BidHistory`; `.lot-page-*`, `.bid-*`, `.room-*` | Até 64 rem: estado/prazo absoluto → arte → título/artista → painel → histórico → detalhes. A partir de 64 rem: arte sticky+ficha. Loading, 404, erro/retry, visitante/leiloeiro/licitante, agendado/live/ended/cancelled, envio/recusa/ambíguo, stale/reconexão/terminal | Valores de 28 px e um timer; posição em texto+símbolo, histórico de até 50. Timer ainda dentro do painel; título longo o empurra a y1378 a 320 e lance a 1453,5. Links públicos sem token. “Apurando” persiste após settled: QH-01 |
| Carteira `/bidder/wallet` — `WalletPage` | `MoneyField`, avisos; `.wallet-*`, `.money-*`, tokens de fonte/cor/estado | Uma coluna; 40 rem: apoios lado a lado. Disponível 32 px/48 px, total/comprometido 20 px, depósito abaixo. Loading, zerada, erro/retry, recusas, sucesso, pendente/ambíguo, sessão/papel | Já atende hierarquia, legibilidade relativa, valores máximos, sem gráficos/overflow, `dl` válido e feedback sem só cor. Preservo estrutura e ordem disponível/total/comprometido |
| Painel `/auctioneer/lots` — `MyLots`; criação `/auctioneer/lots/new` — `LotCreation` | Painel: `ArtworkImage`, resultado/total, confirmação inline; `.lot-row-*`, `.my-lots-*`. Criação: `CatalogSearch`, `ArtworkDetailPanel`, `LotForm`, `LotArtwork`, `MoneyField`, `DateTimeField`, `LotReview`, `LotCreated` | Painel: grid denso com fatos em 2 colunas; 64 rem distribui em linha com `display:contents` no `dl`. Cancelamento ocupa linha própria. Catálogo 64 rem: lista+detalhe; abaixo alterna lista/detalhe; busca empilha a 30 rem. Formulário 64 rem: obra+campos; abaixo 1 coluna. Loading/erro/vazio/stale/atualizando, live/agendado/pending/sold/unsold/cancelled; fluxo obra/form/revisão/publicação | Já adapta tabela/lista em blocos densos, datas/valores/ações e 50 resultados. Não há quebra comprovada. Campos só explicam formato monetário, não significado; falta microcopy. Criação ainda sem e2e dedicado |
| Auditoria `/lots/{id}/audit` — `AuditPage` | `AppLink`, `time`, `ol.audit-events`, `details/summary`, `dl/code`; `.audit-*` | Layout fluido até 52 rem, resumo flex-wrap, hashes com `overflow-wrap:anywhere`, detalhes fechados por padrão, sem breakpoint próprio. Loading/404/erro/retry; verified/adulterated; scheduled/live/ended-pending/sold/unsold/cancelled | Já parece documento, mantém sequência/alias/valor/timestamp/veredito e hashes completos. 100 eventos com hashes abertos cabem a 320. Link de retorno usa azul UA; faltam 375/1440 e alvos/foco explicitamente provados |
| Meus arremates `/bidder/wins` — `MyWinsPage` | `WinItem`, `ArtworkImage`, `AppLink`; `.my-win*` | Grid miniatura de 72 px+texto; até 400 px:56 px+texto. Ações wrap; input de cópia 100%. Loading/erro/retry/vazio/401/403/integrity; participação ao vivo/agendada, pending/cancelled, won/not_won; cópia/fallback | Já tem lista, estado/resultado, receipt só de vencedor e cópia funcional. Links azul UA, h1 padrão 32 px contra 24 px operacional; título longo sem limite visual torna linha extensa; links de 24 px e copiar com 36,5 px de altura |

Em todas, `index.css` fornece as cores/fontes; `App.css` contém os estilos. Raízes
e filhos acima são caminhos sob `frontend/src/`; não são componentes propostos.

## Tokens, duplicações e acessibilidade

| Inspeção | Resultado e consequência |
| --- | --- |
| Tokens reais × DESIGN | Os 14 tokens de cor e 2 de fonte são idênticos: brand/strong/soft/blue; ink/text/muted; canvas/surface/subtle/border; success/warning/danger; font-ui/font-display. Preservo os valores |
| Hardcodes | `App.css:205` usa branco literal no botão primário: candidato simples a `var(--color-surface)`. As 2 cores específicas do SVG (`#a77bf6`, `#6c35e6`) são intencionais, iguais ao favicon; não as substituo pela paleta geral |
| Estilos ignorados | Links simples da Sala/Auditoria/Arremates caem em azul UA `rgb(0,0,238)`. Corrijo com regra pequena para links de conteúdo, preservando classes de CTA/rail e sublinhado/foco |
| Repetição | `.untitled` aparece 2 vezes; h1 operacionais repetem 24 px/sans/600; bordas de 2 px e espaçamentos locais se repetem. Consolido apenas trechos tocados que tragam ganho; não crio escala universal, framework nem tokens para todo literal |
| Contraste calculado | Brand/branco 5,14:1; muted/branco 5,20:1; muted/canvas 4,86:1; muted/subtle 4,66:1. Não encontrei motivo para trocar a paleta. Isso não substitui verificar os pares efetivamente usados no candidato |
| Foco/teclado | Há outlines de 2 px, links semânticos, restauração de foco/History e área de respiro do rail; catálogo mantém foco entre etapas. `summary` usa controle nativo. Lacuna: prova explícita do foco e toque de links novos/sem classe e Meus arremates no header |
| Labels/alt/live | Campos têm labels; `MoneyField` liga dica/feedback por `aria-describedby`, evita anunciar cada tecla. Imagens grandes têm alt; miniaturas em links nomeados são decorativas. Timer tem `role=timer`/`aria-live=off`; avisos/status/alert já existem. Preservo esses contratos |

Os breakpoints reais são 30 rem/40 rem/48 rem/64 rem/75 rem, com exceção local de 400 px
em arremates e pares max/min já existentes. Não existe suíte tablet específica;
768 px exercita o breakpoint 48 rem real, sem justificar criar outro.

## Baseline executada nesta SPEC

| Comando/sonda | Resultado real | Limite |
| --- | --- | --- |
| `cd frontend && npm run lint` | exit 0 | Sem mudança de produto |
| `npm run typecheck` | exit 0 | app/node/e2e |
| `npm test` |192 pass,0 fail, exit 0 | Lógica/contratos, sem DOM |
| `npm run build` | exit 0, Vite 8.3.5, 80 módulos | Build atual, sem implementação |
| `npm run test:e2e` |265 passed,5 skipped,34,9s, exit 0 | Chromium/API simulada; skips são `real-stack.spec.ts` opt-in |
| Sonda descartável | Seis telas+login em 1440×900/768×812/375×812/320×812, sem overflow global nas amostras; criação em 1440/375/320 também sem overflow | Não é teste versionado nem aceite visual final |

A primeira tentativa E2E falhou antes dos testes por `listen EPERM` na 4173; a
reexecução permitida funcionou. O navegador integrado falhou ao conectar à bridge;
usei o Playwright já instalado, sem adicionar dependência. Os logs e screenshots
diagnósticos ficam em `/private/tmp/atrio-6-2-audit` e `/private/tmp/atrio-6-2-*.log`;
os resultados relevantes estão reproduzidos aqui porque esse diretório é temporário.

A sonda usou Vitrine 5/20/50, painel 30, arremates 20, sala 51 lances com 50 exibidos e
auditoria 100 com detalhes do último evento abertos; mídia 503/fallback, título longo
e valores extremos nos contextos descritos. Ausência de overflow não prova que toda
ação está no primeiro viewport nem que todos os estados/combinações foram medidos.

Também abri o hero com imagens locais já existentes em paisagem 1000×670,
retrato 843×1074 e quase quadrada 1000×960, em 1440/320: `contain`, caixa estável e
sem overflow nas 6 observações. São sondas do estado atual, não prova do novo fade.

Não executei `./verify.sh`, backend/PostgreSQL/Docker, real-stack, deploy ou gates da
6.1 nesta fase documental. Testes verdes da baseline não são evidência pós-build.

## Benchmarks exclusivamente de responsividade

Tentei os 3 URLs por leitura web, sem sucesso nessa ferramenta. No Chromium,
[Render](https://casa-de-leiloes-v0bc.onrender.com/) respondeu 503 e mostrou apenas
“Application loading”: não extraí observações do produto.

| Referência aberta em 1440/768/375/320 | Observação de layout real | Aprendizado aplicável |
| --- | --- | --- |
| [Vercel](https://casa-de-leiloes.vercel.app/) —200 | Navegação desktop recolhe em 768/mobile; grade observada com 2 itens em desktop/tablet e 1 no mobile. Campos passam de linha horizontal para busca inteira+par e depois largura estreita; login 320: formulário 280 px, inputs≈241 px. Sem overflow global nas larguras medidas | Reorganizar grupos e larguras, manter campos contidos. Não copiar menu, filtros ou composição; ÁTRIO já tem navegação própria funcional |
| [Railway](https://martelo-leiloes.up.railway.app/?status=ended) —200 | Grade observada 4→2→1; busca/filtro muda de faixa no tablet e cabe lado a lado no mobile; navegação recolhe em 375/320; login 320: formulário e inputs 238 px. Sem overflow global nas larguras medidas | Reduzir colunas e redistribuir controles antes de comprimir; preservar dados de decisão fora da imagem |

Inspecionei vitrines públicas e login, sem autenticar, submeter formulários ou
importar marca/cores/fontes/textos/ativos. Tabelas administrativas, áreas restritas,
conteúdo extremo e funcionamento dos menus não foram comprovados nesses sites.
Não atribuo a eles nossa estratégia de rails nem os uso como referência estética.

## Referência ÁTRIO recebida durante a SPEC

Inspecionei `WhatsApp Image 2026-10-28 at 18.19.22.jpeg`, fornecida pelo usuário em
`/Users/joaodionizio/Downloads/`. No trecho marcado em verde, a área institucional
fica à esquerda e o retrato à direita, com transição vertical difusa entre branco
e imagem; o quadro ocupa grande parte do hero. Há legenda discreta na imagem.
O verde é uma anotação do usuário, não cor da identidade.

Uso essa evidência para a composição de M02, não para copiar a obra, texto,
wordmark ou estética pixel a pixel. Busca, filtros, favoritos, menu, cadastro,
countdowns e outros controles desenhados na referência não ampliam a 6.2.
DESIGN/EXPERIENCE e os contratos reais continuam definindo dados e tipografia.
Não recebi bitmap AURA separado. O caminho local é proveniência, não dependência
de build nem arquivo que precise ser copiado para o produto.

## Cadastro e demo: estado real

`backend/app/seed.py:46–73` e `README.md:165–178` confirmam contas e senha pública:

| E-mail | Papel | Senha pública |
| --- | --- | --- |
| `auctioneer@example.com` | `AUCTIONEER` | `Demo123!` |
| `bidder1@example.com` | `BIDDER` | `Demo123!` |
| `bidder2@example.com` | `BIDDER` | `Demo123!` |

Confirmei as contas definidas para o seed, sem consultar usuários do banco ou
testar credenciais no deploy. O seed não altera senha existente; eventual falha
do atalho deve usar o erro normal, nunca reparar conta ou burlar autenticação.

`LoginPage` monta `LoginForm`; este chama `api/auth.ts:login`, que faz POST JSON
same-origin em `/api/auth/login`, recebe `{email,role}` e delega a `onLoggedIn`.
`App.handleLoggedIn` aplica `safeReturnPath(navState.returnTo,role)` e replaceRoute.
O formulário atual já tem “Entrando…”, validação/erro e bloqueio via estado React;
os atalhos precisarão compartilhar uma barreira síncrona de tentativa.

`backend/app/auth.py` registra login/logout/me; conferi todos os registradores de
`main.py` e não há endpoint real de cadastro. A decisão D2=A da 2.2 também o exclui.
As rotas frontend não têm signup. A demanda futura está delimitada no contrato
visual; não crio endpoint, tela, link ou story funcional agora.
