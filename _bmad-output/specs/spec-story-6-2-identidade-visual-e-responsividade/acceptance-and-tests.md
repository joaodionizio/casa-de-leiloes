# Critérios, matrizes de prova e gates

## Critérios de aceite rastreáveis

Decidi decompor os 3 CAs originais em provas observáveis e nas melhorias autorizadas
pelo pedido. Descartei screenshots pixel-perfect e testes que só reproduzem CSS.
Nenhuma linha abaixo está aprovada como evidência do futuro build nesta SPEC.

| CA / capacidade | Dado / quando | Então / prova necessária |
| --- | --- | --- |
| CA01 / CAP-1 — CA original 1 | Abro as 6 telas centrais | Marca/direção/tokens próprios coerentes; valores e tempo legíveis. Inspeção CSS+DOM e aceite visual, sem depender de fonte exata |
| CA02 / CAP-4 — CA original 2 | Abro cada tela a 1440×900,375×812,320×812, com conteúdo adverso | Sem scroll horizontal global, corte/ocultação de informação crítica ou controle fora da largura; header sem colisões, campos/CTAs utilizáveis |
| CA03 / CAP-1 — CA original 3 | Exibo ganhando/superado/encerrado/apurando e estados pertinentes | Texto/ícone acessível diferencia os estados; cor só reforça. Prova pelos rótulos e condições da matriz abaixo |
| CA04 / CAP-2 | Vitrine tem live, só próximos ou nenhum elegível | Hero com obra protagonista e um CTA real; desktop texto à esquerda/obra à direita; mobile próprio; fade/ausência não comprometem dados. 5/20/50 mantém rails e arquivo compacto |
| CA05 / CAP-3 | Sala live com título longo, valores altos e diferentes papéis | Um timer junto ao estado antes da obra no mobile; lance/posição/ação antes de histórico/detalhes; título integral consultável; nenhum efeito na ordem/arbitragem REST/WS |
| CA06 / CAP-4 | Carteira extrema,30 lotes,20 arremates,100 eventos | Disponível destacado e 3 saldos; painel e arremates densos; resultado/receipt pertinentes; auditoria com sequência/alias/valor/time/veredito/hash legíveis |
| CA07 / CAP-5 | Crio/reviso lote em desktop/375/320 | Os 2 textos semânticos exatos são visíveis e descritos no campo, sem alterar parsing/validação/payload; anti-sniping separado |
| CA08 / CAP-6 | Escolho conta demo ou uso login manual | Mesmo POST/helper/callback; um envio, “Entrando…”, erro normal, controles liberados após falha, retorno seguro e fluxo manual preservado |
| CA09 / CAP-1/3 — QH-01 | Sala recebe ended+pending ou ended+settled | Pending diz “Encerrado, apurando resultado”; settled diz “Encerrado” e não contém “apurando resultado”; resultado recebido preservado, sem mudar backend |

## Matriz de cobertura atual por tela

`S` = cobertura automatizada pertinente já existe; `P` = parcial, tamanho ou
asserts incompletos; `—` = não encontrei. Esta é a suíte atual, separada das sondas
e da cobertura requerida após o build. Não infiro legibilidade só de overflow verde.

