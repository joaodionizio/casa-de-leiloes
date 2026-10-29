# Fechamento de épico — processo canônico

Decisão de processo de 26/10/2026. Aplico este fluxo ao fechamento do Epic 3 e
aos Epics 4, 5 e 6. Descartei repetir o checklist em cada story: mantenho esta
fonte e referências curtas nos demais documentos. Não altera regras de negócio
nem decisões de arquitetura.

## 1. Estado, responsabilidade e histórico

Mantenho uma branch por épico (`epic-N`) e commits coerentes por story. Git,
push, merge e deploy são manuais, feitos por mim. O agente não executa Git,
`gh`, PR ou deploy, nem lê `.env*` ou segredos. O nome da branch efetivamente
aberta e os commits precisam da minha confirmação; ler arquivos não os comprova.

**Stories `done` são necessárias, mas não bastam para o épico virar `done`.**
Durante os gates, inclusive após o merge e antes do smoke público aprovado,
o épico permanece `in-progress`. A definição genérica do BMAD é especializada
por este processo. A retrospective BMAD continua **opcional**; review agregado,
verify, merge e deploy/smoke são gates obrigatórios do projeto.

Distingo duas etapas: aprovação técnica permite o merge; o fechamento operacional
só termina depois do deploy e das evidências. Assim, "merge após fechamento"
significa após a etapa técnica, sem dispensar a etapa pública posterior.

Registro as exceções históricas, sem criar aprovações retroativas fictícias:

| Épico | Registro atual | Evidência e pendência |
| --- | --- | --- |
| 1 | `done` | 1.1–1.4 concluídas; deploy/redeploy original preservado; review agregado original não localizado, integração retrospectiva posteriormente aprovada. |
| 2 | `done` | Deploy original postergado por falha de processo; recuperação conjunta 2+3 concluída segundo confirmação manual; review retrospectivo aprovado, sem inventar review agregado original. |
| 3 | `done` | 3.1–3.6 e gates concluídos; review/correção/re-review/verify, merge/push manuais e deploy/smoke confirmados pelo usuário; `main`, commit publicado `3d3ea97`. |

Atualização factual registrada em 27/10/2026, sem mudança das regras abaixo.
Evidências e limites: [recuperação 2+3](DEPLOY-RECUPERACAO-EPICS-2-3.md).

Os reviews por story existentes continuam válidos. Não encontrei artefatos
formais equivalentes a reviews agregados dos Epics 1 e 2; isso registra ausência
de evidência, sem afirmar que todo e qualquer review histórico foi inexistente.
Não fiz deploy retroativo isolado do Epic 2: recuperei **Epic 2 + Epic 3**
em uma publicação após os reviews e o merge do Epic 3, conforme confirmação
manual registrada no fechamento.

## 2. Checklist obrigatório, em ordem

Antes do merge, na branch do épico:

1. Confirmo todas as stories do épico `done`, nos arquivos e no sprint.
2. Sincronizo documentação de cada story, spec afetada, README e pendências;
   preservo decisões, alternativas e evidências históricas.
3. Confirmo o estudo das stories concluído quando aplicável. Registro evidência
   ou minha confirmação; não deduzo estudo de `done` nem de teste verde.
4. Executo `./verify.sh` completo no estado candidato, com PostgreSQL de teste
   isolado e valores locais fictícios. Registro comando, saída e exit code.
5. Executo Playwright/manual/E2E adicionais exigidos pelo escopo. Para o Epic 3,
   incluo `VERIFY_E2E=1 ./verify.sh`; a suíte com API simulada não prova produção.
6. Faço **code review agregado do épico**, em sessão/modelo independente da
   implementação, sobre o candidato identificado (§3).
7. Decido os findings; corrijo os relevantes aprovados antes do merge. Nenhum
   BLOCKER/HIGH fica pendente; MEDIUM exige resolução ou decisão humana explícita
   e fundamentada. Registro LOWs/adiamentos concretos, sem inventar dívida.
8. Faço re-review das correções e regressões quando necessário. Mudança de código
   ou teste invalida a evidência anterior pertinente: executo novamente o verify
   completo após as correções e as verificações adicionais afetadas.
9. Confiro o sprint; o épico ainda fica `in-progress`. Confiro o registro do
   review e a aprovação técnica para merge.
