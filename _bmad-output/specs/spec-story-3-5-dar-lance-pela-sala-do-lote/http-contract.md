# Contratos HTTP e leituras

Decidi os nomes finais abaixo dentro de D1–D3. Descartei respostas aninhadas adicionais, IDs de usuário e campos de posição duplicados. O detalhe da 2.5 continua exatamente igual.

## Tipos e nomes

Todos os campos são obrigatórios; `nullable` permite `null`, não omissão. JSON em inglês. `MAX_CENTS = 9_007_199_254_740_991`. Valores monetários positivos são inteiros estritos em `1..MAX_CENTS`. Contadores são inteiros não negativos (sequência começa em 1), sem aplicar teto monetário ao contador. Timestamps são datetimes com fuso, normalizados para UTC e serializados pelo padrão Pydantic atual com `Z`; não imponho formato canônico de hash ao JSON HTTP. O front aceita fração de 0 a 6 casas.

Reutilizo `AcceptedBidResponse` sem mudar suas quatro propriedades: `sequence: int`, `bidder_alias: str`, `amount_cents: int`, `placed_at: datetime`. O alias persistido tem formato `^Licitante-[0-9A-F]{16}$`.

## GET /api/lots/{lot_id}/bids

`api_route`, `methods=[GET]`, `AccessPolicy.PUBLIC`, handler `def`, `response_model=PublicBidRoomResponse`, `responses=error_responses(404,422)`. Não consulta sessão nem depende de segredos. Corpo e query não são necessários; não há parâmetros de paginação. `lot_id` é UUID.

| Campo exato | Tipo | Semântica |
| --- | --- | --- |
| `as_of` | datetime UTC | Uma avaliação de `clock_timestamp()` no statement |
| `phase` | `LotPhase` | `scheduled`, `live`, `ended`, via `lot_phase(starts_at, ends_at, as_of)` |
| `ends_at` | datetime UTC | Fim persistido, incluindo extensões já confirmadas |
| `current_bid_cents` | int nullable | Lance atual persistido; `null` sem lances |
| `minimum_next_bid_cents` | int nullable | Resultado de `minimum_bid_cents`; `null` só se não representável |
| `bid_count` | int >= 0 | Contagem total persistida no lote, nunca tamanho da janela |
| `bids` | array de `AcceptedBidResponse`, tamanho 0..50 | `sequence DESC` explícito |

Exemplo de resposta 200:

```json
{
  "as_of": "2026-10-26T14:30:00.123456Z",
  "phase": "live",
  "ends_at": "2026-10-26T15:00:00Z",
  "current_bid_cents": 125000,
  "minimum_next_bid_cents": 130000,
  "bid_count": 1,
  "bids": [
    {"sequence": 1, "bidder_alias": "Licitante-A83F19C2D4E5B601", "amount_cents": 125000, "placed_at": "2026-10-26T14:29:41.500000Z"}
  ]
}
```

Em runtime há `min(50,bid_count)` itens para dados íntegros. Não existe `leader_alias`: o líder é `bids[0].bidder_alias` quando há lance atual.

| Situação | Resultado |
| --- | --- |
| UUID válido inexistente | 404 `not_found`, envelope exato `{status:404,code:"not_found",message:"Recurso não encontrado."}` |
| UUID malformado | 422 `validation_error`, sanitização global atual; `loc=["path","lot_id"]`, `type="uuid_parsing"`; sem leitura de negócio |
| Zero lances | `current_bid_cents=null`, `bid_count=0`, `bids=[]`, mínimo = lance inicial |
| 51 lances | Total 51; sequências 51..2, 50 itens; sequence 1 não é retornada |
| Atual + incremento = MAX_CENTS | Mínimo = MAX_CENTS, sem clamp |
| Atual + incremento > MAX_CENTS | Mínimo `null`, inclusive atual = MAX_CENTS |
| Agendado | `as_of < starts_at`; mesmos dados/mínimo, sem habilitação implícita |
| Ao vivo | `starts_at <= as_of < ends_at`; mesmos campos |
| Encerrado | `as_of >= ends_at`; histórico e mínimo continuam consultáveis; mínimo continua resultado da função, não vira null pela fase |
| Legado sem âncora | Lê normalmente; nenhuma autenticação/reassinatura; eventual POST continua 409 pela 3.4 |

Não escondo divergência por banco adulterado: as invariantes de líder/quantidade valem sobre dados íntegros produzidos pelo motor. A leitura não prova integridade, não preenche lacunas, não recalcula count ou atual pelo histórico e não devolve 409 de auditoria. Erro de programação/schema segue 500 genérico; não invento reparo.

## Uma consulta pública, coerente e limitada

Decidi uma instrução SQLAlchemy por GET público, sem entidades ORM inteiras:

1. CTE local `clock AS MATERIALIZED` seleciona `clock_timestamp()` como `as_of` uma vez, seguindo o padrão existente de `lots._clock_cte`, sem editar `lots.py`.
2. `FROM clock LEFT OUTER JOIN lots ON lots.id=:lot_id` preserva uma linha mesmo sem lote. Projeto só `id`, `starts_at`, `ends_at`, `starting_bid_cents`, `min_increment_cents`, `current_bid_cents`, `current_leader_id`, `bid_count` e `as_of`.
3. `LEFT OUTER JOIN LATERAL` da projeção `sequence,bidder_alias,amount_cents,placed_at` de bids, com filtro `lot_id`, `ORDER BY sequence DESC LIMIT 50`. Ordenação externa também `sequence DESC` (null por ausência é descartado, não vira item).
4. A PK `(lot_id,sequence)` atende filtro/ordem/limite; não há count de toda a tabela, N+1, índice ou migration nova. Em lote vazio a linha preservada gera lista vazia.
5. Leio colunas, monto os DTOs e calculo `lot_phase` com o mesmo `as_of`. Para o mínimo construo `LotBidState`, incluindo `CurrentBid(amount_cents,current_leader_id)` se necessário, e chamo `minimum_bid_cents` da 3.2. `current_leader_id` é apenas entrada interna exigida pelo tipo real, nunca entra em resposta/log público. Não consulto `Bid.bidder_id` nem hashes.
6. Materializo resultado e encerro a transação de leitura com rollback antes da resposta, padrão da 2.5. Não chamo `database_now` separado, gate ou `place_bid`.

Sobre dados íntegros: `bids[0].sequence == bid_count` e `bids[0].amount_cents == current_bid_cents`; a única instrução vê lote e lances no mesmo snapshot inclusive com commit concorrente. `as_of` classifica esse snapshot, não é promessa de observar commits ocorridos depois do início da instrução. Descartei consultas separadas em READ COMMITTED e isolamento novo para esta leitura.

## GET /api/lots/{lot_id}/bids/mine

`api_route`, `methods=[GET]`, `AccessPolicy.BIDDER`, `Depends(require_bidder)`, `response_model=MyLotBidsResponse`, `responses=error_responses(401,403,404,422)`, handler `def`, sessão curta. Sem `is_leading`, `as_of`, `lot_id`, `user_id`, `bidder_id`, lista de bids ou saldo na resposta.

| Campo exato | Tipo | Semântica |
| --- | --- | --- |
| `bidder_alias` | string | `generate_bidder_alias(lot_id=lot_id,user_id=user.id,pseudonym_secret=integrity.pseudonym_secret)` |
| `my_bid_count` | int >= 0 | Todos os lances daquele alias naquele lote |
| `last_bid_cents` | int nullable | Valor do maior `sequence` do próprio alias, nunca MAX de valores por conveniência |

```json
{"bidder_alias":"Licitante-A83F19C2D4E5B601","my_bid_count":2,"last_bid_cents":120000}
```

Sem lance: mesmo alias determinístico, zero e `null`. Lote inexistente: 404; sem sessão válida/expirada: 401 `unauthorized`; AUCTIONEER: 403 `forbidden`. UUID malformado segue 422 global; a autenticação existente pode fazer seu SELECT antes da validação de path, sem query de negócio. Não prometo banco intocado para 422 autenticado.

Decidi um statement de negócio após autenticação: `SELECT` ancorado em `lots` filtrado por PK, projetando existência do lote e duas subconsultas escalares correlacionadas de bids, ambas filtradas por `(lot_id,bidder_alias)`: `COUNT(*)` completo e `amount_cents ORDER BY sequence DESC LIMIT 1`. Lote ausente produz zero linhas (404); count vazio produz zero e último valor null. A PK limita a busca ao lote e atende a leitura decrescente do último valor; o count examina os lances daquele alias no lote. Não materializo array de todos os valores, não leio os 50 públicos para contar e não faço nova ida ao banco. Na escala do desafio não crio índice. Não seleciono identidade privada histórica nem hashes. Aliases históricos nunca são recalculados; só calculo o alias da sessão. O alias integra o DTO mesmo sem lance.

Autenticação padrão faz o SELECT de User; portanto a contagem esperada é um statement de negócio + SELECT da autenticação, não “um statement total” para `/mine`. Capturo `user.id` antes de encerrar a leitura; monto DTO e rollback. Em qualquer fase os campos próprios mantêm a mesma semântica. Posição é da UI; não cruzo GETs com isolamento compartilhado.

## Headers, erros e privacidade

200 e 404 das duas rotas recebem `Cache-Control: no-store`; 401/403 herdam `NO_STORE` das dependências. **Precedente real preservado:** o 422 de validação do handler global e o 500 genérico não acrescentam `no-store` hoje (`errors.py`, Story 3.1). Descartei alterar proteção global fora de escopo; não afirmo que esses headers já existam. As respostas nunca expõem segredo. Não há novo código no catálogo de erros.

Os schemas novos e itens têm exatamente as propriedades acima; construção explícita + `response_model` evitam serializar ORM. Proíbo em qualquer nível: `bidder_id`, `user_id`, `current_leader_id`, `auctioneer_id`, nome/e-mail, `previous_hash`, `current_hash`, `final_hash`, `anchor_hmac`, segredo e versão canônica. Testo chaves e valores reais sintéticos; não basta procurar chaves. `lot_id` só existe na URL, não como dado pessoal retornado.

## POST existente, inalterado

`POST /api/lots/{lot_id}/bids`, BIDDER, JSON `{amount_cents}` apenas. 201 contém exatamente `bid:{sequence,bidder_alias,amount_cents,placed_at}`, `lot:{current_bid_cents,ends_at,anti_sniping_applied}`, `wallet:{total_balance_cents,committed_balance_cents,available_balance_cents}`. 422 preserva cinco códigos de negócio ou `validation_error`; 409 `lot_integrity_conflict`; 401/403/404 e proteção CSRF/JSON existentes. Não acrescento mínimo, contagem ou histórico ao 201.
