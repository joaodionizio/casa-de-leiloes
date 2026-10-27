# Contrato de integridade — Story 3.3

## 1. Estado real relevante

Conferi `backend/app/money.py`: MAX_CENTS é a fonte única, importando Pydantic
para Cents, sem outro módulo app. `bid_rules.py` já usa dataclasses congeladas,
keyword-only, UUID e ValueError; `evaluate_pre_wallet` e `evaluate_post_wallet`
compõem o aceite sem repetir regras. Não preciso alterá-los.

`lot_time.require_aware(name, value) -> datetime` verifica tipo e offset não-None;
não normaliza UTC nem traduz overflow. Vou reutilizá-lo e completar a normalização
localmente. `Lot` ainda não tem alias, sequence, hashes ou âncora; a lista de
migrations termina em `0004_wallets.py`. Não existe Bid nos arquivos inspecionados
nem bid_integrity.py. Settings ainda não tem os dois segredos de integridade.
Esta inspeção não comprova estado de banco/deploy em execução.

## 2. Tipos e invariantes

Decidi três dataclasses frozen/kw_only, com os campos abaixo **exatos**. Não uso
herança, Pydantic, ORM, cache de bytes, segredo ou campos auxiliares persistentes.

| Tipo | Campos em ordem lógica e tipos |
| --- | --- |
| `CanonicalBid` | `v: int`, `lot_id: UUID`, `sequence: int`, `bidder_alias: str`, `amount_cents: int`, `timestamp: datetime`, `previous_hash: str` |
| `AnchorState` | `v: int`, `lot_id: UUID`, `bid_count: int`, `final_hash: str` |
| `VerifiableBid` | `bid: CanonicalBid`, `current_hash: str` |

Todos os campos são obrigatórios, inclusive `v`. Os construtores são nomeados;
D2 exige init explícito: sentinela privada `_MISSING` em cada parâmetro de campo
permite levantar ValueError para omissão; `**unexpected` levanta ValueError se
não vazio. Isso não aceita dict como representação canônica nem armazena extras.
Validar antes de atribuir campos com `object.__setattr__` no init congelado.
Não criar helper genérico de construção. A chamada válida é, por exemplo,
`AnchorState(v=1, lot_id=LOT, bid_count=0, final_hash=GENESIS_HASH)`.

| Dado | Validação; erro de dados sempre ValueError |
| --- | --- |
| v dos dois tipos | `type(v) is int` e `v == 1`; recusar True, 1.0, "1", 0, 2 |
| IDs | `isinstance(value, UUID)`; recusar string mesmo parseável, int e None; não restringir versão do UUID |
| sequence | `type(value) is int`, >=1; sem teto monetário/persistente |
| amount_cents | `type(value) is int`, `1 <= value <= MAX_CENTS`; importar constante |
| bid_count | `type(value) is int`, >=0; sem teto artificial |
| bidder_alias | str exata; `re.fullmatch(r"Licitante-[0-9A-F]{16}", value)` |
| previous_hash, current_hash, final_hash, assinatura recebida | str exata; fullmatch `[0-9a-f]{64}`; uppercase inválido |
| timestamp | datetime aware, utcoffset não-None e conversível para UTC representável |
| segredo | bytes exatos não vazios; recusar str, bytearray, memoryview e None; `b"x"` válido |
| VerifiableBid.bid | CanonicalBid válido; o construtor valida o tipo, não a igualdade criptográfica |
| AnchorState vazio | count=0 exige final_hash=GENESIS_HASH; não usar None |

Invariantes locais nos construtores. Funções públicas conferem o tipo dedicado
esperado e seus argumentos soltos; não aceitam duck typing nem dicts. Não copio os
helpers privados de bid_rules como imports públicos. Mensagens em inglês citam
somente campo/regra, nunca valores ou segredos: por exemplo `sequence out of range`,
`audit_hmac_secret must be non-empty bytes`, `unexpected fields`,
`timestamp must be representable in UTC`. Testes de erro verificam classe e campo,
sem fixar toda a prosa. Não há códigos HTTP nem recusa de negócio.

O construtor de CanonicalBid **não** obriga sequence=1 a usar genesis; essa é uma
relação de cadeia e seu verificador retorna False. Da mesma forma, current_hash
malformado é ValueError, mas hash bem formado que não corresponde ao bid é False.

## 3. API pública final prevista

Assinaturas abaixo descrevem API futura, não código implementado:

```python
GENESIS_HASH = "0" * 64

generate_bidder_alias(*, lot_id: UUID, user_id: UUID,
                      pseudonym_secret: bytes) -> str
canonical_bid_bytes(bid: CanonicalBid) -> bytes
compute_bid_hash(bid: CanonicalBid) -> str
canonical_anchor_bytes(state: AnchorState) -> bytes
compute_anchor_hmac(state: AnchorState, *, audit_hmac_secret: bytes) -> str
verify_anchor_hmac(state: AnchorState, signature: str, *,
                   audit_hmac_secret: bytes) -> bool
verify_bid_chain(records: tuple[VerifiableBid, ...], *, lot_id: UUID) -> bool
```

