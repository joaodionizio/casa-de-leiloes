# Contrato HTTP exato e precedência

Decidi seguir o POST sem corpo de logout e a infraestrutura real de políticas,
erros e CSRF. Descartei DELETE, PATCH de status e payload com identidade do dono.

## 1. POST /api/lots/{lot_id}/cancel

Registro `register_lot_cancellation_routes(app)` em `app/lot_cancellation.py`, com
`api_route`, `methods=["POST"]`, `policy=AccessPolicy.AUCTIONEER`, status 200,
`response_model=CancelLotResponse`, `responses=error_responses(401,403,404,409,422)`.
Handler síncrono, `lot_id: uuid.UUID`, `Response`, `Depends(require_auctioneer)`,
`Depends(get_session)` e `Depends(get_integrity_config)`. Não recebe body nem
identidade por query. O frontend envia corpo ausente e `Content-Type: application/json`.
A ausência de parâmetro de corpo segue logout: não crio um leitor/validador para
rejeitar conteúdo extra que o endpoint não consome. Não há schema de request no OpenAPI.

Cookie e origem seguem AD-11/29. O guard real aceita Origin válido, ou Referer
válido quando Origin não existe, e exige cabeçalho JSON mesmo sem corpo.

| Sucesso | Campo obrigatório | Tipo e representação |
| --- | --- | --- |
| 200 | `id` | UUID serializado em minúsculas com hífens, do lote solicitado |
| 200 | `cancelled_at` | datetime aware normalizado com `astimezone(UTC)`, ISO 8601 com `Z`, nunca null |

`CancelLotResponse` tem exatamente essas duas propriedades. Não inclui fase,
contagem, carteira, hashes ou flag de idempotência. Timestamp preserva microssegundos;
fração zero pode sair sem fração pelo serializer Pydantic atual, como a 3.4/3.5.
Não imponho os seis dígitos dos bytes canônicos ao HTTP. Exemplo:

```json
{"id":"00000000-0000-4000-8000-000000000001","cancelled_at":"2026-10-26T14:30:00.123456Z"}
```

200 e recusas do handler usam `Cache-Control: no-store`; 401/403 da policy já
herdam `NO_STORE`. 422 global de UUID, guard CSRF/415 e 500 genérico mantêm os
headers existentes; não afirmo no-store onde hoje não existe.

## 2. Erros e mensagens

Envelope padrão: exatamente `status`, `code`, `message`; sem `details` em recusas
de negócio. Apenas validação acrescenta lista sanitizada `{loc,type}`. Nunca
retorno exceção, motivo de gate, HMAC, hash ou nome de campo adulterado.

| HTTP | `code` | `message` |
| --- | --- | --- |
| 401 | `unauthorized` | Autenticação necessária. |
| 403 | `forbidden` | Acesso negado. |
| 404 | `not_found` | Recurso não encontrado. |
| 409 | `lot_integrity_conflict` | Não foi possível concluir a operação porque a integridade do lote não pôde ser confirmada. |
| 422 | `lot_has_bids` | Este lote não pode ser cancelado porque já recebeu lances. |
| 422 | `lot_ended` | Este lote já foi encerrado. |
| 422 | `validation_error` | Os dados enviados são inválidos. |

UUID malformado segue o FastAPI/Pydantic existente:
`details=[{"loc":["path","lot_id"],"type":"uuid_parsing"}]`. Não restrinjo versão
de UUID nem altero a aceitação atual de formas parseáveis. A rota não chama o
serviço para UUID inválido; a dependência de autenticação pode ter feito SELECT.

Origem ausente/divergente dá 403 `csrf_origin_missing`/`csrf_origin_mismatch`;
conteúdo sem cabeçalho JSON dá 415 `unsupported_media_type`, antes do roteamento.
Exceção inesperada segue 500 `internal_error` e rollback da sessão.

## 3. Precedência implementável

Para request que passou pelo guard, policy e validação de path:

1. Lote inexistente → 404.
2. Lote de outro AUCTIONEER → 403, sem rodar gate.
3. Falha no gate → 409.
4. Já cancelado íntegro → 200 original, sem UPDATE.
5. `authenticated.bid_count > 0` → 422 `lot_has_bids`.
6. `now >= ends_at` → 422 `lot_ended`.
7. Cancelar → 200.

BIDDER recebe 403 pela policy antes do serviço, mesmo para lote inexistente.
Não autenticado recebe 401. Guard CSRF/415 vem antes de ambos; portanto essa
precedência de negócio não promete 401 em uma requisição com origem inválida.
Com lances e fim ultrapassado prevalece `lot_has_bids`; com adulteração prevalece
409; outro dono prevalece sobre adulteração. Idempotência íntegra vale mesmo se
o fim temporal já passou. Essa ordem usa as dependências e transações existentes,
sem middleware novo nem alteração de política.

## 4. Delta do lance e D5

Acrescento `LOT_CANCELLED="lot_cancelled"` em `BidRefusal`, a constante correspondente
e `LOT_HAS_BIDS="lot_has_bids"` em `errors.py`. Catálogo fixa
`lot_cancelled` → “Este lote foi cancelado.”. No `place_bid`, retorno
`BidRefusal.LOT_CANCELLED` imediatamente após gate bem-sucedido e antes da
construção de estado/regras pré-carteira. A rota atual já converte BidRefusal em
422 e rollback. Cancelado adulterado ou legado responde 409; cancelado íntegro
responde 422 mesmo se agendado ou encerrado. Nenhum wallet lock ou efeito.

D5 muda a mensagem do catálogo HTTP compartilhado para a frase neutra acima,
preservando código/status. Atualizo testes backend que pinam o texto, sem afrouxar
asserções. A sala mantém seu texto local de integridade já aprovado: a instrução
específica permite nela somente o novo mapeamento `lot_cancelled`, sem alterar as
demais recusas. A mensagem HTTP não dirige o texto da UI.
