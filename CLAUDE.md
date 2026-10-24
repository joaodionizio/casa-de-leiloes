# Casa de Leilões (Desafio Elite Dev, Verzel)

Casa de Leilões online: leiloeiro cria lotes a partir de uma API pública;
licitantes depositam saldo simulado, dão lances ao vivo e recebem comprovante
compartilhável; qualquer pessoa audita o histórico de lances. Desafio técnico
recebido em 22/10/2026, entrega até 29/10/2026. Deploy obrigatório. Projeto
solo, de portfólio. Enunciado em `docs/desafio-elite-dev.md`.

## Estado atual
**ARQUITETURA CONCLUÍDA. IMPLEMENTAÇÃO LIBERADA.** AD-1 a AD-30 vinculantes.
A story atual é sempre definida pelo artefato/prompt da sessão. Trabalhe em
exatamente uma story por vez. Restam só as questões de implementação (abaixo),
que não mudam a arquitetura.

## Regras de trabalho
- **Git é meu.** Nunca execute git (add, commit, branch, merge, push, status,
  diff). Leia arquivos com as ferramentas de leitura. Um commit por unidade
  coerente/story; eu reviso antes de cada commit.
- **As decisões são minhas.** Implemente a partir delas. Não decida nada em
  "Questões para a implementação" nem invente decisão para preencher lacuna:
  pergunte, com opções, consequências, custo e recomendação, e espere.
- **Uma story por vez, e pare.** Rode `verify`, mostre a saída real, avise que
  está pronta. Não comece a seguinte até eu mandar.
- **Fase sem código** enquanto eu não liberar. Documentos, sim.
- **Documentos em primeira pessoa** ("decidi X porque...", "descartei Y..."),
  com a alternativa descartada. Para mudar uma AD, altere antes
  `docs/ARQUITETURA.md`. Código que contraria uma AD está errado.
- **Números só de comandos executados** (cobertura, testes, tempos).
- **`docs/uso_de_ia.md`** atualizado durante o desenvolvimento.
- **Idioma:** código, banco e API em inglês; interface e mensagens em
  português. Não misturar no domínio técnico.
- **Segredos:** nunca leia, imprima nem copie `.env*` ou valores de segredos.

## Como usar o Claude Code aqui
- Plan mode (Shift+Tab) para explorar e planejar (specs, review); modo padrão,
  com aprovação, para implementar. Auto mode só se eu pedir.
- Opus planeja, escreve specs e revisa; Sonnet implementa (`/model`). Quem
  especificou não revisa o que especificou.
- Monitore `/context`. Use `/clear` entre fases ou tarefas não relacionadas.
  Use `/compact` quando a sessão estiver ficando longa ou carregada.
  ~70% pode ser usado como limite conservador interno, não como limite
  oficial do Claude Code.
- Aponte arquivos com `@` (ex.: `@docs/ARQUITETURA.md`) em vez de pedir busca.
- Este arquivo fica enxuto (menos de 200 linhas). Detalhe mora em `docs/`.

## Referência sob demanda (leia só quando a tarefa exigir)
| Quando | Leia |
| --- | --- |
| Lance, travas, fechamento, hora | `docs/ARQUITETURA.md` AD-6 a AD-9, AD-19 |
| Histórico, hash, pseudônimo | AD-13, AD-20, AD-21 |
| WebSocket, auth, CSRF | AD-10, AD-25, AD-11, AD-29 |
| API externa, imagem, seed | AD-12, AD-22, AD-23, AD-24 |
| Testes, `verify`, deploy | AD-17, AD-26, AD-27, AD-28, AD-14 |

## Decisões vinculantes (resumo; alternativas descartadas em docs/ARQUITETURA.md)
- AD-1 Python + FastAPI. AD-2 PostgreSQL, SQLAlchemy 2.x síncrono (`Session`),
  Alembic, psycopg 3.
- AD-3 Dinheiro em centavos, `BIGINT`, sufixo `_cents` (`total_balance_cents`,
  `committed_balance_cents`). CHECK: não negativo e committed <= total. Sem float.