| Tela | Desktop 1440×900 |375×812|320×812| Overflow | Estado sem só cor | Valores/tempo | Teste existente | Lacuna a fechar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vitrine | S | S | S | S, inclusive filhos fora do viewport | S, textos; não matriz completa por largura | P: valores/horários cabem, sem prova de primeiro viewport do hero refinado | `layout`, `vitrine`, `brand`, `keyboard`, `touch-targets` | Nova lateralidade, fade, imagens de proporções reais,5/20/50 e CTA típico no primeiro viewport |
| Sala | P: detalhe público coberto; operação 1280×800 | P: recuperação 375×850 | P: detalhe 812; operação/hierarquia 800 | S nos cenários existentes | S: ganhando/superado/pending/cancelado; settled tem expectativa desatualizada | P: timer/valor visíveis, hierarquia com título longo insuficiente | `layout`, `lot-room`, `lot-room-ws` | Provar operação nas 3 dimensões, timer antes da obra e QH-01 sem apagar asserts terminais |
| Carteira | S | S | S | S com saldo máximo | S em avisos; estados de leilão não se aplicam | S: disponível maior que apoios e todos os números contidos | `wallet`, `touch-targets` | Preservar; completar Meus arremates no header se teste comum mudar |
| Painel | S | P:375×900 | P:320×900/800 | S com 50 resultados e confirmação | S: elegibilidade/sold/unsold/pending/cancelled | P: valor máximo+total/datas, sem prova de toque de todas as ações | `my-lots` | Exatas alturas 812; campos da criação e microcopy sem e2e próprio |
| Auditoria | P:1280×800 | — | P:320×800 | S com 100 eventos e hash aberto | S: fases, integridade e resultados textuais | P: dados presentes; não prova toda geometria/foco | `audit`; navegação em `receipt` |375/1440 e dimensões exatas, resumo/valor/hash/summary por teclado |
| Meus arremates | S | — | P:320×900 | S,50 títulos longos | S: pending/won textuais; matriz de demais resultados incompleta | P: BRL/data/alias presentes, sem alvo mínimo/foco/valor máximo explícitos | `wins` |375/812 e 320/812, ações de toque, título compacto acessível, estados complementares |
| Login, auxiliar | S | S | S | S | Erro em texto | Campos legíveis | `layout`, `session`, fluxos em `wallet/wins/lot-room` | Demo direto, disputa manual/demo, acessibilidade e falhas |
| Novo lote, auxiliar | — | — | — | Só sonda desta SPEC | Erros/formato já têm texto/símbolo | Só lógica pura de dinheiro/rascunho | `lotDraft.test.ts`, `money.test.ts`; não há e2e dedicado | Caminho catálogo→form→revisão, helpers associados, campos/datas/ações e ausência de overflow |

Como complemento exploratório, as sondas desta SPEC mediram as 6 telas e login
nas 4 larguras 1440/768/375/320 e criação nas 3 principais, sem overflow nas amostras.
Isso não transforma `P/—` em teste versionado. Não há teste tablet atual dedicado;
incluo 768×812 como verificação focal do breakpoint 48 rem existente, sem multiplicar
toda a suíte por mais um tamanho.

## Matriz de estados sem depender de cor

| Estado | Ocorrências atuais relevantes | Prova textual/semântica a preservar ou acrescentar |
| --- | --- | --- |
| Ganhando | `LotBidPanel`, calculado de sala/participação pareadas | “✓ Você está ganhando”; oculto quando dado privado não é confiável; nunca borda verde isolada |
| Superado | `LotBidPanel` | “↑ Você foi superado”, inclusive lance próprio fora dos 50; sem inferir de cor/última linha |
| Neutro/participação indisponível | Sala | Não inventar posição; aviso textual quando participação falha; não usar ausência de verde como única explicação |
| Ao vivo | `LotState` em hero/rails/Sala; `MyLots`, `AuditPage`, `MyWinsPage` | “Ao vivo”; ponto decorativo só reforça. Estado continua vindo do servidor |
| Agendado | Próximos/hero sem live, Sala, painel, auditoria e wins quando pertinente | “Agendado” e “Começa…”/abertura quando disponível; sem countdown ou fase calculada no cliente |
| Encerrado/apurando | `phaseStatusText` genérico na Vitrine; Sala pending; painel/auditoria/wins pending | “Encerrado, apurando resultado”; sem winner/receipt inventado e sem CTA de lance |
| Encerrado liquidado | Sala com `settled` — QH-01; auditoria/wins, resultados do painel | Sala “Encerrado”, sem “apurando”; preservar resultado recebido. Painel já distingue “Vendido”/“Sem arremate”; auditoria “Arrematado…”/“Encerrado sem vencedor”; wins “Você arrematou”/“Não arrematado” |
| Cancelado | Sala terminal, painel, auditoria e wins | “Cancelado”/“Este lote foi cancelado”; não reaparece na Vitrine, sem confundir com encerrado pendente |
| Integridade verificada/adulterada | Auditoria e erros pertinentes | Veredito textual; na adulteração, manter retenção dos dados não confiáveis, sem afirmar verificado |
| Conexão/atualização/envio | Sala, painel, wallet, demo/cópia | “Conectando”, “Reconectando”, “Sem conexão…”, “Atualizando”, “Entrando…” e feedback existente; status/alert pertinentes, timer não anunciado a cada segundo |

