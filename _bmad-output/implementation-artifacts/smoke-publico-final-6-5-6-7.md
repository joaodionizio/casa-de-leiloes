# Smoke público final — opcionais 6.5–6.7 e refinamentos

**Resultado: aprovado com ressalva LOW externa. 6.5/6.6/6.7 e Épico 6: done.**
Decidi concluir o fechamento documental autorizado pelo pedido humano, pois não
observei novo BLOCKER/HIGH/MEDIUM. Descartei correção de código e repetição da
Story 6.4: esta sessão verifica somente o candidato publicado e o fluxo solicitado.

## Identidade e proveniência

- Data: **29/10/2026, America/Maceio (UTC−03:00)**. Observação inicial da Vitrine
  às **13:25**; coleta financeira/cadastro registrada **13:27:44–13:31:50**.
- URL: <https://casa-de-leiloes-i1xr.onrender.com>.
- Git read-only autorizado expressamente: HEAD, main e referência local origin/main
  em **2a6dc9394be0174a74016b3de46c276eb5ef6074**, commit de **13:18:13−03:00**,
  `feat: implementa opcionais finais do épico 6 (stories 6.5 a 6.7)`.
  Árvore inicialmente limpa. Reflog local de origin/main: **update by push,
  13:18:27−03:00**. Não fiz fetch nem consultei a referência remota viva.
- O pedido humano identifica o candidato como publicado. Assets observados:
  **index-DWgNZCjr.js** e **index-upyoEx4D.css**, ambos HTTP **200**; os contratos
  novos de UI/API corroboram a publicação funcional.
- **SHA do Render não autenticado.** Não obtive log/ID de deploy nem associação
  autenticada entre serviço e commit. O SHA informado é identidade local, não
  alegação de SHA verificado do Render.
- Aprovação técnica local anterior preservada: [re-review vigente de R6-OPT-01](code-review-r6-opt-01-rereview.md),
  que resolve o MEDIUM anterior e concede aprovação agregada final. Não executei
  nova revisão de código, gate integral ou testes locais nesta sessão.

## Resultados publicados

