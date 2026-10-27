# Critérios de aceitação e plano de testes

## 1. Critérios objetivos

Estes critérios são do **futuro build**, não resultados de execução. QH-01–16 estão decididas; valores e políticas vêm do contrato consolidado. Nenhum teste de aplicação foi executado nesta etapa.

1. **CA01 / CAP-1:** Uma montagem online cria exatamente uma tentativa; `onopen` mantém conectando/reconectando. Só primeiro `room_snapshot` válido do lote/tentativa atual permite conectado. A expira mesmo com socket OPEN sem snapshot.
2. **CA02 / CAP-1:** Cliente envia heartbeat iniciado após snapshot; no máximo um ping pendente. Primeiro ping após snapshot; seguintes 20 s após envio anterior, não após pong. Pong correto dentro de P=10 s encerra pendência; duplicado, atrasado, inválido ou de outro socket não renova saúde. Nenhum heartbeat altera sala, as_of, countdown ou privado.
3. **CA03 / CAP-1:** Ausência de pong até P dispara uma falha e recuperação; frontend não depende de receber onclose. Ausência de ping até S remove cliente backend; nenhum evento de lance é necessário para detectar silêncio.
4. **CA04 / CAP-1:** Estados, guardas e efeitos seguem T01–T25, incluindo erro sem close, close sem erro, falha do construtor, primeiro frame inválido, suspensão e eventos tardios. Ao voltar visible, H devido sem ping pendente envia um ping; P pendente vencido falha; retry devido faz uma tentativa, sempre no máximo uma ação imediata. Todo estado tem saída prevista ou terminal explícito.
5. **CA05 / CAP-2:** Backoff produz a sequência/fórmula e limites aprovados, com RNG controlável; primeira espera correta, saturação sem overflow, uma contagem por falha, reset só no marco aprovado, nenhum retry offline/terminal/disposed.
6. **CA06 / CAP-2:** Após evento perdido ou restart pós-commit, nova conexão começa por snapshot completo e converge ao estado persistido, sem replay ou reenvio de comando. Snapshot é necessário mesmo se GET já atualizou a sala.
7. **CA07 / CAP-2:** No máximo uma geração autoritativa, inclusive timeout, flapping, StrictMode e remount. Substituto pode abrir enquanto antigo está CLOSING: invalidar geração e chamar close antes. Dois intents não criam duas gerações autoritativas. Close/message/pong/retry timer antigos não alteram nova geração nem agendam reconnect.
8. **CA08 / CAP-2:** Offline inicial abre zero sockets; offline ativo fecha o atual e suspende timers. Online rápido/repetido cria uma tentativa conforme política aprovada, sem aguardar fechamento físico e sem restaurar conexão por mera conectividade do navegador.
9. **CA09 / CAP-3:** Últimos preço/histórico/fim/detalhe válidos permanecem durante falha; refresh manual continua; rede/503 no refresh mostra erro local, não apaga sala. Sucesso manual não muda status WS para conectado.
10. **CA10 / CAP-3:** GET antigo e overlay 201 N não fazem regredir snapshot N+1; sucesso do POST continua reconhecido. `shouldApplyRoom` mantém exatamente sua regra atual, inclusive empate de as_of, microssegundos, lot_id distinto e terminal; heartbeat não modifica a função.
11. **CA11 / CAP-3:** Mesmo bid_count/as_of maior é arbitrável normalmente; só as_of diferente reancora sem tempestade de `/mine`; mudanças públicas reais preservam revalidação coalescida, posição oculta enquanto pendente e conta correta. Nenhum POST duplicado nem alteração de digitação/foco por reconexão.
12. **CA12 / CAP-3:** `lot_cancelled` válido ou cancelamento REST explicitamente confirmado cancela todos os retries, fecha transporte e mantém terminal contra REST/201/online/close tardios; 404 na recuperação interrompe tentativas com texto genérico. Não inferir cancelamento/Origin de handshake recusado ou 1006.
13. **CA13 / CAP-4:** Ping válido não abre Session nem consulta PostgreSQL; snapshots/publicações mantêm threadpool e Session curta. Nenhuma leitura/heartbeat liquida ou escreve domínio, nem segura trava financeira esperando rede.
14. **CA14 / CAP-4:** Primeiro frame backend continua snapshot, mesmo com ping precoce/broadcast concorrente. Um único sender serializa snapshot/eventos/pong; fila limitada e timeout de send isolam cliente lento, com saudável recebendo e POST preservando resultado.
15. **CA15 / CAP-4:** Disconnect, silêncio, falha de send/close, fila cheia, cancelamento, shutdown e abandono durante subscribe limpam tasks/subscriber/room; após liberar eventual leitura em curso não sobra Session nem entrada sem dono. CancelledError propaga após cleanup.
16. **CA16 / CAP-4:** Toda reconexão repete política Origin da 4.1; ausência aceita, inválido/null/repetido/estrangeiro recusados. Payloads/logs não contêm dados privados; nenhum JWT na URL e nenhuma escrita WS.
17. **CA17 / CAP-1–4:** Textos de estado acessíveis, anúncio só de mudança, refresh por teclado e tela sem overflow em 320 px; cancelamento mantém foco no h1. Não redesenhar sala/Vitrine ou antecipar 4.3.
18. **CA18 / CAP-1–4:** Executar e registrar testes abaixo e verify no build; distinguir simulação de pilha real e smoke local de Render. QH-11/12 foram adiadas: documentar ausência de tetos e espera pós-commit sem limite; nenhum timeout arbitrário de publicação entra no build.

