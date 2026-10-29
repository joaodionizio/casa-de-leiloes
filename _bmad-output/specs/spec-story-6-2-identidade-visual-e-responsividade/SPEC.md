---
id: SPEC-story-6-2-identidade-visual-e-responsividade
title: 'Story 6.2 — Identidade visual e responsividade'
status: done
date: '2026-10-28'
companions:
  - current-state.md
  - visual-contract.md
  - acceptance-and-tests.md
  - ../../../CLAUDE.md
  - ../../../docs/ARQUITETURA.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../../docs/FECHAMENTO-DE-EPICO.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
  - ../../planning-artifacts/VITRINE-BLUEPRINT.md
sources:
  - ../../../docs/desafio-elite-dev.md
  - ../../planning-artifacts/epics.md
  - ../../implementation-artifacts/deferred-work.md
---

# Story 6.2 — Identidade visual e responsividade

> Estado vigente em 29/10/2026: **done** por aceite humano técnico/visual e review independente aprovado. LOW R6.2-01 aceito sem correção; os registros anteriores de in-review são históricos.

> Este kernel e os companions formam o contrato completo para a revisão humana.
> Aceite visual humano FINAL concedido em 28/10/2026, incluindo os indicadores finais. Gate completo pós-aceite aprovado; pronta para review independente.
> Os esclarecimentos humanos do pedido de build prevalecem sobre as notas da fase documental.

## Why

Quero concluir o acabamento ÁTRIO das telas centrais, preservando as funcionalidades
aprovadas. A interface real já oferece boa parte da direção editorial e da adaptação
mobile; decidi concentrar a 6.2 no hero, na hierarquia operacional da Sala, nas
inconsistências verificadas e nas provas que faltam. Descartei reescrever o frontend.

## Capabilities

- **CAP-1**
  - **intent:** Reconhecer ÁTRIO e ler os dados operacionais com uma identidade editorial coerente nas seis telas centrais.
  - **success:** CA01/03: tokens próprios, tipografia e marca preservados, valores/tempo legíveis e estados críticos compreensíveis sem cor.
- **CAP-2**
  - **intent:** Encontrar uma obra protagonista e identificar estado, valor, horário e acesso ao lote cedo na Vitrine.
  - **success:** CA04: hero claro conforme direção humana, composição mobile própria, transição visual robusta e catálogo 5/20/50 utilizável sem overflow global.
- **CAP-3**
  - **intent:** Acompanhar o tempo e decidir o lance sem perder posição e ação entre a obra e os metadados.
  - **success:** CA05: um cronômetro junto ao estado antes da obra no mobile, dados de decisão antes do histórico, título integral acessível e regressões REST/WS/foco preservadas.
- **CAP-4**
  - **intent:** Consultar carteira, painel, auditoria e arremates com conteúdo extenso em tela estreita.
  - **success:** CA02/06: provas a 1440×900, 375×812 e 320×812, com listas densas, valores inteiros legíveis, hashes expansíveis e volume representativo.
- **CAP-5**
  - **intent:** Entender o significado dos valores ao criar um lote.
  - **success:** CA07: explicações exatas de lance inicial e incremento junto aos campos, associadas de forma acessível, preservando formato, validação, API e anti-sniping.
- **CAP-6**
  - **intent:** Experimentar os papéis pelas contas públicas de demonstração, mantendo o login manual.
  - **success:** CA08: um clique usa o login existente, com “Entrando…”, uma requisição por tentativa, erro normal e `returnTo` seguro; nenhuma mudança de backend/autenticação.

## Constraints

- Preservo **ÁTRIO — Leilões de Arte**, obra protagonista, branco/superfícies claras, roxo pontual, serif editorial e sans operacional. Sem biblioteca, fonte remota ou sistema visual novo.
- Trabalho nos componentes/CSS existentes; cada alteração é necessária a um CA ou polimento explicitamente autorizado, conforme `visual-contract.md`.
- A direção humana deste pedido permite texto à esquerda/obra à direita no hero desktop; prevalece sobre o esquema anterior do blueprint. Referências externas não definem nossa identidade.
- A Vitrine continua mostrando **lance inicial e horário**, conforme seu DTO; não recebe lance atual, countdown, polling ou WebSocket.
- Preservo centavos, formatadores, autorizações, cookies/CSRF, POST de lance, reconexão, anti-sniping cumulativo do servidor, liquidação, privacidade, auditoria, comprovante, imagens e navegação/foco aprovados.
- Se o acesso demo exigir backend, sessão, seed, segurança ou contrato novos, interrompo esse item e o classifico fora da 6.2.
- Playwright é evidência obrigatória do candidato final; baseline desta SPEC não aprova mudanças futuras nem prova produção.
- A 6.1 permanece intocada em `review`; aprovação técnica informada pelo usuário e pendência pública de deploy/6.4 não bloqueiam esta especificação.
- A restrição documental de não implementar foi superada pela autorização humana de build em 28/10/2026. Continuo sem executar Git/gh/deploy, ler `.env*` ou iniciar a 6.3.

## Non-goals

- Busca/filtro público 6.5, dark mode 6.7, estorno 6.6, paginação/endpoint/WS novos, novas regras de domínio ou autenticação paralela.
- Cadastro de conta, tela/link sem função, recuperação de senha, gráficos decorativos, redesign geral e arte final da marca.
- Resolver gates publicados da 6.1, efetuar deploy/6.4 ou substituir a aprovação humana e o review independente.

## Success signal

Consigo percorrer as seis telas a 1440/375/320, com os volumes e estados da matriz,
identificar obra/estado/valor/tempo/ação sem recorte crítico e operar por teclado/toque
sem overflow global. O candidato passa pelos gates de `acceptance-and-tests.md` e
recebe aceite visual humano, sem regressão funcional.

## Assumptions

- Preservo a Carteira com disponível primeiro e destacado, seguida de total/comprometido, como no código e teste aprovados; interpreto a enumeração dos três saldos do pedido como prioridades de leitura, não uma nova ordem obrigatória.
- A imagem ÁTRIO enviada durante a especificação confirma a direção textual do hero. Uso-a como composição, sem copiar ativos, fontes, controles ou dados; não recebi uma imagem AURA separada.

## Open Questions

- Não há decisão de produto/arquitetura aberta. **QH-01 foi resolvida pelo usuário:** a Sala distingue `ended+pending` de `ended+settled`, com correção apenas de apresentação e prova dos dois estados. Registro em `visual-contract.md`.
- O usuário aprovou esta SPEC e autorizou o build em 28/10/2026, com esclarecimentos vinculantes: título principal da Sala integral; QH-01 em todas as regiões visíveis; login demo com guarda síncrona; evidência visual antes de qualquer review independente. O usuário concedeu o aceite visual humano FINAL do candidato, incluindo hero, responsividade, Sala, microcopy, login demo e indicadores finais, em 28/10/2026.

## Evidência de implementação

Registrei mudanças, provas CA01–CA09, comandos e limites em [implementation-evidence.md](implementation-evidence.md). Registrei o aceite visual humano FINAL e o gate completo pós-aceite com exit 0. Mantenho a SPEC `in-review`, pronta para review independente; não executei esse review nem declarei `done`.

## Encerramento humano — 29/10/2026

Decidi concluir a 6.2 por aceite humano técnico/visual e review aprovado, com R6.2-01 LOW conscientemente aceito sem correção. Autorização expressa no pedido de 6.2A; histórico anterior preservado.
