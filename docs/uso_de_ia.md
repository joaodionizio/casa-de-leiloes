# Como usei IA no ÁTRIO

## Resposta curta

Usei IA intensivamente para planejar, especificar, implementar backend e frontend,
escrever testes, revisar código e redigir documentação. As sugestões passaram por
minha decisão: mantive responsabilidade por arquitetura, regras de domínio,
identidade visual, prioridades, aceite de mudanças e publicação.

O resultado é o **ÁTRIO — Leilões de Arte**, de João Luís Dionízio, para o
**Desafio Elite Dev — Verzel**. Requisitos obrigatórios e opcionais estão
concluídos e validados em produção; o Épico 6 está `done`. Este documento explica
meu processo; os links finais permitem conferir as evidências sem repetir o log.

## Ferramentas que usei

| Ferramenta | Uso no projeto |
| --- | --- |
| Claude Code | Planejamento, specs, implementação e reviews em etapas registradas. |
| Codex | Implementação, correções, testes, revisões independentes e documentação. |
| BMAD Method | Organização de planejamento, decisões, specs, stories, critérios de aceite e revisão. |
| Figma / Figma Make | Prototipação inicial dos fluxos, com estudo, revisão e ajustes sob minha direção. |

Separei implementação e revisão em modelos/sessões independentes quando indicado
nos registros. Isso ajudou a questionar as propostas; não tornou nenhum parecer
uma aprovação automática.

## Onde a IA ajudou

- **Planejamento e decomposição:** transformar o enunciado e minhas escolhas em
  epics, stories, dependências e critérios de aceite.
- **Arquitetura e specs:** comparar alternativas e formalizar contratos antes
  da implementação, incluindo concorrência, privacidade e comportamento da Sala.
- **Backend:** escrever serviços, rotas, migrations e integração AIC; implementar
  carteira, lances, integridade, cancelamento e liquidação conforme as decisões.
- **Frontend:** implementar os fluxos React, estados de erro/reconexão,
  responsividade, acessibilidade, temas e refinamentos visuais aprovados.
- **Testes:** propor casos negativos, integração, concorrência, regressões e
  cenários de navegador; executar comandos e registrar resultados e limites.
- **Code review:** procurar falhas de aceitação, segurança, estado e cobertura;
  reproduzir achados e reavaliar correções.
- **Documentação:** redigir e conferir README, arquitetura, specs e evidências
  contra código e resultados, sob meu direcionamento editorial.

## Decisões que mantive sob minha responsabilidade

| Decisão minha | Consequência no produto ou na implementação |
| --- | --- |
| Leiloar arte de domínio público da AIC e criar a identidade ÁTRIO | O acervo e a obra orientam o produto e a apresentação. |
| FastAPI + React/Vite + PostgreSQL; monólito single-origin | Uma publicação reúne SPA/API/WS; descartei microservices na escala do desafio. |
| Dinheiro em centavos inteiros; lote antes das carteiras; hora do banco após a trava | Consistência financeira não depende de float nem do relógio do navegador. |
| SHA-256 encadeado + âncora HMAC e pseudônimos por lote | Auditoria pública sem expor identidade; limites de segredo e rollback são declarados. |
| Lance por REST, atualizações por WebSocket e snapshot no reconnect | Reconexão não reenvia um lance cujo resultado pode ser incerto. |
| Anti-sniping cumulativo sobre o fim vigente | Cada lance válido na janela soma 2 minutos; corrigi a interpretação intermediária e alinhei código/testes. |
| Liquidação por scheduler/catch-up, usando a mesma trava | GET não muda saldo nem liquida; repetição não duplica transferência ou comprovante. |
| Cortar opcionais inicialmente e reativá-los depois | Priorizei o fluxo obrigatório e depois concluí busca/filtros, estorno e dark mode, hoje publicados. |
| Cadastro público para ambos os papéis | Carteira inicial zero, sem login automático; leiloeiro continua sem poder depositar ou dar lance. |
| Senha forte nos dois lados; confirmação só no frontend | Backend exige força; a confirmação é comparada literalmente e não é enviada à API. |
| Preservar a precedência das recusas de lance | O contexto de saldo do líder complementa a interface sem mudar `already_winning` para exibir dois motivos. |
| Triar findings e decidir publicação | Aceitei ou rejeitei mudanças com base em reprodução, impacto e escopo. |

As alternativas e os motivos estão na [arquitetura](ARQUITETURA.md) e nas specs.
Não atribuo cadastro, ajuda contextual, footer ou refinamentos de senha/feedback
financeiro a novas exigências da Verzel: foram escolhas minhas e respostas a
feedback humano externo.

## Figma, protótipos e prevenção de AI slop

