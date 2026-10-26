---
id: SPEC-story-3-3-integridade-historico
companions:
  - decisions.md
  - integrity-contract.md
  - golden-vectors.md
  - test-plan.md
  - implementation-map.md
  - ../../../docs/ARQUITETURA.md
sources:
  - ../../implementation-artifacts/3-3-fundamentos-de-integridade-do-histórico.md
---

# Story 3.3 — Fundamentos de integridade do histórico

Contrato derivado da memória da spec e das decisões P1–P20/A1–A5 aprovadas em
26/10/2026, com correções S-01/S-02 solicitadas após revisão independente.
Decidi preservar as decisões de bytes, tipos e APIs. Os companions são
obrigatórios; esta spec está pronta para implementação futura, não implementada.
Nenhuma questão bloqueante aberta. A autorização desta sessão termina na spec.

## Why

Preciso que cada lance futuro nasça com representação histórica determinística,
identificação visual privada e integridade verificável, atendendo AD-13/20/21 e
os requisitos de histórico e privacidade do desafio. Entrego os primitives puros
antes de a Story 3.4 persistir lance e âncora na mesma transação. A cadeia sozinha
não autentica o histórico: preciso também da âncora protegida por segredo externo
ao banco.

## Capabilities

- **CAP-1**
  - **intent:** Identificar visualmente um licitante de forma determinística dentro de um lote, sem expor sua identidade real.
  - **success:** Mensagem, HMAC completo e alias coincidem com os literais de `golden-vectors.md`; diferenças controladas de lote, usuário e chave têm os resultados previstos; entradas inválidas são recusadas.
- **CAP-2**
  - **intent:** Representar cada lance e seu vínculo ao anterior de maneira reproduzível.
  - **success:** Os sete campos v1 produzem os bytes e SHA-256 literais; UTC, microssegundos, UUID, números, alias, previous hash e genesis passam na matriz de testes.
- **CAP-3**
  - **intent:** Autenticar o resumo de um lote, inclusive quando não há lances.
  - **success:** Os quatro campos da âncora produzem bytes/HMAC literais; assinatura correta confere, alterada ou chave errada não; verificação usa `hmac.compare_digest`.
- **CAP-4**
  - **intent:** Verificar a cadeia recebida e autenticar seu estado anterior antes de autorizar uma extensão.
  - **success:** Lote, sequência 1..n, genesis, links e hashes conferem; a composição exige HMAC anterior válida e vínculo exato de lote/count/final_hash. Recálculo com assinatura antiga e replay de âncora vazia de outro lote impedem extensão e emissão de nova âncora nos testes puros.
- **CAP-5**
  - **intent:** Usar os primitives com dados explícitos, independentemente de infraestrutura.
  - **success:** Guardas de pureza passam; entradas são imutáveis; nenhum relógio, ambiente, rede, ORM ou banco é acessado; somente o teto monetário e a validação temporal puros são reutilizados.
- **CAP-6**
  - **intent:** Preparar a integração posterior sem antecipar sua implementação.
  - **success:** APIs, vetores, matriz, mutações e fluxo de consumo estão especificados; no build futuro, testes e verify têm resultados reais registrados, sem criar persistência ou interface nesta story.

## Constraints

- Um módulo produtivo: `backend/app/bid_integrity.py`. Tipos, APIs e validações exatos em `integrity-contract.md`.
- P1–P20/A1–A5 permanecem vinculantes; D1–D12 detalham o contrato, D13–D14 incorporam S-01/S-02 (`decisions.md`).
- Nenhum histórico é estendido sem autenticação do estado anterior e correspondência exata com a cadeia e o lote esperado, conforme receita única em `integrity-contract.md` §9. Falha impede efeitos do lance e nova âncora; verificar só depois de atualizar é proibido.
- Vazio confiável também exige HMAC válida do próprio lote; ausência de assinatura não autoriza extensão. A inicialização confiável persistida é requisito da 3.4.
- Segredos `bytes` não vazios, explícitos e distintos na integração; nenhuma configuração operacional nesta story.
- Alias histórico é persistido por lance na 3.4 e nunca recalculado durante auditoria. Não há tabela de mapeamento nem rotação transparente.
- Nenhuma coerção silenciosa de tipos, hashes, alias ou datas naive. Erros de dados são `ValueError`; mismatches verificáveis são `False`.
- Testes novos são unitários. O harness atual ainda prepara PostgreSQL; não o refatoro nem apresento composição em memória como prova AD-17.
- Git manual; código/identificadores em inglês; documentação em português. Nenhuma dependência nova.

## Non-goals

- Migration, tabela/ORM de bids, estado persistente de integridade, backfill, Settings, transação, travas, leitura de hora do banco ou alteração de carteiras (3.4).
- Endpoint, auditoria pública, adulteração direta no PostgreSQL (5.1), frontend, WebSocket, comprovante, liquidação ou scheduler.
- PKI, blockchain, Merkle tree, key ring, KMS, rotação, rehash, realias, recuperação de segredo ou referência externa contra rollback integral.
- Corrigir documentos históricos ou dívidas de outras stories nesta sessão.

## Success signal

Na futura implementação, os testes reproduzem literalmente os vetores independentes,
recusam toda entrada inválida prevista, matam as mutações críticas e passam novamente
após restauração. `./verify.sh` termina com exit 0 e evidência real registrada. A 3.4
consegue usar as APIs sem redesenhar bytes, criptografia ou persistência do alias.
O checklist de conclusão e a separação entre readiness da spec e conclusão da story
estão em `implementation-map.md`.
