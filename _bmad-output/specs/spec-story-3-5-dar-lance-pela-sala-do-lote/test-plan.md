# Testes proporcionais e critérios refinados

Decidi testar os novos contratos e fluxos de UI. Descartei repetir concorrência financeira, rollback, ordem de locks, hash/HMAC e matriz de domínio já cobertos pela 3.4. A coerência do snapshot público vem de a leitura ser uma única instrução (B8) e das invariantes de B3; não simulo commit no meio de uma instrução.

## Integração backend

Novo `backend/tests/integration/test_bid_reads.py`, PostgreSQL real pelo harness existente. Reutilizo `tests/auth_support.py`, `lot_support.py`, `bid_support.py`, fixtures/recorder e segredos fictícios; não crio harness nem SQLite. Fixtures podem preparar 51 linhas por helpers de teste; basta uma prova de integração real com POST para demonstrar reflexo do novo fim, sem executar 51 POSTs redundantes.

| ID | Casos e prova |
| --- | --- |
| B1 | Chaves exatas e obrigatórias dos sete campos públicos, quatro do bid e três próprios; nullable obrigatório; schemas OpenAPI sem dado privado |
| B2 | 0 bids: atual null, total 0, lista vazia, mínimo inicial; `/mine`: alias presente/estável, count0/lastnull |
| B3 | 51 bids: exatamente50, sequências51..2, total51; amount/sequence do primeiro iguais a current/total; ordem por sequence mesmo se placed_at empatar |
| B4 | Dois bidders: `/mine` count/último somente do alias autenticado; antes/depois do primeiro alias igual; bidder com sequence1 e sem participação entre2..51 mantém count1 e último correto fora da janela pública |
| B5 | Mínimo: primeiro lance/incremento via domínio, soma=MAX_CENTS numérica, soma>MAX_CENTS null; mesmo contrato em scheduled/live/ended; fronteiras de fase com as_of fixo e margens no caminho real |
| B6 | Público igual para anônimo, ambos papéis e cookie inválido com as_of fixo; nenhuma consulta de User. `/mine`: 401 anônimo/expirado,403 AUCTIONEER,404 ausente,422 UUID inválido; autenticação precede dado privado |
| B7 | Headers no-store nos200/404/auth401/403;422 segue handler global existente, sem adicionar assert falso de no-store. Envelope/loc/type reais; malformado público sem banco, privado sem query de negócio |
| B8 | Recorder público: exatamente1 statement,1 clock_timestamp, clock MATERIALIZED, LATERAL com LIMIT50 e DESC. Projeção sem bidder_id/hash/HMAC, sem FOR UPDATE/FOR SHARE/escritas (isso cobre a ausência de lock); transação de leitura encerrada ao responder; `/mine`: uma consulta negócio + SELECT esperado de User, count completo e último limitado |
| B9 | Estado persistido de lots/bids/wallets idêntico antes e depois dos GETs, inclusive ended e legado. Alias generator chamado somente para a própria sessão no /mine, nunca público nem sobre linhas históricas |
| B10 | Um POST real com anti-sniping, seguido de GET: ends_at estendido e estado do último bid iguais ao201; API externa indisponível não altera leitura/nenhuma chamada de negócio à AIC |
| B11 | Privacidade de chaves e valores em200/schemas: proibir nomes/e-mails/UUIDs de usuários, hashes/HMAC e segredos sintéticos em JSON recursivo. Distinguir alias público legítimo de email/ID privado |

Ajusto `test_openapi.py`: caminho bids agora tem GET e POST, mantendo POST201 e erros intactos; novo /mine; response refs de `PublicBidRoomResponse` e `MyLotBidsResponse`; required e propriedades exatos. `test_access_policy.py` ganha somente as duas entradas GET com PUBLIC/BIDDER. Não afrouxo verificador de política nem os testes dos17 campos/statement da2.5.

## Testes puros frontend (node --test)

