# Story 6.2 — evidência de implementação

Data: 28/10/2026, America/Maceio. Estado atual: **aceite visual humano FINAL concedido e gate completo pós-aceite aprovado (exit 0)**. Story/sprint `review`, SPEC `in-review`, pronta para review independente; esse review não foi executado.

Os registros anteriores abaixo preservam a sequência de implementação e polimentos. O adendo final pós-aceite ao fim deste documento é a evidência vigente do candidato.

## Escopo e decisões

Implementei exclusivamente o contrato aprovado e os esclarecimentos humanos do
pedido de build. Usei Codex e a skill `bmad-build`, com implementação delegada
conforme seu passo 03, seguida de conferência do diff e verificação pelo agente
principal. O subagente atingiu limite de uso após a rodada focal; concluí a
verificação, ajuste de foco e registros no agente principal. Isso não constitui
code review independente. Preservei a baseline histórica da 4.2; o usuário
aprovou uma área local exclusiva para a 6.2.

- Hero: superfície branca, texto à esquerda e palco da imagem com 60% da largura
  a partir de 64rem. Usei somente os dados existentes do destaque e o descritor
  curto “Leilões de Arte”; descartei copy institucional extensa e controles novos.
  Em 768 mantive composição vertical curta; em 375/320 a obra vem cedo, seguida de
  estado, título/artista, valor/horário e CTA. O título compacto mantém seu nome
  acessível e o acesso à Sala integral. Valores/horários não são truncados.
- Transição: pseudo-elemento branco→transparente em 10% da borda esquerda do palco,
  com `pointer-events:none`. Mantive `object-fit:contain`, uma única imagem/URL e
  bytes intactos. O efeito só existe no desktop e quando a imagem carregada tem
  largura superior a 1,1× a altura; retrato/quase quadrada/fallback/carga pendente
  e mobile ficam sem efeito. Descartei máscara na obra e download decorativo.
- Sala: movi a única instância de `CountdownTimer` para estado/prazo, mantendo
  a mesma `anchor` e `handleZero`, `role=timer` e `aria-live=off`. O h1 permanece
  integral, sem clamp. A posição do licitante vem após o lance atual e antes do
  mínimo. Não alterei arbitragem, REST/WS, heartbeat, reconexão, POST, zero ou
  anti-sniping.
- QH-01: tanto o estado superior como `.room-phase-note` distinguem
  ended+pending (“Encerrado, apurando resultado”) de ended+settled (“Encerrado”).
  Não alterei `phaseStatusText` nem fiz a Vitrine inferir settlement.
- Novo lote: acrescentei exatamente “Valor mínimo aceito para o primeiro lance
  deste lote.” e “Valor mínimo que cada novo lance deverá acrescentar ao lance
  atual.” A prop opcional `description` do MoneyField soma descrição, dica monetária
  e feedback/erro em `aria-describedby`. Preservei parsing, centavos, payload,
  revisão, rascunho e foco de erro; descartei o parágrafo opcional redundante.
- Login: três contas públicas documentadas (auctioneer, bidder1, bidder2 em
  example.com, senha pública Demo123!) chamam diretamente o helper `login()`.
  Manual e demos compartilham ref síncrona de tentativa; botões indisponíveis
  durante envio, “Entrando…” no acionado, erro anunciado e controles liberados
  na falha. Mantive callback, JSON, same-origin, returnTo e papel. Corrigi o foco
  da validação manual após uma falha demo, sem mudar autenticação.
- Links: tokens e foco aplicados a links de conteúdo com seletores locais.
  Arremates mantém lista, ações/receipt condicionado e fallback de cópia;
  títulos compactos mantêm nome acessível, links/botão têm cerca de 44px.
  Carteira e Painel não receberam mudança estrutural; auditoria continua documento.

## Matriz de provas

