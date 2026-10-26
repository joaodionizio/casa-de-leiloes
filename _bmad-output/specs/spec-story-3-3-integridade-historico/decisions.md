# Decisões — Story 3.3

## Herança preservada

Decidi manter P1–P20/A1–A5 da story consolidada; a numeração abaixo segue a
**story**, que separa P4 digest, P5 mensagem e P6 formato do alias.

| Origem | Contrato mantido | Alternativa descartada |
| --- | --- | --- |
| P1/P2 | Módulo único puro; tipos dedicados congelados | Package/framework, dict arbitrário, wrappers de retorno trivial |
| P3/P20 | Segredos bytes não vazios injetados, sem mínimo arbitrário | Settings, str convertido, segredo em objeto canônico |
| P4–P6 | HMAC-SHA-256 da mensagem UUID:UUID; `Licitante-` + 16 hex uppercase | Digest/concatenação diferentes; 8/12 hex; promessa de unicidade |
| P7/A1 | Alias histórico persistido na 3.4; segredos estáveis | Recalcular alias na auditoria; tabela de mapeamento; rotação transparente |
| P8/P9 | Sete campos v1; JSON ordenado/minimal UTF-8 sem newline | Campos extras, default=str, JSON HTTP, dict público |
| P10 | Instante aware convertido para UTC, seis microssegundos e Z | Assumir UTC, substituir tzinfo sem conversão, omitir fração |
| P11/P12 | Sequence >=1 sem teto artificial; centavos 1..MAX_CENTS; int sem bool | Float, coerção, teto monetário em contador |
| P13/P14 | Hashes 64 lowercase; genesis público; SHA256 só dos bytes do bid | Uppercase normalizado, salt, HMAC por linha, hash duplo |
| P15–P17 | Quatro campos na âncora v1; HMAC-SHA-256 completo; vazio 0/genesis | None, assinatura truncada, autenticar só final hash |
| P18/P19 | Geração/verificação puras; cadeia pequena; compare_digest no HMAC | ORM, auditoria integrada agora, comparação comum da assinatura |
| A2/A3 | Alias ASCII estrito; golden literals independentes | Unicode livre; expected calculado pela função testada |
| A4/A5 | Pureza e testes unitários, com precedente Pydantic transitivo | Infraestrutura no domínio; teste PostgreSQL novo por ritual |

## Detalhes técnicos fechados nesta spec

