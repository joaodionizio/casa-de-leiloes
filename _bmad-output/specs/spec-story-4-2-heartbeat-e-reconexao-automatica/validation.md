# Autovalidação final — consolidação de 27/10/2026

Autovalidação da skill, não review independente nem execução de aplicação. QH-01–16 estão decididas; SPEC/story/sprint ficam ready-for-dev por instrução humana, sem autorização de código nesta sessão.

## Passagem 1 — Coerência

Preservei CAP-1–4 com intent/success, constraints, exclusões e sinal demonstrável. Reavaliei T01–T25: retirei barreira CLOSED, estado closing e permanent inferido de transporte; online cancela retry e abre uma vez; callbacks/timers antigos são inertes por geração. Connected depende de snapshot; reset de k depende ainda de pong da mesma geração.

Cadência corrigida para 20 s entre envios; pong não desloca H. Visible não faz replay: H devido sem pendência envia um ping; P pendente vencido falha sem substituir pendência; retry devido tenta uma vez. Prioridades e tokens deduplicam callback de timer e visibilidade. Snapshot/GET/201 continuam sujeitos exclusivamente à arbitragem existente.

Cancelamento REST explícito e 404 têm terminais distintos; read model público atual só permite 404 genérico. Confirmação REST automática é uma por episódio e não por tentativa, sem polling. Códigos opacos não encerram recuperação por inferência. Tetos e D-A são adiados decididos, sem condicionais pendentes no plano de build.

**Veredito: coerente e pronta para desenvolvimento documentalmente.** Não promete duas conexões físicas impossíveis: aceita overlap curto, proíbe duas autoridades. Não promete deadline de SQL por E de transporte.

## Passagem 2 — Preservação

| Requisito consolidado | Contrato / prova planejada |
| --- | --- |
| QH-01/02 heartbeat puro H/P/S | §5/7; CA02/03/13; F03/F20, B02/B03/B05 |
| QH-03 snapshot e A; reset QH-08 | T03–07; CA01/05; F01/F06/F19 |
| QH-04–07 backoff/jitter | §2; CA05; F05/F06 |
| QH-09/10 offline/online | T12–15; CA08; F08/F18/E04 |
| QH-11/12 adiadas | §7/9; CA18; PG05; arquitetura/CLAUDE |
| QH-13 terminal e REST sem polling | T17–19, §6; CA12; F14/F15/PG03/E06 |
| QH-14 suspensão | T23 e prioridade §5; CA04; F16 |
| QH-15 geração | §2, T11/T25; CA07; F07/F10/F17/F18 |
| QH-16 send travado isolado | §7; CA14/15; B04/B06 com saudável concorrente |
| Perda de eventos recuperada por snapshot | §8; CA06; PG01/02 e manual |
| GET/201 antigo e shouldApplyRoom intacto | T04/T19, §8; CA10/11; F11–13/E03 |
| Teardown e cancelamento durante retry | T17/18/22/24; CA12/15; F09/F14/E05/E06 |
| Privacidade, Origin, AD-10/25, exclusões | §1/7/9; CA13/16/17; B05/B07 |

**Veredito: decisões e requisitos preservados**, inclusive alterações explícitas sobre as recomendações do draft. Nenhuma questão humana aberta; nenhuma implementação iniciada.

## Verificação documental e limites

Conferir links/companions, unicidade de IDs, valores H/P/S/A/B/C/E, ausência de políticas superadas e chave ASCII única no sprint. Memória conserva histórico anterior como supersedido, não como contrato vigente. Invólucro do anexo e comando da skill são wrapper-only; proibições de Git/.env/código/4.3 permanecem registradas.

Não executei testes de aplicação, banco, verify, smoke ou deploy. Testes listados são plano do build, não resultados. Referências técnicas já verificadas na criação não substituem a decisão humana. Revalidação não é review independente.