Estudei e validei referências visuais antes da implementação. Criei protótipos
no Figma/Figma Make para os principais fluxos, revisei o resultado e descartei
parte da direção inicial que lembrava SaaS ou plataforma de cursos. Não aceitei
a primeira geração como direção visual final.

Defini a identidade ÁTRIO com a obra como protagonista e o roxo como assinatura.
Comparei alternativas com referências de leilão e catálogo, validei escala e
navegação e rejeitei o aspecto genérico de template, o “AI slop”. Usei IA para
organizar feedback e formalizar escolhas já aprovadas em `DESIGN.md`,
`EXPERIENCE.md` e `VITRINE-BLUEPRINT.md`.

Os três artefatos têm funções distintas:

| Artefato | Papel no processo |
| --- | --- |
| Figma | Processo de design/prototipação conduzido por mim, com validação de referências e ajustes. |
| [Protótipo HTML versionado](../ux-designs/casa-de-leiloes/) | Referência navegável de experiência, gerada com apoio de IA; simula estados, sem API, autenticação ou WS reais. |
| [Frontend React](../frontend/src/) | Implementação de produção, sujeita aos contratos do backend e aos testes. |

O [PROTOTIPO.md](../ux-designs/casa-de-leiloes/PROTOTIPO.md) registra cenários e
validações de responsividade, com comparação de larguras até 320 px. O protótipo
não é código de produção e não substitui as regras de estado. Não afirmo que
Figma gerou o frontend React; não há link público do arquivo Figma neste relato.

Depois comparei a implementação com a direção aprovada em desktop/mobile.
Testes de layout, teclado, foco, temas e imagens quebradas complementaram a
inspeção visual. Evitar AI slop exigiu escolher e rejeitar soluções concretas,
não apenas pedir à ferramenta uma interface “bonita”.

## Como verifiquei o trabalho da IA

Usei specs e critérios antes de implementar quando aplicável; depois confrontei
código, comportamento e contrato. Revisões em sessões/modelos independentes
questionaram o resultado, e findings pertinentes exigiram reprodução. Probes e
mutações direcionadas, restauradas após a prova, ajudaram a verificar se os
testes realmente detectavam a falha alegada.

Para dinheiro e integridade, usei PostgreSQL real: sessões concorrentes, travas,
rollback, serialização de lance/cancelamento/liquidação e tentativas de
adulteração. SQLite ou respostas simuladas não provariam essas propriedades.

