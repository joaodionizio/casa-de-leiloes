# Golden vectors — Story 3.3

## Entradas fixas e procedimento

Decidi fixtures exclusivamente fictícias, sem segredo operacional:

- lot_id: UUID("12345678-1234-5678-9abc-def012345678").
- user_id: UUID("87654321-4321-8765-abcd-0123456789ab").
- pseudonym_secret: b"atrio-test-pseudonym-v1".
- audit_hmac_secret: b"atrio-test-audit-v1" (diferente).
- v=1, sequence=1, amount_cents=12000, previous_hash=GENESIS_HASH.
- timestamp: datetime(2026, 10, 23, 4, 15, 30, 123456, tzinfo=UTC).
- Âncora principal: v=1, mesmo lote, bid_count=1, final_hash=SHA abaixo.
- Âncora vazia: v=1, mesmo lote, bid_count=0, final_hash=GENESIS_HASH.

Em 26/10/2026 conferi os valores fora do código produtivo: escrevi a mensagem e
os JSONs explicitamente (sem json.dumps para montar os bytes de referência);
passei os bytes por stdin a OpenSSL via subprocess, sem newline; conferi os
digests com hashlib/hmac sobre os mesmos bytes literais. Nenhum módulo app foi
importado. O arquivo produtivo ainda não existe. Isto é conferência dos vetores
da spec, não teste executado da implementação.

Procedimento reproduzível: para bytes literais B, executar
`openssl dgst -sha256` com B no stdin; para HMAC, usar
`openssl dgst -sha256 -mac HMAC -macopt hexkey:<hex da chave fictícia>`.
A opção hexkey representa os bytes da chave, não texto hexadecimal como segredo.
Não usar echo, que pode acrescentar newline; subprocess.run(input=B) preserva
os bytes. Comparar o digest hexadecimal final com os literais abaixo.

Na futura suíte, colar os expected abaixo como literais. Não executar OpenSSL,
não regenerar expected por json.dumps, compute_bid_hash ou qualquer primitive
produtivo. Não adicionar biblioteca de criptografia. A mensagem e o HMAC completo
podem ser conferidos com spy que delega ao HMAC real e captura os argumentos/
resultado usados por generate_bidder_alias; não criar API pública só para teste.

## Literais normativos

Os delimitadores b'...' abaixo são notação Python; não fazem parte dos bytes.
Não há newline dentro dos valores.

### G1 — Mensagem exata de pseudônimo

```python
b'12345678-1234-5678-9abc-def012345678:87654321-4321-8765-abcd-0123456789ab'
```

### G2 — HMAC-SHA-256 completo do pseudônimo

```python
'9374e0069a540cec1acdb860953a4af2edf74d9329b6a29b7537e3373ccaa8ba'
```

### G3 — Alias derivado

```python
'Licitante-9374E0069A540CEC'
```

### G4 — Bytes JSON exatos do bid v1

```python
b'{"amount_cents":12000,"bidder_alias":"Licitante-9374E0069A540CEC","lot_id":"12345678-1234-5678-9abc-def012345678","previous_hash":"0000000000000000000000000000000000000000000000000000000000000000","sequence":1,"timestamp":"2026-10-23T04:15:30.123456Z","v":1}'
```

### G5 — SHA-256 completo do bid

```python
'a2ee0d3f151b6fd530657539654b2e8064352fc0c3a8d0e5db0c4744f931a4ed'
```

### G6 — Bytes JSON exatos da âncora de um lance

```python
b'{"bid_count":1,"final_hash":"a2ee0d3f151b6fd530657539654b2e8064352fc0c3a8d0e5db0c4744f931a4ed","lot_id":"12345678-1234-5678-9abc-def012345678","v":1}'
```

### G7 — HMAC-SHA-256 completo da âncora de um lance

```python
'fdba84b9b662b56a8495e68dd507a446a72e9801e228c337a1dcbc360494e0d5'
```

### G8 — Bytes JSON da âncora vazia

```python
b'{"bid_count":0,"final_hash":"0000000000000000000000000000000000000000000000000000000000000000","lot_id":"12345678-1234-5678-9abc-def012345678","v":1}'
```

### G9 — HMAC-SHA-256 da âncora vazia

```python
'302910667af56824d35920407dcead2b941798b39b1100e006a27fc7289e73a4'
```

## Variações controladas

Usar lote alternativo UUID("12345678-1234-5678-9abc-def012345679"),
usuário alternativo UUID("87654321-4321-8765-abcd-0123456789ac") e chaves
b"atrio-test-pseudonym-v2" / b"atrio-test-audit-v2" nos testes de diferença.
Esses rótulos v2 são apenas nomes de fixtures de chaves, não versionamento do
contrato nem suporte a rotação. Comparar resultados distintos nos casos escolhidos
não prova unicidade. O teste independente de hash/âncora sempre usa G4/G5/G6/G7;
testes relacionais de composição podem gerar cadeias com os primitives.

Mesmo timestamp representado como 2026-10-23T01:15:30.123456-03:00 deve produzir G4.
A construção de UUID a partir da string uppercase deve manter G1/G3/G4.