| CA | Evidência executada |
| --- | --- |
| CA01 | Tokens existentes preservados, branco do CTA usa token; inspeção das capturas e suites brand/layout/touch/keyboard no gate. Aceite humano ainda pendente. |
| CA02 | Layout e consultas nas dimensões exatas 1440×900,375×812,320×812; passagem 768×812. Sonda adicional: 28 cenários sem overflow global nem descendentes críticos fora do viewport, excluindo rails intencionais. |
| CA03 | Suites da Sala/WS preservam textos ganhando/superado/pending/cancelled e situações de conexão; QH-01 acrescenta settled. |
| CA04 | 5 live/20 próximos/50 encerrados, 6 iniciais/+6, último item do rail alcançável; lateralidade/presença/foco/CTA no primeiro viewport típico; 3 proporções, carga atrasada estável, 1 download e 503/fallback. |
| CA05 | Sala 1440/375/320, título longo integral, um timer antes do título e antes da obra no mobile, 50 lances recentes (janela máxima), ação/histórico e alvos. Suites completas de zero, REST/WS, POST, anti-sniping e recuperação passam. |
| CA06 | Carteira extrema preservada; 50 resultados de Painel e 50 arremates nos testes, 100 eventos de auditoria com hash expandido pelo teclado; foco/toque em auditoria e arremates, receipt/cópia/fallback preservados. Sonda adicional usa painel 30/arremates 20. |
| CA07 | Novo `lot-creation.spec.ts` percorre catálogo→form→erro/foco→revisão→publicação em 1440/768/375/320; descrições exatas, aria-describedby acumulado, centavos/payload e POST único. |
| CA08 | 3 demos diretos com papel/POST JSON/retorno ao lote; manual→manual/manual→demo/demo→manual/demo→demo no mesmo turno JS e em pendência; 401/503/rede, sem retry, liberação e foco; retorno externo/papel incompatível recusados; login manual existente preservado. |
| CA09 | Pending em duas regiões da Sala; snapshots settled sold/unsold exigem “Encerrado” nas duas, zero ocorrências de “apurando resultado”, zero timer. Receipt somente sold e histórico preservados; asserts anteriores de heartbeat, reconexão, late REST, ausência de POST e terminalidade permanecem. |

A sonda estrutural usa títulos extensos, dinheiro máximo, aliases/hashes sem espaços,
imagem 503, histórico máximo, e mede descendentes além do scroll global. As capturas
usam obras locais existentes com API simulada; não são prova da AIC/produção nem
golden files. Não modifiquei fontes do produto após o candidato do gate.

## Comandos e resultados reais

| Execução | Resultado | Exit |
| --- | --- | --- |
| Playwright focal inicial, 8 arquivos | 174 passed,4 failed; novos testes procuravam “Lote publicado”, mas o texto existente é “Lote criado”. Corrigi somente o seletor. | 1 |
| Playwright focal final, 10 arquivos | 240 passed,24.8s | Não capturado pelo agente principal; suíte concluiu sem falhas no log |
| Focal session após ajuste final de foco | 25 passed,4.8s | 0 |
| Sonda visual com obras locais | Screenshots Vitrine/Sala/login/criação; medições sem overflow | 0 |
| Sonda estrutural final | 28 cenários, zero ocorrências de overflow/descendentes fora do viewport | 0 |
| `VERIFY_E2E=1 ./verify.sh`, candidato final | Todas as etapas abaixo passaram | **0** |

O focal session no sandbox falhou antes dos testes por `listen EPERM` na porta 4173;
reexecutei com acesso ao servidor local e Chromium. Uma primeira captura temporária
parou por seletor de busca incorreto (`textbox`, em vez do label do searchbox);
a captura corrigida terminou exit 0. Nenhuma dessas falhas exigiu mudança de produto.

Executei o verify intacto em cópia isolada sem dotenv/credenciais, dependências
locais reutilizadas e URLs fictícias para os bancos dev/test. Conferi SHA-256 dos
256 arquivos de execução antes/depois: zero divergências entre raiz e cópia.
A variável `COMPOSE_DISABLE_ENV_FILE=1` evitou leitura automática de dotenv.

Saída relevante do gate:

```text
All checks passed!
110 files already formatted
2343 passed, 1 warning in 141.51s (0:02:21)
Frontend: lint — aprovado
Frontend: typecheck — aprovado
ℹ tests 192
ℹ pass 192
ℹ fail 0
ℹ skipped 0
Vite: 80 modules transformed
5 skipped
291 passed (29.8s)
Docker build: DONE
verify.sh: todas as etapas passaram.
```

