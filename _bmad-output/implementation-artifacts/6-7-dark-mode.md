---
title: 'Story 6.7 — Dark mode, footer e refinamentos pós-entrega'
type: feature
created: '2026-10-29'
status: done
route: dispatch
context:
  - CLAUDE.md
  - docs/ARQUITETURA.md
  - _bmad-output/planning-artifacts/DESIGN.md
  - _bmad-output/planning-artifacts/EXPERIENCE.md
---

<frozen-after-approval reason="mesmo candidato explicitamente autorizado, sem parada entre stories">

## Intent

Decidi implementar tema por tokens e footer institucional junto da 6.7 e incorporar refinamentos pós-entrega derivados de feedback humano externo: senha forte/confirmada, ajuda contextual e contexto financeiro confiável do líder. Descartei novas stories numeradas, dependências, migrations e qualquer mudança na precedência de lances. O usuário autorizou os blocos sequenciais sem aprovações intermediárias e somente um gate integral final; não executar review independente.

## Boundaries & Constraints

Tema: :root claro; [data-theme="dark"] sobrescreve tokens e color-scheme. Antes do mount, preferência local `atrio-theme` (light/dark); sem ela, prefers-color-scheme. Toggle acessível no header “Ativar modo escuro”/“Ativar modo claro”, foco/touch target, persistência através de reload, History API, login/logout e nova sessão. Sem dados de usuário no storage; storage indisponível degrada sem crash. Sem ternários de tema pelos componentes; revisar tokens/texto/surface/brand/estados/inputs/botões/links/auditoria/comprovante; preservar reduced-motion e impressão legível. Roxo discreto, editorial, obra protagonista, sem glow/neon.

Footer semântico, responsivo e pertencente aos dois temas: símbolo existente e ÁTRIO; tagline “Leilões de arte em domínio público, em tempo real.”; “ÁTRIO — Leilões de Arte”; “Projeto demonstrativo desenvolvido para o Desafio Elite Dev — Verzel.”; Recursos com links seguros para Código-fonte https://github.com/joaodionizio/casa-de-leiloes e Acervo artístico — Art Institute of Chicago (URL oficial já usada, https://www.artic.edu/collection). Aviso distinguível: “Leilões, saldos, depósitos e transações são simulados — este é um projeto de demonstração, não uma plataforma comercial em operação.”. Fechamento exato, sem ponto extra: “© 2026 ÁTRIO — Leilões de Arte” e “Desenvolvido por João Luís Dionízio — Desafio Elite Dev — Verzel”. Preservar health status real (“Serviço no ar” ou falha/carregando). Não adicionar email/telefone/endereço/CNPJ/redes sociais. RockHub é só inspiração estrutural, sem copiar identidade/conteúdo.

Cadastro: exclusivamente NOVOS cadastros exigem 8–1024 caracteres e pelo menos 3 de 4 grupos (minúsculas/maiúsculas/números/símbolos), sem trim/lowercase/normalização, nova lib ou serviço remoto. Espaços preservados e contam no comprimento; usar critérios equivalentes BE/FE, documentar escolha de classificação. Backend RegisterRequest valida força com HTTP 422 sanitizado, sem senha em erro/log. Login/hashing Argon2id/contas existentes/demos/JWT inalterados. Frontend feedback compacto com regra real 3/4 e requisitos atendidos em texto, sem percentual científico ou cor única.

Adicionar “Confirmar senha”: igualdade exata exclusivamente na interface. Ambos campos password padrão, autocomplete=new-password, permitem paste/password manager, limites coerentes com contrato por caracteres. Confirmação vazia exige preenchimento; mismatch “As senhas não coincidem.” junto ao campo, aria-describedby/invalid, foco adequado na tentativa inválida; corrigir igualdade remove erro sem anunciar a cada tecla. Força só sobre Senha. Um toggle “Mostrar senhas”/“Ocultar senhas” type=button pode controlar ambos e preservar valores. Criar conta só inicia submit com papel/email/senha/igualdade válidos; validar também no handler, não apenas disabled. Payload continua EXATAMENTE email/password/role; nunca enviar campo de confirmação. Proteger double submit. O botão fica desabilitado enquanto os requisitos não são satisfeitos; o handler também valida tentativas inválidas e protege envio programático, com foco/erros adequados.

