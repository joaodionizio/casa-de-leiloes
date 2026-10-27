# Seed das carteiras (P2, P6, D10)

## 1. Mudança em `app/seed.py`

```python
from app.wallet import ensure_wallets

def run_seed(session: Session) -> tuple[int, bool]:
    acquire_seed_lock(session)          # 1º statement (inalterado)
    users = seed_users(session)         # inalterado
    ensure_wallets(session)             # NOVO: todo usuário sem carteira, só INSERT
    now = database_now(session)         # inalterado
    created = seed_demo_lot(session, now)
    return users, created               # retorno inalterado
```

- Mesma transação, sob a mesma trava consultiva: dois seeds simultâneos não disputam a
  inserção (e o `ON CONFLICT DO NOTHING` cobre o resto).
- Saldo zero pelos defaults (P6); nenhuma constante de saldo demo.
- Nunca `UPDATE`/`DELETE` em `wallets`, `users` ou `lots`.
- `seed_users` mantém assinatura e comportamento (testes da 2.2).
- `main()` mantém a linha `"seed: %d user(s) inserted; demo lot %s"`, que os testes
  procuram por substring, emitida depois do commit.
- **Sem log de carteiras (desvio registrado na implementação).** A versão inicial desta
  spec fazia `run_seed` logar `"seed: %d wallet(s) inserted"`. Na revisão final do
  build decidi tirar essa linha: ela sairia antes do commit, afirmando um sucesso ainda
  não confirmado, e levá-la para depois do commit exigiria mudar o retorno de
  `run_seed`. A contagem continua sendo o retorno de `ensure_wallets`, e os testes do
  subprocesso afirmam a ausência do log de carteira.
- `app.seed` continua sem importar `app.main` e sem chamar o catálogo nem cliente HTTP
  (a checagem por AST da 2.4 continua valendo); `app.wallet` não importa `app.main`,
  `app.lots`, `app.catalog`, `app.artic` nem `httpx`.

## 2. Comportamento observável

| Banco antes do seed | Carteiras inseridas | Log (depois do commit) |
| --- | --- | --- |
| vazio (depois de `upgrade head`) | 3 | `3 user(s) inserted` |
| usuários e carteiras já existentes | 0 | `0 user(s) inserted` |
| usuários existentes de antes da `0004` (backfill já feito) | 0 | — |
| um usuário a mais sem carteira (SQL) | 1 | — |
| carteira com saldo alterado | 0; saldo intacto | — |

Nenhuma linha menciona carteiras (ver o desvio acima).

## 3. Ordem na inicialização

`start.sh` não muda: `alembic upgrade head` (inclui o backfill da `0004`) →
`python -m app.seed` (garante as ausentes) → `uvicorn`.
