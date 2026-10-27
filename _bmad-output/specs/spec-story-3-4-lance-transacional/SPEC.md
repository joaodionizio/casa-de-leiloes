---
id: SPEC-story-3-4-lance-transacional
companions:
  - decisions.md
  - current-state.md
  - database-schema.md
  - config-secrets.md
  - transaction-contract.md
  - concurrency-analysis.md
  - http-contract.md
  - seed-and-lot-creation.md
  - test-plan.md
  - implementation-map.md
  - ../../implementation-artifacts/3-4-lance-transacional-com-travas-e-anti-sniping.md
  - ../spec-story-3-3-integridade-historico/integrity-contract.md
  - ../spec-story-3-2-regras-aceitacao-lance/domain-contract.md
  - ../../../docs/ARQUITETURA.md
sources: []
---

> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

> **Contrato canônico.** Este SPEC e os `companions:` são o contrato completo para
> construir, testar e validar a Story 3.4. A story consolidada continua companion
> (P1–P9 e critérios CA1–CA14 vinculantes). Nada foi implementado.

# Story 3.4 — Lance transacional com travas e anti-sniping

## Why

Preciso que um lance aceito seja uma única transação PostgreSQL que reserve o saldo do
novo líder, devolva o do anterior, aplique o anti-sniping e estenda a cadeia
autenticada (AD-7, AD-13), sem estado intermediário visível, mesmo com lances
simultâneos. Sem isso, o desafio falha no requisito central (consistência sob
concorrência) e a auditoria da 5.1 não teria o que verificar. A 3.2 e a 3.3
entregaram regras e primitives puros; esta story os integra sob a trava do lote, com
a hora do banco e com o gate que impede assinar estado adulterado (S-01).

## Capabilities

- **CAP-1**
  - **intent:** O licitante tem o lance aceito registrado como uma unidade atômica: lance, carteiras, líder, lance atual, `ends_at`, sequência, `bid_count`, `final_hash` e HMAC.
  - **success:** Depois do 201, todos os efeitos estão confirmados juntos (T-OUTBID, T-CHAIN); falha injetada depois de cada statement real e no commit deixa `lots`, `bids` e `wallets` idênticos (T-ATOM).
- **CAP-2**
  - **intent:** O sistema recusa estender um histórico que não se autentica, antes de qualquer efeito.
  - **success:** Cada adulteração G1–G17, G19–G23, G9b, G10b e G11b resulta em 409 `lot_integrity_conflict` com corpo idêntico, zero efeitos e nenhuma HMAC nova, inclusive onde a regra pura daria 422 (G9b–G11b, sem travar carteira); G18 resulta em 500 (T-GATE); a ordem gate → pré-carteira é observada em T-REUSE.
- **CAP-3**
  - **intent:** Lances simultâneos, no mesmo lote ou em lotes com carteiras cruzadas, terminam no resultado de alguma ordem serial, sem deadlock no protocolo.
  - **success:** T-CONC-2, T-CONC-N (5 rodadas), T-DEADLOCK e T-DEPOSIT passam em PostgreSQL real com I1–I6; o controle negativo de travas por papel produz SQLSTATE 40P01.
- **CAP-4**
  - **intent:** As regras da 3.2 e o anti-sniping decidem com um único instante do PostgreSQL lido depois da trava do lote.
  - **success:** Recorder mostra `FOR UPDATE` do lote antes do único `clock_timestamp()`; o `placed_at` gravado é o mesmo instante devolvido por `database_now`, e o `CanonicalBid` reconstruído dele reproduz o hash gravado; a resposta HTTP traz o mesmo instante (comparação semântica); extensão = `ends_at` lido + 2 min exatos; B concorrente observa o fim estendido por A (T-CLOCK, T-SNIPE).
- **CAP-5**
  - **intent:** Só o `BIDDER` dá lance por `POST /api/lots/{lot_id}/bids`, recebendo aceite ou o motivo exato.
  - **success:** Status e corpos de `http-contract.md` §3 conferidos (T-ROLE e recusas); OpenAPI com campos exatos e sem `bidder_id`, hashes ou HMAC.
- **CAP-6**
  - **intent:** Todo lote novo nasce autenticado e todo lote legado continua bloqueado para lance.
  - **success:** `POST /api/lots` e o seed gravam âncora vazia válida do próprio id na mesma transação; legado responde 409; seed repetido não duplica demo nem assina legado (T-INIT, T-MIG).
- **CAP-7**
  - **intent:** A aplicação só inicia com segredos de integridade válidos e nunca os expõe.
  - **success:** T-SECRETS: ausente, curto em bytes, iguais entre si ou iguais ao `JWT_SECRET` impedem a inicialização sem ecoar valor; seed só exige `AUDIT_HMAC_SECRET`; nenhum segredo em log, resposta ou `repr`.

