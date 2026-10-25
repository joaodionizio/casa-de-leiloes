# Mapa de implementação — Story 2.3

## 1. Arquivos

| Área | Arquivo | Ação |
| --- | --- | --- |
| Back-end | `backend/app/artic.py` | novo: constantes, `ArticClient`, `CatalogUnavailable`, `ArticArtwork`, parsing |
| Back-end | `backend/app/catalog.py` | novo: modelos, elegibilidade, `image_url_for`, serviço, `get_artic_client`, rotas (busca, detalhe e imagem pública) |
| Back-end | `backend/app/errors.py` | `CATALOG_UNAVAILABLE` + mensagem; `CODE_BY_STATUS` intacto |
| Back-end | `backend/app/main.py` | `app.state.artic_client = ArticClient()`; `register_catalog_routes(app)` após auth |
| Infra | `backend/pyproject.toml`, `backend/uv.lock` | `httpx` para `dependencies` |
| Smoke | `backend/scripts/smoke_artic.py` | novo |
| Testes | `backend/tests/fixtures/artic/*.json` | novos (7, `aic-contract.md` §5) |
| Testes | `backend/tests/catalog_support.py` | novo |
| Testes | `backend/tests/test_artic.py`, `backend/tests/test_network_guard.py` | novos |
| Testes | `backend/tests/test_catalog_image_route.py`, `backend/tests/fixtures/artic/image_sample.jpg` | novos (P6.1, proxy de imagem) |
| Testes | `backend/tests/integration/test_catalog_routes.py` | novo |
| Testes | `backend/tests/conftest.py` | guarda de rede |
| Testes | `backend/tests/test_openapi.py`, `test_errors.py`, `test_access_policy.py` | só acréscimos |
| Front-end | `frontend/src/api/catalog.ts` | novo |
| Front-end | `frontend/src/CatalogSearch.tsx`, `ArtworkDetailPanel.tsx`, `ArtworkImage.tsx` | novos |
| Front-end | `frontend/src/App.tsx` | busca para `AUCTIONEER`; `onSessionExpired` |
| Front-end | `frontend/src/LoginForm.tsx` | só se preciso para exibir o aviso de sessão expirada (já recebe `initialError`) |
| Front-end | `frontend/src/App.css` | seção "Catálogo" |
| Front-end | `frontend/public/artwork-placeholder.svg` | novo |
| Docs | `README.md`, `docs/uso_de_ia.md`, `docs/ARQUITETURA.md` | §3 e a revisão do AD-22 (P6.1, proxy de imagem) |
| BMAD | story 2.3, `sprint-status.yaml` | P1–P11, P7.1, P8.1 e C1–C4 de `decisions.md` em primeira pessoa; saídas reais do `verify` e do smoke; status `review` |
| Intocados | migrations, `seed.py`, `users.py`, `access.py`, `auth.py`, `csrf.py`, `security.py`, `config.py`, `spa.py`, `infra_check.py`, `Dockerfile`, `compose.yaml`, `start.sh`, `verify.sh`, `vite.config.ts`, `package.json` | — |

Ordem sugerida: `artic.py` + `test_artic.py` → guarda de rede → `catalog.py` +
`errors.py` + `main.py` + testes de rota/contrato → smoke → front → docs →
`./verify.sh`.

## 2. Plano em até 8 linhas (para o `bmad-build` mostrar antes de editar)

Arquivos do §1; integração AIC isolada em `artic.py` e regra em `catalog.py`;
duas rotas `AUCTIONEER` (busca e detalhe) e a rota pública de imagem (P6.1); 503 `catalog_unavailable`; front com os 10 estados de
`frontend-catalog.md` §3; testes de `test-plan.md` §2–§5; smoke §6; `verify`.

## 3. Documentação

