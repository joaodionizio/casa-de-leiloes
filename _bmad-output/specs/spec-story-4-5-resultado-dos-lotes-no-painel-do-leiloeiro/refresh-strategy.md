# Estratégia final de atualização — QH-05/06

Decidi fetch na montagem, botão **Atualizar** e refetch ao voltar foco/visibilidade.
Não implemento polling, timer de 10 s, interval, WS do painel ou callback de scheduler.
Aba visível parada conserva fotografia até ação; não prometo mudança espontânea.

- Uma coordenação de leitura por tela; manual/foco/visible durante GET em voo reutilizam/ignoram rodada, sem requests simultâneos duplicados ou fila.
- Focus e retorno visible da mesma retomada são deduplicados; não usar timer de polling. Invalidar autoridade por sequência/montagem/sessão mesmo se abort for ignorado.
- Montagem lê uma vez. Sucesso troca lista/total/as_of juntos e limpa stale. Falha inicial mostra erro recuperável. Falha posterior conserva snapshot inteiro com aviso claro, sem zerar total/lista.
- 401 usa sessão expirada; 403 encerra automático e dados não autorizados. Desmontagem/logout/troca de conta remove listeners, aborta/invalida reads.
- Cancelamento pendente suspende novos refreshes; invalida leitura pré-comando e mantém refetch pós-cancelamento/avisos existentes. Não reenviar comando nem tirar foco da confirmação.
- Leituras não liquidam ou publicam; não há request por card/linha, cálculo de resultado por evento, prazo ou quantidade de elementos.
- Testar foco/manual, pending→sold/unsold, leitura velha entregue apesar de abort, zero overlap e cleanup. Sem polling, não há teste de intervalo a instalar.

Descartei somente manual (menos recuperação), polling (tráfego contínuo) e WebSocket
(novas conexões/reconciliação). Reuso fetchMyLots/readList e geração atuais.
