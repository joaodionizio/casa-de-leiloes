# Operação transacional final de fechamento

## Serviço e dono da transação

Decidi expor somente o comando interno síncrono `settle_lot(session_factory, *, lot_id, integrity)`, testável diretamente, sem HTTP. O comando abre/fecha sua Session, coordena a transação inteira e é o único dono do commit/rollback. Um helper interno `prepare_settlement(session, ...)` compõe locks/validações/flush e produz dados provisórios **sem campo transitioned**; não é contrato de sucesso público e nunca faz commit sozinho. Preservo o padrão de helpers do Epic 3 e torno explícita a confirmação antes de devolver sucesso.

A assinatura descreve o contrato do futuro build, não código criado nesta sessão. Não compartilhar Session entre threads, não importar manager WS, não executar rede na transação. Chamador async futuro executará o comando síncrono em worker/threadpool (AD-25), com Session criada/fechada nesse worker. Testes usam session_factory do banco dedicado.

Todos os writers obedecem lote → carteiras por user_id crescente. Localização de candidato é só dica; a decisão exige lock por ID sem predicado temporal pré-lido. `lock_lot` força populate_existing para não usar identity map antigo; histórico/settlement/receipt são relidos sob lock. A seleção do comando não usa relação outer join em FOR UPDATE: travo a linha lots primeiro, leio os registros depois.

## Sequência explícita final

| Passo | Operação | Condição e efeito |
| --- | --- | --- |
| 1 | Abrir Session/transação e localizar por lot_id | Localização pode ser o próprio SELECT seguinte; inexistente retorna None após encerrar a transação, sem escrita |
| 2 | Adquirir `SELECT lots WHERE id=:lot_id FOR UPDATE`, com releitura forçada | Mesma trava do lance; nenhuma carteira/decisão crítica antes dela |
| 3 | Consultar `clock_timestamp()` uma vez após aquisição efetiva | Guardar now para toda a operação; não CURRENT_TIMESTAMP, relógio da aplicação ou instante pré-espera |
| 4 | Reler ends_at e estado do lote sob lock | Usar fim confirmado, inclusive extensão cumulativa; não alterar ends_at |
| 5 | Consultar settlement e receipt atuais por lot_id; identificar idempotência/terminal | Settlement existente entra no ramo de revalidação abaixo, nunca em nova liquidação; cancelado sem settlement é recusa; receipt sem settlement ou cancelado com settlement é conflito |
| 6 | Sem settlement, verificar tempo | Se now < ends_at: encerrar sem escrita e retornar not_due/transitioned=false. Igualdade é elegível. Nunca fechar ativo |
| 7 | Autenticar histórico completo e estado operacional | Gate existente: canonical v1, SHA-256, count/hash/âncora/HMAC, sequência final, líder/valor/alias atual ligados ao último lance. Falha/legado: IntegrityConflict, zero efeitos e nenhum reparo |
| 8 | Determinar sold ou unsold do estado autenticado | Count 0: sem vencedor/preço; count >0: último lance define winner_user_id, alias persistido, referência do bid e F; não MAX(valor) ou líder avulso |
| 9 | Para sold, identificar carteiras existentes de vencedor e leiloeiro | IDs internos confirmados; vencedor distinto do dono; sem criar carteira ou inferir destinatário de input |
| 10 | Travar carteiras em user_id crescente e reler saldos | Mesmo critério do lance; unsold não precisa carteira; não travar outro lote depois dessas carteiras |
| 11 | Validar invariantes e crédito | 0<=C<=T<=MAX; C_w>=F; T_s+F<=MAX. Reserva insuficiente/invariante/teto gera conflito financeiro tipado; zero efeitos |
| 12 | Liquidar sold | Um UPDATE conjunto de T_w−F e C_w−F, depois crédito T_s+F mantendo C_s; CHECK imediata sempre válida. Flush não é commit. Unsold não move dinheiro |
| 13 | INSERT lot_settlements | ID próprio, lot_id UNIQUE, resultado econômico e âncora HMAC validada congelados; unsold também gera settlement |
| 14 | Se sold, INSERT receipts | ID próprio, lot_id UNIQUE e settlement_id UNIQUE; cópia pseudonimizada dos campos aprovados. Unsold exige ausência de receipt |
| 15 | Flush/conferir coerência e executar um único COMMIT | Dinheiro/settlement/receipt confirmam juntos. Exceção pré-commit ou commit abortado reverte tudo; descartar dados provisórios |
| 16 | Só após commit confirmado construir retorno final | settled_sold ou settled_unsold, transitioned=true; nenhum evento/publicação na 4.3. A futura 4.4 poderá consumir esse retorno |