## 2. Estratégia determinística

Frontend: testes `node --test` com relógio monotônico, scheduler, socket factory e RNG controlados por adapter simples; sem biblioteca de máquina de estados ou stack nova por padrão. Asserções sobre efeitos/contadores/estado, não só função de transição espelhada. Gerar callbacks de socket antigo e callbacks de timer já cancelado de propósito. Avançar H/P/A/backoff manualmente e verificar imediatamente antes, no limite e depois. Deadline usa `>=`; resposta só é tempestiva com `<`.

Backend: relógio/watchdog injetável ou controlável nos testes e Events/Barriers para send/read/commit. Deadlines de segurança encerram teste travado; sleeps não provam ausência de evento. Não prender `receive_json` esperando “nada”: observar contador de enfileiramento/sender e checkpoints. Liberar barreiras e fechar clientes em finally, inclusive ao falhar assert.

Playwright: controlar relógio antes de iniciar aplicação e interceptar sockets para sequências de frames/close; respostas REST retidas liberadas em ordem adversa. Mock não é prova de TCP, Origin ou PostgreSQL. Teste real em dois contextos complementa interceptação. Não interpretar API interceptada respondendo em offline como acesso de rede real.

## 3. Unitários frontend

| ID | Arranjo/ação | Oráculo | CAs |
| --- | --- | --- | --- |
| F01 | Montar online, emitir open, reter snapshot até A | Conectando antes de snapshot; timeout único; snapshot válido antes de A conecta | 01,04 |
| F02 | Primeiro frame pong/bid/terminal/inválido; snapshot de outro lote | Não conecta; política de protocolo, sem aplicação indevida | 01,04,16 |
| F03 | Snapshot→ping; avançar P−ε/P/P+ε; pong certo/errado/repetido | Um pendente, limite exato, nenhum reviver após falha | 02,03 |
| F04 | Falhar sem close; depois error+close+timeout duplicados | Uma falha, um k, um timer; preserva sala | 04,05 |
| F05 | Muitas falhas com u=0, 0.5 e 1, atingir teto e índice grande | Delay dentro do intervalo aprovado, teto efetivo e sem overflow | 05 |
| F06 | Open/snapshot seguido de queda antes do pong; depois recuperação completa | k não zera cedo; zera no marco aprovado; nenhuma progressão artificial offline | 05 |
| F07 | Retry vence com antigo CLOSING; criar novo, receber snapshot; só então antigo fecha | Substituto não espera CLOSED; uma geração autoritativa; close antigo não altera status/k nem agenda retry | 07 |
| F08 | Offline inicial, offline→online→offline→online rápido; repetir online | Zero tentativa offline, deduplicação, nenhuma mensagem de socket aposentado | 08 |
| F09 | Desmontar com retry/H/P/A pendentes, disparar callbacks cancelados; montar outro lote | Zero efeitos e sockets autoritativos do lote anterior; close solicitado, timers/listeners removidos | 07,15 |
| F10 | Remontagem mesmo lote e setup→cleanup→setup de StrictMode | Cleanup invalida geração antes de close; remount pode substituir sem aguardar TCP; nenhum segundo socket autoritativo | 07,15 |
| F11 | REST manual N+1 antes do snapshot N; GET N após snapshot N+1; 201 N antigo | Conecta pelo snapshot válido sem regredir sala; GET não conecta; POST reconhecido sem overlay antigo | 09,10 |
| F12 | Matriz existente shouldApplyRoom + heartbeat/reconnect ao redor | Mesmos outputs: menor descarta, maior aplica, igual as_of >= aplica em microssegundos; lot_id/terminal bloqueiam | 10 |
| F13 | Snapshot igual salvo as_of maior; depois phase/mínimo diferentes | Reancora primeiro sem nova chamada privada; segundo segue revalidação normal | 11 |
| F14 | Terminal válido com intenção retry; terminal de socket aposentado; REST 404 posterior | Válido para tudo; aposentado ignorado; 404 terminal genérico; callbacks não ressuscitam | 12 |
| F15 | Falha de handshake + GET 404/rede/503; close codes de transporte e terminal REST | No máximo uma confirmação por episódio, coalescida; rede/503 continuam retry WS sem repetir REST; 404 terminal; sem inferir Origin | 12,16 |
| F16 | Visible após H devido sem pendência; após P pendente vencido; após retry devido; disparar timers atrasados e visibility juntos | Respectivamente um ping com P normal, uma falha, uma tentativa; zero rajada e nenhuma segunda ação imediata | 03,04 |
| F17 | Nova geração connected; emitir message e pong do socket antigo, inclusive mesmo id de ping atual | Nenhuma alteração de sala/as_of/âncora; P atual continua; k não reseta | 02,07,10 |
| F18 | Criar geração nova por online; executar callback do retry antigo já cancelado | Zero sockets adicionais, zero mudança de k/status/dados | 05,07,08 |
| F19 | Snapshot novo recebido, nunca responder pong; depois recuperar com snapshot+pong válido | Connected após snapshot, k preservado até P expirar; uma falha e backoff crescente; só snapshot+pong da recuperação seguinte zera k | 01,02,05 |
| F20 | Ping em t=0, pong em t=9 s; avançar para t=20 s | Segundo ping em t=20, não t=29; pong não desloca H; uma pendência no máximo | 02 |