Não exponho função genérica SHA de bytes livres, serializer de dict nem geração
de mensagem/HMAC completo de pseudônimo como API adicional. Helpers privados
podem validar UUID/int/secret/hex/alias e serializar JSON. Retornos simples não
ganham classes. GENESIS_HASH é a única definição produtiva de 64 zeros.

## 4. Pseudônimo e alias

Mensagem exata: `f"{str(lot_id)}:{str(user_id)}".encode("utf-8")`.
UUIDs tipados viram lowercase hifenizado sem braces, espaços, BOM ou newline.
Calcular HMAC-SHA-256 usando pseudonym_secret, obter hexdigest completo, selecionar
os primeiros 16 caracteres e convertê-los para uppercase. Prefixar `Licitante-`.
Resultado: 26 caracteres ASCII. Nome/e-mail nem entram na API. O user_id privado
é entrada do HMAC, nunca texto na saída; lot_id aparece no bid como identidade do
lote público, não identidade do licitante.

Alias é identificação visual de 64 bits, não chave única. Para n usuários e saída
uniforme, a aproximação de colisão por aniversário é n(n−1)/(2×2^64); para 1000,
cerca de 2,71×10^-14. Adequado à exibição na escala do desafio, com risco residual;
a identidade interna continua sendo UUID. Diferenças em vetores não provam
ausência de colisão. Nem banco nem primitive devem exigir alias único por lance.

## 5. Timestamp e JSON canônico v1

CanonicalBid valida com `require_aware("timestamp", value)` e converte com
`astimezone(UTC)` na construção, preservando instante, microssegundos e fold.
Guardar o datetime UTC resultante no campo timestamp. Traduzir OverflowError e
TypeError de offset/conversão em ValueError; ValueError de offset permanece
ValueError. Não capturar exceções arbitrárias de código hostil em tzinfo.

Para serializar, usar `timestamp.isoformat(timespec="microseconds")`, depois
substituir **o sufixo UTC final** `+00:00` por `Z`. A normalização anterior garante
esse sufixo. Não usar strftime dependente de plataforma para ano 0001, timestamp
numérico, arredondamento, replace(tzinfo=UTC) ou relógio. Exemplos normativos:
`2026-10-23T04:15:30.123456Z`, `2026-10-23T04:15:30.000000Z`.

Construir payload interno explicitamente na ordem lógica dos campos da tabela,
convertendo somente lot_id para str e timestamp para o formato acima. Valores
numéricos continuam int, v sempre 1. Não incluem user_id, current_hash, ends_at,
saldo ou segredo. Serialização única para bid e âncora:

```python
json.dumps(payload, sort_keys=True, separators=(",", ":"),
           ensure_ascii=False).encode("utf-8")
```

Sem indent, default=str, BOM ou newline final. Ordem efetiva bid:
amount_cents, bidder_alias, lot_id, previous_hash, sequence, timestamp, v.
Ordem efetiva âncora: bid_count, final_hash, lot_id, v. Alias e demais strings v1
são ASCII por contrato; ensure_ascii=False é obrigatório, mas não cria licença
para aceitar Unicode arbitrário. Um spy prova o parâmetro sem ampliar o domínio.

## 6. Hash de linha e genesis

`compute_bid_hash(bid)` calcula exatamente
`hashlib.sha256(canonical_bid_bytes(bid)).hexdigest()`.
previous_hash já está dentro dos bytes: sem concatenar novamente, adicionar salt,
segredo, prefixo, hash duplo ou HMAC de linha. Saída 64 hex lowercase.

Vazio: count=0/final_hash=GENESIS_HASH. Primeiro bid: sequence=1/previous=genesis;
segundo: sequence=2/previous=hash do primeiro; terceiro: previous=hash do segundo.
Cada hash de linha tem o mesmo formato textual. Zero não é assinatura de vazio:
o estado vazio recebe seu próprio HMAC válido.

## 7. Âncora e verificação HMAC

Payload exato de AnchorState: v, lot_id, bid_count, final_hash. Serializer do §5,
UUID textual canônico e números inteiros. Não adicionar key_id, tipo, algorithm,
timestamp ou versão de segredo à v1.

`compute_anchor_hmac` aplica HMAC-SHA-256 a canonical_anchor_bytes(state), com
audit_hmac_secret explícito; retorna hexdigest completo lowercase.
`verify_anchor_hmac` valida state, assinatura e segredo antes de comparar; calcula
o esperado pela mesma função e retorna **hmac.compare_digest(expected, signature)**.
Igualdade normal `==` fica proibida para assinatura. Chave não vazia errada ou
assinatura bem formada alterada -> False; tipo/formato inválido ou chave vazia ->
ValueError. Não medir tempo para provar constant-time.

