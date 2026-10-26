# Mapa de implementação — Story 3.4

Para o `/bmad-build`, numa sessão autorizada. Nada aqui foi implementado.

## 1. Código de produção

| Arquivo | Ação |
| --- | --- |
| `backend/migrations/versions/0005_bids.py` | Novo (`database-schema.md` §1–§4) |
| `backend/app/config.py` | `MIN_INTEGRITY_SECRET_BYTES`, `AuditSettings`, `IntegritySettings`, `IntegrityConfig`, `integrity_config`, `get_audit_settings`, `get_integrity_settings` (`config-secrets.md`) |
| `backend/app/lots.py` | 5 colunas e 8 CHECKs no `Lot`; `lock_lot`; `get_integrity_config`; `create_lot(..., audit_hmac_secret)`; `POST /api/lots` passa o segredo |
| `backend/app/bids.py` | Novo: `Bid`, `IntegrityFailure`, `IntegrityConflict`, `AuthenticatedLot`, `PlacedBid`, `read_history`, `authenticate_previous_state`, `place_bid`, DTOs, `register_bid_routes`. Não importa `app.main` |
| `backend/app/errors.py` | 6 constantes e mensagens (`http-contract.md` §4) |
| `backend/app/main.py` | `create_app(..., audit_hmac_secret=None, pseudonym_secret=None)`; `app.state.integrity_config`; `register_bid_routes` depois da carteira |
| `backend/app/seed.py` | `audit_hmac_secret` em `seed_demo_lot`/`run_seed`; predicado; `main` lê `get_audit_settings()` antes do engine; docstring |
| `wallet.py`, `bid_rules.py`, `bid_integrity.py`, `lot_time.py`, `money.py`, `csrf.py`, `access.py`, `frontend/` | Intocados |

## 2. Documentação no build

| Documento | O quê |
| --- | --- |
| Story 3.4 | Dev Agent Record, File List, comandos e saídas reais, mutações (§6 do plano); Q-1, Q-2 e Q-3 já resolvidas (`decisions.md` §4) |
| `sprint-status.yaml` | Só no build (`in-progress` → `review`); esta spec não altera |
| `docs/uso_de_ia.md` | Sessão de spec e de build |
| `deferred-work.md` | Uma seção "Deferred from: spec da 3.4" com as obrigações de `current-state.md` §5: gate compartilhado (sem duplicar) para 3.6/4.3/6.6; marcador terminal em 4.3/6.6; `auctioneer_id` fora da âncora (4.3); snapshot coerente na 5.1; Q9 na 4.4. Mais IC-1 (confirmado): cumulatividade do anti-sniping provada só pela 3.2 |
| `README.md` | Variáveis `PSEUDONYM_SECRET` e `AUDIT_HMAC_SECRET` no Render **antes** do deploy (sem a de auditoria o seed falha e o servidor não sobe); valores aleatórios fortes (`secrets.token_urlsafe`); conflito de segredos no boot: não trocar `AUDIT_HMAC_SECRET` depois que âncoras existem, corrigir `PSEUDONYM_SECRET` ou `JWT_SECRET` (`seed-and-lot-creation.md` §5); lotes legados visíveis e sem lance (409); anti-sniping cumulativo e sem teto; recusas com motivo; 409 de integridade; falha de rede depois do commit pode esconder um lance aceito, e repetir pode responder "você já está ganhando" (F-6); rotação de segredos não suportada (inclui o demo, F-4); rollback consistente não detectado; âncora não cobre termos nem saldos |
| `backend/.env.example` | Fora do build: o dono edita manualmente (Q-1 resolvida); agentes não leem nem editam |
| `docs/ARQUITETURA.md`, `CLAUDE.md`, `epics.md` | Nada (P9). `CLAUDE.md` "Armadilhas" só se algo custar tempo no build (candidata: CHECK × `UPDATE` parcial do lote, D1) |

## 3. Testes existentes que mudam (sem afrouxar)

| Arquivo | Mudança |
| --- | --- |
| `tests/conftest.py` | Gera `PSEUDONYM_SECRET` e `AUDIT_HMAC_SECRET` antes de importar `app.main`, distintos; `TRUNCATE bids, wallets, lots, users`; `clean_lots` → `TRUNCATE bids, lots` (sem `CASCADE`) |
| `tests/lot_support.py` | `LOT_COLUMNS` + 5; `insert_lot(..., anchored=True)` |
| `tests/integration/test_lots_migration.py` | Colunas, tipos, nulos (3 novas anuláveis), nomes das CHECKs, duas FKs (o desempacotamento de uma só quebra) |
| `tests/integration/test_wallets_migration.py` | Nada obrigatório (o downgrade para `0003` passa pela `0005`) |
| `tests/test_openapi.py` | Lista de caminhos; `test_lot_routes_come_after_the_catalog_routes` com as novas posições |
| `tests/test_access_policy.py` | Nova entrada em `EXPECTED_POLICIES` |
| `tests/test_errors.py` | Catálogo literal com 6 entradas |
| `tests/test_bid_rules.py` | Inversão prevista pela 3.2 (F-1) |
| `tests/integration/test_seed.py` | `run_full_seed` e chamadas diretas com o segredo; subprocesso com `DATABASE_URL` + `AUDIT_HMAC_SECRET` e `PSEUDONYM_SECRET=""`; casos de demo legado |
| `tests/integration/test_wallet_service.py`, `test_public_lots.py` | `seed.run_seed(session, audit_hmac_secret=...)` |
| `tests/integration/test_lot_creation.py` | Âncora vazia válida (CA11) |
| `tests/test_config.py` | T-SECRETS (parte) |