Ajuda contextual: UM componente acessível reutilizável sem lib. Abrir/ler/fechar por mouse, teclado, toque; Escape; foco visível; nome acessível; sem hover obrigatório, recorte ou overflow 320px; instâncias não interferem. Textos: Saldo total “Todo o saldo simulado disponível na sua carteira, incluindo valores atualmente reservados em lances.”; comprometido “Parte do seu saldo que está reservada enquanto você lidera um ou mais lotes.”; disponível “O valor que pode ser usado em novos lances: saldo total menos saldo comprometido.”; próximo mínimo “Menor valor aceito para superar o lance atual, considerando o incremento mínimo definido pelo leiloeiro.”; pseudônimo “Identificador usado neste lote para proteger sua identidade pública no histórico e na auditoria.”; integridade “O histórico gravado confere com a cadeia de hashes e a âncora de integridade do lote.”. Integrar em Carteira, Sala e auditoria, sem poluição ou alegação de blockchain/imutabilidade absoluta.

Líder: mostrar proativamente “Seu saldo disponível no momento também é menor que o próximo lance mínimo.” somente viewer BIDDER + winning + live + carteira ready e não stale + sem overlay/sync incerta + mínimo conhecido + available < minimum. Manter “Você está ganhando”. Não inferir se wallet falha/stale, mínimo desconhecido, overlay, sincronização ou fim. Usar conexão confiável/dados atuais conforme flags existentes. Sem chamadas extra. Já está ganhando continua motivo autoritativo de already_winning, nunca mapear para insufficient_balance. Sem mudar botão de lance ou backend AD-7/evaluate_pre_wallet/evaluate_post_wallet. Recalcular com atualizações WS, remover contexto quando outbid/ended/incerto.

Nunca executar Git, gh, deploy, review independente, gate integral, ler .env*, credenciais/segredos. Dados de teste fictícios, segredos em memória. Não tocar dev. Não mudar 6.5/6.6 salvo integração estritamente necessária, a relatar.

## I/O & Edge-Case Matrix

| Cenário | Ação | Esperado |
| --- | --- | --- |
| Tema | sistema/override/toggle/reload/nav/auth/storage bloqueado | tema correto e persistente, sem crash/flash claro |
| Senha | 3/4 grupos, 4/4, 1/4, 2/4, curta, >1024, espaços/caixa | aceita só contrato; login anterior/demos preservados |
| Confirmação | igual/diferente/vazia/caixa/espaço/corrigida/toggle/duplo | igualdade literal; erros/foco; POST único só com email/password/role |
| Ajuda | mouse/teclado/toque/Escape/várias instâncias | conteúdo e aria corretos, fecha e não corta/overflow |
| Líder | winning suficiente/baixo, outbid baixo, stale/falha/overlay/null/fim, already_winning, WS | contexto só com confiança; motivo autoritativo preservado |
| Footer | claro/escuro/mobile | conteúdo exato, links reais, autoria completa e health real |

</frozen-after-approval>

## Code Map

- `frontend/e2e/keyboard.spec.ts`, `layout.spec.ts`, `touch-targets.spec.ts`, `brand.spec.ts`: regressões do header/ordem de foco após toggle real, sem remover garantias existentes. Incluir focais pertinentes antes do gate conjunto.

- `frontend/src/index.css`, `App.css`, `main.tsx`, `frontend/index.html`, `SiteHeader.tsx`: tokens, inicialização pré-mount, toggle; componentes novos pequenos permitidos.
- `frontend/src/App.tsx`: health real existente; extrair footer para `SiteFooter.tsx` se útil.
- `backend/app/auth.py:RegisterRequest`, `backend/tests/integration/test_registration.py`: força só cadastro; erros sanitizados existentes em errors.py.
- `frontend/src/api/auth.ts`, `api/auth.test.ts`, `RegisterForm.tsx`: validação de força/igualdade local e payload intocado; helper puro novo permitido.
- `frontend/src/WalletPage.tsx`, `LotBidPanel.tsx`, `AuditPage.tsx`: ajuda reutilizável e condição de líder com dados existentes; `LotPage.tsx` já passa flags de confiança, não muda domínio.
- `frontend/e2e/registration.spec.ts`, `real-stack.spec.ts`, `lot-room*.spec.ts`, `support/mockApi.ts`: fixtures/contratos e regressões; novo e2e para tema/footer/ajuda/feedback permitido.

## Tasks & Acceptance

- [x] Tema e footer completos com testes focais e responsividade 1440/375/320.
- [x] Cadastro BE/FE forte e confirmação local, matriz completa incluindo erro sanitizado/login antigo/demos/payload/submit/toggle.
- [x] Ajuda reutilizável em seis conceitos e testes aria/teclado/foco/click/Escape/320px/dois temas/instâncias.
- [x] Contexto financeiro do líder sob confiança, todos os estados e transições WS testados sem alterar recusas ou gerar rede extra.
- [x] Focais reais Node/Playwright/backend pertinentes, registrar comandos/resultados e deixar story review; coordenação executará único gate integral e inspeção visual final.

