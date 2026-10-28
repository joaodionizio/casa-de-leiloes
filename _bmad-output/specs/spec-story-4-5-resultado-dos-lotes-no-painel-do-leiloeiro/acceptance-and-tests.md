# Critérios de aceite e plano de testes final

Consolidei QH-01–13; cenários B/F/E serão executados no build autorizado.
## Critérios de aceite

| ID | Oráculo de aceite | CAP / prova planejada |
| --- | --- | --- |
| CA01 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então dono reconhece scheduled/live e pending expirado sem settlement; nenhum resultado econômico inferido | CAP-1; B01/02/19, F01/02/17, E03 |
| CA02 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então sold mostra somente resumo persistido aprovado, valor BRL/alias/instante corretos | CAP-2; B03/06/07/08/18, F03/06/07/08, E01 |
| CA03 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então unsold não apresenta vencedor ou valor artificial; count=0 e settled_at persistido | CAP-2; B04, F04/09/10, E02 |
| CA04 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então cancelado sem settlement prevalece sobre fase; cancelado+settlement não vira sucesso | CAP-1/5; B05/17, F05/17, E07 |
| CA05 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então ownership no banco, 401/403, inexistente/alheio sem enumerar dados privados | CAP-4; B09–12, F22, E04 |
| CA06 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então dTO whitelist, cents inteiros e nenhum dado privado/HMAC/wallet/receipt indevido | CAP-4; B06–08/18, F14/17, E01/04 |
| CA07 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então leitura não escreve/liquida/publica/repara; conflito/contrato inválido falha seguro | CAP-5; B14–17/20, F12/17, E03 |
| CA08 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então vários lotes usam uma chamada e quantidade fixa de statements; snapshot coerente | CAP-5; B13/21, F18/19, E08 |
| CA09 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então montagem/manual/foco atualiza pending para sold e unsold sem regredir por resposta antiga | CAP-3; F15/16/18/19/20, E05/06 |
| CA10 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então loading/erro/vazio/atualização desatualizada distintos, foco/teclado/mobile legíveis | CAP-5; F11–13/20/21, E07/08 |
| CA11 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então total recebido = soma sold próprios coerentes no mesmo snapshot, zero sem vendas; nunca parcial ou saldo de carteira | CAP-6; B22–24, F21/22, E01/02/08 |
| CA12 | Dado o cenário indicado na matriz, quando consulto/atualizo o painel, então preservados painel/criação/cancelamento, finanças, bids, sala, heartbeat, fechamento e AD-5 cumulativa | Todas; regressões existentes e E07 |

## Backend B01–B24

Usar PostgreSQL real para autorização, persistência, queries, par e provas de ausência
de efeitos. Fixtures de sold/unsold via comando existente de teste autorizado no build;
nenhuma preparação econômica pela rota GET. Expired pending exige controlar o lifecycle
no harness existente (como testes legados 4.4), para que scheduler/catch-up não feche
o lote antes da prova; não criar switch de produção. Capturar statements e snapshots
só ao redor da leitura, separando atividade externa deliberada do scheduler.