- **README**, seção nova "Catálogo do Art Institute of Chicago": o que a busca
  faz (só domínio público com imagem, 20 mais relevantes, acervo em inglês);
  identificação enviada (`User-Agent` e `AIC-User-Agent`), descrita assim: a
  documentação oficial recomenda; nos probes desta story o Cloudflare devolveu
  403 sem identificação adequada; não é autenticação; limite de 60 req/min por
  IP; o que acontece se a AIC
  cair (busca mostra indisponível; login e resto seguem; lotes futuros não
  dependem dela); imagem pelo nosso proxy same-origin (`GET /api/catalog/images/{image_id}`, público, sem guardar bytes) com placeholder; comando do smoke e o
  que cada item prova. Em "Comportamentos que podem surpreender": busca limitada
  aos 20 mais relevantes; o firewall da AIC pode recusar termos com certos
  caracteres e isso aparece como catálogo indisponível; a imagem pode falhar sem
  afetar os dados.
- **`docs/uso_de_ia.md`**, seção "Story 2.3": o que a IA fez (validação do
  contrato real da AIC na spec, achados de identificação, `q` e firewall; spec;
  implementação), o que eu decidi (P1–P11), alternativas descartadas e o que eu
  revisei; números só de comandos executados.
- **`docs/ARQUITETURA.md`**, sem alterar AD: na Questão 7, acrescentar
  "**Resolvida na Story 2.3 (data):** o smoke test da AIC é o script manual
  `backend/scripts/smoke_artic.py` (`cd backend && uv run python -m
  scripts.smoke_artic`), fora do `verify`; a indisponibilidade é a falha
  controlada e determinística do mesmo cliente apontado para `127.0.0.1:9`
  (conexão recusada); timeout fica coberto pelos testes com transporte falso;
  descartei rodar o smoke como `pytest -m smoke` e deixar a indisponibilidade só
  nos testes com transporte falso. Detalhes na story 2.3." e uma linha no
  "Histórico de alterações" ("Questão 7 resolvida na Story 2.3. Nenhuma AD
  alterada.").

## 4. Riscos

| # | Risco | Mitigação |
| --- | --- | --- |
| R1 | ~~Cloudflare bloquear o IIIF no navegador.~~ **Ocorreu** (403 no teste manual de 24/10/2026). | Proxy same-origin (P6.1); placeholder continua para falha da mídia; passo 14 do roteiro confere que o navegador só fala com a nossa origem. |
| R8 | A rota de imagem é pública e cada imagem exibida custa uma requisição à AIC (sem cache, `no-store`): 20 miniaturas por busca contra 60 req/min por IP. | Aceito nesta correção por instrução; 429 → 503 → placeholder. Cache HTTP de navegador ou do servidor fica como decisão minha, fora desta correção. |
| R2 | A AIC mudar regras do firewall, a exigência prática de identificação, `config.iiif_url` ou nomes de campo. | Smoke itens 4 e 5; testes não dependem da AIC real. |
| R3 | DNS lento não é limitado pelo `connect` no modo síncrono; `read` é por bloco. | Aceito; documentado; threadpool isola o event loop. |
| R4 | Limite de 60 req/min por IP compartilhado no Render. | Um leiloeiro; sem cache (P8); 429 → 503. |
| R5 | Starlette 1.9 avisa que `TestClient` sobre `httpx` está deprecado (`httpx2`). | Fora do escopo; runtime usa `httpx` diretamente; acompanhar em upgrade. |
| R6 | A guarda de `getaddrinfo` pegar algum teste existente que resolva host externo. | O build roda a suíte completa; se surgir, relatar em vez de afrouxar. |
| R7 | Termos legítimos recusados pelo firewall aparecem como "indisponível". | Mensagem sugere outro termo; README. |

## 5. Fora de escopo

Igual a SPEC "Non-goals". Em especial: nada de lote, snapshot persistido,
navegação do leiloeiro, botão de criar lote, paginação, cache (de dados e de
imagem), proxy genérico, CSP, testes de front, Story 2.4. O proxy de imagem
controlado (`GET /api/catalog/images/{image_id}`, P6.1) **faz parte** da Story 2.3.
