# Invariantes financeiras finais

## Modelo preservado do Epic 3

Decidi manter a contabilidade existente: lance não debita total, apenas compromete saldo do líder; quando superado, o líder anterior é liberado na transação do novo lance. Liquidação não devolve reservas de todos os bids, não cria ledger/escrow/taxa nem muda teto. O leiloeiro já tem carteira criada pelo seed/migration; crédito interno não exige API de carteira de leiloeiro.

Defino T=total_balance_cents, C=committed_balance_cents, A=available=T−C, M=9007199254740991, F=valor vencedor autenticado; W=vencedor, S=leiloeiro. Valores inteiros em centavos. Settlement autoritativo registra o resultado; não é novo saldo ou fonte paralela de dinheiro.

## Invariantes vinculantes

1. Sempre `available = total - committed`, com `0 <= C <= T <= M`. Disponível é derivado, nunca outra coluna contábil.
2. Nova venda exige `1 <= F <= M`, `C_W >= F`, identidades W/S distintas e carteiras existentes. Não completar reserva faltante a partir do disponível para esconder inconsistência.
3. Vencedor: `total_after = total_before - F` e `committed_after = committed_before - F`; portanto `available_after = available_before`. F já estava reservado; **não subtrair F novamente do disponível**, não acrescentar outro débito nem liberar só C sem debitar T.
4. Se C_W=F+R, em que R representa outros lotes, C'_W=R. Reservas de outros lotes ficam intactas; não zerar C_W indiscriminadamente.
5. Leiloeiro: `total_after = total_before + F`, `committed_after = committed_before`, `available_after = available_before + F`.
6. Conservação: `sum(total_after) = sum(total_before)` nas carteiras envolvidas, sem dinheiro criado/destruído; a transferência é −F/+F. Globalmente, ΣC diminui F e ΣA aumenta F por consumo da reserva/receita disponível, sem aumentar ΣT.
7. Perdedores: T/C/A iguais antes/depois. A reserva de L deles já foi liberada no lance em que perderam; compromisso que ainda possuem pode pertencer a outro lote e não é tocado.
8. Unsold: zero alterações financeiras, settlement unsold confirmado e zero receipts. Repetição válida: zero alterações financeiras e zero novos settlements/receipts.
9. Teto violado (`T_S+F>M`), reserva insuficiente/invariante financeira inválida: conflito financeiro tipado e rollback completo, sem débito, liberação parcial, crédito, settlement ou receipt. Carteira ausente mantém MissingWalletError com rollback, sem criação automática.
10. Falha antes do commit ou COMMIT abortado: todas as carteiras e registros permanecem como antes. Confirmação de COMMIT perdida é ambiguidade; retry por lot_id descobre o resultado confirmado sem novo efeito.
11. CHECK vale a cada UPDATE. Especifico UPDATE conjunto de T_W e C_W para evitar C>T intermediário; depois crédito em S, ambos na mesma transação. Descartei debitar T isoladamente antes de reduzir C.

Em estado íntegro, C_u é a soma dos valores em que u lidera lotes ainda sem settlement, inclusive expirados pendentes. Essa identidade é oráculo do teste, não instrução para travar outros lotes depois da carteira. A âncora não autentica saldos; não prometo prova criptográfica da origem de cada centavo agregado.

## Estado antes → operação → estado depois (centavos)

Uso `(T,C,A)`; S começa `(5000,0,5000)`; exemplos isolam a transação, sem depósitos.

| Caso | Antes | Operação | Depois |
| --- | --- | --- | --- |
| 1. Sem lances | Âncora 0/genesis válida, sem líder | Fecha expirado íntegro | Settlement unsold; vencedor/alias/bid/F nulos; zero receipts e carteiras idênticas |
| 2. Um lance F=12000 | W `(50000,12000,38000)` | W T−12000/C−12000; S T+12000 | W `(38000,0,38000)`, S `(17000,0,17000)`; soma T=55000 antes/depois; disponível W continua 38000 |
| 3. Vários lances | A perdeu lance 10000 e está `(40000,0,40000)`; B lidera 12000 em `(50000,12000,38000)` | Liquida só bid vencedor B | A igual; B `(38000,0,38000)`; S `(17000,0,17000)`; não somar bids históricos |
| 4. Vencedor em outro lote | W `(80000,32000,48000)` com F_L=12000 e R_K=20000 | Consome só F_L | W `(68000,20000,48000)`; R_K e A intactos; S +12000 |
| 5. Perdedor em outro lote | A `(40000,7000,33000)` perdeu L e lidera K | Fecha L | A idêntico; reserva K=7000 não liberada |
| 6. Repetição horas depois | Caso 2 confirmado; IDs settlement/receipt e instante originais | Revalida e retorna already_settled | Mesmos T/C/A, IDs, vencedor/F/count/hash/data; transitioned=false; zero INSERT/UPDATE |
| 7a. Lance vence | A reserva 10000; B tem 50000 disponíveis, fim E | B válido estende E→E+2min e commit; closer relê fim futuro | A reserva L=0, B reserva L=12000; totais iguais; closer not_due, sem settlement/receipt |
| 7b. Fechamento vence | W `(50000,12000,38000)`, now>=fim | Closer confirma; B espera e depois tenta lance | Caso 2 persistido; B recusado e intacto; fim/count/hash não mudam |
| 8. Rollback durante liquidação | Caso 2 antes, UPDATE W já enviado sem commit | Crédito, INSERT settlement/receipt ou COMMIT aborta | W `(50000,12000,38000)`, S `(5000,0,5000)`; nenhum settlement/receipt novo |

Se T_S=M−5 e F=10, a venda inteira falha: não saturo, aumento ou ignoro teto, não faço crédito parcial, carteira alternativa ou alteração da regra financeira. QH-08 está decidida; o mecanismo operacional da 4.4 fica fora, com obrigação explícita de não fazer retry quente infinito dessa condição.
