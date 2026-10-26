# Plano de testes — Story 3.3

Decidi `backend/tests/test_bid_integrity.py` para os testes funcionais e ampliação
de `backend/tests/test_domain_purity.py` para pureza. Nenhum teste novo em
`tests/integration/`. Os testes abaixo são futuros, não executados nesta sessão.
Uso pytest/parametrize, UUIDs/datas fixos e literais G1–G9; sem relógio, rede ou RNG.

## 1. Matriz de entradas e construtores (CAP-1/2/3/5)

| Grupo/teste | Casos e resultado obrigatório |
| --- | --- |
| `test_exact_fields_and_frozen_types` | dataclasses.fields coincide exatamente com as três listas do contrato; atribuição -> FrozenInstanceError; nenhuma mutação das entradas depois de função |
| `test_missing_and_extra_fields` | Omitir cada campo, inclusive v; passar campo extra como user_id/current_hash no CanonicalBid -> ValueError; nenhum campo silenciosamente ignorado |
| `test_keyword_only_construction` | Construção posicional -> TypeError de assinatura Python; não confundir com validação dos dados |
| `test_v1_only` | Nos dois tipos v=1 aceita; 0, 2, -1, True, False, 1.0, "1", None -> ValueError |
| `test_uuid_types` | Em alias, tipos e verificador: str(uuid), int, None -> ValueError; dois objetos UUID iguais mas não idênticos são equivalentes |
| `test_sequence` | 1 válido; 0/-1/True/False/float/string/None inválidos; MAX_CENTS+1 e 2**100 válidos (sem teto artificial) |
| `test_amount_cents` | 1/MAX_CENTS válidos; 0/-1/MAX_CENTS+1/True/False/1.0/1.5/string/None inválidos |
| `test_bid_count` | 0/1/MAX_CENTS+1/2**100 válidos; negativo/bool/float/string/None inválidos; count=0 com hash não-genesis -> ValueError |
| `test_strict_alias` | G3 válido; prefixo/case errado, sufixo 8/15/17, lowercase, g, whitespace, newline terminal, controle, Unicode/confusável, vazio, bytes e None -> ValueError |
| `test_strict_hashes` | previous/current/final/signature: 64 lowercase válidos; 63/65, maiúsculas contendo A–F, g, espaços/newline, bytes, None -> ValueError. Não usar só zeros para provar rejeição uppercase |
| `test_secrets` | Nas duas funções que recebem audit secret e em alias: vazio, str, bytearray, memoryview, None -> ValueError; bytes de comprimento 1 válidos |
| `test_foreign_objects` | dict/SimpleNamespace/None em cada parâmetro dedicado -> ValueError; tuple com elemento inválido -> ValueError; lista/gerador/string/None em records -> ValueError |
| `test_error_messages_do_not_echo_data` | Marcador fictício em alias/secret inválido não aparece na mensagem; mensagens citam campo/regra, nunca valores |

Não testar arquivos de configuração com segredos reais. IDs/alias são dados
históricos; não introduzir constraint de unicidade artificial.

## 2. Pseudônimo (CAP-1)

- `test_pseudonym_golden`: G1, G2 e G3 literais. Spy pequeno em hmac.new captura
  chave, mensagem, digest e hexdigest completo, delegando ao original. Testar o
  resultado público G3 também; não comparar só um mock com outro mock.
- `test_pseudonym_deterministic`: chamadas repetidas, UUIDs distintos de mesmo
  valor, UUID construído de texto uppercase -> G3.
- `test_pseudonym_changes_for_selected_inputs`: alterar somente lote, usuário ou
  chave usando as fixtures de golden-vectors -> alias diferente nos casos escolhidos.
- `test_pseudonym_format_and_privacy`: prefixo literal, fullmatch, tamanho 26,
  nenhum UUID real em claro; assinatura da API não possui nome/e-mail.
  Não declarar anonimização absoluta nem impossibilidade de colisões.

## 3. Timestamp, bytes e hash (CAP-2)