## 8. Verificação pequena de cadeia em memória

Incluí verify_bid_chain: somente uma tuple de VerifiableBid; não aceitar lista,
dict, generator ou None. O consumidor materializa a tuple, já na ordem desejada.
lot_id explícito identifica o lote esperado inclusive para cadeia vazia.

1. Validar lot_id UUID, tuple e tipo de **todos** os elementos antes de qualquer
   retorno False. Os tipos congelados já validaram seus campos na construção.
2. Iniciar hash esperado em GENESIS_HASH e sequence esperada em 1.
3. Para cada registro na ordem recebida, conferir bid.lot_id por igualdade de
   UUID, sequence exata esperada, previous_hash igual ao hash esperado e
   current_hash igual a compute_bid_hash(bid). Qualquer divergência -> False.
4. Avançar hash esperado para current_hash e sequence para a seguinte.
5. Ao final, retornar True; tuple vazia retorna True para qualquer UUID válido.

Sem ordenar, reparar, mutar, buscar estado ou recalcular alias. Não verificar
mínimo do lance, saldo, papel, cronologia estritamente crescente, alternância de
licitantes ou existência do lote: faltam dados e isso não é contrato criptográfico.
Links/hashes não secretos podem usar igualdade comum. Custo linear no total de
bytes canônicos, duas passagens pequenas (estrutura e relações), sem cópia da cadeia.

## 9. Composição autenticada, adulteração e truncamento

True de verify_bid_chain atesta apenas coerência interna. verify_anchor_hmac
atesta apenas o estado que recebeu. Para autenticar o histórico, o consumidor
precisa da receita única abaixo, tanto na auditoria quanto **antes de estender**
qualquer histórico existente (S-01). Decidi manter as APIs atuais: a composição
fica explícita nos testes puros da 3.3 e no consumidor futuro, sem helper público novo.

### Receita obrigatória para autenticar o estado ANTERIOR

Receber o lote esperado, a cadeia anterior completa e ordenada, o AnchorState
anterior e sua assinatura persistida, com AUDIT_HMAC_SECRET injetado. Na 3.4,
essas leituras pertencem ao mesmo estado protegido pela trava do lote e pela
transação; não misturar snapshots anteriores/depois de escrita.

1. Validar a estrutura de todas as entradas. Avaliar as duas verificações abaixo
   antes de combinar seus resultados, para não esconder entrada inválida por
   curto-circuito de um mismatch. Erro estrutural continua ValueError.
2. Obter `chain_ok = verify_bid_chain(records, lot_id=expected_lot_id)`.
3. Obter `hmac_ok = verify_anchor_hmac(previous_state, previous_signature,
   audit_hmac_secret=audit_hmac_secret)` contra o estado **anterior**, nunca o novo.
4. Conferir explicitamente as três igualdades de vínculo:
   - `previous_state.lot_id == expected_lot_id`;
   - `previous_state.bid_count == len(records)`;
   - `previous_state.final_hash == (records[-1].current_hash if records else GENESIS_HASH)`.
5. O resultado composto é True **somente se chain_ok, hmac_ok e todas as três
   igualdades forem verdadeiros**. Estado bem formado com qualquer divergência
   retorna False, inclusive sequence/link/hash, assinatura, lote, count ou final_hash.

Somente resultado True autoriza usar `previous_state.bid_count` para determinar
a próxima sequence e `previous_state.final_hash` como previous_hash. **Nenhum
histórico existente pode ser estendido antes de o estado anterior ser autenticado
e vinculado à cadeia usada.** False ou erro estrutural interrompe a extensão;
não usar o predecessor, criar bid, atualizar wallets/líder/ends_at nem emitir ou
persistir nova âncora. A comparação HMAC do estado anterior naturalmente calcula
um digest esperado; isso não é emissão de assinatura para um novo estado.

### Cadeia vazia e replay entre lotes (S-02)

Vazio confiável exige state.lot_id igual ao lote esperado, count=0,
final_hash=GENESIS_HASH **e HMAC anterior válida**. `verify_bid_chain((), lot_id=A)`
True não autentica o lote. Uma âncora vazia de B com HMAC válida continua dando
False na composição para A, mesmo com count/hash idênticos. Âncora vazia de A
válida dá True. A igualdade do lote é obrigatória até quando não há registros.

Ausência de assinatura nunca equivale a True: None, string vazia ou formato
inválido gera ValueError no primitive, conforme contrato já existente; assinatura
bem formada mas incorreta gera False. Não criar fallback `count=0 => confiável`.

### Ataques e limites da garantia

