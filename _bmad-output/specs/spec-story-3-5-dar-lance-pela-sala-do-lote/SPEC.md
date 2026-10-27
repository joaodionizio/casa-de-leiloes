---
id: SPEC-story-3-5-dar-lance-pela-sala-do-lote
companions:
  - http-contract.md
  - frontend-flow.md
  - test-plan.md
  - implementation-map.md
  - validation.md
  - ../../../CLAUDE.md
  - ../../../docs/ARQUITETURA.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
sources:
  - ../../implementation-artifacts/3-5-dar-lance-pela-sala-do-lote.md
  - ../../implementation-artifacts/2-5-vitrine-pública-e-página-do-lote.md
  - ../../implementation-artifacts/3-1-carteira-e-depósito-simulado.md
  - ../../implementation-artifacts/3-2-regras-de-aceitação-do-lance-com-hora-injetada.md
  - ../../implementation-artifacts/3-3-fundamentos-de-integridade-do-histórico.md
  - ../../implementation-artifacts/3-4-lance-transacional-com-travas-e-anti-sniping.md
---

> **Nova revisão humana da AD-5 — 27/10/2026 (antes da Story 4.3).** Decidi voltar à regra cumulativa: com `0 < ends_at - now <= 2 minutos`, cada lance válido acrescenta 2 minutos ao término vigente (`ends_at vigente + 2 minutos`), inclusive com exatamente 2:00 restantes (flag verdadeira). A decisão intermediária `now + 2 minutos` foi revogada. Preservo abaixo o texto original como registro histórico; fórmulas e notas anteriores devem ser lidas na sua data. Lote encerrado nunca reabre; frontend/WebSocket apenas aplicam o `ends_at` persistido. Ver AD-5 em `docs/ARQUITETURA.md`.


# Story 3.5 — Dar lance pela sala do lote

## Why

Decidi completar a página pública do lote para que o licitante participe pela interface do motor transacional já entregue na 3.4. A sala precisa ler disputa e participação própria sem expor identidade privada, informar resultados confiáveis e permitir atualização explícita enquanto as atualizações entre clientes ainda não existem.

## Capabilities

- **CAP-1**
  - **intent:** Qualquer pessoa pode consultar o estado da disputa e seus lances recentes.
  - **success:** A leitura pública entrega os sete campos definidos no contrato, até 50 lances em sequência decrescente e a contagem total; com 51 lances retorna 50 itens e total 51, sem dados pessoais, hashes ou HMAC.
- **CAP-2**
  - **intent:** O licitante pode reconhecer seu pseudônimo, sua participação e sua posição.
  - **success:** A leitura própria entrega alias mesmo sem lance, quantidade completa e último valor; a UI distingue ganhando, superado e neutro mesmo com o lance próprio fora dos 50 exibidos.
- **CAP-3**
  - **intent:** O licitante pode enviar lance e entender aceite, recusa ou resultado incerto.
  - **success:** O 201 atualiza valor/fim/carteira imediatamente; as cinco recusas têm os textos contratados; envio pendente não duplica após remontagem; erro ambíguo nunca afirma resultado nem reenvia; mínimo e saldo não bloqueiam POST válido em formato.
- **CAP-4**
  - **intent:** A pessoa pode acompanhar o tempo indicado pelo servidor e atualizar a sala.
  - **success:** A contagem usa âncora do servidor e relógio monotônico, reflete anti-sniping, dispara uma releitura por `ends_at` em zero e permite atualização manual sem polling ou reclassificação local.
- **CAP-5**
  - **intent:** Cada papel pode acessar a sala com ações apropriadas e retorno seguro após login.
  - **success:** Visitante e leiloeiro não recebem formulário nem chamadas privadas; licitante vê formulário ao vivo; 401 volta ao mesmo lote após login; sala funciona por teclado e em 320 px sem overflow global.

## Constraints

- Preservei D1–D5 fechadas; os detalhes vinculantes estão nos companions. Descartei enriquecer o detalhe da 2.5, calcular alias/mínimo no browser, `is_leading` e validação de saldo/mínimo no cliente.
- Mantive contratos e motor da 3.4, detalhe da 2.5 e primitivas da 3.2/3.3; nenhum schema persistido muda. As duas rotas novas ficam em `bids.py` para evitar dependência circular.
- As leituras são puras, sem locks explícitos de linha, autenticação de cadeia, reparo, escrita ou recálculo de alias histórico. `ended` significa “Encerrado, apurando resultado”; não há vencedor afirmado.
- Estado dinâmico vem exclusivamente do read model público ou dos dados seguros do 201. Datas do detalhe não substituem snapshot da sala. O servidor continua autoridade de fase e aceitação.
- Reutilizo React/TypeScript simples, fetch same-origin, política declarada, envelope de erro, dinheiro inteiro e componentes/tokens existentes; sem dependência nova.
- Não exponho identidade da conta nos componentes da sala; o header autenticado existente continua identificando a própria sessão. Segredos permanecem no backend.
- Marca ÁTRIO, obra protagonista, texto e símbolo para estados, foco visível, controles reais e alvos de toque de 44 px orientam a UI.

## Non-goals

- WebSocket, heartbeat, reconexão, polling periódico, estrutura antecipada para transportes, cancelamento/Story 3.6 e Epic 4.
- Fechamento, liquidação, scheduler, catch-up, resultado, comprovante, auditoria 5.1, paginação, cursor, idempotency key, nova migration e alteração do motor de lance.
- Vitrine com lance atual, revisão de branding ou de componentes alheios à sala.

## Success signal

Abro um lote ao vivo como BIDDER, envio um valor inclusive abaixo do mínimo ou acima do saldo e vejo a resposta real do servidor; num aceite, valor/fim/carteira mudam antes da releitura. Outra conta só observa a mudança depois de “Atualizar sala”. A chegada a zero causa uma única releitura, e 401 preserva o retorno ao lote. O plano de testes prova esses comportamentos e os contratos sem repetir a suíte transacional da 3.4.