**Critérios:** Dado tema escolhido, quando navego/autentico/recarrego, então aparência e preferência persistem com controles legíveis. Dado cadastro, quando tento enviá-lo, então somente senha forte e confirmação idêntica permitem POST sem duplicação de senha na rede. Dado líder com dados confiáveis, quando saldo/minimum/posição mudam, então contexto se atualiza sem inferir estados financeiros incertos.

## Implementation Notes

Para confiança no contexto do líder, `LotBidPanel` já recebe networkOffline,
connection, manualFresh, syncFailed (publicStale), zeroConfirming/zeroFailed,
participationUnavailable, acceptedSyncFailed, refreshing e overlay. Reutilizar
essas flags para não inferir finanças durante reconexão, confirmação do fim ou
sincronização parcial; não mudar habilitação do formulário ou recusas.

Investigação: `frontend/e2e/registration.spec.ts` tem helper fill e asserts do toggle
singular; `real-stack.spec.ts` preenche só uma senha; atualizar ambos para a nova
confirmação, preservando asserts de payload exato e sessão. Testes backend de
limites usam senha só “x” e duplicidade usa senha sem 3 grupos; atualizar fixtures
para satisfazer composição quando o teste verifica outro comportamento, mantendo
novos casos explícitos de fraqueza. Escolha de implementação recomendada para
paridade: categorias Unicode Ll/Lu/Nd e pontuação/símbolos P/S; espaços contam no
comprimento sem constituir um dos quatro grupos. `Array.from` mantém contagem por
code points igual ao Python; evitar truncamento UTF-16 inconsistente. Login não
recebe validador de força. Tema dark pode exigir token separado para texto do
botão primário se o roxo claro usado em links não contrastar com texto branco.

6.5–6.7 foram inicialmente cortadas por prazo após a entrega obrigatória e posteriormente reativadas por decisão humana para implementar os opcionais. Footer é polimento visual complementar junto da 6.7; refinamentos de feedback humano não são exigências atribuídas à Verzel. Autorização de execução já concedida; não interromper para aprovação. Coordenação atualiza README/uso IA/planning/status/fechamento.

## Verification

Para impedir leitura implícita de .env pela configuração existente durante pytest,
prefixar execuções Python com PYTHONPATH=/private/tmp/atrio-optionals-noenv. O
sitecustomize temporário desliga só DotEnvSettingsSource._read_env_files, sem
carregar módulos do app e sem mudar produto; todas as configurações vêm das
variáveis fictícias abaixo. Não abrir/copiar/renomear .env. Se uv/cache bloquear,
usar backend/.venv/bin/python ou escalation justificada. Não parar o PostgreSQL
compartilhado desta rodada.

Focais Node, lint/typecheck/build e Playwright dos fluxos afetados. Backend pytest em PostgreSQL isolado: DATABASE_URL=postgresql://atrio_test:atrio_local_test@127.0.0.1:55436/atrio_optionals_dev TEST_DATABASE_URL=postgresql://atrio_test:atrio_local_test@127.0.0.1:55436/atrio_optionals_test APP_ORIGIN=http://localhost:5173 uv run pytest tests/integration/test_registration.py tests/integration/test_auth_flow.py tests/integration/test_seed.py (workdir backend). Sandbox pode exigir escalation para loopback/browser. Não rodar verify integral, review ou deploy. Relatar arquivos/comandos/limitações e contrato de classificação usado para força.


### Implementação e focais executados — 29/10/2026

Implementei tema pré-mount no HTML, baseado em preferência salva válida ou no
sistema, tokens CSS para os dois temas, color-scheme e toggle com nome acessível.
A escolha manual fica apenas em atrio-theme e atravessa History API, reload,
login/logout e outra aba. Storage indisponível não impede a aplicação. Preservei
reduced-motion e defini tokens claros para impressão.

Criei footer em colunas no desktop e uma coluna no mobile, com marca existente,
O projeto, Recursos, aviso de demonstração distinguível e health real. Usei
exatamente “© 2026 ÁTRIO — Leilões de Arte” e “Desenvolvido por João Luís Dionízio —
Desafio Elite Dev — Verzel”, sem abreviar ou adicionar contatos/redes sociais.
Os links externos são o repositório solicitado e a coleção oficial da AIC,
com noopener noreferrer. RockHub serviu apenas como inspiração estrutural.