| Item | Evidência real / resultado |
| --- | --- |
| Infraestrutura | GET /health **200**, `{"status":"ok"}`; SPA e assets 200; GET /api/lots 200; nenhum pageerror ou HTTP 500 observado nos fluxos da aplicação. Não forcei cold start. |
| Busca 6.5 | `lil` e `LIL` → Water Lilies; `monet` e `MONET` → Water Lilies; `heméssen` → Judith, cujo artista é Hemessen. Demonstrei título parcial, artista parcial, caixa e normalização de acento. Limpar filtros restaurou os quatro lotes do snapshot. |
| Filtros 6.5 | Todos, Ao vivo, Próximos e Encerrados coerentes. Na primeira coleta havia 2 live / 0 scheduled / 2 ended; um lote de terceiro encerrou naturalmente às 13:27. Na coleta final: 1 live / 0 scheduled / 3 ended. Próximos mostrou “Nenhum lote encontrado com esses filtros.”; sem filtro, “Nenhum lote agendado.”. Não fabriquei scheduled. |
| Combinação | `MONET` + Encerrados deixou somente Water Lilies. |
| Rede da filtragem | Listener de requests durante busca/filtros/limpar: **[]**. Zero novo GET por tecla, zero POST e zero consulta AIC. Snapshot preservado. |
| Primeira carga do tema | Contexto novo: `atrio-theme=null`, sistema claro, `data-theme=light`. Não alterei o SO. |
| Toggle e persistência 6.7 | light→dark→light e seleção manual de dark; reload completo preservou dark. History API Carteira→Vitrine, logout, Login→Vitrine e novo login preservaram dark. Chave observada somente `atrio-theme=dark` (ou light ao alternar), sem dados de usuário. |
| Visual do tema | Vitrine/header/inputs/botões/estados/footer inspecionados em claro e escuro; Carteira e ajuda a 320px. Capturas reais sem interceptação de API. |
| Senha fraca | 8+ caracteres, minúsculas+números: Criar conta disabled. POST público direto seguro respondeu **422**. Nenhum usuário fraco criado. Não preservo senha nem corpo de erro potencialmente sensível. |
| Confirmação | Senha forte e confirmação divergente: “As senhas não coincidem.”, CTA disabled, **zero POST /api/auth/register**. Corrigir habilitou cadastro. |
| Cadastro real | BIDDER e AUCTIONEER descartáveis @example.com pela UI: **201**. Chaves do payload BIDDER exatamente **email/password/role**, sem confirm_password. Redirecionamento para login com aviso de conta criada, sem autologin; login manual posterior bem-sucedido. |
| Criação controlada | AUCTIONEER pesquisou Monet na UI AIC e selecionou obra elegível, criou lote ao vivo com inicial R$90 e incremento R$10, término 14:58 BRT. POST /api/lots **201**. |
| Depósito e lance | BIDDER depositou R$100 pela Carteira (**200**) e lançou R$90 pela Sala (**201**). Sala mostrou conexão de atualizações ao vivo antes do cancelamento. |
| Feedback ao líder | “✓ Você está ganhando” e “Seu saldo disponível no momento também é menor que o próximo lance mínimo.”; disponível R$10, próximo mínimo R$100. Não disse que perdeu, que o lance aceito foi recusado ou que jamais poderá lançar novamente. |
| Nova tentativa enquanto líder | Uma tentativa pela UI de R$100 respondeu **422 already_winning**, “Você já está ganhando este lote.”; mesma mensagem principal na UI. Não insisti. |
| Cancelamento 6.6 | Ação disponível com 1 lance. Confirmação: “Este lote possui lances. Ao cancelar, o saldo comprometido do licitante líder será liberado automaticamente.”. **Uma única POST /cancel, 200**. Painel: Cancelado · 1 lance e um aviso de sucesso. Sala recebeu “Este lote foi cancelado”. |
| Refund real | Antes, total/comprometido/disponível = **10000/9000/1000 centavos**; depois = **10000/0/10000**. Igualdade exata verificada. Total preservado, liberação de exatamente 9000; nenhum depósito adicional. |
| Vitrine pós-cancel | Lote ausente na UI e na listagem pública normal; não aparece em live/scheduled/ended. |
| Auditoria pós-cancel | Link público da Sala acessível; UI “Integridade verificada”, “Cancelado”, “1 lance registrado”, R$90. API **integrity=verified, phase=cancelled**. Array de bids e final_hash comparados antes/depois: idênticos. |
| Ajudas por clique | Carteira com três ajudas: A→B→C produziu `[true,false,false]`, `[false,true,false]`, `[false,false,true]` em aria-expanded; Escape → todas false. |
| Ajudas por teclado/mobile | Em 320px, foco+Enter em A e B manteve somente B aberta; Escape fechou; Enter em C reabriu. Conteúdo legível e sem recorte na captura inspecionada; scrollWidth não excedeu innerWidth. Não repeti matriz de toque local. |
| Footer | Marca ÁTRIO, tagline, O projeto, Recursos, disclaimer de simulação e “Serviço no ar” presentes. Textos finais exatos abaixo. Links com noopener noreferrer. Sem CNPJ/endereço/telefone/rede social inventados. |
| Links externos | GitHub real **200**. AIC aponta ao domínio oficial /collection e abre nova aba; GET direto **403**, navegador exibe desafio Cloudflare. Conteúdo final da coleção **não confirmado**; ressalva LOW abaixo. A busca/criação pela API pública AIC funcionou. |
| Mobile | Vitrine, footer e ajuda/Carteira a **320px**, claro/escuro, inspecionados sem overflow horizontal; controles e texto legíveis. |
| Regressão mínima | Login/logout das duas contas, Vitrine, Sala, conexão WS indicada na Sala, atualização terminal após cancelamento, /api/lots e assets funcionaram. Zero exceções JS e zero HTTP 500 observados na aplicação. |

