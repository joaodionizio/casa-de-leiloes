# Back-end — Story 3.1

## 1. Base reutilizada

| De | O quê |
| --- | --- |
| `app/access.py` | `api_route`, `AccessPolicy.BIDDER`, `require_bidder`, `NO_STORE` (sem mudança) |
| `app/db.py` | `Base`, `get_session` (Session curta, sem commit, `expire_on_commit=False`) |
| `app/errors.py` | `error_response`, `error_responses`, `MESSAGES`, handler global de 500 |
| `app/csrf.py` | `POST /api/*` exige `Origin`/`Referer` = `APP_ORIGIN` e JSON (sem mudança) |
| `app/users.py` | `User` (sem mudança) |

## 2. `app/money.py` (novo)

```python
"""Contrato monetário único (AD-3, Story 3.1 P3). Sem dependência de outro módulo do app."""
MAX_CENTS = 9_007_199_254_740_991   # Number.MAX_SAFE_INTEGER; limite técnico, não comercial
Cents = Annotated[StrictInt, Field(gt=0, le=MAX_CENTS)]   # valor positivo em centavos
```

`app/lots.py`: remover as duas definições e `from app.money import MAX_CENTS, Cents`.
Comportamento, mensagens de erro e OpenAPI de `/api/lots` idênticos (os testes da 2.4
provam). O comentário do `MAX_CENTS` muda de lugar para `money.py`.

## 3. `app/wallet.py` (novo)

```python
class Wallet(Base): ...                       # database-schema.md §5

class MissingWalletError(RuntimeError):       # usuário autenticado sem carteira (P2, D6)
    ...

class DepositRefusal(StrEnum):
    BALANCE_LIMIT_EXCEEDED = "balance_limit_exceeded"

# --- regra pura ---
def available_cents(total: int, committed: int) -> int          # total - committed
def apply_deposit(total: int, amount: int) -> int | DepositRefusal
    # total + amount > MAX_CENTS → BALANCE_LIMIT_EXCEEDED; senão total + amount

# --- serviço (nenhum faz commit) ---
def ensure_wallets(session: Session) -> int
    # INSERT INTO wallets (user_id) SELECT users.id FROM users
    #   WHERE NOT EXISTS (SELECT 1 FROM wallets WHERE wallets.user_id = users.id)
    #   ON CONFLICT (user_id) DO NOTHING RETURNING user_id   → len(rows)
    # insert(Wallet).from_select(...).on_conflict_do_nothing(...).returning(...)
def read_wallet(session: Session, user_id: uuid.UUID) -> Wallet
    # SELECT simples, sem trava; None → MissingWalletError
def lock_wallet(session: Session, user_id: uuid.UUID) -> Wallet
    # select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    #   .execution_options(populate_existing=True); None → MissingWalletError
def deposit(session: Session, user_id: uuid.UUID, amount_cents: int) -> Wallet | DepositRefusal
    # wallet = lock_wallet(...); result = apply_deposit(wallet.total_balance_cents, amount)
    # refusal → devolve; senão wallet.total_balance_cents = result; session.flush(); devolve

# --- contratos HTTP ---
class DepositRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_cents: Cents

class WalletResponse(BaseModel):
    total_balance_cents: int
    committed_balance_cents: int
    available_balance_cents: int

def wallet_response(wallet: Wallet) -> WalletResponse   # available = available_cents(...)

def register_wallet_routes(app: FastAPI) -> None
```

`ensure_wallets` é o único caminho de `INSERT` em `wallets` fora da migration. Nenhuma
função cria carteira para um usuário específico em resposta a uma requisição.

## 4. Rotas

| Rota | Política | Entrada | Sucesso | Erros |
| --- | --- | --- | --- | --- |
| `GET /api/wallet` | `BIDDER` | nenhuma | 200 `WalletResponse`, `no-store` | 401, 403 (`no-store`); 500 genérico (carteira ausente) |
| `POST /api/wallet/deposit` | `BIDDER` | `DepositRequest` (JSON) | 200 `WalletResponse`, `no-store` | 403 `csrf_*`, 415 (2.1); 401, 403; 422 `validation_error`; 422 `balance_limit_exceeded` (`no-store`); 500 genérico (carteira ausente) |