- AD-4 React + Vite + TypeScript simples e explicável: interface/type, unions
  simples, `Promise<T>`, contratos HTTP e eventos WebSocket tipados. Evitar
  generics complexos, conditional/mapped types. Sem JavaScript puro.
- AD-5 Anti-sniping: lance válido com `0 < restante <= 2 min` soma 2 min ao fim
  atual; lance depois do fim nunca reabre. README: "Comportamentos que podem
  surpreender".
- AD-6 Hora: `clock_timestamp()` do PostgreSQL, lido depois da trava do lote,
  um único instante por operação. O navegador nunca decide.
- AD-7 Lance: uma única transação, 16 passos (ver ARQUITETURA.md).
- AD-8 Travas: lote primeiro, depois carteiras em `user_id` crescente.
- AD-9 Fechamento: mesma trava, relê `ends_at`, idempotente,
  `UNIQUE(lot_id)` em `receipts`.
- AD-10 WebSocket só para a sala; lances por `POST /api/lots/{lot_id}/bids`;
  heartbeat do cliente; snapshot completo ao (re)conectar; 1 processo.
- AD-11 JWT em cookie HttpOnly, mesma origem; Argon2; papéis `AUCTIONEER`
  (cria e gerencia os próprios lotes, não dá lance) e `BIDDER` (deposita, dá
  lances, não cria lote), como `UserRole.AUCTIONEER`/`UserRole.BIDDER`. Nunca
  LEILOEIRO/LICITANTE em código, banco ou payloads. Stream da sala público.
- AD-12 Art Institute of Chicago; snapshot copiado para o lote na criação.
- AD-13 Cadeia SHA-256 + âncora HMAC (`AUDIT_HMAC_SECRET`, em variável de
  ambiente, nunca versionado). Trigger só como defesa extra, se houver tempo.
- AD-14 Render gratuito: um Web Service (FastAPI + API + WebSocket + SPA) e
  PostgreSQL gratuito. `GET /health`. Primeiro deploy no épico 1.
- AD-15 Catálogo de museu; tokens CSS próprios; dark mode depois dos fluxos
  obrigatórios; estados nunca só por cor.
- AD-16 Fluxo vertical completo primeiro (lote criado até auditoria).
- AD-17 Testes críticos em PostgreSQL real. AD-18 Git e IA como acima.
- AD-19 Fechamento: scheduler simples + catch-up na inicialização e em
  operações que já alteram estado (tentativa de lance). **GET, HEAD e OPTIONS
  nunca alteram estado: nenhuma leitura liquida lote.** Leitura de lote vencido
  e não liquidado mostra "Encerrado, apurando resultado". Evento só depois do
  commit.
- AD-20 Pseudônimo por lote: `HMAC(PSEUDONYM_SECRET, "{lot_id}:{user_id}")`,
  parte do resultado. Segredo diferente do `AUDIT_HMAC_SECRET`.
- AD-21 Representação canônica v1 (JSON ordenado, UTF-8, UTC com 6 casas e
  `Z`, genesis de 64 zeros). Teste de bytes e hash idênticos.
- AD-22 Imagem direto do IIIF, placeholder local se falhar; sem guardar bytes.
- AD-23 `is_public_domain=true` obrigatório; snapshot mínimo no ARQUITETURA.md.
- AD-24 Seed idempotente na inicialização; IDs fixos; lotes demo marcados;
  novo lote demo só se todos estiverem encerrados; fixtures, sem API externa.
- AD-25 WebSocket async + Session síncrona em threadpool (curta); publicar só
  depois do commit; sem outbox agora.
- AD-26 O domínio recebe `now`; a aplicação lê `clock_timestamp()` após a trava.
- AD-27 `verify` (abaixo). AD-28 Monorepo + `uv` + Dockerfile multi-stage.
- AD-29 JWT 8 h; cookie HttpOnly/Secure/SameSite=Lax/Path=/ sem Domain,
  `__Host-` quando possível; CSRF: JSON, validar `Origin`/`Referer`, sem CORS
  permissivo. AD-30 Inglês no código, banco e API (`/api/lots`, `/api/wallet`,
  `/api/me/wins`...).