Footer final conferido literalmente:

> © 2026 ÁTRIO — Leilões de Arte
>
> Desenvolvido por João Luís Dionízio — Desafio Elite Dev — Verzel

Lote descartável: **be034048-bb25-466e-9cab-7d795506bb5a**,
**Arrival of the Normandy Train, Gare Saint-Lazare**, AIC **16571**.
Criado **13:28:37**, lance **13:28:55**, cancelado nesta sessão.
Hash público preservado:
`7d09b2af226903f5898da1dde3f22ca8aa86bf49c4cb156300a87ef8cc561d28`.
As duas contas e o histórico cancelado permanecem como dados descartáveis criados
pelas interfaces normais; não tentei apagá-los pelo banco.

## Finding e limites

**SMOKE6-EXT-01 — LOW, limitação externa:** a coleção oficial AIC devolveu 403
à requisição direta e um desafio Cloudflare ao abrir o link real no navegador.
URL oficial e abertura funcionam, mas não afirmo acesso completo ao destino.
Decidi registrar sem bloquear o fechamento, pois não há destino incorreto nem
falha no fluxo da aplicação; descartei tentar contornar a proteção externa.
Não classifico como regressão financeira, de segurança ou funcional do candidato.

**0 BLOCKER / 0 HIGH / 0 MEDIUM; 1 LOW externo.** R6-OPT-01 foi comprovado resolvido
na interface publicada. LOW histórico R6.2-01 continua aceito; não o reavaliei.

Usei a skill browser:control-in-app-browser; ponte integrada indisponível.
Fallback Chromium real do Playwright instalado. Execução de navegador/rede fora
do sandbox aprovada automaticamente. Sem mocks, interceptação de negócio,
SQL, acesso direto ao banco, secrets ou .env*. Senhas fortes geradas só em memória;
não armazenei senhas, cookies, tokens de sessão ou cabeçalhos de autenticação nas
evidências. Removi query transitória do desafio externo do registro persistido.

Tentativas iniciais do coletor expiraram por falta de seleção explícita do papel
e por nomes acessíveis contendo ✓/ajuda. Ajustei somente o runner temporário,
sem mudança de produto. Um comando interativo excedeu o limite da entrada e foi
reemitido antes da submissão; o cancelamento efetivo continuou único. Não alego
runner monolítico integral verde: as observações e asserções focais registradas
acima são a evidência. O browser principal foi encerrado após a coleta.

Não repeti anti-sniping, settlement, comprovante, auditoria antiga, CORS/CSRF,
inventário de escritas nem toda 6.4. O indicador “Sala conectada” e a atualização
terminal são prova funcional de WS; não capturei um handshake HTTP 101 separado.
Não alego teste humano novo nem contraste instrumental completo em produção.

Evidência temporária sanitizada: `/private/tmp/final-smoke-evidence.json`.
Capturas abertas e inspecionadas: `smoke-final-help-320.png`,
`smoke-final-vitrine-dark-320.png`, `smoke-final-vitrine-light-320.png`,
`smoke-final-vitrine-dark-1440.png`, em `/private/tmp/`.
Este relatório preserva os resultados essenciais, sem depender desses temporários.

## Fechamento definitivo

Preservo a sequência: **fechamento obrigatório anterior → reabertura posterior
por decisão humana para opcionais → implementação/gate local → aprovação técnica
agregada local, incluindo R6-OPT-01 RESOLVED → publicação informada e corroborada
funcionalmente → smoke público final → fechamento definitivo**.

**6.5 done; 6.6 done; 6.7 done; footer/refinamentos validados em produção com a
ressalva externa acima; Épico 6 done novamente.** Autorização para atualizar os
estados está expressa no pedido humano desta sessão. Preservo 6.1–6.4 e suas
provas anteriores. Não executei commit, push, merge ou deploy. Apenas documentação
necessária ao smoke/status foi alterada; parei após o fechamento.