Os cinco skips são `real-stack.spec.ts`, opt-in com E2E_REAL_BASE_URL. O warning
Starlette/httpx e avisos NO_COLOR/FORCE_COLOR são preexistentes; não alterei
bibliotecas por eles. O gate não comprova deploy nem cookie publicado.
Após o gate restaurei o bind mount original do PostgreSQL com Compose, sem dotenv,
preservando o volume: exit 0, Healthy. Não alterei verify.sh/backend.

## Arquivos alterados

Produto (11, incluindo o polimento posterior):

- `frontend/src/App.css`
- `frontend/src/ArtworkImage.tsx`
- `frontend/src/FeaturedLot.tsx`
- `frontend/src/LoginForm.tsx`
- `frontend/src/LotBidPanel.tsx`
- `frontend/src/LotForm.tsx`
- `frontend/src/LotPage.tsx`
- `frontend/src/LotState.tsx`
- `frontend/src/LotRail.tsx`
- `frontend/src/ClosedLots.tsx`
- `frontend/src/MoneyField.tsx`

Testes (11; criação é novo):

- `frontend/e2e/audit.spec.ts`
- `frontend/e2e/layout.spec.ts`
- `frontend/e2e/vitrine.spec.ts`
- `frontend/e2e/lot-room-ws.spec.ts`
- `frontend/e2e/lot-room.spec.ts`
- `frontend/e2e/my-lots.spec.ts`
- `frontend/e2e/session.spec.ts`
- `frontend/e2e/touch-targets.spec.ts`
- `frontend/e2e/wallet.spec.ts` (seletor manual exato)
- `frontend/e2e/wins.spec.ts`
- `frontend/e2e/lot-creation.spec.ts` (novo)

Registros: SPEC.md, este documento, artefato 6.2, sprint-status.yaml e
`docs/uso_de_ia.md`. `frontend/test-results/.last-run.json` foi gerado pelo
Playwright fora da lista prevista de fontes; é saída local de execução.
Não alterei Story 6.1, arquitetura, marca/fontes, dependências ou deferred-work;
cadastro continua apenas como candidata já documentada no contrato visual.

## Evidências temporárias e aceite

Diretório: `/private/tmp/atrio-6-2-build-visual/`.

- `vitrine-1440.png`, `vitrine-768.png`, `vitrine-375.png`, `vitrine-320.png`.
- `vitrine-retrato-1440.png`, `vitrine-quase-quadrada-1440.png`, `vitrine-fallback-1440.png`.
- `sala-1440.png`, `sala-375.png`, `sala-320.png`; versões `sala-completa-*` mostram a página inteira.
- `novo-lote-1440.png`, `novo-lote-375.png`, `novo-lote-320.png`; versões `novo-lote-completo-*` mostram a página inteira. Capturas curtas focam a microcopy.
- `login-1440.png`, `login-375.png`, `login-320.png`.
- `measurements.json` guarda medidas básicas; `/private/tmp/atrio-6-2-build-stress/measurements.json` guarda os 28 cenários e descendentes.

Logs temporários: `/private/tmp/atrio-6-2-focal-final.log`,
`/private/tmp/atrio-6-2-session-final.log`, `/private/tmp/atrio-6-2-verify-final.log`,
`/private/tmp/atrio-6-2-build-visual.log`, `/private/tmp/atrio-6-2-build-stress.log`.
A lista e o diff sem Git ficam no runtime exclusivo; não adicionei golden files.

Não encontrei regressão funcional nos gates. O limite restante é o **aceite visual
humano**, sobretudo composição/fade do hero e hierarquia da Sala. Browser integrado
não conectou à bridge; usei Playwright existente como fallback. Não alego auditoria
WCAG geral, teste de outros navegadores ou validação publicada. Mantenho Story/SPEC
6.2 `in-progress`, explicitamente aguardando esse aceite; 6.1 permanece `review`,
Épico 6 `in-progress`, 6.3 não iniciada. Não executei Git/gh/commit/push/merge/deploy,
li dotenv/segredos, implementei cadastro, ou chamei code review independente.

## Polimento das seções — antes do aceite visual