## Regras do domínio (invariantes)
- Saldo disponível = total - comprometido, sempre. O lance só entra se couber.
  Ao ser superado, o líder anterior volta ao disponível na mesma transação.
- A CHECK vale a cada UPDATE: cuidado com a ordem das atualizações na liquidação.
- Lance: só em lote ao vivo; 1º >= lance inicial; seguintes >= atual + incremento;
  o líder não cobre o próprio lance. O POST devolve aceito ou recusado com o
  motivo exato (abaixo do mínimo, saldo insuficiente, já está ganhando, lote não
  iniciado, lote encerrado). Lances nunca passam pelo WebSocket.
- Operação bloqueante de banco nunca roda no event loop.
- Fechamento idempotente: duas execuções não debitam, creditam, geram
  comprovante nem trocam o vencedor. Lote sem lances fecha sem vencedor.
- A auditoria detecta alteração, inserção, remoção do meio, truncamento e
  recálculo sem o segredo. Comprovante registra quantidade de lances e hash final.
- Vitrine, sala, auditoria e comprovante não dependem da API externa para dados
  de negócio. Só a imagem vem do museu.
- Auditoria e comprovante mostram só pseudônimo, nunca nome, e-mail ou ID real.
- AUCTIONEER não dá lance; BIDDER não cria lote. Toda rota declara sua política
  de acesso e um teste reprova rota sem política.
- Erro: formato único; 500 genérico, sem stack. `GET /health` desde o 1º deploy.

## Testes e verify (AD-17, AD-27)
- Teste no mesmo commit da entrega. Críticos em PostgreSQL real, nunca SQLite:
  lances simultâneos, saldo, líder superado, anti-sniping, lance após o fim,
  fechamento concorrente, idempotência da liquidação, adulteração, papéis.
- PostgreSQL de teste em Docker/Compose, banco dedicado e isolado do de dev.
- `verify` falha na primeira etapa que falhar. Back-end: `pytest`, Ruff,
  `ruff format --check`, integração em PostgreSQL real. Front-end: ESLint,
  `tsc --noEmit`, testes existentes, build de produção do Vite.
- Nunca afrouxe teste para o código passar. Se falhar, relate o erro.

## Seed e deploy
- 1 leiloeiro (`AUCTIONEER`), 2 licitantes (`BIDDER`) e ao menos 1 lote demo
  aberto. Nunca altere nem apague o histórico de lote antigo.
- README: roteiro de avaliação, cold start do Render, liquidação tardia,
  limitação commit/publicação, logout (token vale até `exp`), imagem externa,
  limites do histórico, anti-sniping sem teto.

## Fluxo BMAD
BMAD em português, artefatos em `_bmad-output/`. Brainstorm, arquitetura (feita),
UX, épicos e stories (o épico 1 inclui o 1º deploy), sprint planning,
implementação story a story, code review por épico. PRD dispensado: o enunciado
já é a especificação (registrar o motivo).

## Questões para a implementação (perguntar antes; não mudam a arquitetura)
1. Intervalos do scheduler e do heartbeat; reconexão do cliente com espera crescente.
2. Validar `Origin` no handshake do WebSocket?
3. `bidder_alias` persistido na linha do lance ou recalculado na auditoria?
4. Ordem na inicialização: catch-up antes do seed e antes do tráfego normal.
5. Limite exato dos 2 min: `now` fixo; caminho real com margens.
6. Só quem de fato fechou o lote publica o evento de encerramento.
7. Smoke test: "API indisponível" exige falha simulada.
8. Nome e cálculo do estado "Encerrado, apurando resultado" nas leituras.
9. Tentativa de lance em lote vencido: fechar primeiro, depois responder.
10. Nomes ainda não definidos: rota do WebSocket, rotas do comprovante e do
    link, segredo do JWT, ferramenta de teste do front. (Resolvidos na 1.2:
    `compose.yaml` na raiz, Python 3.13, PostgreSQL 18, `DATABASE_URL` e
    `TEST_DATABASE_URL`.)

## Armadilhas conhecidas
(Cada problema que custar tempo vira uma linha aqui.)