Testo rótulos visíveis/nome acessível e o payload que os determina, não a cor.
Não exijo screenshot em escala de cinza: a diferenciação já é demonstrável pelo
texto/semântica. Na Vitrine, não invento settlement ausente para distinguir vendido.

## Plano mínimo de Playwright

Reutilizo `frontend/playwright.config.ts`, Chromium, `mockApi`, `makeLots`,
`makeBids`, `LONG_TITLE` e `MAX_CENTS`. As APIs simuladas continuam sem banco/AIC.
Fixtures adicionais ficam no suporte de testes, sem nova biblioteca de testes.

| Prova | Alteração mínima de cobertura / asserts |
| --- | --- |
| P01 — hero/layout | Adaptar teste de lateralidade desktop em `layout.spec.ts`: informação à esquerda, arte à direita e maior presença; preservar mobile obra antes da ficha. Verificar caixas dentro do viewport, texto/CTA visíveis, sem overlay sobre foco/ações; nenhum screenshot diff |
| P02 — volumes/imagem | Ampliar a fixture existente para 5 live/20 próximos/50 encerrados; assert de 6 iniciais/+6, rail interno, último item alcançável, sem duplicar destaque. Três proporções por imagens de teste determinísticas, uma falha 503/fallback e carga atrasada; medidas antes/depois da carga sem deslocar dados |
| P03 — sala mobile | Estender prova de hierarquia existente às dimensões contratadas, com um timer antes da arte e título limitado visualmente sem perder nome integral; CTA/inputs/alvos≥43 px, histórico depois da operação e detalhes depois do histórico |
| P04 — estados terminais | Em `lot-room`/`lot-room-ws`, provar pending e settled (sold/unsold já exercitados). Atualizar expectativa legada T22/T23/T40 de “apurando” somente para settled; manter zero heartbeat/retry/POST indevido, late REST sem reabrir e sem formulário/timer terminal |
| P05 — consultas | Preservar carteira extrema e 50 resultados administrativos existentes; ajustar viewports 375/320 para 812 no teste pertinente ou acrescentar o mínimo. Auditoria 100 em 1440/375/320 com details abertos e teclado; wins 20 em 3 viewports, resultado/links/fallback de cópia contidos |
| P06 — foco/toque | Reusar `touch-targets`/`keyboard` para incluir link Meus arremates e ações de wins/demo/audit; verificar contorno e hit-area próximos de 44 px sem sobreposição. Manter foco do rail primeiro/último e Back/Forward |
| P07 — criação | Um focal novo, por exemplo `lot-creation.spec.ts`, intercepta busca/detalhe/POST atuais. Percorre seleção→campos→revisão; valida textos exatos, `aria-describedby` com descrição+dica+erro, inputs/datas/CTAs dentro do viewport. Uma publicação simulada verifica payload inalterado e ausência de duplo envio; sem motor de domínio no mock |
| P08 — demo | Estender `session.spec.ts`: papel/e-mail corretos para cada opção renderizada; POST JSON do endpoint existente, `credentials` preservadas no helper; pendente exibido, clique repetido e cruzado manual/demo gera 1 POST. Sucesso/erro 401/5xx/rede, nova tentativa manual e `returnTo` seguro/por papel |
| P09 — seletores legados | Rótulos “Entrar como…” tornam `name:'Entrar'` não exato ambíguo em `session`, `wallet`, `wins`, `lot-room`. Tornar o alvo manual `exact:true` preserva o mesmo teste/fluxo; `my-lots` já usa exato. Não apagar testes de login manual |
| P10 — tablet | Uma passagem focal a 768 para header, hero, painel/lista e campos; medir recomposição/ausência de colisões no 48 rem real. Conferência manual dos pontos de transição 64 rem/75 rem conforme região alterada |

