---
id: SPEC-story-6-1-revisao-de-seguranca-e-de-erros
status: in-review
companions:
  - security-audit.md
  - ../../../CLAUDE.md
  - ../../../docs/ARQUITETURA.md
  - ../../../docs/desafio-elite-dev.md
  - ../../planning-artifacts/epics.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
  - ../../planning-artifacts/VITRINE-BLUEPRINT.md
  - ../../../docs/FRONTEND-WORKFLOW.md
sources: []
---

# Story 6.1 — Revisão de segurança e de erros

Especificação preparada em 28/10/2026 e autorizada para implementação nesta
sessão, exclusivamente para a Story 6.1. Este SPEC e
`security-audit.md` formam a especificação completa; as fontes vivas adotadas
continuam vinculantes. Resultados reais em [implementation-evidence.md](implementation-evidence.md).

## Why

Preciso comprovar os quatro critérios da Story 6.1 no estado integrado após o
Épico 5, identificando provas ausentes por rota e por fluxo antes da entrega.
Reutilizo as proteções existentes e acrescento somente evidência ou correção
necessária. Descartei transformar esta auditoria em uma refatoração geral de
segurança ou confundir teste local com validação do candidato publicado.

## Capabilities

- **CAP-1 — Escritas protegidas**
  - **intent:** Confirmar que cada rota HTTP de escrita rejeita requisições de origem divergente e conteúdo sem o tipo JSON exigido.
  - **success:** O inventário real de POST/PUT/PATCH/DELETE corresponde às provas individuais de 403 `csrf_origin_mismatch` e 415 `unsupported_media_type`, incluindo Content-Type ausente e não JSON, sem efeitos. Matriz e complementos mínimos em `security-audit.md` §3.
- **CAP-2 — Sessão e mesma origem**
  - **intent:** Confirmar cookie de sessão e CORS conforme AD-11/29, distinguindo configuração local e comportamento publicado.
  - **success:** Testes HTTPS de login/logout confirmam HttpOnly, Secure, SameSite=Lax, Path=/, ausência de Domain e prefixo `__Host-`; configuração e respostas não habilitam CORS permissivo. A inspeção do candidato publicado fica explicitamente pendente até haver evidência, também na Story 6.4 (§7).
- **CAP-3 — Continuidade sem AIC**
  - **intent:** Manter dados e fluxos de vitrine, sala, auditoria e comprovante quando a AIC estiver indisponível.
  - **success:** As leituras locais corretas e o snapshot WebSocket funcionam sem chamadas externas de negócio; o proxy falha controladamente e as telas que exibem mídia usam placeholder local, preservando os dados. A auditoria atual não exibe imagem. Provas compostas e complementos em §4, sem reabrir Q7.
- **CAP-4 — Erro inesperado seguro**
  - **intent:** Garantir uma resposta 500 genérica ao cliente, sem revelar informações internas.
  - **success:** Testes de exceção inesperada, falha de resposta e falha no middleware verificam o contrato JSON e ausência de stack, detalhes privados e sentinelas fictícias; o app real mantém debug desativado e nenhuma rota sintética de crash (§5).

## Constraints

- Preservo AD-11/12/19/22/29, arquitetura e contratos atuais. Reutilizo `ApiWriteGuardMiddleware`, handlers, sessão, snapshots locais e proxy; só corrijo produto se uma prova pertinente revelar defeito dentro das decisões existentes.
- Derivo as escritas da aplicação atual; a extração dos registradores identificou seis POST e nenhum PUT/PATCH/DELETE. Não trato esses métodos sintéticos do teste de middleware como rotas reais.
- GET/HEAD/OPTIONS e handshake WebSocket não liquidam nem alteram estado; não movo catch-up/seed nem introduzo fechamento por leitura ou POST vencido.
- Uso PostgreSQL de teste isolado e falha de transporte simulada, sem rede real; preservo controles positivos e provas transacionais existentes. Não adiciono framework ou suíte redundante.
- O candidato inicial da branch `epico-6-entrega-robustez-documentacao-e-opcionais` foi confirmado externamente como `8a460d26bb280e5a35379254a82b73c3224813a1`. Não atribuo a confirmação ao usuário, não a verifico com Git e não a uso como evidência de deploy. Produção documentada em `3d3ea97` não comprova publicação do candidato atual.
- Não leio `.env*`, não exponho segredos nem executo Git/gh/commit/push/merge/deploy. Não crio endpoint de crash/debug de produção.
- O gate da implementação é `./verify.sh`; os testes de fallback também exigem Playwright direcionado ou `VERIFY_E2E=1 ./verify.sh`. Registro somente execuções reais e seus exit codes na evidência.

## Non-goals

- Refatoração geral, nova arquitetura de segurança, CSRF/token/sessão novos, revogação de JWT, alteração de canonical v1, hash/HMAC, regras financeiras ou liquidação.
- Cache/rate limit de mídia, proxy genérico, armazenamento de imagens, idempotência, rotação de segredos, limites de capacidade ou demais dívidas fora dos critérios.
- Alterações visuais da 6.2, README final da 6.3, execução do deploy/validação final da 6.4 e opcionais 6.5–6.7.
- Iniciar outra story ou concluir épico por escrever esta spec; code review nesta sessão de implementação.