Consultar settlement antes de retornar not_due evita ocultar terminal adulterado por fim futuro. Settlement já confirmado nunca reabre mesmo com clock regressivo/termos incoerentes; inconsistência retorna conflito. A trava serializa a decisão; a durabilidade vem do commit.

## Ramo de repetição: revalidação obrigatória, sem carteiras

Sob o mesmo lot lock e após o clock/releitura, ler histórico inteiro e autenticar o gate atual. Conferir settlement.lot_id, outcome, settled_at com fuso e relação temporal consistente (`settled_at >= ends_at`), count/hash e âncora HMAC congelada iguais ao estado autenticado; verificar a assinatura da cópia com o mesmo lot_id/count/hash. O instante é o original, nunca now da repetição.

Para sold: último bid/referência/usuário/alias/F iguais ao settlement e ao estado do lote, count>0; exatamente um receipt, com settlement_id e lot_id corretos, referência do bid, alias/F/settled_at/count/hash idênticos. Para unsold: count=0, genesis, quatro campos de vencedor/preço nulos e nenhum receipt. Cancelamento contraditório também falha. Revalidar por comparações explícitas, não por mera existência de linhas.

Inconsistência retorna IntegrityConflict e encerra por rollback sem UPDATE/INSERT/DELETE, sem sobrescrever, recriar receipt ou reliquidar. **Não** revalidar C_w>=F nem debitar carteiras nesta fase: a reserva já foi consumida e saldos podem ter mudado legitimamente por outras operações. Repetição válida encerra a transação de leitura/lock sem escrita e retorna already_settled com os dados persistidos e transitioned=false.

## Instante e fronteira de confirmação

settled_at é o now pós-lock da primeira apuração, não ends_at nem hora exata do COMMIT. Fechamento tardio guarda instante tardio; repetição devolve o mesmo. Settlement inserido/flushado na Session ainda é provisório: somente sua existência confirmada, visível por outra transação, significa apuração concluída. O comando não entrega objetos ORM mutáveis nem resultado de sucesso antes dessa confirmação.

## Falhas e recuperação

| Falha | Garantia persistida |
| --- | --- |
| Depois do lock/hora ou do cálculo | Nada novo; encerrar transação/liberar locks |
| Entre UPDATE do vencedor e crédito | Rollback restaura T e C do vencedor e todas as carteiras |
| Depois do crédito/INSERT settlement | Rollback também remove settlement provisório |
| INSERT receipt falha, inclusive UNIQUE/FK/CHECK | Rollback do dinheiro e settlement; não engolir erro para confirmar metade |
| Antes do commit após flush completo | Outra Session ainda vê estado anterior; falha reverte tudo |
| COMMIT rejeitado/abortado pelo banco | Nenhum efeito novo, sem transitioned=true |
| Confirmação perdida depois do envio de COMMIT | Resultado indeterminado para o chamador: banco contém tudo ou nada; não certificar rollback ou sucesso |

Erro de banco/commit propaga como falha; não vira already_settled. Em confirmação perdida, encerrar/descartar Session comprometida e repetir explicitamente por lot_id em nova Session. Se o primeiro commit ocorreu, settlement é encontrado/revalidado, devolvendo already_settled sem transferência duplicada; se não ocorreu, a tentativa pode liquidar uma vez. Nada compensa automaticamente, cria retry no GET ou retorna transitioned=true da tentativa ambígua.

Crédito acima do teto retorna conflito financeiro tipado e rollback integral. A 4.4 deverá tratar esse caso como condição operacional sem retry quente infinito; não especifico nem implemento seu mecanismo nesta story. Falha de publicação futura depois de commit não desfaz a liquidação (AD-25); a 4.3 não publica.