| ID | Cenário | Asserção concreta |
| --- | --- | --- |
| B01 | Dono consulta lote ativo e agendado | 200, phase correto pelo as_of, status técnico pending/null, sem campos de vencedor |
| B02 | ends_at <= as_of sem settlement | 200 ended+pending/null, inclusive igualdade com now fixo; sem conclusão sold/unsold |
| B03 | Sold persistido | Alias/amount/count/settled_at iguais ao settlement confirmado, nunca recomputados de maior bid |
| B04 | Unsold persistido | outcome unsold, alias/amount null, count 0, data original; nenhum receipt criado |
| B05 | Cancelado sem settlement, antes/depois do fim | cancelled_at preservado, nenhum unsold; cancelado incluído na lista do dono |
| B06 | Privacidade do vencedor | Chaves exatas, winner_user_id/bidder_id/nome real ausentes no JSON aninhado e seus valores privados não aparecem |
| B07 | Privacidade de integridade | anchor_hmac/HMAC/segredos ausentes, inclusive no erro; final_hash ausente conforme QH03 |
| B08 | Privacidade financeira/email | Nenhuma wallet/saldo/email do vencedor em payload; sem consulta users do vencedor/wallet para resumo; User fixo do auth permitido |
| B09 | Outro leiloeiro | Lista e total só próprios, IDs/alias/valores alheios ausentes; query string não muda owner |
| B10 | Bidder | 403 forbidden/no-store antes de ler resultados privados |
| B11 | Anônimo/sessão inválida/expirada | 401 unauthorized/no-store e nenhum resultado |
| B12 | Inexistente | Não há lookup privado por lot_id; item inexistente/alheio ausente, queries não mudam owner |
| B13 | Lista com 1/30/101 lotes e resultados mistos | Um statement de negócio, um clock, custo de auth constante; zero SELECT por item, sem requests adicionais no contrato |
| B14 | Leitura não cria settlement | Comparar conjunto/valores completos de settlements antes/depois; spies de prepare/settle/scheduler falham se chamados; nenhum DML/FOR UPDATE/commit |
| B15 | Leitura não altera wallet/bids/lots | Snapshot de todas carteiras, bids e lotes antes/depois idêntico; sem lock de escrita ou reparo |
| B16 | Leitura não cria receipt/publicação | Conteúdo/quantidade/IDs de receipts preservados, manager não recebe lot_closed; nenhum agendamento financeiro |
| B17 | Par estrutural inválido | Sold sem receipt, unsold com receipt, receipt órfão, cópias divergentes, vínculo incorreto, cancelled+settlement e campos inválidos falham seguro; zero repair/efeito |
| B18 | Tipos/limites monetários | Cents inteiros exatos até MAX_CENTS; bool/float/string/overflow em projeção não entram no DTO; unsold null, não 0 |
| B19 | Hora/fase | Clock PostgreSQL único, UTC/micros preservados, scheduled/live/ended limites e cancelamento prevalecendo; browser não decide |
| B20 | Divergência contra Lot | Count/hash/current bid/current leader incompatíveis ou settled_at < ends_at/phase futura falham sem dado contraditório/reliquidação |
| B21 | Snapshot/concorrência de leitura | Commit externo antes/durante statement: par e total inteiros ou ausentes juntos, nunca mistura; reader não bloqueia em lot lock de escrita retido |
| B22 | Total misto próprio + alheio | Dois sold próprios 13000+25000 = 38000; alheio/pending/unsold/cancelled excluídos; soma no mesmo snapshot da lista |
| B23 | Total zero | Lista vazia e lista sem sold dão 0 inteiro; erro/ausência de contrato não se tornam zero |
| B24 | Total e falha | Item inconsistente impede total parcial; soma fora de intervalo seguro falha sem saturar/float; sold que passa a existir só entra com snapshot novo |

Adulterações de fixture são exclusivas do banco de teste e restauradas; não remover
constraints globalmente ou alterar produção para fabricar estados impossíveis.
Testar no-store também em falha operacional 500 ou integridade409; não confiar apenas no retorno padrão de exceção.
HEAD/OPTIONS, se suportados, são puros; se não, 405 sem escrita é aceitável como hoje.

## Frontend F01–F22

Lógica pura/parse em node:test existente; DOM, foco, formatação na tela e coordenação
de refetch em Playwright Chromium com API simulada. Testes não espelham apenas a função:
injetar respostas contrastantes, atrasadas e malformadas para provar observáveis.

| ID | Cenário | Oráculo |
| --- | --- | --- |
| F01 | Ativo | Agendado/Ao vivo segundo contrato servidor, texto além de cor |
| F02 | Expirado sem settlement | Encerrado, apurando resultado; nenhum vencedor/preço final |
| F03 | Sold | Label aprovado, não Encerrado genérico ou Apurando |
| F04 | Unsold | Sem arremate, sem label Cancelado |
| F05 | Cancelado | Cancelado prevalece sobre phase ended/zero bids |
| F06 | Vencedor sold | Mostra alias literal persistido; sem email/nome real |
| F07 | Valor sold | 13000 → R$ 130, 00; máximo seguro sem perda; não usa starting_bid_cents |
| F08 | Data sold | settled_at por formatDateTime no fuso do navegador; distinguir Término ends_at de Apurado em |
| F09 | Unsold vencedor | Não renderiza campo/alias vencedor ou dado anterior de sold |
| F10 | Unsold preço | Não mostra R$0, 00 como arremate, nem lance inicial como preço final |
| F11 | Loading | Estado carregando sem resultado/total fictícios |
| F12 | Erro inicial/refetch | Erro inicial não vira vazio; refetch mantém snapshot marcado antigo e limpa aviso após sucesso |
| F13 | Vazio | Texto e Criar lote funcionais; total=0 só depois de sucesso válido |
| F14 | Payload privado inesperado | Nenhum valor/chave privada chega ao DOM; novo resumo com extra proibido é recusado; API também possui whitelist testada |
| F15 | Pending→sold | Refresh escolhido muda label/alias/amount/date/count e total juntos |
| F16 | Pending→unsold | Refresh muda para Sem arremate, total exclui lote, sem alias/preço antigo |
| F17 | Contrato desconhecido/inconsistente | Status/outcome desconhecido, nulls errados, números inseguros, datas inválidas e cancelled+settlement não viram sucesso/vazio |
| F18 | Deduplicação | Foco/visible/manual simultâneos não geram GET por linha, overlap ou rajada |
| F19 | Resposta substituída | Leitura A pending retida, B sold/unsold aceita, A é entregue apesar de abort e não regride B; conta A nunca contamina B |
| F20 | Cleanup e erro | Desmontar/401/403/offline/hidden remove listeners/reads; falha não cria retry recursivo; cancelamento pendente coordena reads |
| F21 | Contagem/total/layout | Count congelado sem duplicação, total formatado/rotulado; 30/50 registros, títulos/alias/valores longos, 320px sem overflow |
| F22 | Total privado e inválido | Total do backend é usado, não soma de bids; zero/máximo válidos; ausente/bool/float/negativo/overflow recusados; logout troca conta e limpa total |

