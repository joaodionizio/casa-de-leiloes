# Story 3.3 — Fundamentos de integridade do histórico

Status: done

Chave do sprint: `3-3-fundamentos-de-integridade-do-histórico`
Épico: 3 (Carteira e lances íntegros). Data de criação: 26/10/2026.

> **Registro histórico das decisões, anterior à implementação.** O estado atual e as
> evidências do build autorizado estão na seção 13; as descrições futuras abaixo
> preservam o contexto da criação.
>
> **Decisões consolidadas em 26/10/2026.** Decidi P1–P20 e A1–A5 antes
> da spec e do código. As seções abaixo refletem o contrato aprovado, inclusive
> o ajuste da P18 para verificação pura de cadeia. Não resta decisão bloqueante
> para elaborar a spec quando eu a solicitar. `ready-for-dev` permanece; esta
> consolidação não autoriza executar spec, build ou implementar código.

## 1. Story e objetivo

Como qualquer pessoa que vá auditar um lote,
quero funções determinísticas de pseudônimo, serialização canônica, hash encadeado
e autenticação da âncora,
para que o motor de lances grave cada lance íntegro desde o primeiro.

Planejo entregar os primitives puros do AD-13, AD-20 e AD-21 antes da transação
crítica da 3.4. A mesma entrada deverá produzir os mesmos bytes e digests. Não
confundo uma cadeia internamente consistente com uma cadeia autenticada: a âncora
HMAC é necessária para detectar truncamento e recálculo sem o segredo.

## 2. Fontes e método

Li integralmente `CLAUDE.md`, `docs/ARQUITETURA.md`, `docs/desafio-elite-dev.md`,
`README.md`, `docs/uso_de_ia.md`, `_bmad-output/planning-artifacts/epics.md`,
`_bmad-output/implementation-artifacts/sprint-status.yaml`,
`_bmad-output/implementation-artifacts/deferred-work.md`,
`_bmad-output/planning-artifacts/DESIGN.md` e
`_bmad-output/planning-artifacts/EXPERIENCE.md`.

Usei a estrutura das Stories 3.1/3.2; li o artefato final da 3.2 e seus cinco
arquivos de spec em `_bmad-output/specs/spec-story-3-2-regras-aceitacao-lance/`
(`SPEC.md`, `decisions.md`, `domain-contract.md`, `test-plan.md`,
`implementation-map.md`). Conferi os módulos reais `backend/app/money.py`,
`bid_rules.py`, `lot_time.py`, a configuração, os campos do modelo `Lot`, a lista
de migrations e `0004_wallets.py`; os padrões em `test_wallet_rules.py`,
`test_bid_rules.py`, `test_lot_time.py`, `test_domain_purity.py` e `conftest.py`.

**Fallback histórico da criação:** `bmad-create-story` não foi encontrado nas skills locais,
no `_bmad`, em `.claude` nem nos plugins locais pesquisados. O README de
`_bmad/bmm/v6-shims/` o listava como “Retained in full”, mas não havia workflow executável
correspondente disponível naquela etapa. Criei manualmente este artefato, como nas stories precedentes.
Não executei `bmad-spec` nem `bmad-build`. A mensagem inicial do agente anunciou
`bmad-build` antes de ler o anexo e seu `SKILL.md` foi lido; a intenção foi corrigida
assim que o pedido foi conhecido, sem executar o renderer/workflow.

**Atualização desta consolidação:** informei que o ambiente agora está em BMAD
6.12.4, com compatibility shims habilitados e `bmad-create-story` funcional.
Decidi preservar o artefato já produzido e revisado; não rerodar create-story.
O fallback acima descreve somente a criação anterior, não um bloqueio atual.