| ID | Arquivo e cobertura |
| --- | --- |
| F1 | `api/bids.test.ts`: GETs200 válidos, nullable/zero/limite50, missing/type inválido/timestamp sem fuso; extras ignorados; POST201 válido e inválido, cinco422,409,401,403 papel vsCSRF,404,validação,outro4xx,5xx,rede,nãoJSON/status inesperado. Corpo request tem só amount_cents e credenciais same-origin |
| F2 | `bidFeedback.test.ts`: textos literais da tabela, status+code; variar message para HTML/texto arbitrário não muda UI; ambíguo com releitura completa/parcial/falha nunca afirma resultado |
| F3 | `bidPosition.test.ts`: ganhando/superado/neutro/sem lance/ended/sem dados; count>0 com alias fora50 continua superado; apenas last_bid não determina posição |
| F4 | `countdown.test.ts`: tempo monotônico injetado,0/1ms/2min/1h/2d04h; ceil/clamp/formatos; trocar âncora/ends_at; Date.now lança sem afetar cálculo; o erro de âncora (`as_of` e `placed_at`) é só para mais, nunca para menos, e nenhum teste usa a contagem como autoridade de encerramento; suspensão de ticks não para elapsed |
| F5 | Mesmo módulo: trigger zero consome antes do fetch, mesmo ends_at/as_of novo/manual/erro não rearma; fim novo arma; fase ended/scheduled não dispara; zero durante POST coalesce sincronização |
| F6 | `bidSubmission.test.ts`: parser monetário reutilizado, vazio/inválido sem request; abaixo mínimo/acima saldo/ganhando/null/zero permitem caminho POST; barreira síncrona por owner+lote bloqueia segundo envio e sobrevive remontagem; isolamento de contas/lotes; nunca retry automático |
| F7 | Estado pós201: aplica current/ends/wallet/sucesso antes de resolver GET controlado; mínimo atualizando, snapshot antigo descartado, falha de follow-up mantém aceite; entrada preservada em recusa/ambíguo e cleared só em201 |
| F8 | `route.test.ts` existente: lote interno normalizado preservado; URL absoluta,//host,/login,path livre,UUID inválido rejeitados; sem ampliar whitelist. Helpers de estado/ref podem ser funções puras no módulo de envio, sem framework DOM novo |

Não repito toda a matriz de money.test; acrescento apenas integração parser→tentativa e atalho que não sobrescreve valor válido. Não testo React internals; efeitos observáveis de DOM e navegação ficam no Playwright.

## Playwright Chromium, API simulada

Amplio `frontend/e2e/support/mockApi.ts` preservando interface atual e defaults de carteira/deposito. Faço read model público coerente para cada lote existente (inclusive fixtures antigas), `/mine` por sessão e POST stateful. Modos de lance: accepted, anti-sniping, cinco recusas, integrity, unauthorized, forbidden, server_error, network,invalid201 e delayed. Capturo owner no início antes do atraso. Headers/erros seguem API real; `message` do mock pode ser deliberadamente diferente do texto esperado para provar mapeamento. Registro payloads e count de métodos/caminhos para provar que valores chegaram ao servidor e que não houve segundo POST.

Fixtures da sala usam as_of/starts_at/ends_at coerentes: makeLot atual tem casos em que `phase=live` e fim não está depois de AS_OF; não baseio countdown nesses defaults incoerentes. Uso `page.clock`/avanço controlado para zero e tempo, sem waits reais. Modos ambíguos simulam gravação antes da falha tanto quanto ausência de gravação; ambos devem produzir a mesma neutralidade do feedback. O mock não vira segunda implementação do motor: testes transacionais reais continuam responsáveis pelas regras.

Novo `lot-room.spec.ts` concentra fluxos abaixo; estendo specs existentes somente onde intenção antiga muda.

| ID | Cenário e observável |
| --- | --- |
| E1 | Visitante e AUCTIONEER: conteúdo público, zero formulário, zero GET/mine e wallet; visitante entra e volta ao lote; checking não pisca formulário |
| E2 | BIDDER live: formulário, alias e saldo; “Situação atualizada às HH:MM:SS” vem do `as_of` de `/bids` (mock com `as_of` distinto do detalhe) e muda a cada releitura; accepted atualiza valor/fim/carteira antes de GET atrasado e depois histórico/total/“Você”/posição |
| E3 | Cinco recusas parametrizadas: texto exato e valor mantido. `lot_not_started`/`lot_ended` partem de snapshot live antigo; código não precisa inventar formulário em scheduled/ended |
| E4 | D4: enviar valor abaixo mínimo e acima saldo, afirmar corpo/count POST recebido e mensagem do servidor. Formato inválido não geraPOST. Mínimo null e ganhando não desabilitam CTA |
| E5 | POST atrasado: botão/readOnly/aria-busy; clique+Enter não duplicam; “Atualizar sala” também desabilitado até o POST terminar e volta ao normal depois; sair e voltar enquanto pendente acompanha mesmoPOST e resultado. Troca conta não recebe carteira/feedback da anterior |
| E6 | Erro ambíguo: feedback neutro, valor mantido, uma rodada GET,zero segundoPOST; follow-up falho não diz estado atual. 409 tem recusa própria; follow-up falho após201 mantém sucesso/dados201 |
| E7 | Anti-sniping201: fim novo em todos os lugares e countdown maior; mínimo só apósGET. Outro lance observado por Atualizar pode substituir posição sem apagar confirmação da tentativa anterior |
| E8 | Zero: uma releitura por fim, não bloqueiaCTA enquanto servidor live; mesmo fim apósGET não dispara novamente mesmo com avanço amplo; snapshot ended remove ação; fim posterior rearma uma vez; falha não causa loop. Botão Atualizar refaz uma rodada |
| E9 | Ganhando/superado/neutro, lance próprio fora50, ended com “Seu último lance” e sem vencedor; vazio/limite/erro parcial sem crashes |
| E10 | 401 em POST e parametrização de401 em/mine ouwallet: /login com expired e returnTo lote; login retorna mesmo lote. Reusar negativo open redirect e seu controle positivo existente |
| E11 | Privacidade em painel/histórico/DOM da sala: somente aliases, nenhum email/UUID de pessoa/hash/HMAC. Header existente do próprio usuário pode mostrar seu email; não afirmar proibição no DOM global contradizendo App/SiteHeader |
| E12 | 320px e1280px, valores/títulos longos,50 linhas/fallback imagem: sem overflow; mobile painel antes do histórico, estado/tempo cedo, leitura por teclado/foco/labels/alert/status,alvos44px |

