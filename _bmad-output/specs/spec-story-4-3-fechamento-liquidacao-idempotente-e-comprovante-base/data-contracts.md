# Contratos finais — settlement, receipt, serviço e readers

Consolidei QH-01–10. Os nomes abaixo adaptam as decisões humanas às convenções do projeto; não são propostas abertas. Código e migrations permanecem para build autorizado.

## Identidade do lance vencedor

`bids` já usa PK `(lot_id, sequence)` e não tem `id`. Adapto **winning_bid_id conceitual** para `winning_bid_sequence BIGINT` junto de lot_id, com FK composta `(lot_id, winning_bid_sequence) → bids(lot_id, sequence)`, ON DELETE RESTRICT. Esta é a identidade exata do lance; não criar bids.id, usar bidder_id como referência pública ou mudar canonical bid v1. Nos DTOs, o par lot_id/winning_bid_sequence representa a mesma referência. Isso vale para settlement e receipt.

## lot_settlements: registro econômico autoritativo

| Campo final | Tipo PostgreSQL/null | Regra |
| --- | --- | --- |
| id | UUID, NOT NULL, PK | UUID próprio gerado pela aplicação conforme padrão dos modelos; imutável |
| lot_id | UUID, NOT NULL, UNIQUE | FK lots.id ON DELETE RESTRICT; no máximo um settlement por lote |
| outcome | TEXT, NOT NULL | CHECK IN ('sold','unsold') |
| winner_user_id | UUID, nullable | FK users.id ON DELETE RESTRICT; interno, preenchido só sold |
| winner_alias | TEXT, nullable | Alias do último bid autenticado, preenchido só sold |
| winning_bid_sequence | BIGINT, nullable | winning_bid_id adaptado; FK composta acima; preenchido só sold |
| final_amount_cents | BIGINT, nullable | 1..MAX_CENTS só sold; não zero para unsold |
| bid_count | BIGINT, NOT NULL | >=0; contagem autenticada, sem limite da janela pública |
| final_hash | TEXT, NOT NULL | 64 hex minúsculos; último hash ou genesis |
| anchor_hmac | TEXT, NOT NULL | Cópia exata interna da âncora validada, 64 hex minúsculos; nunca o segredo |
| settled_at | TIMESTAMPTZ, NOT NULL | Mesmo now pós-lock da nova liquidação; sem default de relógio separado |

Constraints locais: sold exige winner_user_id/alias/winning_bid_sequence/final_amount todos NOT NULL, bid_count>0, winning_bid_sequence=bid_count, preço positivo <=MAX, alias `^Licitante-[0-9A-F]{16}$`. Unsold exige **todos os quatro campos NULL**, bid_count=0 e final_hash=64 zeros. Não depender de CHECK que resulte UNKNOWN: expressar IS NULL/IS NOT NULL explicitamente. anchor_hmac ausente nunca é aceito, mesmo vazio.

Além de PK id e UNIQUE(lot_id), criar chave candidata UNIQUE(id,lot_id) para o vínculo composto do receipt. Uso o naming convention atual de `app/db.py`; versão 1 da âncora é o contrato vigente, sem inventar nova assinatura ou coluna de versão redundante.

A existência **commitada** do settlement é a conclusão econômica da apuração, inclusive unsold. Não calcular resultado a partir de presença de receipt, phase, saldo ou horário sozinho. Antes do commit, INSERT/flush é apenas trabalho provisório da transação.

## receipts: comprovante base separado e pseudonimizado

| Campo final | Tipo PostgreSQL/null | Regra |
| --- | --- | --- |
| id | UUID, NOT NULL, PK | Identidade própria estável; não share token |
| lot_id | UUID, NOT NULL, UNIQUE | FK lots.id RESTRICT; no máximo um receipt por lote |
| settlement_id | UUID, NOT NULL, UNIQUE | Relação 1:1 com settlement; FK composta `(settlement_id,lot_id) → lot_settlements(id,lot_id)` RESTRICT |
| winning_bid_sequence | BIGINT, NOT NULL | winning_bid_id adaptado; FK composta para bids do mesmo lote |
| winner_alias | TEXT, NOT NULL | Alias persistido do vencedor, mesmo padrão do settlement |
| final_amount_cents | BIGINT, NOT NULL | 1..MAX_CENTS; igual ao settlement |
| settled_at | TIMESTAMPTZ, NOT NULL | Igual ao instante original do settlement |
| bid_count | BIGINT, NOT NULL | >0; winning_bid_sequence=bid_count |
| final_hash | TEXT, NOT NULL | 64 hex minúsculos, igual ao settlement |

O schema do receipt **não contém** winner_user_id, bidder_id, auctioneer_id, e-mail, carteira/saldos/compromissos, HMAC, segredo, JWT ou outro identificador privado de pessoa. Seus UUIDs identificam documentos/lote; a referência do bid não revela bidder_id. Não incluir canonical_version redundante no receipt: a referência aponta a um bid v1 existente.

Sold exige exatamente um receipt; unsold exige zero. PK/UNIQUE/FKs e CHECKs locais defendem identidade/referências; a cardinalidade condicional entre tabelas e igualdade de campos duplicados são garantidas pelo serviço atômico, revalidação e testes. Não afirmo que CHECK comum consulte outra tabela nem adiciono trigger de produto silencioso para esse fim. SQL manual pode corromper relação não coberta por constraints; isso é detectado no retry, sem reparo.

## Coerência e fonte dos dados

No novo fechamento, copiar os dados econômicos/autenticados para settlement e depois receipt na mesma transação. IDs próprios não mudam em repetição. winning_bid_sequence aponta o último bid aceito; alias é o gravado, não recalculado no reader. As cópias receipt/settlement devem concordar em lot_id, referência do bid, alias, F, settled_at, count/hash.

