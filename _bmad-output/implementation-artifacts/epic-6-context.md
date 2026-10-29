# Epic 6 Context: Entrega: robustez, documentação e opcionais

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

**Atualização vigente, 29/10/2026:** reabri o épico após o fechamento obrigatório
validado em produção, preservando 6.1–6.4 (incluindo 6.2A) done e as evidências
anteriores. 6.5–6.7 foram inicialmente cortadas por prazo após a entrega obrigatória e posteriormente reativadas por decisão humana para implementar os opcionais.
O pedido atual autoriza implementação sequencial dos três opcionais, footer junto
da 6.7 e refinamentos pós-entrega derivados de feedback externo (senha forte e
confirmação local, ajuda contextual, contexto financeiro do líder). Não executar
review independente nesta sessão, Git, gh ou deploy. Focais por bloco e um único
gate integral final. Opcionais terminam em review e épico in-progress aguardando
review agregado. As instruções antigas de sessão abaixo permanecem como histórico.

Consolidar uma entrega documentada, revisada e validada no ambiente público para que um avaliador consiga percorrer o fluxo completo de leilão sem adivinhar configuração, credenciais demo ou limitações. O planejamento não tem PRD separado: o enunciado é a especificação. Na sessão de 29/10/2026, executo somente a documentação da Story 6.3; o Épico 6 permanece `in-progress` até os gates posteriores.

## Stories

- Story 6.1: Revisão de segurança e de erros
- Story 6.2: Identidade visual e responsividade
- Story 6.2A: Cadastro de usuários
- Story 6.3: README completo e registro de uso de IA
- Story 6.4: Validação final no ambiente publicado
- Story 6.5: Busca e filtro de lotes — cortada por prazo
- Story 6.6: Cancelamento com estorno automático — cortada por prazo
- Story 6.7: Dark mode — cortada por prazo

## Requirements & Constraints

O avaliador precisa encontrar configuração local, banco, migrations, seed, execução, verificação, deploy e roteiro com contas demo. A documentação de IA deve explicar onde e como foi usada e o que recebeu revisão ou ajuste humano em todas as stories. Números empíricos só entram com evidência de comandos reais; constantes de domínio continuam documentadas.

Registro explicitamente cold start, apuração posterior ao término, publicação WebSocket depois do commit, validade do JWT até `exp`, dependência externa da imagem, limites da auditoria e anti-sniping renovável sem teto. Não confundo funcionalidade implementada localmente com candidato comprovadamente publicado. A validação pública atualizada pertence à 6.4, após deploy manual.

Preservo decisões antigas como história quando substituídas. O escopo original de login apenas com demos foi ampliado por decisão humana na 6.2A para cadastro público de ambos os papéis. Não documento opcionais cortadas como existentes, nem reabro regras de domínio para acomodar redação.

Nesta sessão, o usuário autorizou SPEC e BUILD sem aprovação intermediária e proibiu review, Git, `gh`, deploy e leitura de `.env*` ou segredos. Por restrição de prazo, 6.2A e 6.3 ficam para review agregado independente final; a ausência de review individual da 6.2A não bloqueia 6.3. A 6.1 conserva a pendência de evidência publicada. Mudança exclusivamente documental usa validações focais, sem repetir o gate integral apenas por ritual.

## Technical Decisions

Mantenho monorepo React/TypeScript e FastAPI/Python, PostgreSQL, migrations Alembic, imagem Docker multi-stage e uma origem para SPA, API e WebSocket. Testes críticos usam PostgreSQL real e banco isolado do desenvolvimento. Dinheiro é inteiro em centavos; transações e travas preservam consistência entre lote, carteira e histórico.

Lances usam REST; WebSocket comunica atualizações e snapshots de recuperação. Hora autorizativa vem do PostgreSQL depois da trava. Anti-sniping vigente soma dois minutos ao fim atual a cada lance válido com restante positivo de até dois minutos, inclusive o limite exato. Leituras nunca liquidam; scheduler e catch-up fazem fechamento idempotente.

Autenticação usa JWT em cookie HttpOnly, Argon2id e políticas de acesso por papel; escritas exigem JSON e validação de origem, sem CORS permissivo. Auditoria combina cadeia SHA-256, âncora HMAC e pseudônimo por lote, sem prometer resistência ao comprometimento integral de aplicação, segredos e dados. Dados essenciais da obra são snapshot local; imagem externa pode degradar para placeholder.

## UX & Interaction Patterns

A direção aprovada é catálogo de museu/casa de leilões: obra protagonista, roxo como assinatura, tipografia editorial para obras e valores, controles operacionais simples e sem decoração competitiva. Protótipos são referência; enunciado/story e arquitetura têm precedência sobre direção visual.

Vitrine organiza destaque, ao vivo, próximos e encerrados. Sala equilibra arte e decisão, priorizando estado, tempo, lance, posição, saldo e ação. Carteira evidencia total, comprometido e disponível; painel usa lista/tabela densa; auditoria e comprovante têm formato documental. Mobile precisa preservar prioridade e ação alcançável, sem rolagem horizontal global.

Estados têm texto ou ícone, nunca somente cor. Reconexão recupera snapshot; interface reflete horário e resultado do servidor. Durante apuração, não declara vencedor. Falha de imagem não impede o leilão. Não crio controles sem funcionalidade ou busca/filtros antes de sua implementação.

## Cross-Story Dependencies

Robustez e documentação consolidam autenticação, catálogo, lotes, carteira, lances, tempo real, liquidação, auditoria e comprovante dos épicos anteriores. A 6.2 tem aceite visual humano e review independente; seu LOW aceito permanece registrado. O cadastro 6.2A deve aparecer na documentação atual sem apagar o planejamento original.

Após 6.3, paro. A próxima sessão é o review agregado independente do Épico 6; Git, merge e deploy são manuais depois da aprovação. Só então vem a validação pública 6.4. Nenhuma conclusão documental substitui esses gates ou autoriza marcar o épico como `done`.