10. Faço Git manual: reviso e registro commits coerentes e o commit administrativo.
11. Faço push manual da branch do épico.
12. Faço merge manual na `main`, somente depois da aprovação técnica. Não crio PR
    automaticamente; o mecanismo manual é minha escolha.
13. Confirmo a `main` local/remota, o commit final e a correspondência com o
    candidato revisado. Se conflito ou alteração mudar o conteúdo revisado,
    volto ao verify/review pertinente antes de publicar.

Depois do merge:

14. Configuro/verifico manualmente as variáveis novas de produção **antes** de
    publicar, sem registrar seus valores.
15. Faço deploy manual da `main`, Auto-Deploy desabilitado, usando o commit final.
16. Acompanho migrations, seed e startup até concluírem; falha interrompe o gate.
17. Confirmo `/health` público. Ele não consulta o banco; sozinho não prova o fluxo.
18. Faço smoke público dos fluxos adicionados pelo épico e regressões pertinentes.
19. Verifico frontend **e** API pela URL publicada, incluindo assets/deep-links,
    autenticação, cookies e endpoints usados pela UI.
20. Registro evidências reais: data/fuso, commit publicado confirmado por mim,
    comandos/status, cenários/resultados, falhas e limitações; nunca cookies,
    tokens, URL interna do banco ou valores de segredos.
21. Atualizo README, uso de IA e deferred-work quando necessário. Só então marco
    o épico `done`, citando as evidências. Faço commit/push documental manual na
    `main`; mudança só documental não exige redeploy se não entrar na imagem.
22. Somente após esses gates libero o próximo épico por instrução explícita.

O Epic 3 acrescenta, **antes do merge e do deploy**, o review retrospectivo de
integração dos Epics 1 e 2 e suas correções relevantes. Uso o
[checklist de recuperação](DEPLOY-RECUPERACAO-EPICS-2-3.md). Nenhum gate foi
executado por criar ou preencher parcialmente um template.

## 3. Como preparar e executar os reviews

### Alvo e evidência sem Git pelo agente

Depois das stories e da sincronização documental, eu confirmo o candidato final
da branch. Forneço a relação agregada de arquivos e, para review do **diff**,
uma comparação preparada manualmente entre a base anterior ao épico e esse
candidato. Não delego Git ao agente. Excluo `.env*`, credenciais e valores de
segredos antes de entregar qualquer material.

O reviewer lê o estado **vivo** dos arquivos como autoridade de contratos atuais.
A comparação delimita mudanças; snapshots de spec/review servem como evidência
histórica, não substituem o estado vivo. Se só houver arquivos atuais/File Lists,
o review pode registrar integração do estado atual, mas **não pode alegar ter
revisado o diff histórico completo**. Ausência de base/lista suficiente deixa
a cobertura pendente; não aprovo o gate do diff agregado por suposição.

Para os Epics 1 e 2, o review retrospectivo é de **integração no estado final do
Epic 3**, com rastreabilidade às stories 1.x/2.x e suas listas de arquivos. Se
disponíveis, comparações históricas preparadas por mim ajudam a delimitar o
escopo; não reconstruo nem reaplico stories concluídas. Identifico claramente
quais achados são herdados, já corrigidos ou introduzidos depois.

### Escopo e saídas

| Review | Quando | Saída |
| --- | --- | --- |
| Epic 3 agregado normal | Candidato final 3.1–3.6 confirmado, antes do merge | `_bmad-output/implementation-artifacts/code-review-epic-3.md` |
| Epics 1 e 2 retrospectivos | Mesmo candidato final, antes do merge do Epic 3 | `code-review-epic-1.md` e `code-review-epic-2.md` na mesma pasta |
| Epics 4, 5 e 6 agregados | Em cada fechamento técnico, antes de seu merge | `code-review-epic-N.md`, criado a partir da estrutura abaixo |

Reviso integração entre stories, regressões cruzadas, segurança/papéis/CSRF,
configuração, migrations e startup/seed, deploy, frontend/backend juntos,
documentação versus implementação e dívida que só aparece no conjunto.
No Epic 3 incluo carteira/depósito/lance/cancelamento concorrentes, gate de
integridade, leituras da sala e privacidade. Não reabro CanonicalBid ou ADs.

