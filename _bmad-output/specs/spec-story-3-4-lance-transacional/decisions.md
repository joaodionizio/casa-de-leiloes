
> **Nova revisão humana da AD-5 — 27/10/2026 (antes da Story 4.3).** Decidi voltar à regra cumulativa: com `0 < ends_at - now <= 2 minutos`, cada lance válido acrescenta 2 minutos ao término vigente (`ends_at vigente + 2 minutos`), inclusive com exatamente 2:00 restantes (flag verdadeira). A decisão intermediária `now + 2 minutos` foi revogada. Preservo abaixo o texto original como registro histórico; fórmulas e notas anteriores devem ser lidas na sua data. Lote encerrado nunca reabre; frontend/WebSocket apenas aplicam o `ends_at` persistido. Ver AD-5 em `docs/ARQUITETURA.md`.

# Decisões — Story 3.4

> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

## 1. Herança vinculante (não reabro)

| Origem | Contrato | Onde vira detalhe |
| --- | --- | --- |
| P1 | Trava → `clock_timestamp()` → gate → pré-carteira | `transaction-contract.md` §2 |
| P2 | Vínculo operacional; alias recalculado só do líder atual | `transaction-contract.md` §3 |
| P3 | Âncora vazia assinada no `INSERT`; legado `NULL` bloqueado; nada reassina | `seed-and-lot-creation.md` |
| P4 | Seed com `DATABASE_URL` + `AUDIT_HMAC_SECRET`, sem `PSEUDONYM_SECRET` | `seed-and-lot-creation.md` §3 |
| P5 | Segredos ≥ 32 bytes UTF-8, distintos entre si e do `JWT_SECRET`, fail-fast | `config-secrets.md` |
| P6 | 201 / 422 (código da 3.2) / DTO mínimo, sem `bidder_id`, hashes, HMAC | `http-contract.md` |
| P7 | 409 `lot_integrity_conflict`, mensagem única, log só com categoria | `http-contract.md` §4 |
| P8 | Schema §7 da story; `sequence = bid_count` autenticado + 1 | `database-schema.md` |
| P9 | `ARQUITETURA.md`, `CLAUDE.md`, `epics.md` já sincronizados | `implementation-map.md` §2 |
| 3.2 D2/D3/D8 | `evaluate_pre_wallet` → `evaluate_post_wallet`; `EligibleBid` só da pré | reuso literal |
| 3.3 D13/D14 | Receita §9; vazio exige HMAC do próprio lote; sem helper público novo | reuso literal |

## 2. Decisões técnicas desta spec (delegadas pela story à spec)