Não crio um produto cartesiano de todas as variantes e volumes. A menor amostra
estrutural combina 5/20/50 numa Vitrine; reutiliza 50 lotes de painel (supera 30) e
50 wins já existentes (supera 20), acrescentando apenas o tamanho faltante; mantém
51 lances/50 recentes na Sala e 100 na auditoria. Um título longo, valor extremo e
imagem falha por família detectam a estrutura. Tipos adicionais de imagem e estados
são focais; não repito centenas de registros por cor/papel.

## Asserts e inspeção visual

- `documentElement.scrollWidth <= documentElement.clientWidth`; também medir
  descendentes críticos para não “resolver” overflow com `overflow-x:hidden`.
  Rails podem rolar internamente; CTA, campos, hashes e texto crítico não ficam
  recortados. Tolerância de 1–2 px só para caixas/subpixel, não para scroll global.
- Valores inteiros, cronômetro, labels e horários devem caber/quebrar sem ellipsis
  nem sobreposição. Verificar conteúdo, `scrollWidth/clientWidth`, caixas e
  hierarquia relativa; manter font-size de entrada ≥16 px e não reduzir valor/tempo
  até virar texto de rodapé para passar. A moeda máxima permanece exata.
- Normal e stress: R$850, R$18.450, R$1.250.000 e limite técnico
  `9007199254740991` centavos; relógios com horas, aliases/hashes e texto sem espaços.
  Não somar valores que ultrapassem o contrato para fabricar fixture inválida.
- Foco visível por teclado, ordem pertinente, labels/alt/nome acessível, helpers
  associados, toque próximo de 44 px e sem regiões sobrepostas. Verificar contraste
  nos pares usados, não apenas existência de token. Não realizar auditoria WCAG
  completa fora desta story nem anunciar timer/valor reconhecido a cada tecla.
- Conferência humana: obra domina o hero, fade suave não parece glow/SaaS,
  mobile recomposto, valor/tempo/CTA evidentes, listas compactas e documentos
  legíveis. Screenshots servem de apoio humano, não contrato pixel-perfect.

## Regressões a preservar

| Família focal existente | Contrato que continua valendo |
| --- | --- |
| `vitrine`, `layout`, `brand`, `keyboard`, `touch-targets`; `vitrine/lotLabels/lotPhase/asOf/route/brand/publicLots` Node | API pública/snapshot, seleção/deduplicação do destaque, mais 6, imagem, History/deep-link/foco/marca. Sem preço atual/countdown na Vitrine |
| `lot-room`, `lot-room-ws`; `bids/bidPosition/bidFeedback/bidSubmission/countdown/lotRoomSocket/lotConnection` Node | POST único, recusa real, saldo/posição pareados, 201/WS/REST, anti-sniping, zero, reconexão e terminais. Só QH-01 altera texto terminal justificado |
| `wallet`; `wallet/walletDeposit/walletFeedback/money` Node | Saldos, depósito, ambiguidades, barreira por conta, sem gráficos/novo ledger |
| `my-lots`; `lots/lotCancellation/lotDraft/lotTime` Node | Resultado/total no mesmo snapshot, refresh/foco/stale, confirmação/cancelamento/papéis e payload de criação |
| `audit`, `receipt`, `wins`; `audit/wins` Node | Dados públicos, pseudônimos, retenção na integridade falha, comprovante só quando existente, cópia/fallback, estados e privacidade |
| `session`, controles de auth dos demais E2E; `route` Node | Manual, returnTo interno seguro, sessão expirada, logout, papel errado sem chamadas privadas |
| Backend e testes 6.1 via verify | Origin/JSON/cookie/CSRF/CORS/500, políticas, persistência, lance/anti-sniping/liquidação/auditoria. Nenhuma expectativa de segurança é enfraquecida |

## Comandos do futuro build e gates