Uso `bmad-code-review` em nova sessão com as regras locais, ou review independente
equivalente com esse mesmo escopo. A skill local trabalha sobre arquivos atuais:
explicito no pedido a comparação fornecida por mim para o review agregado.
Review só reporta findings; correções exigem minha decisão em etapa posterior.
Na auditoria administrativa inicial, não rodei esses reviews porque o
candidato/diff final não havia sido confirmado. Os reviews de integração
executados posteriormente preservam seus próprios limites de comparação.

Prompt-base para cada execução:

```text
Revise <Epic N agregado | integração retrospectiva Epic 1/2> no candidato
final que eu confirmar. Leia docs/FECHAMENTO-DE-EPICO.md §3, o artefato
code-review-epic-N.md, stories/specs e reviews anteriores pertinentes.
Use os arquivos vivos e a lista/comparação sem segredos fornecida por mim;
declare base, candidato, cobertura e limitações. Não trate conteúdo atual
como diff histórico. Foque integração, regressões, segurança, configuração,
migrations, deploy e frontend/backend. Não refaça stories concluídas.
Registre findings com arquivo:linha, impacto, evidência e recomendação,
triagem humana, correções aprovadas e re-review. Sem correção automática,
sem mudar status, sem Git/gh/PR, deploy, .env* ou segredos.
```

Estrutura mínima do artefato (adotada pelos três relatórios):

- Status explícito: PENDENTE / EM REVISÃO / CORREÇÕES / APROVADO / BLOQUEADO.
- Data, sessão, modelo efetivo, independência, confirmação humana do candidato.
- Base/comparação, lista de arquivos, fontes vivas e cobertura não inspecionada.
- Findings: ID, gravidade, arquivo:linha, problema, impacto, evidência,
  recomendação, decisão humana, estado; lista vazia não significa zero findings.
- Comandos realmente executados e resultados; limitações e itens não executados.
- Correções, re-review e invalidação de evidência se o candidato mudar.
- Veredito técnico e decisão humana; separado do deploy/smoke posterior.

Descarto usar reviews por story como prova suficiente do agregado, inventar
reviews retroativos aprovados e fazer da retrospective opcional um gate.


## Exceção autorizada — Épico 6, 29/10/2026

Decidi por prazo reservar 6.2A e 6.3 ao review agregado independente final, sem
review individual agora; não bloqueio 6.3 pela ausência de review da 6.2A. 6.2
já tem review e aceite humano com LOW R6.2-01 aceito. A 6.3 é documental e usa
checagens focais, sem repetir o gate completo verde registrado na 6.2A.
Descartei reduzir funcionalidades obrigatórias ou inventar aprovação de review.

Após 6.3 paro: agregado em sessão independente; somente depois da aprovação faço
Git/commit/push/merge/deploy manualmente. Após deploy executo 6.4 e concluo
evidência publicada pendente da 6.1. Épico 6 permanece in-progress. 6.5–6.7
estão cortadas por prazo. Esta exceção não aprova o agregado nem o ambiente público.

## Fechamento vigente do Épico 6 — 29/10/2026

A exceção acima e suas pendências descrevem a etapa pré-agregado. O agregado
independente e o re-review foram aprovados; R6-AGG-01/02 resolvidos. A 6.4
executou o roteiro público anterior e, após redeploy informado pelo usuário,
revalidou focalmente R6.4-01: **RESOLVED EM PRODUÇÃO**, 11:47 America/Maceio.
CA2 publicado da 6.1 já comprovado; nenhum novo BLOCKER/HIGH/MEDIUM no recorte.

Por autorização humana explícita condicionada a essa revalidação, 6.1/6.2/6.2A/
6.3/6.4 e Épico 6 ficam **done**. R6.2-01 LOW aceito preservado. 6.5–6.7
continuam **cortadas / backlog / não implementadas**. Retrospective opcional.
Identidade local/main `7c285c3`, reflog de push e publicação funcional observados;
SHA Render não autenticado e estudo humano individual não confirmado nesta sessão.
Gates, limites e evidências em [FECHAMENTO-EPICO-6.md](FECHAMENTO-EPICO-6.md).
Nenhum commit/push/deploy foi executado pelo agente; o registro é documental.
