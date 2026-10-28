# Contrato final de dados e API privada

Decidi estender somente GET /api/lots/mine (QH-02), sem rota de detalhe.
O formato atual já é envelope as_of/items; preservo campos e acrescento total.

## Envelope final

`GET /api/lots/mine` → 200, `Cache-Control: no-store`,
`{as_of, items, total_received_cents}`. Preservo todos os campos atuais de cada item,
o 201 da criação e a resposta do cancelamento; adiciono apenas os eixos abaixo.
Sem paginação atual; não invento parâmetros page/limit/owner ou ordenação dinâmica.

| Campo novo por item | Tipo | Regra |
| --- | --- | --- |
| settlement_status | pending ou settled | pending = ausência de registro, não sinônimo de lote expirado ou fila em execução |
| settlement | null ou PrivateLotSettlementSummary | null só na ausência de settlement válido; erro nunca é convertido em null |

| Campo do resumo | Sold | Unsold |
| --- | --- | --- |
| outcome | sold | unsold |
| winner_alias | string persistida `Licitante-` + 16 hex maiúsculos | null |
| final_amount_cents | inteiro 1..9007199254740991 | null, nunca zero/preço inicial |
| bid_count | inteiro positivo congelado | inteiro 0 |
| settled_at | ISO 8601 UTC Z, até 6 casas, persistido | mesma regra, obrigatório |

As cinco chaves do resumo são obrigatórias, com nulls explícitos só nos campos
sem significado em unsold. Não uso `outcome=pending/cancelled`; outcome só pertence
a settlement. Fora do resumo, o bid_count atual permanece para lotes sem settlement;
com settlement, contagem exibida e total são derivados dos valores congelados e a
coerência com Lot é validada. Não confundir settlement_status com SettlementStatus
do comando (settled_sold/already_settled/not_due).

Whitelist final exclui final_hash, receipt/link/has_receipt,
winner_user_id, winning_bid_sequence, ids de settlement/receipt, anchor_hmac,
wallet/saldos e dados users. `id` do lote já existente permanece. Não serializo ORM
ou dataclass interna. Modelo privado tem validação explícita de outcome, tipos,
intervalos, datas com fuso e nulabilidades. Frontend valida JSON antes de renderizar;
valor desconhecido/malformado não vira pending/unsold/vazio. Validação privada pode
rejeitar chaves extras no novo resumo; dados privados inesperados jamais são copiados
para estado/DOM. Não afirmo que validar no cliente substitui a whitelist da API.

Exemplos de fragmentos (não substituem os campos herdados):

```json
{"settlement_status":"pending", "settlement":null}
```
```json
{"settlement_status":"settled", "settlement":{"outcome":"sold", "winner_alias":"Licitante-0123456789ABCDEF", "final_amount_cents":13000, "bid_count":3, "settled_at":"2026-10-28T15:00:01.123456Z"}}
```
```json
{"settlement_status":"settled", "settlement":{"outcome":"unsold", "winner_alias":null, "final_amount_cents":null, "bid_count":0, "settled_at":"2026-10-28T15:00:01.123456Z"}}
```

## Soma simples decidida — QH-13

Uso `total_received_cents` no envelope: inteiro 0..MAX_CENTS, soma no backend
após validar todos os registros, apenas `final_amount_cents` dos sold próprios.
Zero para lista vazia ou sem sold. Não somo lance atual/inicial, pending, unsold,
cancelados ou lotes de terceiros. Não consulto carteira nem infiro saldo disponível;
é total histórico das vendas presentes na listagem completa do proprietário.

Uso os mesmos resultados do snapshot da lista, sem request de agregação extra,
float, formatação BRL no servidor ou número calculado pelo navegador. Soma Python
inteira e verificação do intervalo seguro antes de serializar. Nunca saturar/truncar:
se não couber no contrato numérico seguro, a leitura falha genericamente. Essa defesa
não introduz teto comercial nem movimenta dinheiro. Inconsistência em qualquer lote
impede total parcial ser apresentado como completo (QH-11).
Se futuramente houver paginação/filtros, a semântica global terá de ser explicitada;
A QH-08 decidiu nenhum filtro novo.

## Statement e snapshot

Uso um statement para dados de negócio: CTE MATERIALIZED com um
clock_timestamp; LEFT JOIN de Lot restrito a `auctioneer_id=user.id`, seguido de
LotSettlement e Receipt por lot_id. Incluo cancelados. O CTE garante as_of mesmo
sem lotes; propriedade fica no ON, preservando lista vazia. FKs/UNIQUE permitem
uma linha por lote. Projetar somente os campos necessários aos checks/DTO; IDs de
vencedor podem existir internamente para comparação, nunca na resposta.

Lotes/settlements/receipts e instante pertencem ao mesmo snapshot PostgreSQL;
commit concorrente aparece inteiro ou só na leitura seguinte. Não juntar leitura
da lista a N `read_settlement`s ou a queries independentes com snapshots diferentes.
Query da autenticação é custo fixo separado, não N+1 de negócio. Manter autoflush
inibido no caminho de leitura e transação curta encerrada por rollback/cleanup,
sem commit, DML, FOR UPDATE, lock de carteira ou rede externa.

Reuso `_structural_conflict` da 4.3 por composição/extração pura, como a 4.4 já faz,
sem chamar prepare_settlement, settle_lot ou gate de histórico. O helper atual
não basta sozinho: acrescento checks de Lot e validação do DTO.

## Máquina de projeção e conflitos

1. Verifico presença/coerência do par e dos vínculos antes de apresentar resultado.
2. Cancelled sem settlement/receipt → cancelado, mesmo phase ended e count zero.
3. Sem settlement/receipt e não cancelado → scheduled/live/pending temporal conforme phase calculada pelo servidor; `ends_at <= as_of` é apurando.
4. Settlement íntegro sold/unsold → resultado persistido, sem estimar maior lance.
5. Qualquer inconsistência → falha segura, sem reparar, recarregar liquidando ou esconder conflito como cancelamento/unsold.

Detectar pelo menos: cancelled+settlement/receipt; receipt sem settlement; sold sem
receipt; unsold com receipt; cópias divergentes; lot_id/settlement_id incompatíveis;
outcome/alias/amount/count/data inválidos; count/hash/amount/winner divergentes do
Lot; settled_at anterior ao ends_at vigente, ou settlement com fase temporal ainda
não encerrada; resultado/cancelamento contraditórios. Comparações internas de
winner_user_id não autorizam sua exposição. Não revalidar reserva já consumida.

Leitura não reautentica toda cadeia/HMAC nem promete detectar adulteração arbitrária
coordenada. Preservo limites da 4.3/4.4: resultado estruturalmente coerente não é
selo de auditoria. Hash pode ser usado nos checks internos sem entrar no painel.

## Erros finais

Preservo envelope {status, code, message} e no-store em sucesso/erro privado.
401 unauthorized e403 forbidden pela policy existente. IntegrityConflict estrutural
é mapeado para409 lot_integrity_conflict já existente, sem dados contraditórios ou
parciais; erros operacionais continuam500 internal_error. Zero repair ou liquidação.
Logs seguros: categoria e lot_id, sem SQL/identidade/HMAC/DTO cru.