## Constraints

- AD-1 a AD-30 e P1–P9 da story vinculantes; `decisions.md` §1. Regras só de `bid_rules`; alias, bytes, hash e HMAC só de `bid_integrity` (ambos intocados); hora só de `database_now`; trava de carteira só de `lock_wallet` (CA13).
- Ordem: trava do lote → hora → gate → pré-carteira → carteiras em `user_id` crescente → saldo → efeitos. Gate com a receita §9 da 3.3 mais o vínculo operacional P2 (`transaction-contract.md` §3).
- Nenhuma regra de negócio roda antes do gate: lote adulterado ou legado responde 409 antes de qualquer 422 (P1, D15).
- Fisicamente: `UPDATE wallets`, `INSERT bids`, **um** `UPDATE lots` final e coerente (lance atual, líder, `bid_count`, `final_hash`, `anchor_hmac`; `ends_at` só com extensão); nenhuma mutação do `Lot` antes disso (D1; CHECK não é adiável).
- Data canônica sempre com seis casas e `Z`; data HTTP é o instante ISO 8601 do serializer, sem contrato de casas (D16).
- `READ COMMITTED`; trava do lote sem `JOIN`; toda escrita em `bids` e no estado de lance passa pela trava do lote (`current-state.md` §4).
- `sequence = bid_count` autenticado + 1; nunca `MAX(sequence) + 1`.
- Migration `0005` aditiva, sem segredo, sem backfill assinado; schema exato em `database-schema.md`.
- Nenhum caminho (lance, boot, seed, migration) assina estado encontrado no banco.
- 422 para recusa de negócio, 409 genérico para integridade, 500 para violação interna; nunca converter erro de banco em recusa.
- Sem retry, sem hook de falha em produção, sem nova stack de observabilidade.
- Git, `.env*` e decisões são do dono do projeto; código em inglês, mensagens e documentos em português.

## Non-goals

- Interface da sala, endpoint de "meu pseudônimo", lance atual na vitrine (3.5).
- Cancelamento (3.6); WebSocket, eventos, snapshot (4.1/4.2); fechamento, liquidação, `receipts`, scheduler, catch-up, "fechar antes de responder" (4.3/4.4, Q9).
- Auditoria pública (5.1), comprovante e meus arremates (5.2/5.3), estorno (6.6).
- Comando de autenticação de lotes legados; idempotência por chave; outbox; retry; rotação de segredos.
- Mudar regras da 3.2 ou bytes, tipos e golden vectors da 3.3.

## Success signal

Em PostgreSQL real, a matriz de `test-plan.md` §2 (22 cenários) e os 26 casos de
T-GATE (G1–G23, G9b, G10b, G11b) passam; cada mutação M-1..M-26 é morta pelo teste
indicado e restaurada; e
`./verify.sh` termina com exit 0, com saída real registrada na story. Um lote criado
depois da 3.4 recebe N lances concorrentes e termina com cadeia 1..N e âncora válida;
um lote adulterado recusa o próximo lance sem mudar nada.

## Assumptions

- O banco de produção pode ter lotes manuais e demo anteriores à 3.4 (não confirmado).
- Escala do desafio: leitura O(n) da cadeia e fila na trava são aceitáveis; sem `statement_timeout`.

## Open Questions

Nenhuma. As três questões da spec estão resolvidas (`decisions.md` §4):

- Q-1 (resolvida): `backend/.env.example` é editado manualmente pelo dono do projeto;
  agentes não o leem, não o editam e não param o build por ele.
- Q-2 (resolvida por SR-09): troca de segredo documentada no README, sem mitigação.
- Q-3 (resolvida): substituição de IC-1 confirmada; sem teste real de "+4 min".

## Mapa da estrutura pedida

| Seção pedida | Onde |
| --- | --- |
| 1 resumo · 2 non-goals | Este arquivo |
| 3 estado atual | `current-state.md` |
| 4 schema/migration | `database-schema.md` |
| 5 config/segredos | `config-secrets.md` |
| 6 tipos · 7 algoritmo · 8 gate · 12 falhas | `transaction-contract.md` §1, §2, §3, §7–§9 |
| 9 travas/deadlock + autorrevisões | `concurrency-analysis.md` |
| 10 HTTP | `http-contract.md` |
| 11 seed/criação | `seed-and-lot-creation.md` |
| 13 matriz PostgreSQL · 14 unitários · 15 mutações | `test-plan.md` §2–§6 |
| 16 docs · 17 mapa por arquivo · 18 rastreabilidade · 19 riscos · 20 checklist | `implementation-map.md` |
| Decisões, incompatibilidades, questões, review adversarial final (SR-01..SR-09) | `decisions.md` §2, §3, §3a, §4 |
| Obrigações futuras (sem escopo na 3.4) | `current-state.md` §5 |