## 4. Rastreabilidade dos critérios

| CA | Spec | Testes |
| --- | --- | --- |
| CA1 rota e papéis | `http-contract.md` §1–§3 | T-ROLE, `test_access_policy`, `test_openapi` |
| CA2 recusa 422 | `http-contract.md` §3–§4; `transaction-contract.md` §2 | T-FIRST, T-NEXT, T-SELF, T-BAL, T-PHASE, T-REFUSE-NOOP |
| CA3 aceite atômico 201 | `transaction-contract.md` §2, §5 | T-OUTBID, T-CHAIN, T-ATOM |
| CA4 anti-sniping | `transaction-contract.md` §6 | T-SNIPE |
| CA5 hora | `transaction-contract.md` §2, §6.1; `concurrency-analysis.md` §2 | T-CLOCK, M-1, M-2, M-26 |
| CA6 ordem das travas | `concurrency-analysis.md` §1, §3 | T-ORDER, T-DEADLOCK |
| CA7 gate | `transaction-contract.md` §2 (regras), §3 | T-GATE (G1–G23, G9b, G10b, G11b), T-REUSE (ordem), `test_bids_gate`, T-REFUSE-NOOP, M-24, M-25 |
| CA8 sequência e cadeia | `transaction-contract.md` §4 | T-CHAIN, T-CONC-2, M-4 |
| CA9 concorrência | `concurrency-analysis.md` | T-CONC-2, T-CONC-N, T-DEADLOCK, T-DEPOSIT |
| CA10 falha no meio | `transaction-contract.md` §7 | T-ATOM |
| CA11 inicialização | `seed-and-lot-creation.md` | T-INIT, T-MIG, G9 |
| CA12 segredos | `config-secrets.md` | T-SECRETS |
| CA13 reuso | `current-state.md` §1 | T-REUSE |
| CA14 verify | §6 | `./verify.sh` com saída real |

## 5. Riscos e limitações

| Item | Tratamento |
| --- | --- |
| Âncora não cobre termos do lote (`ends_at`, inicial, incremento) nem saldos | Limitação AD-13, README |
| Rollback consistente de cadeia + âncora | Limitação AD-13 |
| Segredo comprometido / trocado | Fora da garantia; troca bloqueia todos os lotes (F-4, SR-09) |
| Falha de conexão depois de enviar o `COMMIT` | Resultado indeterminado para o cliente; sem idempotência (F-6) |
| `bidder_id` histórico não autenticado | Só o último, por igualdade com o líder vinculado; futuras stories não decidem dinheiro com ele sem vínculo |
| Leitura O(n) da cadeia; fila na trava; sem timeout | A2/A3 |
| `clock_timestamp()` pode recuar (ajuste do relógio do servidor) | Cadeia não exige tempo crescente (3.3); só a fase depende do `now` |
| `DETAIL` de CHECK no log do servidor | Herdado (2.2, P16) |
| Valor ilegível pelo driver (`infinity`) | 500 sem efeito, não 409 |
| Demo legado visível e com 409 até vencer | F-5, README |
| Deadlock fora do protocolo | 500, sem retry (D13) |
| `pytest` mais lento (concorrência, 5 rodadas) | Aceito; medir no build |

## 6. Checklist do build

1. Nenhuma questão a responder: Q-1, Q-2 e Q-3 resolvidas (`decisions.md` §4).
2. `0005` + ORM (`Lot`, `Bid`) + `conftest`/`lot_support` + T-MIG.
3. `config.py`, `create_app`, segredos no `conftest` + T-SECRETS.
4. `create_lot` com âncora, `POST /api/lots`, seed + T-INIT e ajustes de `test_seed`.
5. `bids.py`: `lock_lot`, `read_history`, `authenticate_previous_state` + `test_bids_gate`.
6. `place_bid` (ordem D1) + T-FIRST..T-PHASE, T-SNIPE, T-CLOCK, T-ORDER, T-CHAIN, T-ATOM, T-REFUSE-NOOP.
7. Rota, DTOs, `errors.py` + T-ROLE, `test_openapi`, `test_access_policy`, `test_errors`, `test_bid_rules`.
8. Concorrência: T-CONC-2, T-CONC-N, T-DEADLOCK (+ controle negativo), T-DEPOSIT.
9. `drop_checks` determinístico; T-GATE G1–G23, G9b, G10b, G11b; T-REUSE com a ordem semântica.
10. Mutações M-1..M-26, uma por vez, restauradas.
11. README, `uso_de_ia.md`, `deferred-work.md`, story.
12. `./verify.sh` exit 0, saída real colada na story. Parar e avisar; Git é meu.