Implementei o pequeno polimento solicitado posteriormente pelo usuário: ponto
roxo de 8px junto ao título Ao vivo, com ciclo de 1,8s ease-in-out, opacidade
1→0,55→1 e escala 1→0,85→1; relógio lilás estático em Próximos lotes; ponto
estático em `--color-danger` para Encerrados. Usei spans `aria-hidden=true` e
pseudo-elementos, sem nova dependência, JS de animação ou mudança de roles.
A animação só transforma/pinta o ponto, sem deslocar a caixa reservada.
Descartei glow/ring e animações de entrada/relógio para manter discrição.

Modifiquei somente App.css, LotRail.tsx, ClosedLots.tsx e vitrine.spec.ts, além
dos registros. Hero e comportamento dos rails não receberam alteração.
O teste novo mantém os três nomes acessíveis, verifica que somente Ao vivo
anima, que sua caixa não muda ao longo do ciclo e que movimento reduzido
remove todas as animações mantendo o indicador visível.

Comandos desta rodada:

- `npm run lint && npm run typecheck`: exit 0.
- `npm run test:e2e -- e2e/vitrine.spec.ts e2e/layout.spec.ts e2e/keyboard.spec.ts`: **60 passed, 6.9s, exit 0**. O servidor de teste também recompilou o build.
- Captura temporária da Vitrine atualizada: exit 0; `scrollWidth/clientWidth`
  1440/1440,375/375,320/320, sem overflow. Os testes de layout também medem
  descendentes críticos e preservam a rolagem interna dos rails.

Novas screenshots em `/private/tmp/atrio-6-2-vitrine-polish/`:
`vitrine-1440.png`, `vitrine-375.png`, `vitrine-320.png` (primeiro viewport);
`vitrine-completa-*` (página inteira, incluindo os três indicadores) e
`vitrine-secoes-*` (viewport começando na seção Ao vivo).
Log focal: `/private/tmp/atrio-6-2-polish-focal.log`.

**O verify exit 0 registrado acima corresponde ao candidato anterior a este
polimento.** Conforme instrução humana, não o repeti nesta rodada estética.
Após o aceite visual, será necessário renovar os gates finais invalidados
antes do review independente. Mantenho story/sprint in-progress. Não iniciei review.

## Refinamento final dos indicadores — aguardando novo aceite visual

O usuário aprovou o primeiro ajuste e solicitou uma segunda afinação, ainda dentro
do aceite visual. A orientação anterior de Encerrados estático foi substituída
explicitamente por vermelho mais evidente e fade mais lento.

Alterei somente `frontend/src/App.css` e a apresentação coberta por
`frontend/e2e/vitrine.spec.ts`, além dos registros. Usei `.vitrine .lot-state-dot`
para aplicar a mesma respiração roxa de 1,8s ao hero e a todos os itens ao vivo da
Vitrine, reaproveitando os marcadores decorativos existentes. A Sala continua sem
animação; o teste confirma o isolamento do seletor. Não modifiquei dados, hero,
comportamento dos rails ou markup nesta rodada.

Encerrados usa o token danger em intensidade plena nos extremos do ciclo, em vez
da opacidade fixa de 0,8 anterior; seu fade de 2,8s varia apenas entre 1 e 0,85,
sem escala. Descartei criar vermelho neon/token novo ou copiar o ritmo mais ativo
de Ao vivo. Próximos mantém exatamente o relógio lilás estático. A media query
reduced motion desliga as duas animações, mantendo os indicadores e seus textos.

Comandos e resultados desta rodada:

- `npm run lint && npm run typecheck`: exit 0.
- `npm run test:e2e -- e2e/vitrine.spec.ts e2e/layout.spec.ts`: **51 passed, 7.0s, exit 0**.
- Capturas atualizadas em 1440×900,375×812,320×812: exit 0; scrollWidth igual a
  clientWidth (1440,375,320). Os focais de layout preservam as provas dos
  descendentes críticos, títulos/valores extremos, rails e fallback.

O focal verifica o marcador do hero e os dois itens ao vivo da fixture com a mesma
animação; nomes acessíveis/aria-hidden; ritmo de Encerrados; relógio estático;
caixa estável e todas as animações decorativas removidas em reduced motion.

