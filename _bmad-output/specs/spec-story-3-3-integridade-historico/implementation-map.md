# Mapa de implementação e conclusão — Story 3.3

## 1. Arquivos da futura implementação

| Arquivo | Ação limitada à 3.3 |
| --- | --- |
| `backend/app/bid_integrity.py` | Criar único módulo puro com contrato completo |
| `backend/tests/test_bid_integrity.py` | Criar matriz, golden literals e composição em memória |
| `backend/tests/test_domain_purity.py` | Acrescentar módulo/allowlist/guardas simples, preservando detector e casos da 3.2 |
| `_bmad-output/implementation-artifacts/3-3-fundamentos-de-integridade-do-histórico.md` | Registrar spec, tarefas, implementação, comandos/resultados, mutações, limitações |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | 3.3 in-progress ao iniciar build; review ao entregar código; done só após fluxo de aprovação; atualizar last_updated sem mexer nas demais stories |
| `docs/uso_de_ia.md` | Nova seção da 3.3 em primeira pessoa: decisões humanas, spec, implementação, revisão/ajustes e evidências reais |

Não criar `test_bid_integrity_purity.py`, package, migration, biblioteca ou
script permanente de geração dos expected. Preservar código de money, bid_rules,
lot_time, lots, wallet, users, config, main, seed, errors, db e demais módulos;
migrations, conftest, testes de integração, frontend, verify.sh e dependências
ficam intocados. Não implementar adaptador ORM nesta story.

## 2. Sincronização documental futura

Decidi registrar aqui a necessidade de sincronizar Q3 com P7 e documentar A1 em
`docs/ARQUITETURA.md`, quando autorizada essa edição: alias persistido por evento,
auditoria usa o valor histórico, sem tabela de mapeamento, segredos estáveis e
rotação transparente não suportada. Atualizar o exemplo ilustrativo antigo de
oito hex para o formato aprovado evita confusão. Isso registra decisões já
aprovadas, sem redesenhar AD-13/20/21. CLAUDE.md Q3 e pendência Q3 do epics também
precisam refletir o fechamento quando houver escopo documental autorizado.

Essa sincronização não bloqueia implementar o primitive aprovado; precisa estar
clara antes de integrar a 3.4. README com garantias/limitações públicas entra na
entrega integrada/documentação final (5.1/6.3), sem prometer auditoria já disponível
na 3.3. Nenhum desses arquivos é alterado na sessão atual de spec.

## 3. Sequência de implementação futura

1. Ler SPEC e todos os companions; confirmar estado dos três precedentes puros.
   Atualizar só status da 3.3 para in-progress na sessão autorizada de build.
2. Escrever testes de tipos/validações/golden literals antes do módulo; registrar
   erro de coleta separadamente de teste vermelho de comportamento.
3. Implementar constante, validadores pequenos e dataclasses, com construtores
   explícitos de D2 e timestamp UTC. Sem alteração em módulos anteriores.
4. Implementar pseudônimo, serializer privado, canônicos, SHA e HMAC/verificação.
   Confirmar G1–G9 e toda matriz de entradas.
5. Implementar VerifiableBid/verify_bid_chain; testes de coerência e composição
   autenticada, incluindo truncamento, recálculo sem segredo, gate anterior à
   extensão e replay cross-lot vazio (S-01/S-02, test-plan §5.1–5.2). A composição
   local dos testes não implementa a transação da 3.4 nem cria API produtiva nova.
6. Ampliar guarda existente de pureza; rodar focados com regressões da 3.1/3.2.
7. Executar mutações de test-plan, restaurar por cópia/cmp e verificar novamente.
8. Rodar verify completo; registrar saídas reais, documentação da implementação
   e status review. Parar na 3.3; revisão independente conforme processo do projeto.

Não executar Git, deploy, criação de segredos ou início da 3.4 como parte dessa
sequência. Não marcar done só porque os testes passaram.

## 4. Riscos e limitações assumidos

| Risco/limitação | Tratamento |
| --- | --- |
| Bytes divergentes por timezone, fração, ordem ou normalização | Golden literals, fold/extremos e mutações específicas |
| Alias truncado de 64 bits pode colidir | Identificação visual apenas; UUID privado preservado; sem promessa matemática de unicidade |
| Mudança de PSEUDONYM_SECRET | Aliases históricos persistidos preservam bytes antigos; novos aliases/consultas podem mudar. Rotação transparente não suportada |
| Mudança de AUDIT_HMAC_SECRET | Chave nova não verifica âncoras antigas; sem key ring, rehash ou reautenticação cega no boot |
| Atacante com segredo de auditoria | Pode autenticar estado adulterado; fora da garantia AD-13 |
| Rollback integral de cadeia e âncora antigas válidas | Pode passar sem referência externa confiável; não acrescento uma nesta entrega |
| HMAC não é assinatura assimétrica pública | A futura página pública consulta o servidor; não recebe o segredo |
| Cadeia consistente confundida com autenticada | Composição exige coerência, comparação de resumo e HMAC; testes negativos explícitos |
| S-01: serviço reautenticar passado adulterado ao aceitar lance legítimo | Proibido: autenticar/vincular estado anterior antes de usar predecessor ou emitir nova âncora; receita §9 e gate puro nos testes. Interrupção transacional real será provada na 3.4 |
| S-02: âncora vazia válida de outro lote | Conferir lot_id esperado explicitamente, mesmo sem registros; composição False e zero emissões novas |
| Vazio sem assinatura usado como atalho de confiança | Nenhum fallback; inicialização confiável deve persistir âncora válida na 3.4 para novos/existentes/seed. Não reautenticar dados arbitrários no lance ou boot |
| Limites do datetime | Instante deve caber em UTC; falha -> ValueError; sem saturação |
| Contadores enormes | Sem teto artificial no domínio; serialização ainda sujeita aos limites nativos de inteiros/recursos do runtime, sem alterar configuração global |
| Dataclass congelada não é sandbox | Protege uso normal, não execução Python hostil/reflexão |
| Pytest focado prepara banco | Harness existente preservado; nenhum teste novo prova persistência. verify somente no build autorizado |
| Pydantic transitivo por money | Aceito por A4; sem import direto ou uso de Cents/Pydantic neste módulo |

