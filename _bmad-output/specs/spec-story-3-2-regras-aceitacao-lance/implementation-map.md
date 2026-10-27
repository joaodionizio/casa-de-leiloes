# Mapa de implementação — Story 3.2

> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

## 1. Arquivos a criar

| Arquivo | Conteúdo |
| --- | --- |
| `backend/app/lot_time.py` | `LotPhase`, `require_aware`, `check_lot_window`, `lot_phase` (`domain-contract.md` §2) |
| `backend/app/bid_rules.py` | constantes, `BidRefusal`, tipos, auxiliares privados, `minimum_bid_cents`, `evaluate_pre_wallet`, `evaluate_post_wallet`, `evaluate_bid` (§3 a §8) |
| `backend/tests/test_lot_time.py` | `test-plan.md` §2 |
| `backend/tests/test_bid_rules.py` | §3 a §8, `test_injected_now_drives_the_result` |
| `backend/tests/test_domain_purity.py` | §9 |

Docstring de módulo de `bid_rules.py`: regra pura da aceitação do lance (Story 3.2,
AD-5, AD-7, AD-26, P1–P13, C1); a precedência como contrato; o fluxo pré/pós-carteira
da 3.4 em duas linhas; "não importa ORM, FastAPI, Pydantic, `Session` nem lê relógio".

## 2. Arquivos a modificar

| Arquivo | Mudança |
| --- | --- |
| `backend/app/lots.py` | remover `LotPhase` e `lot_phase`; `from app.lot_time import LotPhase, lot_phase`; nada mais |
| `_bmad-output/implementation-artifacts/3-2-regras-de-aceitação-do-lance-com-hora-injetada.md` | tarefas T3–T7, registro de implementação, saída real do `verify`, resultado das mutações M1–M11, desvios da spec (se houver) |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | 3.2 → `in-progress` ao começar, `review` ao terminar |
| `docs/uso_de_ia.md` | seção "Story 3.2" no formato da 3.1 (o que decidi, o que a IA fez, onde errou ou divergiu, limitações) |

**Intocados:** `app/money.py`, `app/wallet.py`, `app/errors.py`, `app/main.py`,
`app/seed.py`, `app/access.py`, `app/users.py`, `app/db.py`, `app/catalog.py`,
`app/artic.py`, migrations, `tests/test_lot_phase.py`, `tests/test_lot_rules.py`,
`tests/test_wallet_rules.py`, `tests/test_errors.py`, `tests/test_openapi.py`,
`tests/test_access_policy.py`, `tests/integration/*`, `tests/conftest.py`, `frontend/`,
`README.md`, `docs/ARQUITETURA.md`, `CLAUDE.md`, `deferred-work.md`, `verify.sh`,
`pyproject.toml`, `uv.lock`. Nenhuma dependência nova.

## 3. Sequência

1. **`lot_time.py` + `lots.py`.** Mover sem mudar nada além da defesa (P8) e da
   normalização UTC (D7). Rodar `uv run pytest tests/test_lot_phase.py
   tests/test_openapi.py tests/integration/test_public_lots.py` — verde sem editar
   teste.
2. **`test_lot_time.py`.** Verde.
3. **`bid_rules.py`, tipos e invariantes** (§3–§4) + testes de `test-plan.md` §3.
4. **Mínimo, pré-carteira, pós-carteira, `evaluate_bid`** (§5–§8) + §4–§8 do plano.
5. **`test_domain_purity.py`.**
6. **Mutações M1–M11** (`test-plan.md` §10), cada uma revertida e conferida com `diff`.
7. **`uv run ruff check .`, `uv run ruff format --check .`, `./verify.sh`** com a saída
   real; documentação (§2); `sprint-status.yaml` → `review`. **Parar.** Não iniciar 3.3.

## 4. Riscos

| Risco | Mitigação |
| --- | --- |
| Precedência acidental | P3 + D11: passos numerados, 36 linhas à mão, 8 nomeados, M1–M3 |
| Etapa pré-carteira divergir da completa | D2: `evaluate_bid` é a composição literal; `test_composition_equals_evaluate_bid` |
| Regras repetidas no caminho da 3.4 | D2/D12: spies provam zero reexecução na pós-carteira |
| Chegar ao saldo sem a pré-carteira | D3: `EligibleBid` só emitido pela pré-carteira; construção e `replace` → `ValueError` |
| Clamp/overflow do mínimo | P6: `int \| None`; §6; M7 |
| Corrupção escondida como recusa | P7/D8: `ValueError` antes de qualquer regra; M11 |
| Comparação de parede com o mesmo `tzinfo` | D7: `astimezone(UTC)`; teste `FoldOffset`; M10 |
| Regressão da vitrine com a defesa nova de `lot_phase` | lotes vêm do banco com fuso e CHECK `ends_after_starts`; suítes da 2.5 intocadas e verdes |
| Mudança acidental do OpenAPI | `LotPhase` movida com nome, valores e docstring idênticos; `test_openapi.py` intocado |
| Relógio oculto | D13: AST com detector provado + teste 2000 × 2100 |
| `ends_at + 2 min` ou `astimezone(UTC)` perto de `datetime.max`/`min` | só alcançável com `now` no ano 9999 ou 1; o `now` real vem do banco; registrado, sem código especial |
| `pydantic` carregado de forma transitiva via `app.money` | aceito (P9 trata de imports diretos; `bid_rules` usa só `MAX_CENTS`) |

## 5. Critérios objetivos de conclusão

A 3.2 está pronta para review quando **todos** valem:

1. Os 10 CAPs da SPEC têm os testes de `test-plan.md` que os decidem, todos verdes.
2. `./verify.sh` termina com exit 0, com a saída real registrada na story (contagens só
   dessa execução). `VERIFY_E2E=1` não é exigido: nada de front muda.
3. M1–M11 executadas; cada uma derrubou ao menos o teste previsto; todas revertidas,
   `diff` vazio, suíte verde de novo; resultado registrado na story.
4. `app/lots.py` não define `LotPhase` nem `lot_phase`; `app/lot_time.py` é a única
   definição.
5. `app/bid_rules.py` e `app/lot_time.py` passam em `test_domain_purity.py`.
6. Nenhum arquivo da lista "Intocados" mudou.
7. Story, `sprint-status.yaml` (`review`) e `docs/uso_de_ia.md` atualizados.
8. Nenhum item fora do escopo (§6) apareceu.

## 6. Fora do escopo (implementação proibida nesta story)

Migration; tabela/ORM `bids`; lance atual/líder persistidos; `app/bids.py`; adaptador
ORM → domínio; endpoint, política HTTP, `MESSAGES`, mensagens da API; `SELECT ... FOR
UPDATE`; travas; `clock_timestamp()` real; `Session`; consulta a `Wallet` ou import de
`app.wallet`; alteração de saldo, comprometimento, liberação do líder anterior;
persistência de `ends_at`; pseudônimo, canônico, SHA-256, HMAC, sequência, histórico;
WebSocket; front de lance; fechamento, liquidação, catch-up; cancelamento (sexto motivo,
`cancelled`); verificação de papel; teto de extensões; mudanças em `ARQUITETURA.md`,
`CLAUDE.md`, `README.md`; dívidas administrativas.