Settlement é autoritativo; receipt não comanda débito/crédito nem substitui settlement faltante. Sold sem receipt, unsold com receipt, receipt sem settlement ou com settlement de outro lote são conflitos, nunca instruções para completar registros na leitura. Título/artista e demais metadados públicos vêm do snapshot existente de lots; nenhuma consulta AIC, novo snapshot, share_url, token, botão, link ou página pública nesta story.

## Serviço interno: resultado discriminado

Comando `settle_lot(session_factory, *, lot_id, integrity)` gerencia sua Session e confirmação; helpers de preparação não retornam transitioned. DTOs finais imutáveis, sem ORM exposto:

| status | settlement | receipt | transitioned | Significado |
| --- | --- | --- | --- | --- |
| settled_sold | SettlementRecord sold confirmado | ReceiptRecord confirmado | true | Nova venda: retorno somente depois de commit bem-sucedido |
| settled_unsold | SettlementRecord unsold confirmado | None | true | Nova apuração sem lances, commit confirmado |
| already_settled | SettlementRecord persistido e revalidado, sold ou unsold | ReceiptRecord original se sold; None se unsold | false | Nenhuma escrita econômica ou criação de registro |
| not_due | None | None | false | Sem settlement e now < ends_at; nenhuma liquidação |

lot_id acompanha os DTOs. SettlementRecord é **interno** e pode conter winner_user_id/anchor_hmac; ReceiptRecord tem exclusivamente as colunas seguras do receipt. A diferença entre already_settled e resultado novo não muda dados/IDs/instante do registro persistido.

Falhas seguem o padrão tipado existente, fora dos sucessos acima:

- Gate ou coerência lote/settlement/receipt: `IntegrityConflict`; categorias internas de mismatch do settlement/receipt complementam as falhas de integridade existentes. Nunca already_settled com warning ignorado.
- `SettlementFinancialConflict` com razão tipada `credit_limit_exceeded`, `insufficient_commitment` ou `wallet_invariant_conflict`: rollback integral, sem resultado de sucesso. Sem valores privados na mensagem/log.
- Lote inexistente: None, como nos serviços atuais; lote cancelado sem settlement: recusa tipada `SettlementRefusal.LOT_CANCELLED`. Cancelado contraditoriamente liquidado é IntegrityConflict.
- Carteira ausente: preservar violação de invariante `MissingWalletError` já existente, rollback integral e sem criação. Erros inesperados de DB/commit propagam; não viram sucesso ou recusa financeira artificial.

Não mapear essas variantes para status HTTP: nenhuma rota é criada. Preferência humana futura HTTP 200 para novo/repetido fica registrada em human-decisions.md, sem contrato HTTP vigente na 4.3.

## Readers internos por lot_id e eixo de liquidação

`read_settlement(session, lot_id)` recupera SettlementRecord ou None; `read_receipt(session, lot_id)` recupera ReceiptRecord ou None. Nenhum faz commit, INSERT/UPDATE/DELETE, FOR UPDATE, liquidação ou criação tardia. O chamador encerra a transação de leitura. Usar projeções explícitas e snapshot coerente (um statement com joins para checagens relacionadas), sem serializar relações ORM inteiras.

Os readers distinguem ausência legítima de receipt (pendente/unsold) de sold sem receipt/unsold com receipt/órfão, retornando IntegrityConflict na incoerência estrutural. Uma leitura de referência persistida não certifica nova verificação criptográfica nem se apresenta como auditoria pública. O comando repetido executa a revalidação completa do transaction-contract antes de sucesso idempotente.

| Condição | settlement status conceitual | outcome | Regra |
| --- | --- | --- | --- |
| Não cancelado, sem settlement | pending | None | Phase continua scheduled/live/ended, derivada do relógio do banco |
| Fim alcançado, sem settlement | pending | None | “Encerrado, apurando resultado”; leitura não fecha |
| Settlement sold confirmado | settled | sold | Dados do vencedor/valor e receipt persistidos |
| Settlement unsold confirmado | settled | unsold | Quatro campos nulos, zero receipt, sem preço fictício |
| Cancelado | Não representa settlement de fechamento | None | Terminal separado; preservar ocultação pública/404 existente |

Não persistir coluna pending que duplique ausência de settlement. Não alterar phase, protocolo WS, room_snapshot, bid_accepted, shouldApplyRoom, máquina 4.2, UI da sala ou painel. Stories posteriores integrarão resultado persistido.

## Privacidade e limites de integridade

Whitelist estrita para receipt; não expandir por joins com users/wallets ou serialization automática de SettlementRecord. Nenhuma representação pública criada nesta story. Logs novos controlados somente com lot_id/categoria/classe, sem texto bruto de exceção SQL, HMAC ou parâmetros privados; testes usam segredos/marcadores sintéticos. Secret nunca é persistido, copiado em receipt ou impresso.

Antes de nova liquidação e de sucesso idempotente, autenticar cadeia inteira/gate e vínculo operacional existentes; não usar apenas últimos 50 bids. Settlement congela count/final_hash/anchor_hmac e winning bid; receipt só count/hash/referência pública. Nunca recalcular HMAC para legitimar legado ou gerar novo bid de fechamento.

Âncora v1 cobre histórico/count/hash; não autentica settled_at, carteiras, dono ou ends_at. Copiar a âncora preserva a evidência do histórico validado, não assina o resultado financeiro inteiro. Não criar assinatura própria ou alterar canônico. Segredo comprometido e rollback integral para estado antigo consistente permanecem limitações AD-13.
