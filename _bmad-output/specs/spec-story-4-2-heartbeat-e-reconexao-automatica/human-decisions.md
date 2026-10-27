# Decisões humanas consolidadas — 27/10/2026

**QH-01–16 DECIDIDAS.** Este documento substitui a tabela de recomendações do draft. As decisões abaixo são minhas, fornecidas no pedido de consolidação; o histórico anterior fica na memória append-only.

| ID | Estado | Decisão vigente | Alternativa descartada / consequência |
| --- | --- | --- | --- |
| QH-01 | DECIDIDA | Ping/pong JSON de aplicação com ID correlacionado, sem dados privados nem estado de sala | Ping de controle como API JS ou heartbeat carregando snapshot; transporte separado do domínio |
| QH-02 | DECIDIDA | Ping a cada 20 s; uma pendência; pong correspondente em 10 s; servidor remove após 60 s sem atividade válida do cliente; zero SQL/snapshot por heartbeat | Cadência contada do pong descartada: são 20 s entre envios, não 20 s após resposta |
| QH-03 | DECIDIDA | 30 s totais desde criação do WS até primeiro room_snapshot | Open sem snapshot não restaura conexão nem reinicia deadline |
| QH-04 | DECIDIDA | Backoff exponencial | Atraso fixo/linear descartados |
| QH-05 | DECIDIDA | Base inicial 1 s antes do jitter | Primeira espera efetiva 0,5–1 s, não tentativa imediata em falha normal |
| QH-06 | DECIDIDA | Teto 30 s | Jitter nunca ultrapassa esse teto |
| QH-07 | DECIDIDA | Equal jitter entre 50% e 100% do exponencial limitado; RNG controlável | Sem jitter/full jitter descartados; testes determinísticos |
| QH-08 | DECIDIDA | Tentativas indefinidas enquanto elegível/montado; reset somente nova conexão + snapshot + primeiro pong válido dessa geração | Open ou snapshot isolado não zeram falhas |
| QH-09 | DECIDIDA | Offline invalida/fecha socket, cancela heartbeat/pong/retry e suspende tentativas enquanto onLine false; preserva dados | Socket autoritativo sobrevivendo offline e retry offline descartados |
| QH-10 | DECIDIDA | Online elegível produz exatamente uma tentativa imediata deduplicada | Sem rajada, sem competir com tentativa ativa, sem reset prematuro |
| QH-11 | DECIDIDA — ADIADA | Nenhum teto por lote/global nesta story; capacidade não medida | Não escolher números arbitrários; exaustão por conexões públicas permanece risco |
| QH-12 | DECIDIDA — ADIADA | Nenhum timeout novo da publicação pós-commit D-A | Deadline de transporte não limita espera por lock/limiter/SQL da publicação; 201 pode atrasar |
| QH-13 | DECIDIDA | Cancelamento explícito WS/REST terminal; REST 404 terminal genérico; transporte/1006/timeouts/rede recuperáveis; REST rede/5xx não permanente; confirmação pelo read model público existente quando necessária | Não inferir 404/cancelamento de handshake opaco; sem endpoint novo ou polling REST como reconexão |
| QH-14 | DECIDIDA | Visible recalcula deadlines; no máximo uma ação imediata; heartbeat devido envia ping, reconnect devido tenta; sem reproduzir ticks, deduplicar | Não transformar simplesmente todo H vencido em queda; P já pendente e vencido continua sendo falha conforme QH-02 |
| QH-15 | DECIDIDA | Invalidar geração antiga, retirar autoridade e chamar close; substituto pode nascer sem esperar CLOSED | Descartada barreira física CLOSED. Sobreposição TCP curta aceita, dois sockets autoritativos nunca |
| QH-16 | DECIDIDA | 10 s por operação relevante de envio/fechamento backend; isolar travado, não esperar rede sob trava de lote | Sem espera de rede ilimitada; não confundir com D-A |

## Detalhamento técnico derivado

Mensagens exatas `{"type":"ping","id":n}` e `{"type":"pong","id":n}`: n inteiro seguro positivo, sequencial por socket; geração é local e não dado privado no payload. Não imponho o teto de 128 bytes sugerido no draft, pois não foi aprovado. Validação estrutural impede eco arbitrário de payload.

Primeiro ping imediatamente após snapshot; próximo vencimento H=20 s após o envio efetivo anterior, não após pong. No retorno de suspensão, um envio atrasado ancora a próxima janela no envio atual, descartando períodos perdidos. P=10 s corre desde cada envio; pong não move H. Um timeout já consumido não pode ser desfeito por pong tardio.

Elegível = instância montada do lote atual, online e sem terminal confirmado. Phase ended não é terminal de conexão. Confirmação REST automática, quando necessária após falha sem snapshot, é única por episódio de recuperação (até próximo snapshot), coalescida com GET já em curso; não se repete a cada retry. GET manual permanece livre. Isso concretiza a proibição de polling, sem adicionar política permanente por close code.

Nenhuma decisão humana aberta para a 4.2. Ready-for-dev indica especificação pronta; **não autorizei implementação nesta sessão**. QH-11/12 são adiamentos decididos, não pendências impeditivas. Alterações futuras voltam à memória e à rederivação.
