# Contrato HTTP — Story 3.4 (P6, P7)

## 1. Rota

```python
@api_route(app, "/api/lots/{lot_id}/bids", methods=["POST"],
           policy=AccessPolicy.BIDDER, status_code=201,
           response_model=PlaceBidResponse,
           responses=error_responses(401, 403, 404, 409, 422))
def place_bid_route(lot_id: uuid.UUID, body: PlaceBidRequest, response: Response,
                    user: User = Depends(require_bidder),
                    session: Session = Depends(get_session),
                    integrity: IntegrityConfig = Depends(get_integrity_config)
                    ) -> PlaceBidResponse | Response
```

Registro: `register_bid_routes(app)` em `app/bids.py`, chamado em `create_app`
**depois** de `register_wallet_routes` (o `bids` depende de `lots` e `wallet`). O
módulo não importa `app.main`. 403/415 de CSRF vêm do middleware; a ordem 401 × 422
segue o comportamento existente (2.4/3.1), coberta por teste.

## 2. Schemas

```python
class PlaceBidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_cents: Cents                    # StrictInt 1..MAX_CENTS

class AcceptedBidResponse(BaseModel):
    sequence: int
    bidder_alias: str
    amount_cents: int
    placed_at: datetime                    # instante UTC; ISO 8601 do serializer

class BidLotStateResponse(BaseModel):
    current_bid_cents: int
    ends_at: datetime                      # instante UTC; já com a extensão, se houve
    anti_sniping_applied: bool

class PlaceBidResponse(BaseModel):
    bid: AcceptedBidResponse
    lot: BidLotStateResponse
    wallet: WalletResponse                 # reuso de app.wallet
```

Exemplo 201 (`Cache-Control: no-store`, sem `Location`), ilustrativo:

```json
{"bid": {"sequence": 3, "bidder_alias": "Licitante-0123456789ABCDEF",
         "amount_cents": 12000, "placed_at": "2026-10-26T18:01:02.123456Z"},
 "lot": {"current_bid_cents": 12000, "ends_at": "2026-10-26T18:04:00Z",
         "anti_sniping_applied": true},
 "wallet": {"total_balance_cents": 50000, "committed_balance_cents": 12000,
            "available_balance_cents": 38000}}
```

**Datas no HTTP × canônico.** As datas da resposta são ISO 8601 em UTC, no formato
que o serializer de `datetime` do Pydantic produz: com fração zero pode sair
`18:04:00Z`; com fração, as casas correspondentes. Isso **não** é a representação do
`CanonicalBid`, que é sempre `YYYY-MM-DDTHH:MM:SS.ffffffZ` (seis casas) e nunca sai
pela API nesta story. O contrato HTTP é o **instante**, não a string;
`transaction-contract.md` §6.1.

**`bidder_alias` na resposta: incluído (D6).** É público (aparece no histórico e na
auditoria), pertence ao próprio usuário autenticado, e permite à 3.5 marcar "seu
lance" sem antecipar o endpoint de "meu pseudônimo". Não liga ninguém mais a uma
identidade.

**Nunca na resposta nem no OpenAPI desses schemas:** `bidder_id`, `user_id`,
`current_leader_id`, `email`, `previous_hash`, `current_hash`, `final_hash`,
`anchor_hmac`, `canonical_version`, segredos, `is_demo`, `auctioneer_id`.

## 3. Respostas

| Situação | Status | Corpo | Origem |
| --- | --- | --- | --- |
| Aceito | 201 | `PlaceBidResponse` | rota, após `commit` |
| Sem sessão | 401 `unauthorized` | envelope | política |
| `AUCTIONEER` | 403 `forbidden` | envelope | política (handler não roda; lote intocado) |
| Origem/JSON | 403 `csrf_*` / 415 | envelope | middleware |
| `lot_id` não UUID, corpo inválido (0, negativo, `float`, `bool`, string, `> MAX_CENTS`, campo extra, ausente, JSON malformado) | 422 `validation_error` com `details` | envelope | FastAPI |
| Lote inexistente | 404 `not_found` | envelope | rota, após rollback |
| Recusa de negócio | 422, `code` = `BidRefusal.value` | envelope, sem `details` | rota, após rollback |
| Integridade | 409 `lot_integrity_conflict` | envelope | rota, após rollback |
| Violação interna | 500 `internal_error` | envelope | handler genérico |

Todas as respostas de erro da rota com `headers=NO_STORE` (precedente).

## 4. Catálogo (`app/errors.py`)

Constantes novas: `LOT_INTEGRITY_CONFLICT = "lot_integrity_conflict"` e as cinco de
recusa (valores iguais aos de `BidRefusal`; `errors.py` continua sem importar módulo
do app; um teste prova a igualdade dos conjuntos).

| Código | Mensagem |
| --- | --- |
| `lot_not_started` | Este lote ainda não começou. |
| `lot_ended` | Este lote já foi encerrado. |
| `below_minimum` | Seu lance está abaixo do mínimo para este lote. |
| `already_winning` | Você já está ganhando este lote. |
| `insufficient_balance` | Saldo disponível insuficiente para este lance. |
| `lot_integrity_conflict` | Não foi possível verificar a integridade deste lote. O lance não foi registrado. |

A rota só traduz: `error_response(422, refusal.value, headers=NO_STORE)`. O 409 tem o
mesmo corpo, byte a byte, para todas as categorias de `IntegrityFailure`.
