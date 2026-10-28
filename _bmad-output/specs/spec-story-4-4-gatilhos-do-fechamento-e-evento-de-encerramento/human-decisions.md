# Decisões humanas consolidadas — Story 4.4

Recebi decisão explícita para QH-01–16 em 27/10/2026. Todas estão **DECIDIDAS**;
nenhuma recomendação anterior sobrevive como escolha aberta. Os contratos
normativos foram rederivados da memória append-only e dessas respostas.
Ready-for-dev foi aplicado depois da revalidação em 28/10/2026, sem autorizar código.

## QH-01 — Cadência — DECIDIDA

Decidi run_cycle → espera interrompível 2 s → run_cycle. Sem timer fixo que
sobreponha execução. Backoff operacional 2–30 s pode elevar a espera após falha.
Descartei cadência 1 s/5 s e recuperação de ticks perdidos.

## QH-02 — Catch-up — DECIDIDA

Decidi catch-up imediato no lifespan **depois** de migrations/seed existentes e
antes do tráfego, pelo mesmo mecanismo de processamento. Não movo seed para
depois do catch-up. Descartei primeiro ciclo somente após atender tráfego e
reimplementação paralela de settlement.

## QH-03 — Ciclo ativo — DECIDIDA

Decidi guard local por processo com SKIP, sem fila/overlap deliberado. A
idempotência PostgreSQL continua última defesa. Descartei aguardar ciclos
acumulados e usar a segurança da 4.3 como justificativa para overlap.

## QH-04 — Evento — DECIDIDA

Decidi lot_closed com exatamente type,lot_id,outcome,winner_alias nullable,
final_amount_cents nullable,bid_count,final_hash,settled_at,as_of. As_of copia
settled_at persistido, sem nova decisão temporal; unsold alias/preço null.
Descartei evento sem as_of, outro nome e serialização de identidade privada,
wallet, HMAC/segredos ou receipt interno.

## QH-05 — Conectado após terminal — DECIDIDA

Decidi confirmar settlement → publicar lot_closed → permitir drenagem →
close 1000. Cliente terminal não reconecta nem inicia heartbeat. Descartei
manter conexão terminal indefinidamente e fechar antes de drenar, preservando 4.1.

## QH-06 — Nova conexão settled — DECIDIDA

Decidi ler persistido → room_snapshot terminal → close 1000, sem settlement no
handshake. Descartei recusar antes de fornecer resultado e manter socket aberto.
Cancelado continua com semântica própria já existente.

## QH-07 — Commit confirmado com publish perdido — DECIDIDA

Decidi banco autoritativo e snapshot/reconnect como recuperação primária. Falha
viva registra erro, tenta terminalizar/invalidar sala e close best-effort para
reconexão. Descartei outbox, desfazer/refazer settlement ou rollback financeiro
por falha de transporte. Invalidar não equivale a entregar terminal ao cliente.

## QH-08 — already_settled — DECIDIDA

Decidi zero republicação automática: resultado já existe, snapshot converge e
QH-07/12 tratam falha viva. Descartei broadcast por toda observação de settlement
ou redescoberta de settled para replay.

## QH-09 — Financeiro permanente/teto — DECIDIDA

Decidi log de erro operacional e cooldown local em memória 300 s, sem evento,
bypass do teto ou regra financeira nova. Restart pode tentar novamente. Lote
problemático não impede os demais. Descartei retry quente e quarentena durável.

## QH-10 — Integridade inválida — DECIDIDA

Decidi zero settlement novo/evento/reparo, log claro e cooldown local 300 s.
Descartei consertar/reassinar histórico ou bloquear outros lotes.

## QH-11 — Batch e justiça — DECIDIDA

Decidi no máximo 200 linhas candidatas consultadas e 50 tentativas efetivas por
ciclo, ordem/cursor (ends_at,id), wrap ao fim e cooldowns considerados. A query
não substitui settle_lot. Descartei scan ilimitado e voltar sempre aos mesmos
lotes falhos. Páginas de até 50 são detalhamento da mesma política, sem budget
arbitrário 5 s para encerrar transação/ciclo.