| Teste | Prova |
| --- | --- |
| `test_canonical_bid_golden` | igualdade byte a byte com G4; tipo bytes, sete campos exatos; repetir e construir keywords em outra ordem mantém G4 |
| `test_canonical_json_contract` | inteiros JSON e UUID lowercase; ordem alfabética de chaves, sem espaços/BOM/newline; spy delegante em json.dumps confere sort_keys=True, separators=(",", ":"), ensure_ascii=False nos dois serializers |
| `test_timestamp_same_instant` | UTC e -03:00 do G4 geram os mesmos bytes; incluir +05:30 e mudança de dia: 2026-10-23 00:15:30.123456 +05:30 -> 2026-10-22T18:45:30.123456Z |
| `test_timestamp_microseconds` | 0 -> .000000Z; 1 -> .000001Z; 123456 -> .123456Z; 999999 -> .999999Z; nunca +00:00 |
| `test_timestamp_fold` | tzinfo de teste como FoldOffset da 3.2, -03 com fold=0 e -04 com fold=1; 2026-11-01 01:30 gera respectivamente 04:30:00.000000Z e 05:30:00.000000Z, bytes/hashes distintos |
| `test_timestamp_rejects_invalid` | naive, date sem hora, str, None, tzinfo.utcoffset()=None -> ValueError; offset inválido também ValueError |
| `test_timestamp_utc_extremes` | datetime.min/max em UTC serializam 0001-01-01T00:00:00.000000Z / 9999-12-31T23:59:59.999999Z; min com +01:00 e max com -01:00 -> ValueError, sem overflow escapando; min às 01:00 +01:00 e max às 22:59:59.999999 -01:00 válidos |
| `test_bid_hash_golden` | compute_bid_hash do bid fixo == G5 literal; nunca expected=hash da função testada |
| `test_bid_hash_changes_with_each_field` | alterar isoladamente amount, alias válido, timestamp 1µs, previous_hash válido, sequence, lot_id -> diferente nos vetores; v diferente é rejeitado |
| `test_hash_format_and_genesis` | SHA/HMAC 64 hex lowercase; GENESIS_HASH literal de 64 zeros, length 64, set={'0'}, fullmatch; hash de bid não usa segredo |

Não aceitar alias Unicode só para diferenciar ensure_ascii; o spy prova a opção
que é invisível nos bytes de entradas v1 válidas. A ordem lógica de montagem do
payload é diferente da ordem alfabética, tornando sort_keys observável.

## 4. Âncora (CAP-3)

- `test_anchor_golden`: bytes G6 e HMAC G7; repetir mantém ambos.
- `test_empty_anchor_golden`: G8/G9; zero lances usa genesis, nunca None nem HMAC zero.
- `test_anchor_changes_with_each_input`: mudar isoladamente lot_id, count de 1
  para 2, final_hash válido ou secret -> HMAC diferente nos casos escolhidos.
- `test_verify_anchor_hmac`: correto True, assinatura bem formada alterada False,
  segredo errado não vazio False; validar formatos conforme §1.
- `test_verify_uses_compare_digest`: spy delega ao compare_digest real; correto,
  alterado e chave errada passam por ele com duas strings lowercase de 64 hex e
  retornam o esperado. A mutação para == deve derrubar esse teste.
- Estado tipo inválido, assinatura inválida e segredo inválido são recusados
  antes da comparação; nenhuma assinatura ausente autentica o vazio.

## 5. Cadeia e composição autenticada (CAP-4)

Construir fixtures de 0, 1, 2 e 3 registros, mesmo lote, sequence 1..n, previous
correto e datas fixas. O primeiro usa G4/G5; os demais podem ser compostos com os
primitives (os golden tests independentes já fixam o algoritmo). Expected de
verify_bid_chain é sempre True/False literal.

| Teste/caso | Esperado |
| --- | --- |
| tuple vazia + lot_id válido | True; resumo observado 0/genesis |
| 1, 2 e 3 registros válidos | True |
| Primeiro sequence=2; lacuna 1/3; duplicata 1/1 | False |
| Primeiro previous diferente de genesis, mas bem formado e hash correspondente | False |
| Segundo previous diferente do hash anterior, hash próprio recalculado | False |
| current_hash adulterado mas bem formado | False |
| Campo amount/alias/timestamp alterado sem atualizar hash | False |
| Registros de lote diferente ou todos de outro lote; lot_id esperado incorreto | False, mesmo com hashes recalculados |
| UUID do lote igual por valor mas objeto diferente | True |
| Ordem invertida, inserção duplicada, remoção intermediária | False, sem sorting/reparo |
| Primeiro mismatch seguido de elemento de tipo inválido | ValueError; validação estrutural completa precede relações |
| Múltiplas chamadas com a mesma tuple | Mesmo resultado; tuple e objetos inalterados |
| Alterar último amount e recalcular current_hash localmente | True de cadeia; resumo/HMAC original não autentica nova cadeia |
| Alterar primeiro e recalcular toda a cadeia | True de cadeia; composição autenticada False |
| Truncar terceiro mantendo primeiro/segundo | True de cadeia; resumo observado (2,hash2) difere de âncora original (3,hash3) |
| Truncar e também mudar estado para (2,hash2), mantendo assinatura antiga | verify_anchor_hmac False |
| Conferir só assinatura antiga contra estado antigo após truncamento | True de HMAC, mas composição False pela diferença de resumo; teste impede falso positivo |
| Restaurar conjunto antigo inteiro (cadeia, estado e HMAC válidos) | Composição pode passar; limitação documentada, não teste que exige detecção impossível |