Novos cadastros exigem 8–1024 code points e 3/4 categorias Unicode: Ll, Lu, Nd
ou pontuação/símbolos P/S. Espaços contam no comprimento, sem formar grupo e sem
normalização. Login/Argon2id/demos/JWT permanecem intactos. Confirmar senha
compara igualdade literal só na interface; erro ligado ao campo, foco após
tentativa inválida, limpeza ao corrigir e toggle compartilhado. O botão inválido
fica disabled e o handler também valida. Payload permanece email/password/role,
com barreira síncrona contra envio duplo.

Ajuda reutilizável usa divulgação em fluxo, acionável por teclado/mouse/toque,
aria-expanded/controls e Escape, sem recorte de balão. Contexto financeiro do
líder é calculado só com dados confiáveis e desaparece em stale/falha/sync,
valor desconhecido, outbid ou fim. Não alterei AD-7, regras de recusa, botão de
lance ou chamadas de negócio. already_winning mantém sua mensagem principal.

A implementação despachada foi interrompida por limite de uso da ferramenta;
a coordenação retomou os arquivos existentes e concluiu testes/ajustes. Não
houve review independente. Além do mapa inicial, usei ContextHelp.tsx,
contextHelpText.ts, ThemeToggle.tsx, SiteFooter.tsx, passwordStrength.ts e seu
teste, e e2e/post-delivery.spec.ts. Ajustei também wallet.spec.ts para verificar
os três rótulos e os novos controles reais de ajuda/tema.

Focais reais:

- Backend: pytest de test_registration.py, test_auth_flow.py e test_seed.py,
  PostgreSQL isolado e wrapper sem dotenv: **138 passed**, 1 warning preexistente,
  **13.03 s**.
- Node de passwordStrength/api-auth/vitrine/route: **43 passed**, zero skips.
- TypeScript, ESLint completo e Ruff/format completos: aprovados.
- Rodada ampla de navegador: **278 passed**, duas falhas finais reproduzidas
  (CTA tablet fora do primeiro viewport e seletor ambíguo que também encontrava
  explicação oculta). Corrigi o layout e tornei o seletor exato, preservando o
  critério. Reexecução pertinente layout/vitrine/post-delivery: **81 passed**,
  **8.5 s**, sem skips.
- Testes novos cobrem a matriz de tema/storage/persistência, contraste de tokens
  de texto/estado/ação >=4,5:1, footer, ajuda, confirmação literal, disabled +
  handler, payload exato, força Unicode e contexto do líder com transições WS.

A integração exigiu compactar o header e o filtro em telas menores para preservar
obra e CTA. Mantive rádios no desktop; mobile/tablet usam select nativo com label
real, mesmo estado local e alvos de 44px. Não afrouxei teto de header, foco,
overflow ou ação do destaque no primeiro viewport. A inspeção visual temporária
dos dois temas está registrada no fechamento do candidato. O único gate integral
e o real-stack complementar serão registrados pela coordenação ao terminar.


### Gate combinado e estado final

O único VERIFY_E2E=1 ./verify.sh do candidato terminou exit 0: 2446 backend,
206 Node e 355 Playwright; 7 real-stack opt-in ignorados no gate e executados
separadamente com 7 passed. Docker aprovado. Smoke real de cancelamento com
estorno/WS/auditoria aprovado. Inspeção visual em 35 capturas temporárias.
Detalhes, arquivos e limites em [FECHAMENTO-EPICO-6.md](../../docs/FECHAMENTO-EPICO-6.md).
6.5/6.6/6.7 review, Épico 6 in-progress, sem review independente ou deploy.


## Fechamento vigente — smoke público final, 29/10/2026

**Estado: done.** Decidi concluir esta story após a aprovação técnica agregada
local vigente (R6-OPT-01 RESOLVED) e o smoke real do candidato publicado em
29/10/2026, America/Maceio. Descartei reabrir implementação ou repetir toda 6.4.
Candidato Git local/main: `2a6dc9394be0174a74016b3de46c276eb5ef6074`; SHA do
Render não autenticado. Zero novo BLOCKER/HIGH/MEDIUM; ressalva LOW externa
no acesso ao link oficial AIC por Cloudflare, sem bloqueio do fechamento.

Resultados, limites e fluxo financeiro: [smoke público final](smoke-publico-final-6-5-6-7.md).
6.5: busca/filtros/combinação sem requests extras; 6.6: cancelamento com lance e
refund exato de R$90, total R$100 preservado e auditoria íntegra; 6.7: tema
persistente, footer/cadastro/ajudas/contexto do líder validados em produção.
Preservo o fechamento obrigatório anterior e a reabertura humana posterior para
os opcionais; **Épico 6 done novamente, fechamento definitivo**. Blocos anteriores
que aguardam review/publicação são registros históricos, superados por este.
Nenhuma mudança de código, banco direto, commit, push, merge ou deploy nesta sessão.
