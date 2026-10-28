# Modelo final de recuperação

Decidi QH-07/08/12: banco é a autoridade; snapshot/reconnect é recuperação
primária. Falha de transporte não desfaz nem refaz settlement confirmado.
Não uso outbox, fila persistente, marcador de entrega durável ou broadcast
periódico por already_settled. Alternativas rejeitadas estão em human-decisions.

## Janelas de falha

| Janela | Estado/garantia | Recuperação e publicação |
| --- | --- | --- |
| Antes de commit ou COMMIT abortado | Nada novo confirmado | Zero terminal; próxima tentativa só em ciclo futuro |
| COMMIT com confirmação perdida | Tudo ou nada pode ter persistido; retorno é falha, não sucesso | Zero terminal presumido; comando 4.3 em nova Session descobre/revalida estado em tentativa futura; snapshot lê persistido |
| Commit confirmado, crash antes de publish | Dinheiro/settlement/receipt preservados | Restart não faz replay de settled; sockets reconectam e recebem snapshot terminal |
| Commit confirmado, publicação falha no processo vivo | Resultado econômico preservado, entrega pode ser parcial | Log, tentar terminalização/invalidação e close recuperável das conexões daquele lote; reconnect recebe snapshot terminal |
| Cliente lento/fila cheia/send falha | Outros clientes continuam, sem garantia de entrega ao lento | Isolamento existente, reconnect/snapshot; zero reliquidação |
| Terminal recebido, depois close/timer/REST antigo | Cliente já conhece estado final | Nenhum reconnect/heartbeat nem regressão para pending |
| Shutdown após commit e sem publicar | Persistência continua autoritativa | Drenar o que for possível; log de pendência; snapshot depois do restart |

already_settled retorna dados originais revalidados com transitioned=false,
sem novo evento automático. A seleção normal exclui settlements confirmados;
para provar commit ambíguo, teste chama explicitamente o comando por ID e lê
snapshot. Não preciso varrer settled para recuperação de frames.

Uma transição lógica origina no máximo uma solicitação de publicação no caminho
operacional confirmado. Sem falha, cada socket saudável elegível recebe um frame;
com crash/falha, zero ou entrega parcial são possíveis. Não prometo entrega
exatamente uma vez, ACK de aplicação ou replay. As tasks pós-commit pertencem
ao componente e não são um segundo mecanismo de liquidação.

## Reconexão

- Perdi evento e socket caiu: a 4.2 reconecta e lê snapshot completo, sem reenviar comandos.
- Fiquei offline durante settlement: online abre uma tentativa deduplicada, snapshot sold/unsold torna terminal antes de ping/reconnect adicional.
- Abri settled diretamente: snapshot terminal primeiro, close 1000 depois, sem recusa ou settlement no handshake.
- Perdi frame sem falha detectada e socket permaneceu saudável: limitação de melhor esforço; futura leitura manual pura/reconexão revela resultado. Não invento polling ou SQL no heartbeat.
- Abri cancelado: recusa/404 genéricos existentes; não passa a representar unsold ou snapshot público de cancelado.

Falha viva de publicação tenta invalidar também subscribes pendentes, impedindo
que leitura capturada antes do commit deixe uma nova inscrição pending depois
da invalidação conhecida. Best-effort que também falha é logado; não certifico
recuperação imediata. Sem dados privados em logs ou fechamento de transporte.