Conferi detalhes de biblioteca nas fontes primárias do Python 3.13:
[HMAC](https://docs.python.org/3.13/library/hmac.html),
[JSON](https://docs.python.org/3.13/library/json.html) e
[datetime](https://docs.python.org/3.13/library/datetime.html).
Essas referências esclarecem APIs; não substituem decisões do projeto.

## 3. Estado real encontrado

| Área | Evidência atual e consequência |
| --- | --- |
| Sprint | 3.1 e 3.2 `done`; 3.3–3.6 `backlog`; Epic 3 `in-progress` antes desta criação |
| Dinheiro | `app.money.MAX_CENTS = 9_007_199_254_740_991`; `Cents` é `Annotated[StrictInt, Field(gt=0, le=MAX_CENTS)]`. Importa Pydantic, sem importar outro módulo do app |
| Regra do lance | `app.bid_rules` já existe e é puro; dataclasses `frozen=True, kw_only=True`, invariantes na construção, UUID real, `ValueError` para entradas inválidas. Seus validadores de centavos/UUID são privados |
| Composição da 3.2 | `evaluate_pre_wallet(lot, attempt, now)` → `EligibleBid` ou recusa; `evaluate_post_wallet(eligible, available_balance_cents)` → aceite ou recusa; `evaluate_bid` compõe e valida antecipadamente o saldo separado. Não reabro D8 |
| Tempo | `app.lot_time.require_aware(name, value)` já valida `datetime` e `utcoffset() is not None`; `lot_phase` compara em UTC, inclusive `fold`. `app.lots` reexporta a fase |
| Persistência | Migrations em `backend/migrations/versions/`, até `0004_wallets.py`; modelo `Lot` tem termos, snapshot da obra e horários. Não há `bids`, `Bid`, sequência, hash, alias nem âncora persistidos nos arquivos examinados |
| Integridade | Não existem `app/integrity.py` nem `app/bid_integrity.py`; o módulo abaixo está aprovado para implementação futura, mas ainda não existe; nomes finais de tipos/funções serão detalhados na spec |
| Configuração | `app.config` separa Settings de domínio; ainda não declara os dois segredos de integridade. Ler esse arquivo-fonte não instancia Settings nem lê `.env` |
| Testes | `pytest.mark.parametrize`, esperados literais, UUIDs/datas fixos, `pytest.raises`, imutabilidade e guardas AST. O detector de relógio já resolve aliases normais e referências em factories (correção N-01) |
| Harness | `pytest_sessionstart` sempre valida configuração, conecta e recria o schema do banco de teste. Um teste de domínio puro ainda depende desse harness para rodar pelo pytest normal. Não executei pytest nem verify nesta criação |

Inspeção de arquivos não comprova o estado de um banco ou deploy em execução.
Não consultei nenhum deles nem usei Git para confirmar commits.

## 4. Escopo e fronteiras

**Entra na futura implementação:** pseudônimo por lote; entrada canônica v1;
serialização em bytes UTF-8; genesis; SHA-256; encadeamento via `previous_hash`;
entrada canônica versionada da âncora; HMAC da âncora; validações e testes puros.
Incluo geração e verificação de HMAC, além do algoritmo puro de verificação de
cadeia em memória. A futura spec avaliará sua menor API suficiente (P18), sem
modelos de persistência nem auditoria PostgreSQL.

**Fora absolutamente:** tabela/migration/ORM de bids; colunas em lotes; Session;
`SELECT FOR UPDATE`; transação; sequência e previous hash obtidos do banco;
atualização persistida da âncora; wallets, saldo, comprometimento, liberação do
líder anterior, líder novo; endpoint/HTTP; frontend; WebSocket; anti-sniping
persistido; liquidação; receipts; scheduler; cancelamento; endpoint de auditoria;
UI de histórico. Não crio blockchain, Merkle tree, PKI, assinatura assimétrica,
KMS, rotação completa de chaves ou infraestrutura externa.

| Entrega | Responsabilidade |
| --- | --- |
| 3.3 | Primitives de geração e verificação, algoritmo puro de cadeia em memória, bytes/digests determinísticos e testes unitários |
| 3.4 | Modelo e migrations, travas, uma transação, sequência/previous hash autoritativos, persistir linha e âncora juntas, concorrência e consistência em PostgreSQL real |
| 5.1 | Auditoria pública e os cinco testes de adulteração direta no PostgreSQL, conforme `epics.md` |

Não encontrei necessidade concreta de migration na 3.3. O timestamp canônico da
3.4 deverá ser o mesmo `clock_timestamp()` lido depois da trava do lote e usado
na avaliação; o serializer não consulta a hora nem recebe `ends_at` como timestamp.

## 5. Decisões vinculantes — não reabrir

- **AD-13:** SHA-256 encadeado e âncora HMAC; âncora cobre lote, quantidade e hash
  final; segredo de auditoria fora do banco/Git. Detectar alteração, inserção,
  remoção intermediária, truncamento e recálculo sem segredo. Limitações: segredo
  comprometido e rollback completo para estado antigo consistente.
- **AD-20:** mensagem lógica `{lot_id}:{user_id}`, HMAC com `PSEUDONYM_SECRET`,
  pseudônimo por lote, sem nome/e-mail/ID real. Segredo diferente de
  `AUDIT_HMAC_SECRET`. O exemplo de oito hex não fixa comprimento nem digest.
- **AD-21:** exatamente `v`, `lot_id`, `sequence`, `bidder_alias`, `amount_cents`,
  `timestamp`, `previous_hash`; v1 (`v: 1`); JSON ordenado/minimal, UTF-8, inteiros,
  UUID lowercase, UTC com seis casas e `Z`; genesis de 64 zeros hexadecimais;
  âncora também canônica e versionada.
- **AD-3/contrato herdado:** centavos inteiros positivos até `MAX_CENTS`, sem bool
  ou coerção de float/texto; não invento outro teto monetário.
- **AD-6/AD-7/AD-26:** hora injetada; dados de integridade na mesma transação do
  lance. Obter a hora, travar e gravar são responsabilidades da 3.4.
- **AD-17/AD-27:** testes críticos de persistência em PostgreSQL real; não implica
  criar persistência para testar algoritmos puros. O verify completo continua
  previsto para a implementação autorizada, sem alteração nesta sessão.
- **AD-30 e processo:** nomes técnicos em inglês, texto de produto em português;
  uma story por vez; decisões abertas minhas; Git manual.

## 6. Decisões fechadas P1–P20 (26/10/2026)

Decidi os contratos abaixo. Alternativas registradas como descartadas deixam de
ser recomendações pendentes. Nomes finais, assinaturas e detalhes de organização
interna serão definidos na spec dentro destes limites, sem reabrir as decisões.

### P1 — Módulo — aprovada

Decidi `backend/app/bid_integrity.py`, pequeno e puro. Descartei pacote adicional,
três módulos separados e um módulo genérico de integridade. A 3.4 importa os
primitives e mantém a transação fora deles.

### P2 — Tipos de domínio — aprovada

Decidi usar tipos dedicados/dataclasses congeladas onde agregam contrato explícito,
principalmente na entrada canônica do lance e da âncora. Resultados triviais
continuam `bytes`, `str` ou `bool`; descartei classes só para embrulhar esses
resultados. A spec define nomes e construção dos tipos, seguindo o precedente
puro da 3.2. A 3.4 adapta seus valores para esses tipos, sem passar ORM.

### P3 — Segredos explícitos — aprovada

Decidi receber `pseudonym_secret: bytes` e `audit_hmac_secret: bytes` explicitamente.
`bid_integrity.py` não lê environment, settings, `.env` ou banco. Descartei leitura
implícita de configuração pelo domínio. A integração futura fornece os segredos
operacionais, diferentes entre si, sem colocá-los nos objetos canônicos.

### P4 — Digest do pseudônimo — aprovada

Decidi **HMAC-SHA-256**. A arquitetura fixava HMAC sem especificar o digest; esta
escolha fecha o detalhe. Descartei SHA-512 para este contrato, pois aumentar o
digest não elimina colisões quando o alias continua truncado ao mesmo tamanho.
A 3.4 usa exatamente esse algoritmo.

### P5 — Mensagem exata do pseudônimo — aprovada

Decidi UUIDs tipados e a mensagem exata:

`f"{str(lot_id)}:{str(user_id)}".encode("utf-8")`

`str(UUID)` é lowercase, hifenizado, sem braces. Não há espaços, BOM ou newline.
Descartei strings arbitrárias e concatenação dos bytes crus dos UUIDs. A borda
converte representações externas; os UUIDs do ORM podem ser passados diretamente.

### P6 — Alias com 16 hex — aprovada

Decidi `Licitante-` + os **primeiros 16 caracteres hexadecimais** do digest HMAC,
convertidos para uppercase. Exemplo conceitual: `Licitante-A83F19C2D77B4E91`.
São 26 caracteres no total. Descartei 8 e 12 hex e o digest completo para exibição.
O exemplo de oito caracteres no AD-20 era ilustrativo, não contrato rígido.

Preservo o risco residual de colisão: não afirmo unicidade matemática. A estimativa
calculada na criação, com 1.000 usuários distintos por lote e saídas uniformes,
`n(n−1)/(2 × 2^b)`, foi aproximadamente `1,163e-4` para 8 hex, `1,775e-9` para
12 hex e `2,708e-14` para 16 hex. Não é medição de carga nem prova de ausência de
colisão. A 3.4 preserva UUID privado como identidade; alias não substitui essa
identidade nem é UNIQUE por lote, pois um usuário pode dar vários lances.

### P7 — Alias histórico persistido por lance — aprovada

**Decidi persistir `bidder_alias` em cada lance na futura Story 3.4.** A linha
preserva a identidade interna/privada necessária e o alias histórico congelado.
O alias que entrou no lance e nos bytes canônicos **nunca é recalculado durante
_auditoria_**: o auditor usa o valor persistido.

Descartei persistir apenas o bidder real e regenerar seu alias para verificar o
histórico. Essa alternativa economizaria uma coluna, mas faria a alteração de
`PSEUDONYM_SECRET` mudar bytes históricos e quebrar a conferência. Aceito o custo
de texto por linha para preservar a representação autenticada do evento.

Não crio tabela separada de mapeamento de pseudônimos. O alias é parte do próprio
evento e de seu contrato canônico; isso esclarece a relação com AD-20 e fecha Q3
para a 3.4. Alterar o alias armazenado altera os bytes/hash e exige uma nova âncora
válida para passar pela verificação completa.

**Rotação transparente de `PSEUDONYM_SECRET` durante a vida dos dados/lotes
existentes não é suportada nesta entrega.** O segredo é configuração estável.
Persistir alias preserva o passado, mas não torna transparentes novos lances ou
consulta do próprio alias após uma troca. Versionamento/key id, preservação/reuso
por `(lot_id,user_id)` ou política coordenada de rotação exigiriam estratégia
adicional fora do desafio. Isso é limitação deliberada, não bug (A1).

**Impacto inequívoco na 3.4:** a futura migration/modelagem deve comportar o alias
histórico por linha junto à identidade privada; o serviço grava exatamente o
alias canonicalizado na mesma transação do lance e da âncora. Nenhuma migration
ou tabela é criada nesta consolidação ou na implementação da 3.3.

### P8 — Entrada canônica dedicada — aprovada

Decidi tipo dedicado, campos explícitos e v1 fixa. O payload lógico contém
**exatamente** `v`, `lot_id`, `sequence`, `bidder_alias`, `amount_cents`, `timestamp`,
`previous_hash`, com `v = 1`. A spec define como o tipo representa a versão fixa;
não permite selecionar outra versão em um canonicalizer v1.

Descartei dict arbitrário como API pública e campos extras/omitidos silenciosamente.
Não entram `user_id`, `current_hash`, saldo ou `ends_at`. O payload é construído
internamente a partir do tipo; a 3.4 fornece os valores explícitos.

### P9 — Serialização exata — aprovada

Decidi `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, UTF-8,
sem newline final e retorno **bytes**. Sem indent, BOM, espaços extras ou
`default=str`. O payload é interno, nunca um dict externo arbitrário.
Descartei retorno canônico `str` e normalização implícita por serializer HTTP.
Com alias ASCII estrito (A2), `ensure_ascii` não muda os bytes de entradas válidas;
a spec não deve ampliar o domínio para testar esse parâmetro.
A 3.4 calcula hashes pelos mesmos bytes usados na verificação.

### P10 — Timestamp — aprovada

Decidi datetime timezone-aware obrigatório; naive → `ValueError`; normalização
por instante para UTC, exatamente seis dígitos de microssegundos e sufixo literal
`Z`, nunca `+00:00`. Exemplos: `2026-10-23T04:15:30.123456Z` e
`2026-10-23T04:15:30.000000Z`.

Offsets diferentes são normalizados por instante e `fold` é respeitado pela
conversão UTC. Descartei assumir UTC para naive, trocar tzinfo sem converter o
instante e omitir a fração quando zero. A spec pode reutilizar `require_aware`
existente e detalhar erros nos extremos representáveis. A 3.4 passa o mesmo
instante do banco usado na operação, não um novo relógio ou string HTTP.

### P11 — Sequence — aprovada

Decidi int estrito, bool inválido, mínimo 1; 1 é o primeiro lance. Zero/negativo
são inválidos. Não há teto artificial novo no primitive. Descartei limites
monetários aplicados a contadores por conveniência.
A 3.4 decide tipo persistido/limites e determina a sequência contínua por lote
sob trava. O algoritmo puro de P18 verifica continuidade, sem buscar estado.

### P12 — Amount cents — já decidida e aprovada

Preservei inteiro estrito, bool inválido, faixa `1..MAX_CENTS`, reutilizando
`app.money.MAX_CENTS`. Sem float, coerção de texto ou nova constante monetária.
A 3.4 canonicaliza e persiste o mesmo valor aceito pelas regras, sem refazer
validação de saldo ou mínimo dentro do primitive de integridade.

### P13 — Hashes textuais — aprovada

Decidi exatamente 64 caracteres hexadecimais lowercase. Entrada uppercase é
rejeitada, nunca normalizada silenciosamente. Outputs SHA/HMAC usam hex lowercase;
`GENESIS_HASH` usa a mesma representação: 64 zeros. O trecho público do alias
segue P6 (uppercase), não o formato dos hashes da cadeia/âncora.
Descartei digest binário como saída pública e tolerância de case. A 3.4 escolhe
armazenamento textual/constraints compatíveis, sem fixar schema nesta story.

### P14 — Hash da linha — já decidida e aprovada

Decidi `SHA256(canonical_bid_bytes)`. `previous_hash` já participa desses bytes.
Nenhuma concatenação externa adicional, salt, HMAC por linha ou outro envelope.
A 3.4 usa o hash resultante como previous hash do próximo lance; o recálculo
SHA-256 não requer segredo.

### P15 — Âncora v1 — aprovada

Decidi payload com **exatamente** `v`, `lot_id`, `bid_count`, `final_hash`,
`v = 1`, e o mesmo serializer de P9. `bid_count` é int sem bool, não negativo,
sem teto artificial novo. Descartei `key_id`, algoritmo, tipo ou outros campos
extras nesta versão. Qualquer ampliação requer nova versão de contrato.
A 3.4 monta a âncora com quantidade posterior ao lance e o hash final correspondente.

### P16 — HMAC da âncora — aprovada

Decidi **HMAC-SHA-256 sobre os bytes canônicos da âncora**, com
`audit_hmac_secret`, saída completa de 64 hex lowercase. Descartei truncamento,
SHA-512 e autenticar apenas final_hash. Lote e quantidade também participam.
A 3.4 atualiza HMAC, count e final hash atomicamente com o lance.

### P17 — Cadeia vazia — aprovada

Decidi `bid_count = 0`, `final_hash = GENESIS_HASH`; esse estado pode produzir
âncora HMAC válida. Não uso None como final hash. Semântica única:
zero bids → genesis; primeiro previous_hash → genesis; cada previous_hash seguinte
→ hash anterior. Descartei null como representação alternativa do vazio.

A 3.4 decidirá/persistirá esse estado conforme migration/transação, inclusive
inicialização de lotes existentes/novos/seed e momento de assinatura. Não imponho
nesta story uma estratégia de backfill nem HMAC gerado por migration. Ausência de
assinatura não é prova de cadeia autenticada. A 3.3 define apenas o estado puro.

### P18 — Geração e verificação puras — aprovada com ajuste

Decidi fornecer no mínimo: gerar pseudônimo; canonicalizar bid; calcular hash de
bid; canonicalizar âncora; calcular HMAC de âncora; verificar HMAC de âncora.

**Além disso, a spec deve avaliar uma função pura e pequena de verificação de
cadeia em memória**, conceitualmente `verify_bid_chain(...)`. O algoritmo pertence
à 3.3: sequência começando em 1 e contínua, primeiro previous_hash genesis,
previous_hash de cada linha igual ao hash anterior e hash atual correspondente
aos bytes canônicos. A spec define a menor representação pura suficiente para
as entradas e os hashes a conferir, sem modelos persistentes ou classes triviais.

Esta decisão substitui a recomendação anterior de limitar a API ao helper de
âncora. Descartei antecipar auditoria PostgreSQL ou diagnóstico público completo.
Se o helper exigir modelos inexistentes ou inflar demais a API, a spec deve
reportar isso e manter a menor representação pura suficiente, não iniciar a 3.4.

Cadeia consistente não basta para provar autenticidade: truncar o último lance ou
recalcular todos os hashes pode preservar sua consistência interna. A verificação
completa também compara lote, count e final hash resultantes com a âncora autenticada.
A spec deve deixar explícito o que o helper de cadeia verifica e o que exige essa
composição, sem prometer detectar truncamento só pelos links.

### P19 — Comparação da assinatura — aprovada

Decidi **`hmac.compare_digest`** para verificar HMAC; descartei comparação comum
com `==` para assinatura. A spec detalha tipos/formatos inválidos e retorno,
sem benchmark temporal ou framework adicional. O helper será reutilizável na
integração e na auditoria, sem substituir a conferência do resumo da cadeia.

### P20 — Validação de segredos — aprovada

Decidi tipo bytes, não vazio. Descartei aceitar str e converter silenciosamente,
ou impor comprimento mínimo arbitrário no primitive. Política de força/produção
pertence à futura configuração. Nenhum segredo é criado nesta story.
A integração valida também que os dois segredos são diferentes; um primitive
que recebe só uma chave não pode comprovar essa relação sozinho.

## 7. Decisões adicionais A1–A5 e limites

A numeração desta seção é a do pedido de consolidação. Ela substitui os rótulos
exploratórios A1–A7 da primeira versão; não transfiro aprovações por coincidência
de número. Detalhes técnicos anteriores não explicitamente fechados ficam para
a spec dentro dos contratos aprovados, não como decisões novas tomadas pelo agente.

### A1 — Rotação de segredos — decidida

Decidi `PSEUDONYM_SECRET` e `AUDIT_HMAC_SECRET` como configuração estável nesta
entrega. Não implemento key version, key ring, KMS, rotação automática nem migração
de hashes/aliases. Comprometimento/rotação exige estratégia fora do escopo.
A troca da chave de auditoria invalida a verificação das âncoras antigas com a
nova chave; persistir aliases não resolve isso. Não reautentico cegamente dados
do banco no boot, o que poderia legitimar adulteração.

### A2 — Alias ASCII estrito — decidida

Decidi que o alias gerado é ASCII por construção e a entrada canônica valida
estritamente o formato `^Licitante-[0-9A-F]{16}$`, correspondência da string inteira.
Não aceita whitespace, newline terminal, controles, case errado, Unicode
arbitrário ou alias vazio. Descartei trim, casefold e normalização Unicode
silenciosos. A spec deve preservar esse formato v1 para dados históricos.

### A3 — Golden vectors — decidida

Decidi valores fixos literais para, no mínimo: mensagem de pseudônimo, alias
esperado, bytes JSON completos do bid, SHA-256 completo, bytes JSON completos da
âncora e HMAC completo. Os expected não são calculados pelo mesmo primitive sob
teste. Segredos falsos fixos, claramente identificados como fixtures de teste.
Descartei testes que só comparam a implementação com ela mesma.

### A4 — Pureza — decidida

Decidi que `bid_integrity.py` não lê relógio, ambiente ou banco, não importa
FastAPI/SQLAlchemy nem acessa rede. Timestamp, IDs, valores e segredos entram por
argumento. Descartei infraestrutura embutida no domínio. O uso de MAX_CENTS mantém
o precedente de Pydantic transitivo por app.money, sem dependência direta dele.

### A5 — PostgreSQL — decidida

Decidi não adicionar testes PostgreSQL na 3.3 apenas por ritual. AD-17 será
exercido na integração persistida e adulteração real. O harness pytest existente
continua preparando PostgreSQL até para testes focados; isso não transforma os
novos testes puros em testes de persistência e não autoriza refatorar o harness.

**Detalhamento reservado à spec, sem decisão bloqueante atual:** nomes/assinaturas
finais; representação mínima dos registros e hashes para o verificador; retorno
para corrupção/mismatch e erros estruturais; validação nos extremos UTC; localização
das invariantes entre tipo e função; forma pública da constante GENESIS_HASH. Esses
pontos não autorizam modificar os contratos P1–P20/A1–A5 nem implementar agora.

**Limite de segurança já arquitetado:** uma âncora antiga válida restaurada junto
com toda sua cadeia antiga pode passar. Não prometo detectar rollback completo
sem referência externa confiável; não acrescento uma agora. HMAC não oferece
verificação pública independente como assinatura assimétrica. A página pública
futura consulta o servidor. Colisão de alias continua possível e o UUID privado
permanece a identidade interna; não adiciono resolução aleatória ou persistente.

**Ação documental futura:** na etapa de spec/build, registrar a necessidade de
sincronizar Q3/P7 e a limitação A1 em `docs/ARQUITETURA.md`, mediante autorização
para essa edição. Não alterei a arquitetura nesta consolidação; a decisão vigente
para preparar a 3.4 está explícita nesta story.

## 8. Critérios de aceite da futura implementação

Os critérios abaixo refletem P1–P20 e A1–A5 aprovadas. A futura spec detalha
a API e os testes dentro desses contratos; sua execução ainda não foi autorizada.

1. **CA1 — Pseudônimo:** mesma chave/lote/usuário produz alias idêntico; vetores
   escolhidos com lote/usuário/segredo diferentes produzem aliases diferentes;
   formato exato aprovado; nenhuma entrada de nome/e-mail, nenhum ID real na saída.
2. **CA2 — Canônico v1:** exatamente os sete campos do AD-21, `v: 1`, bytes UTF-8
   literais esperados, independente da ordem de construção; UUID lowercase,
   números inteiros JSON, UTC com seis casas e `Z`, sem espaços/BOM/newline extras.
3. **CA3 — Hash:** SHA-256 de CA2, golden digest fixo; previous hash participa;
   primeiro lance usa genesis; campos alterados nos vetores mudam o hash.
4. **CA4 — Âncora:** campos/versão aprovados, golden bytes e HMAC fixos; cada um
   de lote/count/final hash participa; segredo diferente não autentica a entrada.
5. **CA5 — Validação:** tipos, dinheiro, contador, timestamp, alias e hashes
   inválidos são recusados conforme tabela aprovada, sem coerções silenciosas.
6. **CA6 — Pureza:** nenhum banco, rede, relógio ou ambiente nos primitives;
   sem FastAPI/SQLAlchemy/ORM; segredos explícitos conforme P3; entradas não
   mutadas. `app.money` pode carregar Pydantic transitivamente, como na 3.2.
7. **CA7 — Vazio/genesis:** estado vazio conforme P17, primeiros links conforme
   AD-21; não confundir hash zero com HMAC zero nem ausência com autenticidade.
8. **CA8 — Verificação pura:** HMAC correto/errado conferido com
   `compare_digest`; algoritmo de cadeia em memória conforme P18, com sequência,
   genesis, links e hashes. A spec delimita a composição com a âncora para detectar
   truncamento/recálculo, sem auditoria PostgreSQL ou endpoint na 3.3.
9. **CA9 — Integração preparada:** contratos documentados para receber na 3.4
   UUIDs, timestamp, sequência e previous hash autoritativos; nenhuma persistência
   ou adaptação ORM antecipada.
10. **CA10 — Entrega futura:** testes determinísticos aprovados, regressões e
    verify documentados com saída real, sem afrouxar testes existentes; nenhuma
    funcionalidade fora de escopo. Nesta sessão apenas planejei essas verificações.

## 9. Matriz de testes planejada

| Grupo | Casos e prova |
| --- | --- |
| Pseudônimo | Repetição; UUIDs de mesmo valor em objetos diferentes; UUID construído de representação uppercase resulta nos mesmos bytes; lot/user/segredo diferentes nos vetores; vetor conhecido com segredo falso fixo; prefixo, case e tamanho exatos; saída sem UUID/nome/e-mail |
| Canônico | Pelo menos um vetor de bytes **escrito literalmente** no teste, sem usar serializer produtivo para montar expected. Construção keyword em outra ordem; campos exatos; `v` número 1; inteiros não strings; UUID lowercase; sem espaços/newline/BOM; zero e seis microssegundos; offset para UTC e mudança de dia; repetição idêntica |
| Unicode/alias | Formato aprovado por A2; recusar acentos, confusáveis, whitespace, controle, vazio e case errado; não criar entrada Unicode inválida só para testar ensure_ascii. |
| Timestamp | Naive, date em vez de datetime, string, None e tzinfo sem offset; UTC; offset positivo/negativo; `.000000Z` e `.123456Z`; dois folds com instantes distintos; mesmo instante em fusos distintos; extremos que cabem e tratamento de overflow a detalhar na spec |
| Hash | Golden SHA-256 literal; mudança de um campo/bit em vetor fixo; previous hash alterado; genesis exato; retorno 64 lowercase hex; hashes curtos/longos, uppercase, whitespace e não hex recusados conforme P13 |
| Composição em memória | Primeiro usa genesis, segundo usa hash do primeiro, terceiro usa hash do segundo. Alterar primeiro mantendo links/digests antigos rompe coerência. Remover/inserir linha muda continuidade/quantidade. São provas de composição dos primitives, não API de auditoria completa |
| Algoritmo puro de cadeia (P18) | Planejar entradas mínimas e verificar sequência 1..n, ordem recebida, duplicatas/lacunas, genesis inicial, links e hashes. A spec delimita a checagem de mesmo lote e a composição de count/final hash com âncora autenticada. Testar alteração, inserção, remoção intermediária e, pela composição autenticada, truncamento/recálculo sem segredo. Sem ordenar ou reparar silenciosamente |
| Âncora | Golden bytes/HMAC literais; repetição; mudar isoladamente lot_id, bid_count, final_hash ou segredo; HMAC com formato válido e conteúdo errado; compare_digest no caminho válido (spy simples, sem medição temporal); vazio conforme P17 |
| Validação | bool, float, str, None em campos numéricos; sequence zero/negativo e 1 válido; count zero/negativo; amount zero/negativo/MAX_CENTS/MAX_CENTS+1; UUID de tipo inválido; alias inválido; secrets vazios e tipos conforme P20; campos extras/ausentes; versão não selecionável pelo chamador |
| Pureza | Allowlist AST de imports; proibir app.config, os/environ, I/O e infraestrutura; reutilizar o detector de relógio com aliases/factories já corrigido; controles positivos e negativos da guarda; não duplicar MAX_CENTS; imutabilidade conforme P2 |
| Regressão | Testes existentes da 3.1/3.2 preservados; verify futuro mantém integração PostgreSQL já existente. AD-17: testes reais de cadeia persistida na 3.4 e adulteração direta na 5.1 |

**Golden vectors são requisito, não opção.** Na futura spec/implementação, fixar
mensagem exata de pseudônimo, alias esperado, bytes JSON completos do bid,
SHA-256 completo, bytes JSON completos da âncora e HMAC completo (A3). Gerar/conferir valores de referência
fora da implementação produtiva (por exemplo, ferramenta independente sobre os
bytes literais revisados), registrar o procedimento e colar os resultados como
literais nos testes. Nunca `expected = mesma_função(...)`, nem gerar todos os
esperados com o serializer sob teste. Usar somente segredos fictícios claramente
identificados como fixtures. Nenhum segredo operacional ou novo secret de deploy.

Os formatos estão decididos. A spec/implementação futura fixará os vetores
literais e seu procedimento de conferência; esta consolidação não cria testes
nem executa os primitives.
Planejo mutações pequenas e restauradas na implementação autorizada: mudar
separadores, remover microssegundos, excluir previous hash, omitir count da âncora
e aceitar bool; golden/validação devem falhar. Não executei mutações nesta sessão.

## 10. Divergências e riscos encontrados

1. **Skill — resolvido:** o fallback foi necessário na criação anterior. Conforme
   informação desta consolidação, BMAD 6.12.4 e compatibility shims estão funcionais.
   Não há bloqueio atual nem motivo para recriar o artefato.
2. **AD-20 versus Q3 — resolvido nesta story:** P7 exige alias persistido por
   evento, sem tabela de mapeamento; A1 declara rotação transparente fora do escopo.
   A arquitetura ainda precisa refletir esse fechamento em etapa futura autorizada.
3. **“Segredos vêm do ambiente” nos ACs:** origem operacional não obriga domínio
   a ler ambiente; P3 decidiu injeção. Diferenciar contrato técnico/configuração.
4. **AD-17 versus testes puros:** não é incompatibilidade arquitetural. Há,
   porém, dependência real do harness em PostgreSQL até para pytest focado.
   Não prometo execução sem banco com o runner atual nem crio banco novo.
5. **Challenge amplo versus garantia criptográfica:** enunciado exige detectar
   adulteração; AD-13 já limita segredo comprometido/rollback completo. Não
   ampliar a promessa; levar a limitação ao README no momento planejado.
6. **Planejamento de adulteração:** o prompt menciona 3.4 ou posteriores; o
   `epics.md` aloca explicitamente os cinco ataques diretos ao banco na 5.1.
   A 3.4 já deve provar atomicidade e consistência de cadeia/âncora em PostgreSQL.
7. **Texto histórico:** abertura de ARQUITETURA ainda afirma não haver código;
   epics diz não existir documento UX, mas DESIGN/EXPERIENCE já existem aprovados.
   Trechos “estado atual” da story/spec 3.2 descrevem antes da implementação;
   hoje lot_time já está extraído e valida todos os horários. Uso código e registro
   final como evidência, sem alterar a 3.2.
8. **Dívida administrativa:** Epic 1 ainda `in-progress` embora stories estejam
   done; deferred antigo cita 1.4 em review; histórico de IA cita Epic 2 em andamento
   enquanto sprint está done. Não corrijo dívidas de outros épicos.
9. **Deploy:** README registra preparação ainda pendente para stories anteriores;
   não há validação de deploy nesta sessão. Não infiro estado publicado a partir
   de status done nem verifico por rede.
10. **Escopo HTTP herdado:** texto da 3.2 atribui parte do endpoint à 3.5, mas o
    epics explicita POST transacional na 3.4 e UI na 3.5. Não resolvo esse detalhe
    antecipadamente: integridade pura da 3.3 não depende de rota.

## 11. Tarefas e arquivos previstos

- [x] Ler fontes e inspecionar implementação real sem executar aplicação/banco.
- [x] Criar esta story por fallback; registrar decisões abertas, opções e testes.
- [x] Atualizar apenas 3.3 e last_updated no sprint.
- [x] Decidir P1–P20 e A1–A5; registrar aprovação/alternativas descartadas.
- [x] Consolidar a story e sincronizar escopo, critérios, testes e riscos.
- [x] API mínima de cadeia definida na spec fornecida e implementada (P18).
- [x] Planejar sincronização futura de Q3/P7 e A1 na arquitetura, sem editá-la agora (seção 13).
- [x] Spec pronta fornecida como fonte de verdade; não rerodar `bmad-spec` no build.
- [x] Implementar primitives e testes após autorização própria.
- [x] Executar verificações e registrar saídas reais.
- [x] Revisão independente, correção do F-01 e re-review final: aprovada para `done` (seção 14).

| Arquivo | Situação |
| --- | --- |
| Este arquivo | Criado na etapa anterior; único arquivo alterado nesta consolidação |
| `sprint-status.yaml` | Atualizado na criação anterior; intocado nesta consolidação, 3.3 ready-for-dev |
| `backend/app/bid_integrity.py` | Aprovado por P1; **não criado** |
| `backend/tests/test_bid_integrity.py` | Proposta para futura spec; **não criado** |
| Guarda de pureza | Futuro acréscimo conforme spec aprovada; testes da 3.2 intocados agora |
| `docs/uso_de_ia.md` | Leitura somente agora; registrar criação/decisões na etapa de desenvolvimento, como precedente da 3.2 |

## 12. Definition of Done futura e encerramento desta sessão

As decisões estão registradas. Para concluir a implementação da story no futuro,
ainda preciso de spec autorizada, primitives implementados, golden vectors independentes, testes e
verify com resultados reais, documentação sincronizada e revisão conforme fluxo.
Criar esta story não satisfaz essa Definition of Done nem valida a implementação.

Nesta sessão: **nenhum código implementado; nenhuma migration criada/executada;
nenhum banco alterado; nenhum Git (incluindo status/diff/commit/push); nenhum deploy;
nenhum `.env*` ou segredo real lido; `bmad-spec` não executado; workflow `bmad-build`
não executado; Story 3.4 não iniciada; artefato/spec/código da 3.2 preservados.**
Não executei testes de aplicação. A verificação desta entrega é documental.

Na criação anterior, a 3.3 passou de `backlog` para `ready-for-dev`. Nesta
consolidação, o sprint e seu `last_updated` permanecem intocados; 3.1/3.2 `done`,
Epic 3 `in-progress`, 3.4+ `backlog`. ARQUITETURA.md também permanece intocado.

**Parei após consolidar as decisões. Não resta decisão bloqueante atual para
a futura spec; não a executei, não executei build nem rerodei create-story.**


## 13. Implementação autorizada — 26/10/2026

Implementei exclusivamente a Story 3.3 com a spec fornecida em
`_bmad-output/specs/spec-story-3-3-integridade-historico/SPEC.md` e os companions
obrigatórios, sem redefinir P1–P20/A1–A5 ou D1–D14. Não há chave `context:` no
frontmatter desta SPEC; li os companions, inclusive ARQUITETURA. A execução
termina em `review`: não executei `bmad-code-review`, não houve revisão independente
nem aprovação para `done`. As seções anteriores preservam o histórico pré-build.

### Arquivos entregues e APIs

- `backend/app/bid_integrity.py`: único módulo produtivo novo; três dataclasses
  `frozen=True, kw_only=True, init=False` com sentinela/construtores explícitos,
  validações locais, UTC e uma única definição produtiva de GENESIS_HASH.
- `backend/tests/test_bid_integrity.py`: 95 casos coletados da matriz, incluindo
  G1–G9 literais, spies delegantes de HMAC/JSON/compare_digest, instantes/extremos,
  imutabilidade, cadeia e composição autenticada local de teste.
- `backend/tests/test_domain_purity.py`: módulo acrescido às guardas existentes;
  allowlist específica, imports internos limitados a MAX_CENTS/require_aware,
  imports relativos/wildcard recusados, referências a builtins de I/O/execução
  dinâmica detectadas por AST com controles positivos/negativos. Detector de
  relógio e testes anteriores preservados.
- Este artefato, `sprint-status.yaml` e `docs/uso_de_ia.md`: evidências e status.

Contrato público implementado (somente sete funções):

```python
GENESIS_HASH = "0" * 64
CanonicalBid(v, lot_id, sequence, bidder_alias, amount_cents, timestamp, previous_hash)
AnchorState(v, lot_id, bid_count, final_hash)
VerifiableBid(bid, current_hash)
# Os três construtores exigem keywords; campos ausentes/extras -> ValueError.
generate_bidder_alias(*, lot_id: UUID, user_id: UUID, pseudonym_secret: bytes) -> str
canonical_bid_bytes(bid: CanonicalBid) -> bytes
compute_bid_hash(bid: CanonicalBid) -> str
canonical_anchor_bytes(state: AnchorState) -> bytes
compute_anchor_hmac(state: AnchorState, *, audit_hmac_secret: bytes) -> str
verify_anchor_hmac(state: AnchorState, signature: str, *, audit_hmac_secret: bytes) -> bool
verify_bid_chain(records: tuple[VerifiableBid, ...], *, lot_id: UUID) -> bool
```

`v` é int estrito 1; contadores são int estritos (sequence>=1, count>=0), sem teto
artificial. Amount é 1..MAX_CENTS compartilhado. UUID/datetime tipados; timestamp
aware convertido por instante para UTC representável, seis casas e Z. Alias ASCII
`Licitante-` + 16 hex uppercase; hashes/assinatura 64 hex lowercase; secrets bytes
estritos não vazios, inclusive uma chave fictícia de um byte válida. Não há coerção
silenciosa, acesso a ambiente/relógio/infraestrutura nem leitura de segredo operacional
pelo agente. Entradas inválidas geram ValueError, mismatches bem formados False.

### Evidências executadas

Configuração dos comandos: cache uv temporário e valores
locais fictícios já publicados no verify: DATABASE_URL termina em
`casa_de_leiloes_dev`, TEST_DATABASE_URL em `casa_de_leiloes_test`, ambos no
PostgreSQL loopback porta 5432; APP_ORIGIN `http://localhost:5173`. O harness atual
prepara o schema PostgreSQL de teste mesmo para os testes puros; foi preservado.

1. Antes do módulo, `uv run pytest tests/test_bid_integrity.py -q`: primeira
   tentativa isolada parou com PostgreSQL inacessível no sandbox (exit 3); a
   execução com acesso local autorizado chegou à coleta e falhou com
   ModuleNotFoundError de `app.bid_integrity` (exit 2). Isto é falha de coleta,
   não teste vermelho comportamental. Os testes vermelhos de comportamento são
   os mutantes abaixo; não reivindico ciclo red comportamental anterior ao módulo.
2. Após implementação e formatação, `uv run pytest tests/test_bid_integrity.py
   tests/test_domain_purity.py tests/test_bid_rules.py tests/test_lot_time.py
   tests/test_wallet_rules.py -q`: **573 passed em 0,35 s**, exit 0.
3. Mutações isoladas por script temporário, cópia/restauração em finally e
   **cmp exit 0 após cada mutante**. Cada seleção abaixo terminou exit 1 com
   falha comportamental, sem erro de sintaxe/coleta; nenhum mutante sobrevivente.
4. Mesmo comando focado após restauração: **573 passed em 0,34 s**, exit 0.
5. `./verify.sh`: **exit 0**, Ruff limpo, **73 arquivos** formatados, PostgreSQL
   real dedicado de teste, **1719 passed, 1 warning em 49,42 s**, ESLint,
   typecheck, **114 testes frontend**, Vite e Docker build aprovados. Warning
   herdado de Starlette/httpx; sem E2E opt-in por não haver mudança de interface.

| Mutante executado | Teste que falhou (nome em test_bid_integrity.py) |
| --- | --- |
| M1 sort_keys=False | test_golden_bytes_and_digests; test_serializer_options |
| M2 separadores com espaços | test_golden_bytes_and_digests |
| M3 SHA-512 de linha | test_golden_bytes_and_digests |
| M4 previous_hash ausente no payload | test_golden_bytes_and_digests |
| M5 validar hash após lower(), aceitando uppercase | test_strict_hashes[uppercase A ×64] |
| M6 alias truncado a 8 hex | test_pseudonym_golden |
| M7 == no lugar de compare_digest | test_verify_uses_compare_digest |
| M8 omitir bid_count da âncora | test_golden_bytes_and_digests |
| M9 isoformat sem timespec | test_timestamp_microseconds[0] |
| M10 permitir secret vazio | test_secrets[bytes vazio] |
| M11 aceitar bool com isinstance(int) | test_invalid_fields (v dos dois tipos, sequence, amount_cents, bid_count) |
| M12 ignorar continuidade sequence | test_chain_mismatches |
| M13 ignorar genesis/link anterior | test_chain_mismatches |
| M14 ignorar lot_id na cadeia (pedido explícito) | test_chain_mismatches |
| M15 genesis com 64 uns (pedido explícito) | test_golden_bytes_and_digests |

Os logs e o script manual de mutação foram mantidos apenas na área temporária
da sessão, sem dependências ou scripts permanentes novos no repositório.

### Autenticação anterior e fronteiras

A composição local dos testes segue §9: avalia cadeia e HMAC anterior antes de
combinar resultados e exige vínculo de lote/count/final_hash. O gate só constrói
novo bid/estado e emite nova âncora após sucesso. Histórico recalculado com
assinatura antiga, count/hash alterados, resumo antigo assinado sobre cadeia
alterada, truncamento e replay de vazio B para A retornam False e deixam a lista
de emissões vazia. Ausência de assinatura em vazio causa ValueError, sem bootstrap.
Controles com três bids e vazio autenticado do próprio lote emitem exatamente uma
âncora válida; UUIDs iguais por valor mas distintos por identidade são aceitos.
Também testei alteração somente do último bid com recálculo local: a cadeia é
consistente, mas a composição anterior bloqueia extensão. A auditoria nunca chama
generate_bidder_alias: usa o valor histórico.

Estes testes em memória não demonstram atomicidade nem adulteração PostgreSQL
AD-17. A 3.4 deve inicializar vazio confiável para lotes novos/existentes/seed,
autenticar/vincular o estado anterior sob trava antes de efeitos, persistir alias
por lance e atualizar linha/âncora atomicamente. Os cinco ataques persistidos são
obrigação da 5.1. Rollback integral com cadeia e âncora antiga válidas e segredo
comprometido permanecem limites deliberados; alias de 64 bits pode colidir;
segredos não têm rotação transparente. Inteiros enormes continuam sujeitos aos
limites de serialização/recursos nativos, sem alterar opções globais.

**Pendência documental anterior à 3.4:** sincronizar Q3/P7/A1 e exemplo de 16 hex
em ARQUITETURA/CLAUDE/epics em escopo autorizado. Não editei esses documentos,
não redesenhei ADs e não antecipei persistência. Nenhuma migration, ORM, configuração,
endpoint, carteira, frontend ou dependência foi alterada. Nenhum Git, deploy,
leitura de `.env*`/credenciais/segredos ou início da Story 3.4.


## 14. Code review, correção do F-01 e fechamento — 26/10/2026

As seções 1–13 preservam o histórico até a entrega em `review`.

**F-01 (LOW) — RESOLVIDO.** Os testes não protegiam a rejeição de subclasses de
`int`: uma mutação equivalente a `isinstance(value, int)` com tratamento separado
de `bool` mantinha a suíte verde. O código produtivo (`type(value) is int`) já
estava correto e não foi alterado. Corrigi apenas `backend/tests/test_bid_integrity.py`
com subclasses locais (`CustomInt`, `CustomStr`, `CustomBytes`), cobrindo `int`
(`v` de `CanonicalBid` e `AnchorState`, `sequence`, `amount_cents`, `bid_count`),
`str` (alias, hashes e assinatura) e `bytes` (segredos), conforme os tipos exatos
exigidos pela spec (`integrity-contract.md`, `decisions.md`).

**Evidência da correção e do re-review final:**

- Mutação do F-01: suíte nova falhou nos 5 casos de `int` e voltou a passar após
  restaurar o módulo (conferido por hash).
- Re-review: F-01 corrigido; regressões nenhuma; qualidade dos novos testes
  adequada; `test_bid_integrity.py` 105 passed; subclasses em 10 testes / 13
  asserções; mutações de int/str/bytes mortas; nenhum arquivo produtivo alterado.
- Último `./verify.sh` completo após a correção: back-end 1729 passed, front-end
  114 passed, Ruff, typecheck, build do Vite e Docker build aprovados; 1 warning
  herdado de Starlette/httpx.

**Decisão:** recomendação final APROVADA PARA DONE; Story 3.3 `done`. Epic 3
permanece `in-progress`.

**Pendência herdada, não bloqueante para `done`:** a sincronização de Q3/P7/A1 e do
exemplo de 16 hex em ARQUITETURA/CLAUDE/epics foi registrada na seção 13 como
pendência *antes da integração da 3.4*, não como condição de `done`. Não editei
esses documentos neste fechamento.