QH-06 decidiu sem polling. F18/F20 provam dedupe/cleanup sem interval ou timer de 10 s;
aba parada não promete mudança sem GET. Não instalo novas dependências de teste.

## E2E representativo E01–E08

| ID | Jornada | Prova |
| --- | --- | --- |
| E01 | Sold | Login leiloeiro → Meus lotes → vendido, alias/valor persistidos e total próprio correto |
| E02 | Unsold | Login → Sem arremate, sem preço/vencedor artificial; total exclui lote |
| E03 | Pending puro | Expirado sem settlement → apurando; abrir/atualizar painel não liquida, cria receipt ou altera wallet |
| E04 | Autorização | Outra conta leiloeira não recebe coleção/total alheios; bidder 403/anônimo401 |
| E05 | Atualização sold | Painel inicialmente pending; settlement externo confirmado; mecanismo aprovado relê → sold/total, sem callback do scheduler para React |
| E06 | Atualização unsold | Mesmo fluxo para unsold, sem vencedor/preço |
| E07 | Painel/cancelamento | Estados mistos, confirmar/voltar/cancelar, foco/teclado, criação e navegação preservados; pending/settled não ganham CTA inválido |
| E08 | Densidade/erro/rede | Loading/vazio/falha/refetch, 50 registros em 320/375/desktop, imagem quebrada, uma chamada de dados, total sem parcial e resposta antiga inerte |

Playwright com mock prova DOM/requests, não autorização real ou zero efeitos no
PostgreSQL. E03/E04 e E05/E06 precisam prova integrada adicional no build autorizado:
API real/PG e lifecycle controlado para pending, settlement via serviço de preparação
externo ao GET, login real e antes/depois dos registros. Pode usar harness real-stack
existente opt-in, sem ampliar verify padrão ou atribuir a mock prova financeira.
Quando exercitar scheduler real, não manter harness que o suprima nesse cenário.

## Regressões e gates futuros

Preservar suítes de MyLots, criação e cancelamento (3.6), wallet (3.1), bids e
anti-sniping cumulativo (3.2–3.5), sala/heartbeat (4.1/4.2), settlement/receipt (4.3),
scheduler/catch-up/lot_closed (4.4). Atualizar fixtures/whitelists estritas somente
para novos campos aprovados, sem remover assertions de ownership/pureza/ordem.
Não há edição de lote identificada; não criá-la sob o rótulo regressão.

No build autorizado, executar testes focados e gates requeridos pelo fluxo/AD-27;
Playwright é opt-in existente e real-stack fica separado. Registrar comandos reais,
resultados e limites; teste manual visual e review independente permanecem etapas
próprias. 

## Rastreabilidade executada

Matriz B01–24/F01–22/E01–08 executada por testesparametrizados, regressões e smoke
integrado; nomes/alcance/limites em [implementation-evidence.md](implementation-evidence.md).
B16/B17 receberam provas próprias da rota com zero publicação, unsold+receipt e
receiptórfão. Mantive todos os IDs/oráculos. Não afirmo cobertura de cada mecanismo
hipotético: cleanup é comportamental, não contagem de listeners, suspensãoSO ou offline
físico, fora do mecanismo aprovado sem polling.
