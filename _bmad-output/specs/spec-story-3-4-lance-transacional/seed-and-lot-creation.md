# Criação de lote e seed — Story 3.4 (P3, P4)

## 1. `create_lot` (`app/lots.py`)

Assinatura nova: `create_lot(session, *, snapshot, terms, auctioneer_id, now,
audit_hmac_secret: bytes, is_demo=False) -> Lot | ScheduleViolation`.

1. `resolve_schedule` (inalterado); violação → devolve sem tocar no banco.
2. `lot_id = uuid.uuid4()`.
3. `anchor = compute_anchor_hmac(AnchorState(v=1, lot_id=lot_id, bid_count=0,
   final_hash=GENESIS_HASH), audit_hmac_secret=audit_hmac_secret)` — **antes** de criar
   o objeto. Segredo inválido → `ValueError` → nada foi adicionado → 500 na rota,
   exceção no seed. Nunca lote parcialmente inicializado.
4. `Lot(id=lot_id, ..., current_bid_cents=None, current_leader_id=None, bid_count=0,
   final_hash=GENESIS_HASH, anchor_hmac=anchor)`; `add`; `flush` (como hoje).

Mesma transação do `INSERT`, quem chama faz o commit (inalterado). O `id` vem do
servidor: nenhum chamador consegue fazer `create_lot` assinar um lote existente.
Só `create_lot` produz âncora vazia; nenhum outro código assina estado vazio.

`POST /api/lots`: ganha `integrity: IntegrityConfig = Depends(get_integrity_config)` e
passa `audit_hmac_secret=integrity.audit_hmac_secret`. Resposta (`LotResponse`)
inalterada.

## 2. Seed (`app/seed.py`)

```python
def seed_demo_lot(session, now, *, audit_hmac_secret: bytes) -> bool
def run_seed(session, *, audit_hmac_secret: bytes) -> tuple[int, bool]
def main():  # settings primeiro: get_settings() e get_audit_settings(); depois engine
```

Predicado de "demo realmente aberto" (Q4 + P3):

```python
select(exists().where(Lot.is_demo.is_(True), Lot.ends_at > now,
                      Lot.anchor_hmac.is_not(None)))
```

O predicado **escolhe**, não autentica: o lance no demo passa pelo gate como qualquer
outro. O seed nunca faz `UPDATE`/`DELETE`, nunca assina lote encontrado.

Docstring do módulo: "precisa de `DATABASE_URL` e `AUDIT_HMAC_SECRET`".

## 3. Idempotência no seed real

| Situação | Resultado |
| --- | --- |
| Banco vazio | Usuários, carteiras e um demo assinado; `(3, True)` |
| 1º boot da 3.4 em produção, demo legado aberto (`anchor_hmac NULL`) | Legado não conta; cria um demo assinado; o legado fica intocado, visível até vencer e responde 409 (F-5) |
| Boots seguintes | O demo assinado conta; `(0, False)`; nada criado |
| Demo assinado vencido | Cria outro (AD-24, inalterado) |
| Dois seeds simultâneos | `pg_advisory_xact_lock` serializa; o segundo lê depois do commit do primeiro (`READ COMMITTED`) e não cria |
| Demo assinado com segredo antigo (troca de `AUDIT_HMAC_SECRET`) | Conta como aberto (`IS NOT NULL`), mas o lance dá 409 até ele vencer (F-4; orientação no §5) |
| `anchor_hmac` lixo não nulo (escrita direta no banco) | Conta como aberto; lance dá 409. Exige acesso de escrita ao banco; só disponibilidade |

Nenhum caminho cria demo a cada boot: criação só quando não existe demo aberto e com
âncora não nula, e todo demo criado nasce com âncora não nula.

## 4. Ambiente do seed

| Variável | Exigida? | Prova |
| --- | --- | --- |
| `DATABASE_URL` | sim | inalterado |
| `AUDIT_HMAC_SECRET` | sim, ≥ 32 bytes UTF-8 | subprocesso com valor vazio/curto falha antes de abrir o banco, sem ecoar |
| `PSEUDONYM_SECRET` | não | subprocesso com `PSEUDONYM_SECRET=""` (inválido se lido; sobrescreve um `.env` local) termina com sucesso |
| `JWT_SECRET`, `APP_ORIGIN` | não | `app.main` não importado (teste existente) |

## 5. Conflito de segredos no boot (SR-09, para o README)

Como o seed assina com `AUDIT_HMAC_SECRET` antes de `create_app` comparar os três
segredos, um conflito (dois iguais) só aparece quando o servidor falha ao subir, e o
demo pode já estar assinado. Orientação operacional:

- **Não trocar `AUDIT_HMAC_SECRET` depois que âncoras existem:** a troca invalida todas
  as âncoras já assinadas (todo lote, inclusive o demo, passa a responder 409).
- Corrigir o conflito trocando `PSEUDONYM_SECRET` ou `JWT_SECRET`. Trocar o
  `PSEUDONYM_SECRET` depois de existirem lances também bloqueia esses lotes (o vínculo
  do líder recalcula o alias); antes do primeiro lance, não afeta nada. Trocar o
  `JWT_SECRET` só derruba as sessões abertas.
- O seed não repara, não reassina, e `anchor_hmac IS NOT NULL` **não** prova que a
  âncora é válida: só escolhe o demo. O uso real continua fail-closed (409 no gate).
- Rotação de segredos não é suportada nesta entrega.