1. Executar os focais tocados de Playwright e os Node pertinentes, preservando os
   testes anteriores. Comando focal possível: `cd frontend && npm run test:e2e --
   e2e/layout.spec.ts e2e/vitrine.spec.ts e2e/lot-room.spec.ts
   e2e/lot-room-ws.spec.ts e2e/wallet.spec.ts e2e/my-lots.spec.ts
   e2e/audit.spec.ts e2e/receipt.spec.ts e2e/wins.spec.ts
   e2e/session.spec.ts e2e/brand.spec.ts e2e/keyboard.spec.ts
   e2e/touch-targets.spec.ts e2e/lot-creation.spec.ts`.
2. No frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.
3. Gate completo `./verify.sh`: Ruff/format, PostgreSQL de teste isolado, pytest,
   frontend e Docker build, conforme script atual. Não alterar script por esta story.
4. **É necessário `VERIFY_E2E=1 ./verify.sh` no candidato final**, pois mudanças
   visuais/responsivas exigem Chromium. Ele já executa o gate padrão; uma execução
   final bem-sucedida satisfaz 3+4 sem repetição ritual. Reexecutar após correção que
   invalide evidência pertinente. Registrar comandos, saída real e exit codes.
5. Teste visual humano antes do review independente; depois sigo
   `FRONTEND-WORKFLOW.md` e `FECHAMENTO-DE-EPICO.md`, sem confundir spec/teste com
   aprovação. Os 5 real-stack continuam opt-in com `E2E_REAL_BASE_URL`: execução
   local pode complementar integração, não é gate publicado da 6.1/6.4.

Baseline desta SPEC está em `current-state.md`; não executei os gates 3/4 aqui.
Ambiente de teste do futuro build não deve exigir ler `.env*` nem credenciais
privadas; usar a infraestrutura isolada e valores fictícios já documentados.

## Riscos e mitigação

| Risco concreto | Limite/mitigação |
| --- | --- |
| CSS comum muda recibo/header/form estável | Seletores estreitos, preserve suite receipt/brand/session; sem reset global de fontes ou overflow escondido |
| Mover timer altera vida útil/onZero ou duplica callbacks | Uma instância/âncora existente; suites de zero/WS/anti-sniping/terminal completas |
| QH-01 perde estado pending | Branch por phase+settlement_status,2 cenários explícitos; não mudar helper genérico |
| Fade oculta obra/texto/foco/fallback | Região de transição isolada, containment, sem captura de eventos;3 proporções e falha, efeito removível |
| Título compacto perde conteúdo | Nome integral acessível e texto integral na Sala/ficha; não truncar valor/hash; nada depende de hover |
| Demo abre concorrência ou perde returnTo | Mesma rotina e guarda síncrona; medir 1 POST com clique cruzado/pendente, safeReturnPath existente |
| Mocks não provam cookie/CSRF publicado | Backend real coberto pelo verify; produção permanece gate 6.4, sem alegar nova aprovação 6.1 |
| Muitos dados/imagens sem paginação/cache | Preservar limites visuais/mais 6/lazy/fallback; dívidas API/cache/429/idempotência continuam adiadas, sem backend oportunista |

## Definição exata de “6.2 pronta para build”

Considero pronta para build somente quando:

1. O kernel e os 3 companions estão completos e coerentes com código/direção,
   com CAs, mudanças classificadas, arquivos, estados, matrizes e provas definidas.
2. QH-01 está resolvida: **cumprido pela resposta humana desta sessão**. A premissa
   de preservar a ordem da Carteira está explícita, não encoberta por teste verde.
3. O usuário revisou e aprovou esta SPEC integral, incluindo hero, microcopy, demo
   e tratamento de títulos, sem decisão nova de identidade/domínio pendente.
4. Nenhuma implementação é tratada como autorizada pela classificação documental:
   o build só começa por instrução posterior explícita do usuário.

Nesta entrega, 1–2 estão preparados; 3–4 aguardam revisão/liberação. Mantenho sprint
6.2 em `backlog`, 6.1 em `review` e nenhuma story seguinte iniciada.

Após build, “implementação pronta para review” exige CA01–09 provados, gates
finais verdes, evidência/limitações registradas e teste visual humano. “Done”
depende dos aceites/reviews previstos no workflow; fechamento do épico ainda
depende dos gates próprios. Não antecipo esses estados nesta SPEC.