## 5. Critérios objetivos para conclusão da implementação

1. CAP-1–CAP-6 demonstradas pela matriz, G1–G9 literais e guardas verdes.
2. Campos, nomes, tipos, assinaturas e limites coincidem com integrity-contract;
   nenhuma normalização silenciosa fora de UTC/str(UUID) prevista.
3. SHA só sobre bytes canônicos; previous_hash participa; HMAC da âncora inclui
   lote/count/final_hash/v; compare_digest demonstrado por spy.
4. Cadeia vazia, continuidade, genesis, lote, links e digests testados; composição
   autentica resumo e detecta os cenários puros de truncamento/recálculo. Os testes
   S-01/S-02 provam que estado anterior bem formado mas sem integridade retorna
   False e não emite nova âncora; estrutura inválida gera ValueError. Controle
   normal e vazio do próprio lote permitem extensão; replay vazio cross-lot não.
5. Mutantes relevantes derrubam testes de comportamento, restauração conferida
   por cmp e suíte restaurada verde; nenhuma ferramenta/framework novo.
6. Verify completo exit 0 com saída real na story; nenhuma asserção existente
   afrouxada; testes puros não apresentados como prova PostgreSQL AD-17.
7. Story/sprint/uso_de_ia atualizados na implementação; restrições e pendência
   documental Q3/P7/A1 registradas. Nenhum teste manual específico exigido.
8. Revisão conforme fluxo do projeto; nenhum blocker/high/medium pendente para
   aprovação. Commit pertence ao usuário. Parar antes da Story 3.4.

## 6. Fora de escopo e estado desta entrega

Decidi não implementar migration, schema, ORM, Session, banco, transação, lock,
clock_timestamp, endpoint, carteira, concorrência, auditoria pública, frontend,
WebSocket, liquidação, receipts, scheduler, KMS ou rotação nesta story pura.
O fluxo de integração em integrity-contract é documentação de consumo, não lista
de implementação da 3.3. O vazio não exige migration nesta etapa.

Na criação inicial produzi somente a pasta de spec: SPEC.md, decisions.md,
integrity-contract.md, golden-vectors.md, test-plan.md, implementation-map.md e
.memlog.md. Não atualizei status da story/sprint nem documentos anteriores.
Spec pronta para `/bmad-build` em sessão futura autorizada; story ainda não
implementada. Não executei testes da aplicação, verify, Git ou deploy.

Na correção S-01/S-02 atualizei somente SPEC.md, decisions.md,
integrity-contract.md, test-plan.md, implementation-map.md e .memlog.md.
Golden vectors, story e sprint permanecem intocados. Não implementei código,
migration, build ou início da 3.4. Suas obrigações de inicialização/autenticação
persistidas são requisitos futuros, não tarefas executadas nesta sessão.

## 7. Autovalidação documental

Passada 1: conferi campos exatos v1, JSON determinístico, UTC/fold/seis casas,
UUID lowercase, alias estrito, bool recusado, hashes lowercase, genesis único,
previous_hash no payload, segredo injetado, SHA distinto de HMAC, compare_digest
e golden expected independente. Conferi também a coerência das capacidades e
a preservação das decisões P1–P20/A1–A5 nos companions.

Passada 2: conferi fronteiras. Migration, ORM, Session, transação, lock, endpoint,
PostgreSQL real novo e frontend aparecem apenas como exclusões ou obrigações
futuras da 3.4/5.1. Nenhum deles integra a lista de código da 3.3. Confirmei 5.1
no epics. Não encontrei incompatibilidade real bloqueante nem reabri decisão.
Essas passadas são autovalidação da spec, não code review independente.

### Autovalidação após S-01/S-02

| Cenário | Simulação conceitual pela receita §9 |
| --- | --- |
| A — normal | Cadeia válida + resumo correspondente do lote esperado + HMAC anterior válida: todas as condições True; pode preparar extensão e emitir nova âncora |
| B — banco adulterado | Cadeia recalculada + resumo alterado + assinatura antiga inválida: hmac_ok=False; parar antes de usar predecessor, alterar estado ou emitir nova âncora, mesmo com novo lance legítimo |
| C — replay cross-lot vazio | () de A + resumo vazio B + HMAC válida de B: verificações isoladas True, igualdade de lote False; composição False, extensão proibida |

Conferi também resumo antigo assinado versus cadeia alterada: vínculo falha;
assinatura ausente: ValueError, sem bootstrap permissivo. S-01 não é limitação
aceita de segredo comprometido ou rollback integral. A receita usa as APIs
anteriores, sem mudar bytes, tipos ou golden vectors. Nenhuma decisão bloqueante
nova para o build da 3.3; o mecanismo concreto de inicialização é obrigação
declarada da 3.4. Fronteiras preservadas: testes em memória agora, interrupção
transacional real e inicialização persistida na integração futura.