A composição no teste confere lote pedido, verify_bid_chain, count/final_hash
observados versus estado e verify_anchor_hmac; não acrescenta helper público.
Também testar sequência vazia com âncora vazia válida -> composição True e vazia
com âncora de um lance -> False. Não recalcular alias usando user_id na verificação.
Spy que falha se generate_bidder_alias for chamado durante verificação prova isso.

### 5.1 Autenticação anterior como precondição de extensão — S-01

Decidi adicionar uma composição **local ao teste**, seguindo exatamente a receita
de integrity-contract §9. Não criar API produtiva nova ou serviço transacional.
Receber cadeia anterior, lote esperado, AnchorState anterior, assinatura anterior
e chave; avaliar os primitives e todas as igualdades antes de decidir continuar.
Somente depois de resultado True construir o próximo bid/estado e emitir o novo
HMAC. False interrompe o caminho; erro estrutural propaga ValueError.

Usar um spy/contador local no passo de **emissão da âncora nova**, delegando aos
primitives reais. A verificação do HMAC anterior já calcula um digest esperado:
não confundir essa chamada com emissão de âncora nova nem exigir zero chamadas
globais a compute_anchor_hmac. Guardar resultados emitidos em lista local; nos
ataques, exigir resultado False, zero emissões e lista vazia. A assinatura antiga
e a cadeia original são montadas antes de instalar a instrumentação desse passo.
No controle positivo, exigir True, uma emissão e HMAC nova válida para o novo
resumo correspondente. Não usar mock que substitua a verificação por True/False.

| Teste | Montagem e resultado |
| --- | --- |
| `test_extension_requires_authenticated_previous_state` | Três bids válidos, resumo correspondente e HMAC válida; composição True, quarto bid usa count+1 e final_hash autenticados, uma nova âncora emitida |
| `test_rehashed_history_cannot_be_reauthenticated_by_extension` | Partir dos três bids; alterar primeiro bid, recalcular todos os hashes e atualizar final_hash do resumo, mantendo assinatura antiga; verify_bid_chain True, verify_anchor_hmac False, composição False e zero emissões de nova âncora |
| `test_changed_previous_count_blocks_extension` | Alterar somente count de 3 para 4, manter cadeia/hash/assinatura; estado bem formado, composição False e zero emissões |
| `test_changed_previous_final_hash_blocks_extension` | Alterar somente final_hash para outro hash bem formado, manter count/cadeia/assinatura; False e zero emissões |
| `test_valid_hmac_and_valid_chain_require_matching_summary` | Cadeia recalculada e internamente válida, mas manter resumo e HMAC antigos válidos; ambos os primitives isolados True, vínculo de final_hash False, composição False e zero emissões |
| `test_truncated_chain_cannot_extend_from_old_authenticated_summary` | Remover terceiro bid mantendo resumo/HMAC originais; cadeia e HMAC isoladas True, count/final_hash divergentes; composição False e zero emissões |
| `test_missing_previous_signature_never_bootstraps_extension` | Vazio A com count=0/genesis, signature None ou string vazia -> ValueError e zero emissões; não tentar assinar vazio como fallback |

Asserções também preservam as entradas anteriores. Esses testes provam a receita
com os primitives reais em memória, não que o futuro serviço já a execute. A
Story 3.4 deverá integrar o gate sob lock e provar em PostgreSQL a interrupção
antes de bid, wallets, líder, ends_at e nova âncora, sem efeitos parciais.

### 5.2 Replay de âncora vazia entre lotes — S-02

| Teste | Montagem e resultado |
| --- | --- |
| `test_empty_state_of_expected_lot_allows_extension` | Cadeia () de A, AnchorState(v=1,lot_id=A,bid_count=0,final_hash=GENESIS_HASH) e HMAC válida de A -> composição True; primeiro bid pode usar sequence=1/genesis, uma emissão nova |
| `test_empty_anchor_from_another_lot_blocks_extension` | Cadeia () esperada de A, estado vazio de B e HMAC válida de B -> verify_bid_chain True e verify_anchor_hmac True isoladamente; igualdade de lot_id False, composição False, zero emissões novas |