## 4. Backend WebSocket e PostgreSQL real

| ID | Arranjo/ação | Oráculo | CAs |
| --- | --- | --- | --- |
| B01 | WebSocket aceito, ping recebido assim que abre, publicação retida/liberada | Snapshot primeiro, pong correlacionado depois, sender único e ordem não regressiva | 14 |
| B02 | Enviar JSON exato, extra, boolean id, float, id negativo, oversized, binário e mensagem de lance | Contrato/códigos aprovados; sem serviço financeiro; pong sem dado de domínio | 02,16 |
| B03 | Cliente nunca envia ping; avançar S até limite com saudável ativo | Silencioso removido/fechado, saudável permanece, tasks encerradas | 03,15 |
| B04 | Cliente envia ping mas não drena send; bloquear sender, encher fila | E/fila isolam só lento, fila nunca cresce além do limite, broadcast saudável progride | 14,15 |
| B05 | Após snapshot, contar SQL/sessões em vários ciclos heartbeat | Zero SQL/Session adicional; controle positivo de reconexão faz leitura em worker | 13 |
| B06 | Disconnect, close travado, CancelledError, shutdown e abandono no subscribe | Finalizadores idempotentes; liberar barreira de leitura, sem room/subscriber/task/Session restante | 15 |
| B07 | Origin válido/ausente/hostil/null/repetido/malformado em primeira e nova tentativa | Mesma política antes de accept/leitura; URL/logs públicos apenas | 16 |
| PG01 | Commit real bloqueado por barreira; abortar transporte após commit antes do broadcast, reconectar | Outra Session vê escrita; snapshot novo recupera preço/count/fim/histórico; nenhum POST extra | 06,13 |
| PG02 | Desconectar A, aceitar lances REST alternados em B/C, conectar A de novo | Snapshot com estado final/janela completa até 50 e count total; não replay de estados intermediários | 06,10 |
| PG03 | Desconectar visitante, cancelar lote sem lances, reconectar | Handshake recusado, REST 404 genérico, nenhuma revelação privada; não snapshot inventado | 12,16 |
| PG04 | Handshake concorrente com publicação e limites de tempo; rollback/recusa/commit falho | Primeiro snapshot ordenado; só pós-commit publica; leituras puras/threadpool, sem mudança financeira | 13,14 |
| PG05 | Banco lento mantendo coordenação de leitura, abandonar socket | Transporte sinaliza parada; ao liberar leitura não cria assinante órfão; D-A permanece sem SLA, conforme adiamento aprovado | 15,18 |