| ID | Decidi | Descartei e por quê |
| --- | --- | --- |
| D1 | **Ordem física dos statements.** As etapas 9→17 do AD-7 são calculadas em memória nessa ordem; o banco recebe F1 `UPDATE wallets`, F2 `INSERT bids`, F3 **um único** `UPDATE lots` coerente com líder, lance atual, `bid_count`, `final_hash` e `anchor_hmac`, mais `ends_at` só quando houve extensão (SR-02). Nenhum atributo do `Lot` muda antes de F3 | Dividir o `UPDATE` do lote: a CHECK `(bid_count = 0) = (current_bid_cents IS NULL)` reprova o primeiro lance (CHECK do PostgreSQL não é adiável). Um flush único na ordem implícita do unit of work: opaco e sem pontos reais de falha para injetar |
| D2 | `lock_lot(session, lot_id)` em `app/lots.py`: `SELECT` só de `lots`, `FOR UPDATE`, `populate_existing`, sem `JOIN` nem subconsulta | `FOR NO KEY UPDATE` (deixaria `INSERT` em `bids` fora do protocolo pegar `FOR KEY SHARE` no meio da transação); trava dentro de `bids.py` (a 4.3 precisa da mesma) |
| D3 | Gate como função de módulo `authenticate_previous_state(lot, rows, *, integrity, lot_id)` em `bids.py` (testável sem banco, com objetos simples), com categorias internas `IntegrityFailure`; não é exportado para outro módulo do app | Helper público em `bid_integrity.py` (3.3 D13); `try/except ValueError` amplo (esconderia bug como 409) |
| D4 | Histórico lido como linhas de colunas, `ORDER BY sequence`, depois da trava e da hora | Entidades ORM `Bid` (identity map poderia servir estado antigo) |
| D5 | Rota guarda `user.id` e faz `session.rollback()` antes do serviço: a transação do lance começa limpa | Herdar a transação da autenticação (correto em `READ COMMITTED`, mas o passo 1 ficaria implícito e o `User` carregado ficaria no identity map) |
| D6 | 201 `PlaceBidResponse` = `bid` + `lot` + `wallet` (campos em `http-contract.md` §2); alias incluído | `min_next_bid_cents`, `bid_count` (deriváveis, fora do "mínimo"); omitir o alias (é público na auditoria e é do próprio usuário) |
| D7 | Mensagens das cinco recusas = redação de referência da 3.2 §9; texto próprio do 409 | Mensagem do 409 por categoria (P7 proíbe) |
| D8 | `AuditSettings` (seed) e `IntegritySettings` (app) + `IntegrityConfig` com `bytes` `repr=False` em `app.state`; checagem contra o JWT em `create_app` | Uma classe só exigindo os dois (quebraria P4); converter `SecretStr` a cada requisição |
| D9 | `create_lot(..., audit_hmac_secret: bytes)` obrigatório; HMAC vazio calculado antes do objeto `Lot` existir | Parâmetro opcional (permitiria lote sem âncora); assinar depois do `flush` |
| D10 | Log: 409 `warning` (lot_id + categoria); aceite `info` (lot_id, sequence, anti_sniping); recusa de negócio sem log | Logar recusas (ruído; o cliente já recebe o motivo); logar alias, usuário ou valores |
| D11 | Falha injetada por `monkeypatch` de nomes em `app.bids` e de `Session.commit`, com recorder provando o statement anterior | Hook de falha no código de produção |
| D12 | Mantenho `UNIQUE (lot_id, previous_hash)`, nome explícito `uq_bids_lot_id_previous_hash` | Remover (é defesa barata e não redundante, `database-schema.md` §3); nome da convenção (`uq_bids_lot_id`, enganoso) |
| D13 | Sem retry. Deadlock (40P01) ou outro erro de banco = 500 genérico com rollback | Retry automático (esconderia violação do protocolo de travas; fora do escopo) |
| D14 | Ajustes de testes existentes além da §9.4 da story (`implementation-map.md` §3) | Deixar testes da 3.2/2.1 que fixam "códigos de recusa fora do catálogo" quebrarem sem registro |
| D15 | Prova da ordem gate → pré-carteira por comportamento (G9b, G10b, G11b: 409 onde a regra pura daria 422) e por ordem de chamadas dos primitives públicos (T-REUSE), mais M-24 (SR-01) | Provar só por T-ORDER (as duas etapas são puras e vêm antes das carteiras: não distingue); spy no nome do helper do gate (acopla à composição interna) |
| D16 | Data HTTP = instante ISO 8601 do serializer; data canônica = seis casas e `Z`; T-CLOCK compara instantes e reconstrói o canônico do `placed_at` relido (SR-03) | Prometer seis casas na resposta HTTP; comparar string HTTP com bytes canônicos |
| D17 | `drop_checks` captura `pg_get_constraintdef`, recria só o removido com a definição capturada, mesmo em falha, e confere o catálogo (SR-07) | Reescrever o SQL das CHECKs na fixture; depender de `reset_test_database` da próxima sessão |

## 3. Incompatibilidades e achados