Handlers `def` (threadpool), `user: User = Depends(require_bidder)`,
`session: Session = Depends(get_session)` (a mesma `Session` da política).

**`GET /api/wallet`:**

```text
1. require_bidder               → 401/403; lê o User (abre a transação implícita)
2. wallet = read_wallet(session, user.id)     só SELECT; ausente → MissingWalletError → 500
3. result = wallet_response(wallet)
4. session.rollback()           encerra a leitura antes de responder (padrão da 2.5)
5. Cache-Control: no-store; 200
```

**`POST /api/wallet/deposit` (P4, D7) — uma transação curta:**

```text
1. ApiWriteGuardMiddleware      → 403 csrf_* / 415, handler não roda
2. require_bidder               → 401/403 (política antes do corpo, 2.2 P8)
3. corpo → DepositRequest       → 422 validation_error (inclui amount_cents > MAX_CENTS)
4. user_id = user.id
5. outcome = deposit(session, user_id, body.amount_cents)
     5a. SELECT ... FOR UPDATE da carteira (trava; relê o saldo atual)
         ausente → MissingWalletError → 500, a Session fecha com rollback
     5b. apply_deposit(total travado, amount)
     5c. UPDATE wallets SET total_balance_cents = :novo WHERE user_id = :id (flush)
6. outcome é DepositRefusal → session.rollback() (libera a trava)
                             → 422 balance_limit_exceeded, NO_STORE
7. session.commit()             qualquer erro → 500, nada gravado
8. 200 wallet_response(wallet), no-store   (valores já confirmados; expire_on_commit=False)
```

Nenhuma chamada externa, nenhum lote travado, nenhuma segunda carteira travada. Ordem de
travas compatível com o AD-8: quem trava carteira só trava uma.

## 5. Erros

| Situação | Status | `code` | `details` |
| --- | --- | --- | --- |
| Sem sessão válida | 401 | `unauthorized` | — |
| `AUCTIONEER` | 403 | `forbidden` | — |
| `Origin` estrangeiro/ausente | 403 | `csrf_origin_mismatch` / `csrf_origin_missing` | — |
| Sem `Content-Type: application/json` | 415 | `unsupported_media_type` | — |
| JSON malformado | 422 | `validation_error` | `type: json_invalid` |
| `amount_cents` ausente / `null` | 422 | `validation_error` | `missing` / `int_type` |
| `amount_cents` não inteiro, string, booleano, `1e2` | 422 | `validation_error` | `int_type` |
| `amount_cents <= 0` / `> MAX_CENTS` | 422 | `validation_error` | `greater_than` / `less_than_equal` |
| Campo extra (`user_id`, `total_balance_cents`…) | 422 | `validation_error` | `extra_forbidden` |
| `total + amount_cents > MAX_CENTS` | 422 | `balance_limit_exceeded` | — (sem `details`) |
| Carteira ausente | 500 | `internal_error` | — |

O `type` real de cada caso é fixado pelo teste (o Pydantic pode emitir outro nome para
`null`, por exemplo). `app/errors.py`: `BALANCE_LIMIT_EXCEEDED = "balance_limit_exceeded"`
e `MESSAGES[BALANCE_LIMIT_EXCEEDED] = "O depósito ultrapassaria o limite de saldo da
carteira."`; `CODE_BY_STATUS` não muda. O 422 do handler global segue sem `no-store`
(precedente C4 da 2.3); o 422 `balance_limit_exceeded`, montado na rota, leva `no-store`.

## 6. Registro e OpenAPI

- `create_app()`: `register_wallet_routes(app)` logo depois de `register_lot_routes(app)`
  e antes de `register_infra_check_routes(app)`; dentro, `GET` antes do `POST` (D9).
- `GET /api/wallet`: `response_model=WalletResponse`, `responses=error_responses(401, 403)`.
- `POST /api/wallet/deposit`: `response_model=WalletResponse`, status 200,
  `responses=error_responses(401, 403, 422)`; corpo `DepositRequest`.
- `HTTPValidationError` continua ausente do schema.

## 7. Log

Só o traceback do 500 de carteira ausente (uvicorn), com a mensagem de
`MissingWalletError` = `"wallet missing for authenticated user"` (sem e-mail, sem
corpo). Nenhum log de depósito aceito ou recusado. Seed: `seed-plan.md`.