PG01–05 usam PostgreSQL real em banco de teste dedicado, nunca SQLite nem desenvolvimento. Nenhuma nova liquidação/catch-up. Para restart real, reiniciar servidor mantendo o banco de teste e conectar novamente; distinguir essa prova da injeção de falha pós-commit no TestClient. `TestClient`/ASGI prova contrato; não prova proxy Vite/TCP/wss.

QH-11/12 adiadas por decisão humana: não implementar nem testar tetos novos ou timeout da publicação nesta story. Preservar testes da publicação pós-commit da 4.1; B04 prova E somente no transporte, PG05 explicita a limitação do SQL em andamento.

## 5. Playwright

| ID | Roteiro controlado | Oráculo | CAs |
| --- | --- | --- | --- |
| E01 | Open sem snapshot, snapshot, queda, backoff, open, snapshot | Textos conectando/conectada/reconectando em sequência; conectado nunca cedo | 01,05,17 |
| E02 | Cair com sala exibida e texto digitado; GET 503, depois GET atual; conectar WS | Dados/foco/digitação preservados; aviso local; leitura manual não afirma WS saudável | 09,11 |
| E03 | Segurar GET antigo e 201 N, entregar snapshot N+1, liberar respostas | Nenhuma regressão de preço/histórico/fim, confirmação REST preservada, um POST | 10 |
| E04 | Offline→online rápido/repetido e perda de pong sem evento offline | Um novo socket sem aguardar fechamento físico; reconexão automática e dados preservados | 03,07,08 |
| E05 | Navegar lote A→B com retry agendado; Back/remount; emitir callbacks antigos | Nenhum callback/timer A altera B; no máximo um autoritativo, overlap físico tolerado | 07,15 |
| E06 | Terminal durante tentativa e 404 após cancelamento desconectado | Sem reconnect depois; texto genérico no 404, foco h1 no cancelado conhecido | 12,17 |
| E07 | Só as_of novo vs alteração pública real, visitante/leiloeiro/BIDDER | Sem chamadas privadas inúteis, pending sem erro falso, posição coerente por conta | 11,16 |
| E08 | 320/375/desktop, teclado e status acessível durante falhas | Sem overflow, refresh funcional, texto além de cor, nenhum anúncio por pong | 17 |

Atualizar apenas expectativas da 4.1 incompatíveis com nova autorização (antes exigiam zero reconnect após online). Preservar testes de perda/refresh/terminal/arbitragem; não apagar garantias para a suíte passar. Manter `VERIFY_E2E=1` opt-in e `E2E_REAL_BASE_URL` separado.

## 6. Roteiro manual em dois contextos reais

1. Usar backend real e banco isolado autorizado, mesma origem via Vite; abrir dois contextos independentes A e B no mesmo lote elegível. A pode observar; B como BIDDER com saldo. Confirmar snapshot primeiro e ping/pong sem dados privados.
2. Isolar rede de A; conferir texto e preço/histórico preservados. Tentar refresh e confirmar falha local. B faz lance REST válido; registrar 201 e estado persistido.
3. Restaurar A; observar uma nova geração autoritativa local, indicador só conectado após snapshot, count/preço/fim/histórico convergindo sem refresh manual. Conferir ausência de POST de A. Socket antigo pode permanecer fisicamente em fechamento, mas seus callbacks não têm autoridade.
4. Cortar apenas retorno/heartbeat sem evento offline (proxy/harness local de falha); conferir detecção P. Repetir offline→online rápido, depois navegar para outro lote durante espera e verificar que A antigo não reabre.
5. Em lote separado sem lances, usar B como dono/leiloeiro e cancelar enquanto A está desconectado. A recebe indisponibilidade/404 genérico e para tentativas; cancelar com A conectado mostra terminal explícito. Não confundir os dois resultados.
6. Reiniciar o servidor de teste preservando o banco; recuperar A/B por snapshot. Observar DevTools WS, timers por instrumentação de teste e ausência de logs privados; fechamento de ambas limpa manager.
7. Conferir teclado/foco, viewport 320 px e retomada após suspensão da aba. Registrar observado/não observado por caso. Wss/Render requer smoke separado na versão publicada; prova local não vale como deploy/smoke público.

## 7. Evidência de build futura

Após implementar e executar focados: `./verify.sh`; Playwright opt-in conforme autorização do build e fluxo do projeto; smoke de pilha real separado. Registrar comando, exit code, resultados e limitações reais. Nesta spec não rodei pytest, npm test, Playwright, banco, verify ou deploy.