## Success signal

Considero a preparação concluída quando cada critério e cada escrita possui prova
existente ou complemento mínimo rastreável, com riscos e evidências públicas
pendentes explícitos. A implementação só poderá declarar o aceite completo da
6.1 com os testes/gate reais registrados e a inspeção publicada do CA2; evidência
local não substitui essa inspeção nem a validação final da Story 6.4.

## Open Questions

Nenhuma decisão humana de arquitetura ou implementação identificada como
pendente. A implementação desta spec foi autorizada. Se a implementação revelar necessidade de mudar uma decisão,
paro e apresento opções, consequências, risco, custo e recomendação.

## Execução autorizada da 6.1

Adotei a matriz parametrizada centralizada em `backend/tests/test_csrf.py`:
as seis escritas reais são confrontadas com a lista executada, com e sem SPA;
cada rota recebe os três negativos e um controle de despacho com headers
válidos. A sentinela antes das dependências/handler impede falso positivo por
rota inexistente e prova que banco, AIC e sessão não são alcançados. Preservei
as provas autenticadas/transacionais existentes. Descartei distribuir os
mesmos complementos entre quatro suítes de escrita.

Não altero `conftest.py`, configuração ou infraestrutura para dotenv. Executo
em cópia isolada de fontes permitidas, sem arquivos `.env*` nem segredos, com
valores locais fictícios e PostgreSQL de teste. Essa execução local não
comprova configuração ou publicação do deploy.

- [x] CA1: matriz executável ligada ao inventário runtime, envelopes e ausência de despacho/Set-Cookie/CORS.
- [x] CA3: ampliar provas existentes de leituras REST/WS e imagem falha, com controle de transporte; status 200 na vitrine.
- [x] CA3 navegador: ampliar fallback da sala/comprovante e navegação à auditoria, preservando dados.
- [x] CA4: reforçar envelope 500 completo, debug falso e ausência de rotas sintéticas no app real.
- [x] Executar focais, navegador pertinente e gate completo; registrar resultados reais.
- [x] Encerrar implementação em review, preservando CA2 publicado pendente e sem iniciar 6.2.

## Correção autorizada — R6.1-01 — 28/10/2026

Decidi corrigir exclusivamente o inventário backend da CA1 após o review
independente; descartei fechar a exceção documental por nome ou alterar produto.
O finding confirmou que `policy_by_route` omite rotas sem política efetiva e
`policy_problems` tolera caminhos documentais. Separo a descoberta de escritas
da conferência de políticas. Esta seção delimita a retomada: os demais CAs já
implementados ficam preservados; não refaço tarefas anteriores nem inicio 6.2.

Handoff de implementação: altero somente `backend/tests/test_csrf.py`,
reutilizando os mecanismos existentes para conferir política. A coordenação
executará primeiro o focal de regressão, depois as suítes pertinentes e
`./verify.sh`, e atualizará os artefatos. Não executo code review nesta sessão.

- [x] Derivar o inventário observado diretamente de `app.routes`, usando tipos HTTP públicos FastAPI/Starlette e todos os métodos POST/PUT/PATCH/DELETE declarados. Não consultar `access_policy`, `policy_by_route`, lista esperada ou exceções de caminho para descobrir escritas. Ignorar apenas métodos seguros e WebSockets conhecidos; reprovar Mount não inspecionável e tipo desconhecido, ou percorrer Mount com prefixo usando sua interface pública. Preservar detecção de duplicata método/caminho.
- [x] Confrontar esse inventário com W1–W6 (lista esperada já existente), independentemente das checagens `policy_problems`/`policy_by_route`. Dado o app real com/sem SPA, obter exatamente os seis POST e nenhum PUT/PATCH/DELETE, preservando os 36 negativos e controles positivos de despacho.
- [x] Dada mutação controlada sem política em `/api/docs`, `/api/openapi.json` e caminho inesperado, descobrir a sétima escrita e comprovar falha da validação CA1. Cobrir política incorreta, métodos múltiplos, Route/APIRoute, métodos seguros, WebSocket, Mount e tipo desconhecido com regressões pertinentes. Não registrar mutações em produção nem usar APIs privadas/não documentadas.
- [x] Executar o focal de regressão antes das demais suítes; depois `test_csrf.py`, `test_access_policy.py` e CA1 pertinente. Após focais verdes, executar `./verify.sh` completo, exit 0, sem leitura de `.env*` ou segredos. Playwright CA3 anterior permanece independente; não repeti-lo por rotina nesta correção estritamente backend.
- [x] Atualizar story, implementation evidence, área de correções do review e `docs/uso_de_ia.md`; registrar corrigido/aguardando re-review, sem aprovação pelo implementador. Manter story/sprint `review`, SPEC `in-review` e parar para re-review independente.

Não altero código de produção, middleware, sessão/JWT, erros, configuração,
`conftest.py`, frontend ou comportamento da aplicação. Não executo Git/gh,
publicação ou deploy, nem leio `.env*`, credenciais, cookies ou tokens reais.
