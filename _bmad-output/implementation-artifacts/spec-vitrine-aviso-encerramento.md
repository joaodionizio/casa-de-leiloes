---
title: 'Aviso discreto de encerramento na Vitrine'
type: 'feature'
created: '2026-10-29'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Adicionar somente à Vitrine um aviso discreto de proximidade do encerramento, sem segundos nem countdown. Dado lote live com mais de 10 minutos restantes, quando renderizado, então não recebe aviso; dado restante entre 10 minutos inclusive e mais de 2 minutos, então mostra “Encerrando em breve”; dado restante positivo de até 2 minutos inclusive, então mostra “Últimos 2 minutos”. Dado prazo atingido/passado, lote scheduled ou ended, então não mostra aviso.

Calcular exclusivamente sobre o snapshot recebido, com `ends_at` e relógio injetável. Usar o `as_of` existente como instante de referência da fotografia; manter o aviso estável em renderizações locais e recalculá-lo quando houver novo snapshot pelo fluxo existente. Dado `ends_at` prorrogado em uma nova renderização, então recalcular a faixa corretamente, inclusive remover o aviso quando ultrapassar 10 minutos. Aplicar em FeaturedLot e LiveLotItem, próximo de “Ao vivo”, preservando o layout e a identidade visual, inclusive em 320/375px.

Não alterar backend, contrato da API, lances, anti-sniping, WebSocket, settlement, carteira, banco, arquitetura, filtros nem busca. Não criar timers, polling, requests extras, modal, toast, banner grande ou animação. Adicionar testes dos limites, fases excluídas, prorrogação e mobile; rodar focais e `VERIFY_E2E=1 ./verify.sh`; parar antes de commit, push ou deploy.

</frozen-after-approval>

## Implementation Notes

- Alteração pequena e reversível, sem lacunas de intenção nem efeito externo. Pedido do usuário autoriza a implementação e os testes.
- Criar `frontend/src/lotEndingSoon.ts` e `lotEndingSoon.test.ts`: helper puro `getEndingSoonLabel(endsAt, now)` com `now` em milissegundos. Datas inválidas retornam null; não decidir fase.
- `VitrinePage.tsx`: converter apenas `data.as_of` em milissegundos e passar como prop a FeaturedLot/LotRail. Nenhuma mudança no fluxo de busca/filtros ou fetch.
- `LotRail.tsx`: encaminhar o instante a LiveLotItem. `FeaturedLot.tsx` e `LiveLotItem.tsx`: restringir a live e renderizar linha discreta; incluir aviso no nome acessível do link do rail.
- `frontend/src/App.css`: regra local da Vitrine com token de marca existente, texto menor, quebra natural e nenhuma animação/fundo novo.
- `frontend/e2e/vitrine.spec.ts`: usar AS_OF e mockApi existentes, sem alteração de infraestrutura; testar componentes, fases, prorrogação no próximo snapshot, ausência de requests/WS e overflow em desktop/mobile.
- Atualizar `docs/uso_de_ia.md` com o registro desta tarefa. Preservar integralmente a correção anterior do lance vigente.

## Review Triage Log

- low, rejeitado — resolução das fronteiras: Date.parse usa milissegundos e descarta a fração submilissegundo presente no ISO do PostgreSQL. Reproduzidos os casos a menos de 1 ms de 0/2/10 minutos; o aviso visual pode cair na faixa adjacente nesse intervalo. Ocorrência imperceptível no uso normal e sem efeito financeiro/temporal de domínio. Preservar microssegundos exigiria parser temporal próprio além da correção simples, contrário à superfície mínima pedida. A resolução admitida é explicitamente a padrão do JavaScript, em milissegundos.
- low, rejeitado — E2E de novo as_of mantendo ends_at: oportunidade de cobertura futura, sem erro atual; VitrineContent converte data.as_of em toda renderização e o teste puro já varia now. Não há cache de valor/prop que retenha o instante anterior.
- false como defeito — aviso fora da Vitrine: busca dos usos confirma que o helper só é chamado por FeaturedLot e LiveLotItem, ambos montados exclusivamente pela Vitrine. O detalhe usa LotState sem o novo parágrafo; não há caminho de vazamento do aviso.
- low, rejeitado — associar aviso ao CTA do destaque: melhoria opcional, não violação demonstrada. O texto já é acessível em leitura sequencial e o CTA mantém a convenção existente de título/destino. Acrescentar associação e cobertura específica amplia o trabalho sem corrigir defeito requerido.
- low, rejeitado — E2E de vários avisos no rail: cobertura adicional de combinação; geometria dos dois avisos em 320/375/1440px e testes existentes de vários itens/scroll passaram. O aviso usa o fluxo flex existente e quebra de texto, sem alterar largura ou navegação; um novo cenário de combinação não corrige defeito observado.
- Nenhum achado funcional bloqueante; nenhuma correção adicional aplicada fora do escopo.

## Verification

- `node --test src/lotEndingSoon.test.ts src/lotTime.test.ts src/vitrine.test.ts src/lotLabels.test.ts`: **35 passed**, 0 falhas. `npm run typecheck` e `npm run lint`: aprovados.
- `npm run test:e2e -- e2e/vitrine.spec.ts e2e/layout.spec.ts`: **73 passed (9.2s)**. Inclui fronteiras dos avisos no destaque e no rail; ausência em agendados/encerrados; recálculo de 2 → 4 → 12 minutos após novos snapshots; relógio avançado 15 minutos e filtros locais sem modificar o snapshot nem gerar requests; nenhum WebSocket na Vitrine; ausência de overflow/sobreposição e animação nos avisos em 320, 375 e 1440px.
- `VERIFY_E2E=1 ./verify.sh`: **exit code 0**, todas as etapas aprovadas, incluindo PostgreSQL real isolado, Ruff, formatação, pytest completo, lint, TypeScript, testes Node, build Vite, Playwright e build Docker.

Saída real do gate:

```text
================= 2450 passed, 1 warning in 147.68s (0:02:27) ==================
ℹ tests 215
ℹ pass 215
ℹ fail 0
  7 skipped
  369 passed (42.4s)
verify.sh: todas as etapas passaram.
```

Os 7 E2E de `real-stack.spec.ts` são opt-in por `E2E_REAL_BASE_URL` e permaneceram pulados pela configuração existente. Avisos preexistentes do Starlette/httpx e de cores do Node não impediram a aprovação.

Arquivos de entrega criados/alterados: `frontend/src/lotEndingSoon.ts`, `frontend/src/lotEndingSoon.test.ts`, `frontend/src/FeaturedLot.tsx`, `frontend/src/LiveLotItem.tsx`, `frontend/src/LotRail.tsx`, `frontend/src/VitrinePage.tsx`, `frontend/src/App.css`, `frontend/e2e/vitrine.spec.ts`, `docs/uso_de_ia.md` e esta spec.

Alterado fora da lista prevista: `frontend/test-results/.last-run.json`, artefato local ignorado do Playwright. Nenhum arquivo de segredo alterado detectado por nome; conteúdo não lido nem comparado. Nenhuma mudança de backend, API, WebSocket ou regras de leilão. Nenhum commit, push ou deploy realizado. Revisão interna sem bloqueadores; a única ressalva técnica é a resolução de milissegundos já descrita acima.
