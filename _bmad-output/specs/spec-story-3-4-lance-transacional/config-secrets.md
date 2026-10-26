# Configuração e segredos — Story 3.4 (P5)

Primitives da 3.3 intocados (`bytes` exatos não vazios). Este é o contrato
operacional. Nenhum valor real foi lido nesta sessão.

## 1. `app/config.py`

```python
MIN_INTEGRITY_SECRET_BYTES = 32

class AuditSettings(BaseSettings):          # usado pelo seed (P4)
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore",
                                      hide_input_in_errors=True)
    audit_hmac_secret: SecretStr           # AUDIT_HMAC_SECRET
    # validator: _at_least_32_utf8_bytes

class IntegritySettings(AuditSettings):     # usado por create_app
    pseudonym_secret: SecretStr            # PSEUDONYM_SECRET
    # validator do campo: _at_least_32_utf8_bytes
    # model_validator(mode="after"): os dois diferentes

@dataclass(frozen=True)
class IntegrityConfig:                      # montado uma vez, em app.state
    audit_hmac_secret: bytes = field(repr=False)
    pseudonym_secret: bytes = field(repr=False)

def integrity_config(settings: IntegritySettings, jwt_secret: SecretStr) -> IntegrityConfig
get_audit_settings() / get_integrity_settings()   # lru_cache, como get_auth_settings
```

Regras:

- Tamanho: `len(valor.encode("utf-8")) >= 32`. `UnicodeEncodeError` (surrogate vindo
  do ambiente) vira `ValueError` com mensagem genérica, sem a posição nem o caractere.
- Distinção entre os dois: comparação dos `bytes` UTF-8; mensagem
  `"AUDIT_HMAC_SECRET and PSEUDONYM_SECRET must be different"`.
- Distinção do JWT: em `integrity_config`, contra `jwt_secret.get_secret_value()
  .encode("utf-8")`; `ValueError("AUDIT_HMAC_SECRET and PSEUDONYM_SECRET must differ
  from JWT_SECRET")`. Nunca o valor.
- `IntegrityConfig` guarda `bytes` (decisão da story: convertidos uma vez); `repr=False`
  impede que um log do objeto mostre o segredo.

## 2. Injeção

| Consumidor | Como recebe |
| --- | --- |
| `create_app(..., audit_hmac_secret: str \| None = None, pseudonym_secret: str \| None = None)` | Ambos `None` → `get_integrity_settings()`; senão `IntegritySettings(_env_file=None, ...)` com os dois argumentos. Depois `app.state.integrity_config = integrity_config(settings, auth_settings.jwt_secret)` antes de registrar rotas |
| Rotas (`POST /api/lots`, `POST /api/lots/{lot_id}/bids`) | Dependência `get_integrity_config(request) -> IntegrityConfig` em `app/lots.py` (padrão de `get_artic_client`) |
| Serviço de lance | Parâmetro `integrity: IntegrityConfig` |
| `create_lot` | `audit_hmac_secret: bytes` (só o necessário) |
| Seed (`main`) | `get_audit_settings()` **antes** de criar o engine; `run_seed(session, audit_hmac_secret=...)` |

O seed não lê `PSEUDONYM_SECRET`, `JWT_SECRET` nem `APP_ORIGIN` e não importa
`app.main`. Ele não consegue verificar a distinção entre segredos (não os tem): com
`start.sh` (migrations → seed → uvicorn), `create_app` falha logo depois se houver
igualdade. Consequência e orientação operacional em F-4 (`decisions.md`) e
`seed-and-lot-creation.md` §5 (SR-09).

## 3. Fail-fast

- Produção: `uvicorn app.main:app` importa `app.main` → `create_app()` → erro de
  validação sem valor → o processo não sobe. Seed sem `AUDIT_HMAC_SECRET` válido →
  `start.sh` (`set -eu`) para antes do servidor.
- Render: as duas variáveis precisam existir no painel **antes** do deploy da 3.4
  (README).

## 4. Testes e placeholders

- `tests/conftest.py`, junto do `JWT_SECRET` e antes de qualquer import de `app.main`:
  `PSEUDONYM_SECRET` e `AUDIT_HMAC_SECRET` = `secrets.token_urlsafe(48)` (64 bytes
  ASCII), sempre sobrescritos, nunca impressos; `assert` de que os três são distintos.
- Helper de teste `test_integrity_secrets() -> (audit: bytes, pseudonym: bytes)` lê
  esses valores do ambiente (`tests/bid_support.py`).
- Literais fictícios só em `test_config.py` (ex.: `"a" * 32`, `"é" * 16`), como
  `JWT_SECRET_OK`.
- T-SECRETS em `test-plan.md` §2.

## 5. Nunca

Em banco, Git, log, resposta, payload, `repr`, mensagem de erro, OpenAPI. O log do 409
leva só a categoria e o `lot_id`.