Original: três registros, estado (3, hash3), assinatura A. Remover o último deixa
uma cadeia de dois registros internamente válida, mas resumo (2, hash2) diverge.
Se também alterarem o estado para (2, hash2), A deixa de autenticar esse estado.
Verificar somente A contra o estado antigo continuaria True e seria insuficiente.

Alterar um bid e recalcular todos os hashes é possível só com acesso ao banco;
a nova cadeia pode passar no verificador puro. O resumo final muda, e o atacante
sem AUDIT_HMAC_SECRET não produz uma nova assinatura válida. A composição detecta
esse ataque **antes da extensão**: recalcular três bids, gravar H3' e manter a
assinatura antiga faz hmac_ok=False. Um quarto lance legítimo não pode levar o
serviço a assinar (4,H4') e legitimar o passado adulterado. Alterar somente count
ou final_hash mantendo a assinatura também interrompe a extensão. Se mantiverem
o resumo antigo assinado, o vínculo com a cadeia recalculada falha mesmo com
hmac_ok=True. Verificar apenas depois da atualização não atende S-01.

Este ataque não depende de comprometimento do segredo e não é a limitação aceita
de rollback integral. Restaurar cadeia **e âncora antiga válida juntas** pode passar: sem
referência externa confiável não prometo detecção de rollback integral.

## 10. Contrato de integração futura, sem implementá-lo

Na Story 3.4, dentro da **mesma transação**:

1. Iniciar a transação, travar o lote e obter um clock_timestamp() PostgreSQL depois da trava.
2. Validar regras pré-wallet pela etapa real da 3.2.
3. Ler cadeia e bid_count/final_hash/anchor_hmac anteriores sob a trava; construir
   AnchorState anterior e executar **toda a receita do §9**. Se False ou erro,
   abortar sem efeitos de lance e sem emitir nova âncora. Só se True continuar
   com locks de wallets conforme AD-8, validar saldo e aceitar o lance. Determinar
   sequence a partir do count autenticado; previous_hash é o final_hash autenticado.
4. Gerar alias com UUIDs e segredo injetado; congelá-lo para esse evento.
5. Construir CanonicalBid(v=1, lot_id, sequence, alias, amount, timestamp=esse mesmo now, previous_hash).
6. Calcular current_hash; persistir sequence, identidade privada necessária,
   bidder_alias histórico, amount_cents, timestamp, previous_hash e current_hash,
   preservando/reconstruindo explicitamente v1.
7. Construir AnchorState(v=1, lot_id, bid_count posterior, final_hash=current_hash),
   calcular HMAC e atualizar count/final_hash/assinatura do estado de integridade.
8. Commitar tudo junto com os efeitos do lance. Falha desfaz tudo; recusa não
   cria bid nem muda cadeia/âncora.

Este fluxo é obrigação do consumidor, não tarefa de código da 3.3. É uma orientação
para a integração detalhada da 3.4, não substituição da ordem vinculante do AD-7.
A precondição inegociável é autenticar/vincular o estado anterior **antes** de
usá-lo como base de novo estado autenticado e antes de qualquer efeito do lance.
A 3.4 deve provar em PostgreSQL que falhas dessa precondição deixam bid, wallets,
líder, ends_at e âncora inalterados. A composição pura da 3.3 não prova rollback real.

### Requisito de inicialização confiável para a 3.4

Hoje não existe estado de integridade persistido no modelo Lot. A migration/
inicialização da 3.4 deve resolver explicitamente o vazio autenticado para lotes
novos, existentes e seed. Preferir criar/persistir a âncora válida (v1, lote,
0, genesis) na inicialização confiável do lote, antes do primeiro lance. Não fixo
schema, backfill ou mecanismo de inicialização nesta story. Essa obrigação é da
3.4 e não bloqueia os primitives puros da 3.3.

Ausência de assinatura em lote já usado não permite bootstrap no fluxo de lance.
Não assinar automaticamente o estado encontrado no banco para "repará-lo", nem
no boot: verificar que count=0 não estabelece origem confiável. A 3.4 precisa
definir seu caminho confiável de inicialização; enquanto não houver estado
autenticado, extensão permanece proibida. Não criar migration ou persistência aqui.

**Auditoria futura usa bidder_alias persistido no bid. Nunca chama pseudonym com
segredo atual e bidder_id para reconstruir o histórico.** Não há tabela de
mapeamento. Integração injeta duas chaves distintas, fora do banco e de respostas/
logs; funções que recebem uma chave só não podem verificar distinção entre elas.

A Story **5.1 — Verificação pública da integridade do lote** integra leitura pública
e verificação completa, sem escrita/liquidação ou dependência da API externa. Seus
cinco ataques diretos no PostgreSQL (alteração, inserção, remoção intermediária,
truncamento, recálculo) continuam obrigatórios por epics/AD-17. Nenhum teste puro
desta spec reivindica essa prova persistente.