`session.spec.ts` deixa de exigir ausência de “Dar lance” e carteira no main do BIDDER live: passa a exigir formulário e preservar ausência de ações AUCTIONEER. `vitrine.spec.ts` mantém vitrine sem lance atual; casos de deep-link visitante continuam sem formulário. Teste “lê só detalhe” passa a reconhecer detalhe+/bids sem AIC. Layout/keyboard/touch-targets ganham só assertivas essenciais da sala; sem multiplicar todos os cenários por todos os viewports. `real-stack.spec.ts` continua opt-in separado; não crio suíte nova real-stack para3.5.

## Critérios de aceite refinados (rastreáveis à story)

| Story AC | Critério implementável | Evidência planejada |
| --- | --- | --- |
| AC1 | Sala usa read model e exibe atual/inicial,mínimo,histórico e tempo conforme fase | B1–B5,E2,E9 |
| AC2 | Alias próprio vem do backend mesmo com count0 | B2,B4,F3,E2 |
| AC3 | Cinco códigos e409 mapeiam textos exatos porcode,sem mensagem arbitrária | F1–F2,E3,E6 |
| AC4 | 201 é aplicado antes de reler; falha de sincronização mantém aceite | F7,E2,E6 |
| AC5 | Schemas/JSON/painel/histórico sem dados privados | B1,B11,E11 |
| AC6 | Visitante/leiloeiro sem formulário nem chamadas privadas | B6,E1 |
| AC7/7a | Countdown monotônico não decide fase,um trigger porfim,sem loop | F4–F5,E8 |
| AC8 | Novo ends_at do servidor muda timer e horário absoluto,flag gera aviso | B10,E7 |
| AC9 | Barreira sincronamente impede POST duplicado inclusive remontagem | F6,E5 |
| AC10 | Ambíguo preserva valor,uma releitura,zero reenvio,sem afirmação | F1,F2,F6,E6 |
| AC11 | Scheduled/ended sem formulário;ended apurando,sem vencedor | B5,E9 |
| AC12 | Posição pelos aliases/count completo,própria linha marcada | B4,F3,E9 |
| AC13 | 401 em chamada autenticada retorna via login ao mesmo lote,whitelist preservada | F8,E10 |
| AC14 | Duas políticas,DTOs,erros/no-store nos casos definidos,OpenAPI | B1,B6–B9 |
| AC15 | 320px/teclado/foco/label/status/44px,histórico após painel | E12 |
| AC16 | Abaixo mínimo/acima saldo chegam ao servidor,sem validação local domínio | F6,E4 |

## Verificação no futuro build

Rodo testes novos focados e depois `./verify.sh` e `VERIFY_E2E=1 ./verify.sh`, registrando saídas reais. O verify normal mantém pytest/Ruff/format,PostgreSQL real,ESLint,tsc,node--test,Vite eDocker; Playwright requer Chromium instalado e segue opt-in. Nunca ler `.env*` por inspeção nem configurar banco dev para testes; se restrição da sessão impedir infraestrutura, registrar bloqueio real sem inventar contagem/aprovação. Nesta execução documental **não rodei verify, pytest ou Playwright**.

Manual curto no build: dois navegadores no demo, A dá lance; B só muda após Atualizar; B supera A; A atualiza e vê superado; insuficiência/anti-sniping/ended;401 volta ao lote. O teste manual do dono segue o FRONTEND-WORKFLOW e não substitui evidência automatizada.