| ID | Decidi | Motivo e alternativa descartada |
| --- | --- | --- |
| D1 | Sete funções, três tipos e GENESIS_HASH, nomes em `integrity-contract.md` | APIs de domínio explícitas; descartei canonicalizer genérico de dict e hash de bytes arbitrários |
| D2 | Dataclasses `frozen=True, kw_only=True, init=False`, construtores explícitos nomeados, campos obrigatórios com sentinela privada e `**unexpected` só para recusar extras | Preciso de ValueError também para campo ausente/extra; o init gerado daria TypeError antes da validação. Descartei metaclass, decorator validador e factory genérica. `v` obrigatório aceita somente inteiro 1 |
| D3 | Invariantes no construtor; função confere tipos de objetos e argumentos soltos; timestamp armazenado em UTC | Reutilizo `require_aware`, converto por instante e traduzo overflow/offset inválido em ValueError; descartei dependência nos helpers privados de bid_rules e repetição de validadores |
| D4 | Serializer privado único, payloads explícitos na ordem lógica, `sort_keys=True`; `isoformat(timespec="microseconds")` após UTC e sufixo Z | Evito cache/campo adicional e asdict genérico; ordem lógica torna mutação de sort_keys observável pelos golden bytes |
| D5 | GENESIS_HASH único; fullmatch para alias/hash; count=0 exige genesis | Fullmatch recusa newline terminal; descartei trim/lower. Não proíbo hash zero com count positivo por alegar impossibilidade criptográfica |
| D6 | `VerifiableBid(bid, current_hash)` e tuple ordenada no verificador com lot_id explícito | Nomeia os dois dados necessários sem modelo persistente; descartei pares posicionais, lista mutável/gerador, sorting ou retorno diagnóstico complexo |
| D7 | Estrutura inválida levanta ValueError antes de mismatch; mismatch retorna bool; composição autenticada fica nos testes/consumidor futuro | Não escondo registro malformado depois de link errado; descartei função pública de auditoria completa e False indistinto para qualquer exceção |
| D8 | Novo `test_bid_integrity.py`; ampliar `test_domain_purity.py` com allowlist específica e detector já corrigido | Descartei copiar guarda e criar `test_bid_integrity_purity.py` ou framework |
| D9 | Vetores fixos com UUIDs que contêm a–f, chaves fictícias, bid de 12000 e âncoras de 1/0 lances | OpenSSL sobre bytes explícitos, conferido fora de app; descartei fixtures geradas pela implementação durante testes |
| D10 | Matriz paramétrica, spies pequenos, mutações restauradas e verify futuro; sem teste manual específico | Sem UI/endpoint; descartei testes temporais por benchmark e framework de mutation testing |
| D11 | Documentação futura de story/sprint/uso de IA; registrar sincronização de Q3/P7 e A1 | Preservo todos os documentos existentes agora; descartei correção administrativa ampla e mudança de AD |
| D12 | Sem teto artificial nos contadores e sem alterar limites globais do runtime | Inteiros enormes podem atingir limites nativos de serialização/recursos; descartei um teto de negócio inventado |
| D13 — S-01 | Autenticar o estado anterior e vinculá-lo à cadeia/lote antes de qualquer extensão; receita única no contrato §9, usando APIs existentes | Descartei verificar depois de escrever, confiar só em final_hash ou aceitar verificações isoladas sem correspondência; não crio verify_integrity_state nem outra abstração pública |
| D14 — S-02/bootstrap | Vazio exige âncora válida do próprio lote; replay de B para A retorna False; inicialização confiável persistida fica para 3.4 | Descartei confiança por ausência de assinatura, count=0 isolado ou assinatura válida de outro lote; nove golden vectors permanecem intactos |

Uso `type(x) is int/bytes/str` para os primitivos estritos; UUID/datetime via
`isinstance`. Não prometo proteção contra objetos forjados com `object.__setattr__`
ou execução Python maliciosa. Chamada posicional/duplicação de keyword continua erro
de assinatura do Python (`TypeError`), não entrada de dados aceita pelo contrato.

## Divergências reais e resolução

A revisão independente encontrou S-01 HIGH: o fluxo anterior podia usar resumo
adulterado como predecessor e emitir nova âncora válida. Corrigi o fluxo principal,
os critérios e a matriz conforme D13; não classifico isso como risco aceito de
segredo comprometido/rollback integral. Incorporei também S-02 LOW com replay
cross-lot vazio explícito (D14). Não precisei mudar APIs ou criptografia. A
inicialização confiável exigida da 3.4 fica declarada, sem decisão bloqueante nova
para o build puro da 3.3.

Não encontrei incompatibilidade bloqueante. Q3 ainda aberta em CLAUDE/arquitetura/
epics está resolvida por P7 no pedido e na story. O exemplo antigo de oito hex é
ilustrativo; a v1 aprovada usa 16. Persistir o alias do evento não cria tabela de
mapeamento. A origem ambiental operacional dos segredos não exige leitura ambiental
no primitive. A4 admite Pydantic transitivo via money.

O estado antigo descrito na spec 3.2 precede sua implementação: hoje `lot_time`
já existe e o detector de relógio resolve aliases/factories. A auditoria é **5.1**,
confirmada no título e nos critérios do `epics.md`, não inferida de texto histórico.
O POST transacional aparece na 3.4 do planejamento; descrições antigas que o
atribuem à 3.5 não alteram o escopo puro desta spec.