Screenshots novas em `/private/tmp/atrio-6-2-indicators-final/`:
`vitrine-1440.png`, `vitrine-375.png`, `vitrine-320.png` (primeiro viewport),
`vitrine-completa-*` (página inteira) e `vitrine-secoes-*` (a partir de Ao vivo).
A captura percorre as miniaturas lazy de Encerrados antes da página inteira.
Log focal: `/private/tmp/atrio-6-2-indicators-final-focal.log`.

Não executei verify completo ou review independente nesta rodada. O gate completo
anterior permanece histórico e deverá ser renovado depois do aceite visual final,
conforme solicitado. Story/SPEC/sprint continuam in-progress aguardando esse aceite.

## Gate final pós-aceite visual humano — 28/10/2026

Recebi o aceite visual humano FINAL de hero ÁTRIO, responsividade, Sala,
microcopy, login demo e indicadores finais. O usuário aprovou Ao vivo com
respiração roxa de 1,8s em todas as ocorrências pertinentes da Vitrine,
Encerrados com vermelho mais evidente e fade contido de 2,8s, Próximos lotes
com relógio lilás estático e `prefers-reduced-motion: reduce` desativando as
animações decorativas. Não fiz nova alteração visual ou correção de código/teste.

Executei novamente, integralmente e sem editar o script:

```sh
VERIFY_E2E=1 ./verify.sh
```

O processo terminou com **exit code 0**. Usei a raiz de uma nova cópia isolada
do candidato em `/private/tmp/atrio-6-2-post-acceptance-verify`, sem dotenv/
credenciais, porque os loaders do backend/Vite tentam carregar dotenv
automaticamente. Preservei o mesmo procedimento de isolamento do gate anterior.
As dependências locais foram reutilizadas e os bancos foram configurados com
valores fictícios documentados; `COMPOSE_DISABLE_ENV_FILE=1` impediu o carregamento
automático pelo Compose. Conferi os **256 arquivos de execução por SHA-256**,
comparando raiz original e cópia com o manifesto capturado antes do gate: **zero
divergências**. O verify.sh e todas as fontes/testes são idênticos ao candidato.

| Etapa final realmente executada | Resultado | Exit |
| --- | --- | --- |
| Ruff check | All checks passed! | 0 |
| Ruff format --check | 110 files already formatted | 0 |
| Docker/Compose/PostgreSQL de teste | Healthy | 0 |
| pytest | **2343 passed, 1 warning, 138.46s** | 0 |
| npm run lint | Aprovado | 0 |
| npm run typecheck | Aprovado, incluindo e2e | 0 |
| npm test | **192 tests, 192 pass, 0 fail, 0 skipped** | 0 |
| npm run build | Vite: 80 módulos, build aprovado | 0 |
| npm run test:e2e, dentro do verify | **292 passed, 5 skipped, 30.6s** | 0 |
| docker build | Build da imagem aprovado | 0 |
| Script completo | verify.sh: todas as etapas passaram. | **0** |

Log: `/private/tmp/atrio-6-2-post-acceptance-verify.log`. A suíte completa incluiu
o teste dos indicadores, que prova os pontos do hero/itens ao vivo, nomes
acessíveis/aria-hidden, ritmo lento de Encerrados, relógio estático, geometria
estável e desligamento das animações em reduced motion; o efeito fica restrito
à Vitrine e não atinge a Sala. Nenhuma regressão foi observada no gate final.

Não houve falha nem correção adicional nesta execução. Depois do gate restaurei
o bind mount original do PostgreSQL com Compose, sem dotenv e preservando o
volume: exit 0, Healthy. Não alterei código, testes, verify.sh ou outras stories.

Limitações restantes: cinco testes `real-stack.spec.ts` permaneceram ignorados
porque dependem de E2E_REAL_BASE_URL; Playwright usa API simulada e não comprova
o ambiente publicado. O warning Starlette/httpx já existente permanece, sem falha
de gate. O review independente é a próxima etapa e **não foi executado nesta
sessão**. Story/sprint 6.2 ficam `review`, SPEC `in-review`, nunca done. A 6.1
permanece review, Épico 6 in-progress e 6.3 backlog. Não executei Git/gh/commit/
push/merge/deploy nem li `.env*`.