Não construir o resumo observado usando o lot_id recebido na âncora: o esperado
vem do lote solicitado. Usar A e B distintos e um controle de UUIDs iguais por
valor para evitar comparação por identidade. Os nove golden vectors existentes
continuam intactos; esses casos são relacionais, sem novo vetor literal necessário.

## 6. Pureza (CAP-5)

Ampliar DOMAIN_MODULES em test_domain_purity.py com BID_INTEGRITY, preservando
as guardas antigas. Criar teste específico de imports: subconjunto de
`dataclasses`, `datetime`, `hashlib`, `hmac`, `json`, `re`, `uuid`, `app.money`,
`app.lot_time`; exigir os dois imports internos e limitar seus nomes a MAX_CENTS
e require_aware. Imports relativos ou wildcard proibidos. Pydantic transitivo
de app.money é o precedente aceito; não permitir import direto.

Reutilizar `clock_calls` com resolução de aliases/factories já corrigida; preservar
autotestes como `from datetime import datetime as dt` + factory=dt.now e negativos
com timestamp injetado. Proibir imports de config/settings/os/time/pathlib,
FastAPI, SQLAlchemy, Session, ORM, db, httpx/socket/requests e outros fora da allowlist.
Proibir I/O/dynamic import via builtins open, input, __import__, eval, exec;
guarda simples AST com controle positivo e negativo, sem pretensão de sandbox.
Imports e referências comuns devem ser reconhecidos; reflexão maliciosa não entra.

Aplicar guardas existentes de ausência de float/divisão e redefinição de MAX_CENTS;
conferir identidade com money.MAX_CENTS. Não copiar o literal monetário. Conferir
uma única atribuição produtiva de GENESIS_HASH e consumo da constante em cadeia/
vazio. Constantes golden de teste naturalmente repetem zeros como evidência independente.

## 7. Mutações úteis, futuras (CAP-2/3/4/5)

Cada mutação é isolada, aplicada depois da suíte verde, sem framework. Copiar
arquivos em diretório temporário próprio, restaurar em finally, conferir com cmp
(sem Git), rerodar testes focados. Registrar testes que falharam e restauração na
story. Não executar verify completo para cada mutação. Não aceitar falha só de
sintaxe/coleta como prova do comportamento-alvo.

| ID | Mutação | Prova que deve falhar |
| --- | --- | --- |
| M1 | sort_keys=False | Golden bid/âncora e spy do serializer |
| M2 | separadores com espaços | Golden bytes |
| M3 | SHA-256 de linha trocado por SHA-512 | Golden SHA G5 |
| M4 | remover previous_hash do payload | Golden G4/G5 e teste de variação |
| M5 | aceitar uppercase hash normalizando lower | Rejeição de uppercase nos campos |
| M6 | truncar alias para 8 hex | Golden G3 e formato |
| M7 | usar == no lugar de compare_digest | Spy da verificação HMAC |
| M8 | omitir bid_count da âncora | Golden G6/G7 e variação de count |
| M9 | isoformat() sem timespec fixo | Timestamp .000000Z |
| M10 | aceitar secret vazio | Validação de segredo nos dois usos |
| M11 | aceitar bool como inteiro | v/sequence/amount/count inválidos |
| M12 | ignorar continuidade de sequence | Lacuna com links/hashes recalculados |
| M13 | ignorar genesis/link anterior | Primeiro/segundo previous errado com hash próprio correto |

Não contar mutantes equivalentes como sucesso; se um caso sobreviver, fortalecer
o teste da propriedade correspondente antes de prosseguir. Não adicionar meta
de quantidade, cobertura numérica inventada ou ferramenta nova.

## 8. Execução futura e limites

No diretório backend, rodar `uv run pytest tests/test_bid_integrity.py
tests/test_domain_purity.py tests/test_bid_rules.py tests/test_lot_time.py
tests/test_wallet_rules.py`. O conftest executa pytest_sessionstart e prepara o
PostgreSQL de teste até para esses testes puros: não prometer execução sem banco
nem mudar o harness para esta story. Configuração de teste segue os valores
fictícios já documentados pelo projeto, sem leitura de .env* pelo agente.

Ao final rodar `./verify.sh` na raiz (Ruff, formato, PostgreSQL/testes existentes,
lint/typecheck/testes frontend, Vite, Docker build). E2E opt-in não é necessário
porque não há mudança de UI. Não usar SQLite/mock para alegar adulteração real.
AD-17: consistência/atomicidade persistida na 3.4; cinco ataques PostgreSQL na 5.1.

Não há teste manual específico: esta story não cria UI/endpoint. A conferência
de bytes/digests é automatizada, e revisão de código segue o processo do projeto.
