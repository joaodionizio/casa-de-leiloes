# Migration 0006, leituras e seed

## 1. Schema aditivo

Decidi criar `backend/migrations/versions/0006_lot_cancellation.py`, `revision="0006"`,
`down_revision="0005"`, sem branch/dependency adicionais. Upgrade acrescenta somente
`lots.cancelled_at TIMESTAMPTZ NULL` (`sa.DateTime(timezone=True)`, `nullable=True`),
sem `server_default`, default Python, UPDATE ou backfill. Lotes existentes ficam
NULL; novos lotes manuais/demo também nascem NULL. `Lot.cancelled_at` é
`Mapped[datetime | None]`, `mapped_column(DateTime(timezone=True))`, no padrão local.
Não mudo `create_lot` para assinar ou inicializar timestamp de cancelamento.

Downgrade remove apenas `cancelled_at`; preserva rows, bids, carteiras, índices e
constraints anteriores. Perde o marcador de cancelamento, consequência normal do
downgrade a registrar no build; não é reabertura suportada no runtime. Novo upgrade
recria a coluna NULL, sem reconstruir timestamps descartados.

Descartei CHECK que ligue cancelled_at a bid_count, enum status, fase cancelada,
marcador de liquidação e índice novo. PK de lots atende cancelamento/detalhe; índice
`ix_lots_auctioneer_id` atende seleção administrativa. Vitrine já lê todos os lotes
sem paginação e seed é um EXISTS pequeno na escala aceita. Não há medição/plano
que comprove ganho para índice de cancelled_at; não o adiciono por hábito.

## 2. Filtro público, query por query

| Consulta real | Alteração exata | Por que nesse ponto |
| --- | --- | --- |
| `lots.public_snapshot_statement` / `read_public_snapshot` | Trocar ON true por `Lot.cancelled_at.is_(None)` | LEFT JOIN nasce do clock; mesmo só com cancelados sobra linha de as_of |
| `lots.read_public_lot_snapshot` | ON `and_(Lot.id == lot_id, Lot.cancelled_at.is_(None))` | Cancelado aparece como lote ausente, preservando linha do clock |
| `bids.public_room_statement` / `read_public_room` | ON de Lot com ID AND cancelled_at IS NULL | Não alterar LEFT LATERAL de bids, limite/ordem; lot_id nulo já gera None/404 |
| `bids.my_bids_statement` / `read_my_bids` | WHERE `Lot.id == lot_id` AND `Lot.cancelled_at.is_(None)` | Esta consulta não usa LEFT JOIN/clock; zero linhas já significa None/404 |

Importo `and_` do SQLAlchemy onde necessário; não filtro apenas depois de montar o
DTO, não crio consulta prévia de existência e não uso WHERE sobre Lot nas três
leituras que preservam clock. Mantive o WHERE em `/bids/mine` porque é o formato
real desse statement. A regra “filtro no JOIN” vale só para as três consultas que partem do
relógio (LEFT JOIN), para preservar `as_of` e o caso vazio; `my_bids_statement`
não tem JOIN e usa `WHERE cancelled_at IS NULL`. Não invento JOIN ali; D3 intacta.

Vitrine 200 continua `{as_of,live,scheduled,ended}`, sem cancelados em qualquer
grupo; só cancelados ou banco vazio gera três listas vazias com as_of válido.
Detalhe, `/bids` e `/bids/mine` retornam 404 `not_found` após políticas existentes.
`/bids/mine` continua BIDDER (401 anônimo, 403 AUCTIONEER); o dono vê o cancelado
somente pela lista administrativa. UUID inválido permanece 422. Não adiciono
`cancelled_at` aos DTOs públicos, nem quarta fase. As_of público continua avaliado
uma vez no CTE MATERIALIZED do mesmo statement, sem relógio separado.

GET/HEAD/OPTIONS não cancelam, liquidam, assinam, corrigem ou rodam seed; sem lock
explícito de linha, sem gate nas leituras. Uma leitura já iniciada antes do commit
pode ver o snapshot anterior pelo MVCC; não prometo revogação retroativa ou tempo
real. Depois do commit, uma leitura nova exclui o cancelado.

## 3. GET /api/lots/mine — contrato exato (D7)

Preservo AUCTIONEER, `no-store`, todos os lotes do dono e a ordenação
`created_at DESC,id DESC`, sem paginação/limite/query de outro owner. Crio
`MyLotResponse(LotResponse)` exclusivamente para itens administrativos e altero
`MyLotsResponse` para campos obrigatórios `as_of: datetime`,
`items: list[MyLotResponse]`. Criação 201 continua usando `LotResponse` original.

| Campos exatos de cada item | Tipo |
| --- | --- |
| `id` | UUID |
| `external_id` | int |
| `title`, `artist_display`, `date_display`, `medium_display`, `dimensions`, `department_title`, `artwork_type_title`, `credit_line` | string nullable, sempre presentes |
| `source_url`, `image_id`, `image_url` | string; URL de imagem derivada pelo helper existente |
| `starting_bid_cents`, `min_increment_cents` | int em centavos, sem mudança |
| `starts_at`, `ends_at`, `created_at` | datetime UTC Z |
| `cancelled_at` | datetime UTC Z ou null, obrigatório |
| `bid_count` | int não negativo persistido, sem autenticação de cadeia nesta leitura |
| `phase` | `LotPhase`: scheduled, live ou ended |

São os 18 campos atuais de `LotResponse` mais os três novos, nenhum `as_of` por
item, `auctioneer_id`, líder, hash, âncora, status ou resultado. Envelope tem
exatamente duas chaves; vazio `{as_of:"...Z",items:[]}`. Fase é calculada somente
por `lot_phase(starts_at,ends_at,as_of)`, mesmo quando cancelled_at não é null.

Crio `my_lots_statement(auctioneer_id)` e
`read_my_lots_snapshot(session,auctioneer_id)` em `lots.py`: clock CTE MATERIALIZED
único, `FROM clock LEFT OUTER JOIN lots ON lots.auctioneer_id=:auctioneer_id`,
sem filtro de cancelamento. Ordenação externa `created_at DESC NULLS LAST,id DESC
NULLS LAST`; descarto a entidade nula e preservo as_of. É um statement de negócio
após o SELECT de User da policy, não “um SELECT total”. Não faço
`database_now()` separado seguido de SELECT. Construo itens via campos explícitos
de `lot_response(lot)` mais os três campos novos, antes do rollback da leitura.

`my_lot_response(lot,as_of)` não modifica `lot_response`, que continua servindo o
201. `bid_count` aqui é dica de UX; nunca autoriza cancelamento e não prova
integridade. O cancelado permanece listado mesmo depois de `phase=ended`.

## 4. Seed

`seed_demo_lot` acrescenta `Lot.cancelled_at.is_(None)` no EXISTS existente:
`is_demo=true AND ends_at>now AND anchor_hmac IS NOT NULL AND cancelled_at IS NULL`.
Um demo cancelado não conta como aberto válido. Se não houver outro válido, o
próximo run_seed pode inserir novo demo pelo `create_lot` atual, com âncora vazia
própria e cancelled_at NULL. Se outro já é válido, não cria. Repetir boot não duplica.

Preservo trava consultiva do seed, um instante pós-trava, fixture offline, usuários
e carteiras do seed; nunca faço UPDATE/DELETE, reativação ou assinatura de lote
encontrado. Cancelar não chama seed imediatamente. A exclusão de cancelados é
predicado de seleção, não uma autenticação completa do demo.