O `verify.sh` reúne análise estática, testes backend/Node, build frontend e
imagem Docker; `VERIFY_E2E=1` acrescenta Playwright. A suíte padrão de navegador
simula a API: valida interação e estados, sem substituir a stack real. Os
cenários real-stack opt-in e smokes integrados complementaram essa cobertura.
O [README](../README.md#testes-e-alcance-da-verificação) distingue esses comandos
e registra o gate final, sem somar cenários skipped como executados.

Também fiz validações humanas de interface e fluxos nos momentos registrados.
Outros smokes foram executados pela IA em navegador real; não os apresento como
aceite humano novo. O [smoke público final](../_bmad-output/implementation-artifacts/smoke-publico-final-6-5-6-7.md)
valida os opcionais/refinamentos publicados e preserva os limites do recorte.
Teste verde não foi minha única prova: imagem real, layout e estados assíncronos
revelaram problemas que as verificações anteriores não haviam detectado.

## Erros e revisões que mudaram o resultado

1. **Imagens externas com 403.** Meu teste no navegador encontrou hotlinks IIIF
   bloqueados, embora o smoke do servidor passasse. Aprovei um proxy same-origin
   de destino fixo e placeholder; revalidei imagens reais, sem armazenar os bytes.
2. **Tela branca por `Intl.DateTimeFormat`.** A combinação inválida de opções
   passou pelo gate e falhou ao importar o módulo no navegador. O teste manual
   revelou a falha; corrigi a formatação com apoio da IA e conferi a tela real.
3. **Estado terminal durante retry — R6-AGG-01.** A revisão independente apontou
   que um GET atrasado podia perder o estado terminal conhecido da Sala. A
   correção conserva o snapshot e impede regressão; o teste retém o GET, entrega
   o evento terminal e só depois libera a resposta antiga.
4. **Encerrado em apuração versus liquidado — R6.4-01.** O smoke publicado
   mostrou a Vitrine indicando apuração para um lote já liquidado. Acrescentei
   `settlement_status` ao contrato público e alinhei os rótulos; a correção foi
   revalidada em produção.
5. **Várias ajudas abertas — R6-OPT-01.** O probe independente demonstrou que
   estados locais permitiam abrir várias ajudas, e o próprio E2E aceitava isso.
   Corrigi o componente para uma identificação ativa compartilhada e ajustei os
   testes; re-review e smoke publicado confirmaram exclusividade e fechamento.

A revisão da regra cumulativa de anti-sniping também está documentada nas
[evidências específicas](EVIDENCIA-ANTI-SNIPING-CUMULATIVO.md). Os exemplos acima
não são uma lista de defeitos atuais: as correções foram incorporadas e validadas.

## O que a IA não fez sozinha

Mantive as decisões finais, direção visual, validação das referências,
priorização e aceite/rejeição de findings. Também mantive sob meu controle
credenciais, segredos, decisões de produção e envio da candidatura.

Mantive Git remoto, merge e deploy sob meu controle, com operações manuais
documentadas nos registros de publicação. A decisão de publicar foi minha;
autoria, execução e limites de cada validação constam das evidências.

A publicação funcional está comprovada nos registros. O SHA informado identifica
local/main; não o apresento como SHA autenticado pelo painel do Render. No smoke
final, Cloudflare/403 no destino oficial da coleção AIC foi uma ressalva LOW
externa, sem defeito do ÁTRIO confirmado.

## Correção do lance apresentado na Vitrine (29/10/2026)

Usei Codex para corrigir a divergência de apresentação encontrada em produção:
a Vitrine anunciava sempre o lance inicial, enquanto a Sala já apresentava o
lance vigente. Autorizei somente a extensão do contrato público com
`current_bid_cents` anulável e a escolha do valor/rótulo no snapshot da Vitrine,
inclusive no nome acessível. Mantive as regras financeiras, lances, reservas,
liquidação e WebSocket. Descartei requests individuais, polling e atualização
em tempo real na Vitrine.

Exigi testes de contrato, privacidade, detalhe público, renderização de
`FeaturedLot`/`LiveLotItem`, filtros locais e atualização na fotografia seguinte,
além do gate completo com E2E. A especificação e os resultados estão no
[registro da correção](../_bmad-output/implementation-artifacts/spec-vitrine-lance-vigente.md).
Git e deploy continuam sob meu controle; esta correção não foi publicada pela IA.

## Avisos de encerramento na Vitrine (29/10/2026)

Usei Codex para acrescentar os avisos discretos “Encerrando em breve” e “Últimos
2 minutos” aos lotes ao vivo da Vitrine. Mantive o cálculo na fotografia pública,
com `ends_at` e o `as_of` já retornados pela API; descartei relógio em execução,
segundos, polling e WebSocket novo. O aviso é recalculado quando chega outro
snapshot pelo fluxo existente, inclusive se o anti-sniping prorrogou o prazo.

Exigi função pura com instante injetado, testes de fronteira, exclusão de
agendados/encerrados, prorrogação, ausência de consultas extras e layout em
320/375px. Não autorizei mudanças no backend, contratos ou regras de leilão.
A especificação e a validação estão no
[registro deste refinamento](../_bmad-output/implementation-artifacts/spec-vitrine-aviso-encerramento.md).
Mantive commit, push e deploy sob meu controle.

## Evidências para aprofundar

- [Enunciado](desafio-elite-dev.md) e [arquitetura com decisões e alternativas](ARQUITETURA.md).
- [Epics](../_bmad-output/planning-artifacts/epics.md), [specs](../_bmad-output/specs/) e [stories](../_bmad-output/implementation-artifacts/).
- [Design](../_bmad-output/planning-artifacts/DESIGN.md), [experiência](../_bmad-output/planning-artifacts/EXPERIENCE.md) e [blueprint da Vitrine](../_bmad-output/planning-artifacts/VITRINE-BLUEPRINT.md).
- [Protótipo navegável](../ux-designs/casa-de-leiloes/index.html) e [cenários/validações](../ux-designs/casa-de-leiloes/PROTOTIPO.md).
- [Correção das imagens](../_bmad-output/implementation-artifacts/2-3-busca-de-obras-no-art-institute-of-chicago.md) e [tela branca/formatação](../_bmad-output/implementation-artifacts/2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado.md).
- [Review agregado do Épico 6, correções e re-review](../_bmad-output/implementation-artifacts/code-review-epic-6.md).
- [Validação publicada e correção de R6.4-01](../_bmad-output/implementation-artifacts/6-4-validação-final-no-ambiente-publicado.md).
- [Review dos opcionais](../_bmad-output/implementation-artifacts/code-review-optionals-6-5-6-7-final.md) e [re-review vigente de R6-OPT-01](../_bmad-output/implementation-artifacts/code-review-r6-opt-01-rereview.md).
- [Fechamento definitivo](FECHAMENTO-EPICO-6.md) e [smoke público final](../_bmad-output/implementation-artifacts/smoke-publico-final-6-5-6-7.md).

Os artefatos históricos preservam seus próprios recortes; a decisão final de
fechamento e o smoke final regem o estado publicado. Esta edição apenas substitui
o relato cronológico por uma explicação do processo, sem apagar as evidências.