## QH-12 — Falha WS — DECIDIDA

Decidi preservar settlement, logar, tentar terminalizar/invalidar manager e
fechar conexões afetadas de modo recuperável para snapshot no reconnect. Slow
client segue isolado. Descartei retry periódico de lot_closed, fila persistente
ou outbox. Tasks pós-commit são possuídas/supervisionadas, nunca retry solto.

## QH-13 — Integração startup/seed — DECIDIDA

Decidi preservar migrations/seed externos ao lifespan: migrations → seed →
catch-up lifespan → scheduler → tráfego. Falha individual de integridade/teto
é isolada/cooldown e não derruba startup por si só; falha sistêmica que impede
catch-up confiável pode impedir startup com log. Descartei mover ou repetir seed,
preflight alternativo e tratar lote problemático como falha global.

## QH-14 — POST vencido — DECIDIDA

Decidi manter somente recusa de domínio existente, sem segunda transação de
settle_lot ou evento por requisição. Settlement operacional exclusivo de
catch-up/scheduler. Descartei acoplar recusa de lance ao fechamento e todos os
novos códigos HTTP de settlement antes propostos. Não altero a regra de bidding.

## QH-15 — Snapshot/cliente — DECIDIDA

Decidi estender contrato compartilhado REST/WS apenas com representação de
settlement, separado de phase; pending/sold/unsold e cancelado pela semântica
existente. Cliente reconhece sold/unsold como terminal antes de heartbeat/
reconnect e usa snapshot como autoridade, sem calcular settlement. Descartei
nova tela/UX de resultado, painel 4.5 e endpoint/protocolo versionado adicional.

## QH-16 — Limites e shutdown — DECIDIDA

Decidi preservar send/close 10 s da 4.2, limites DB existentes e ausência de hard
timeout perigoso em settle_lot. Shutdown impede ciclos, cancela sleep, acompanha
workers e fecha recursos corretamente com janela global de drenagem até 30 s;
excesso gera erro operacional claro. Descartei timeout 2 s de enqueue/isolamento,
connect/pool/statement/lock novos e abandonar thread por prazo local. Tempo/
erro de comunicação não prova rollback; COMMIT ambíguo usa idempotência 4.3.

## Histórico superado, sem força normativa

A memória mantém integralmente as entradas do draft, sem editar/reordenar.
Registro aqui as mudanças que afetam a leitura das fontes anteriores:

| Tema | Direção anterior superada | Decisão humana vigente |
| --- | --- | --- |
| Q4/AD-19 e QH-02/13 | Catch-up antes do seed, mover seed para lifespan ou preflight | Preservar seed anterior ao lifespan/catch-up |
| Q9/AD-19 e QH-14 | POST vencido → rollback → comando em transação própria | POST apenas recusa, settlement só operacional |
| CAP-6 | Capacidade de recuperação pelo POST vencido | Aposentada, ID não reutilizado; ausência de efeito virou constraint/CA11/T31/T32 |
| QH-04 | Terminal sem as_of | Campo obrigatório derivado de settled_at |
| QH-16 | Enqueue/isolamento 2 s, limites DB5 s/2 s e budget de ciclo 5 s | Preservar deadlines/limites existentes; drenagem global 30 s com erro se exceder |
| Publicação A/B/C/D do draft | A: replay already_settled; B: marcador persistido; C: só snapshot; D: snapshot + invalidação viva | Decidi D sem replay/marcador/outbox; C permanece recuperação primária |
| Cooldown e lotes permanentes | Quarentena ou tentar todo ciclo | Decidi estado local 300 s, reconstruível após restart |

Atualizei primeiro AD-19/Q4/Q9 em ARQUITETURA por essa decisão humana explícita,
depois resumos CLAUDE/épico/README e spec, sem mudar código nem stories anteriores.
Nenhuma questão humana aberta. Após revalidação em 28/10/2026, story/sprint
ficaram ready-for-dev; build continua exigindo autorização separada.
