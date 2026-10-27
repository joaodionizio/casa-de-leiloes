---
id: SPEC-story-4-2-heartbeat-e-reconexao-automatica
status: done
companions:
  - connection-contract.md
  - human-decisions.md
  - acceptance-and-tests.md
  - validation.md
  - ../../../docs/ARQUITETURA.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
sources: []
---

# Story 4.2 — Heartbeat e reconexão automática

Data: 27/10/2026. **Ready-for-dev; QH-01–16 decididas.** Este kernel e os companions são o contrato consolidado, derivado da memória canônica e das decisões humanas de 27/10/2026. A sessão continua somente documental; não autorizei implementação agora.

## Why

Quero que visitante, licitante e leiloeiro percebam uma conexão perdida e recuperem a sala após queda ou restart, preservando o estado confirmado e sem repetir lances. A 4.1 já entrega o transporte público; esta story acrescenta somente saúde e recuperação.

## Capabilities

- **CAP-1**
  - **intent:** Perceber se as atualizações ao vivo estão disponíveis.
  - **success:** Cada evento da tabela de transições produz o estado textual previsto; abertura sem snapshot nunca exibe conexão restabelecida (CA01–04).
- **CAP-2**
  - **intent:** Recuperar automaticamente a sala após perda de conexão.
  - **success:** Recuperação usa o snapshot completo da nova conexão, segue os parâmetros aprovados e mantém uma geração autoritativa e não duplica comandos (CA05–08).
- **CAP-3**
  - **intent:** Continuar consultando dados válidos durante a recuperação.
  - **success:** Última sala permanece visível, refresh REST continua disponível e respostas antigas não a fazem regredir nem desfazem terminal (CA09–12).
- **CAP-4**
  - **intent:** Impedir que conexões abandonadas prejudiquem os demais clientes.
  - **success:** Timeout/abandono limpam recursos, cliente lento permanece isolado e heartbeat não consulta PostgreSQL nem expõe dados privados (CA13–18).

## Constraints

- Preservo AD-10 e AD-25: um processo, manager em memória, WS de leitura, comandos REST, SQL síncrono só em threadpool/Session curta e publicação somente pós-commit.
- Preservo primeiro frame `room_snapshot`, `bid_accepted`, terminal `lot_cancelled`, janela completa de até 50 bids e `bid_count` total; não reconstruo eventos perdidos.
- Não altero `shouldApplyRoom`: contagem primária, `as_of` apenas desempate, precisão de microssegundos e terminal prevalente; preservo `sameRoomState` e a coordenação privada da 4.1.
- Sala pública; JWT fora da URL; Origin presente igual à APP_ORIGIN, ausente aceito, repetido/malformado/null recusado em cada handshake. Heartbeat e logs sem dados privados.
- Estados em texto, dados válidos preservados, comandos nunca reenviados automaticamente. Parâmetros/políticas estão consolidados em human-decisions.md; nenhum valor vem de default arbitrário.

## Non-goals

- Fechamento, liquidação, scheduler, catch-up, evento de encerramento, resultado, comprovante ou início da 4.3.
- Redis, broker, outbox, vários workers, replay, exactly-once, novas migrations, mudança de regras/locks/saldos, redesign ou upgrade de stack.
- Tetos de conexões e timeout pós-commit D-A foram explicitamente adiados por QH-11/12; não entram nesta story.

## Success signal

Em dois contextos reais, interrompo o transporte de um deles, confirmo um lance no outro e restauro a conexão: o primeiro mostra perda/recuperação, recebe snapshot completo e converge ao banco sem refresh ou reenvio de POST. Cleanup e ausência de regressão são comprovados pelos testes de CA01–18.

## Assumptions

- Trato a 4.1 como concluída/aprovada conforme minha instrução atual, mais recente que os arquivos ainda em `review`. Não atribuo a essa confirmação um smoke Render ou um relatório de review não fornecido.

## Questões para decisão humana

Nenhuma aberta. QH-01–16 decididas em `human-decisions.md`: H=20 s entre envios, P=10 s, S=60 s, A=30 s, backoff exponencial base 1 s/teto 30 s/equal jitter, reset só snapshot+pong, offline suspende/online tenta uma vez, visible sem rajada, geração substituída sem aguardar CLOSED e E=10 s por send/close backend. Tetos de conexões e timeout D-A adiados explicitamente. Connected exige snapshot; shouldApplyRoom continua exclusivo para arbitragem pública.


## Registro do build — 27/10/2026

Autorizei e concluí a implementação nesta sessão posterior à especificação. As notas
anteriores de sessão somente documental permanecem como histórico; não alterei
QH-01–16. Implementação e gates concluídos, Story 4.2 em review para teste manual e
code review posterior. Evidências reais, rastreabilidade F/B/PG/E, arquivos e limites
em [implementation-evidence.md](implementation-evidence.md).