| ID | Achado | Impacto | Recomendação |
| --- | --- | --- | --- |
| IC-1 | Story §10, T-SNIPE: "dois aceites na janela → +4 min" é **inviável** pelo caminho real sem esperar. Depois de uma extensão o restante é `r + 2 min > 2 min`; o segundo aceite só cai na janela se o relógio real andar `r`. Contradiz "margens de minutos, nunca segundos" da própria story | Teste da story, não P1–P9 | Substituído por T-SNIPE (3) (concorrente: B vê o fim já estendido e **não** estende) e T-SNIPE (1) (extensão = `ends_at` gravado, lido sob a trava, + 2 min exatos; nunca `now + 2`). Cumulatividade entre aceites sucessivos já é prova pura da 3.2. **Confirmado (Q-3 resolvida)** |
| IC-2 | AD-7 lista "atualizar líder" (11) antes de "registrar o lance" (16); fisicamente o `UPDATE lots` sai depois do `INSERT` (D1) | Interpretação: a ordem lógica e a atomicidade são preservadas; nenhum efeito é visível antes do commit | Registrar no review; não muda AD |
| F-1 | §9.4 da story omite testes que mudam: `test_bid_rules.py::test_refusal_codes_are_not_http_catalog_codes`, `test_errors.py::test_messages_are_the_fixed_portuguese_catalog`, FK/nulabilidade/CHECKs em `test_lots_migration.py`, `seed.run_seed` em `test_wallet_service.py` e `test_public_lots.py`, `clean_lots` | Sem eles o `verify` quebra | Lista completa em `implementation-map.md` §3. A inversão do teste da 3.2 cumpre o que ela previu ("o contrato HTTP nasce com o endpoint") e não afrouxa nada |
| F-2 | `backend/.env.example` precisa das duas variáveis, mas casa com `.env*` (CLAUDE.md proíbe ler) | Documentação operacional local | Resolvido (Q-1): o dono edita manualmente; agentes não leem nem editam |
| F-3 | 3.6, 4.3 e 6.6 decidem com líder, lance atual ou `bid_count`: precisam do **mesmo** gate | Obrigação futura (SR-08), sem escopo na 3.4 | `current-state.md` §5; `deferred-work.md` no build |
| F-4 | Seed grava a âncora com o segredo antes de `create_app` validar distinção contra o JWT. Se o operador trocar `AUDIT_HMAC_SECRET` depois, o demo vira 409 e, como `anchor_hmac IS NOT NULL`, ainda conta como aberto até vencer (72 h) | Disponibilidade do demo após troca de segredo (rotação não suportada, A1 da 3.3) | Resolvido por SR-09: documentar no README; sem mitigação no seed |
| F-5 | Demo legado de produção continua "ao vivo" na vitrine até vencer e responde 409 | Aceito por P3/§13 da story | README (já previsto) |
| F-6 | Falha de conexão depois de enviar o `COMMIT`: resultado indeterminado para o cliente; nova tentativa pode dar `already_winning` (SR-04) | Limitação transacional aceita | README; sem chave de idempotência nesta story |

## 3a. Review adversarial final (26/10/2026) — onde cada achado foi tratado

| Achado | Severidade | Tratamento |
| --- | --- | --- |
| SR-01 ordem gate → pré-carteira não provada | MEDIUM | D15; G9b, G10b, G11b, ordem semântica em T-REUSE, M-24 (`test-plan.md`) |
| SR-02 `ends_at` sempre no `SET` | LOW | `ends_at` só com extensão; T-ORDER com e sem extensão (`transaction-contract.md` §2) |
| SR-03 data HTTP × canônica | LOW | D16; `transaction-contract.md` §6.1; `http-contract.md` §2; T-CLOCK |
| SR-04 falha de commit | LOW | F-6; `transaction-contract.md` §7; A3 limitado a "antes de enviar" |
| SR-05 mutações | LOW | M-25, M-26; nota sobre releitura (`test-plan.md` §6) |
| SR-06 cobertura de adulteração | LOW | G19–G23 |
| SR-07 `drop_checks` | LOW | D17; `test-plan.md` §1 |
| SR-08 obrigações futuras | LOW | `current-state.md` §5; `implementation-map.md` §2 |
| SR-09 seed e segredo | LOW | `seed-and-lot-creation.md` §5; README em `implementation-map.md` §2 |
| Textuais | — | Termos do lote não autenticados (`transaction-contract.md` §3.7); justificativa do `READ COMMITTED` e `40001` (`concurrency-analysis.md` §2) |

## 4. Questões resolvidas (nenhuma aberta)

- **Q-1. Resolvida.** Eu edito `backend/.env.example` manualmente, quando necessário
  (acrescentar `PSEUDONYM_SECRET=` e `AUDIT_HMAC_SECRET=`). Agentes não leem nem
  editam o arquivo e não param o build por ele; o build só cita as variáveis no README.
- **Q-2. Resolvida** pelo review (SR-09): documentar no README, sem mitigação no
  seed e sem rotação.
- **Q-3. Resolvida.** Confirmei IC-1: não haverá teste em PostgreSQL real que espere
  duas extensões somando +4 min sem avanço real do relógio. A 3.2 prova a
  cumulatividade; a 3.4 prova integração, serialização e o uso do `ends_at` já
  atualizado (T-SNIPE (1) e (3)).

## 5. Premissas

- A1. O banco de produção pode conter lotes manuais e demo anteriores à 3.4; não
  confirmei o banco real.
- A2. Escala do desafio: leitura O(n) da cadeia por tentativa e fila na trava do lote
  são aceitáveis (pool padrão do SQLAlchemy, threadpool padrão do AnyIO).
- A3. Sem `statement_timeout`/`lock_timeout` configurados; a transação do lance não
  faz chamada externa.
