# Contrato visual e mudanças mínimas

## Direção e fronteiras

Decidi manter a marca, o portal vetorial de duas faces, o wordmark leve, as fontes
locais e a paleta aprovada. Descartei trocar fontes, redesenhar o logo, introduzir
UI kit ou transformar cada região em card. O polimento do símbolo, manifest,
apple-touch-icon e versão escura citados em deferred-work não são obrigações desta
rodada; não altero a marca silenciosamente.

Mantenho o container de 72 rem e o header funcional por papel, com descritor a 64 rem,
marca sempre reconhecível e wrap sem colisões. Não adiciono menu hambúrguer,
busca/filtros, favoritos, compartilhamento inexistente, navegação sem destino ou
CTA de cadastro para imitar referências. Branco e superfícies claras dominam;
roxo assina ações/foco/indicadores, sem glows ou gradientes decorativos.

## Classificação e arquivos prováveis

`N` = necessária ao CA; `P` = polimento autorizado; `X` = fora de escopo.
Arquivos abaixo são previsão para o futuro build, não alterações desta etapa.

| ID / classe | Alteração mínima e ganho verificável | Arquivos prováveis |
| --- | --- | --- |
| M01 / N | Estilizar links de conteúdo com tokens, mantendo sublinhado, contraste e foco; substituir branco redundante do CTA pelo token; evitar interferir em rails/botões | `frontend/src/App.css`; `index.css` só se um token estritamente necessário for identificado |
| M02 / P prioritário | Recompor apenas o destaque da Vitrine conforme contrato abaixo, preservar coleções e dados | `FeaturedLot.tsx`, bloco `.featured*` de `App.css`; `ArtworkImage.tsx` somente se precisar expor estado de fallback à decoração |
| M03 / N | Trazer timer ao estado/tempo, impedir que título longo enterre dados; preservar um único timer, texto integral e lógica da sala | JSX de `LotPage.tsx`/`LotBidPanel.tsx`, CSS local; props de `CountdownTimer.tsx` somente se inevitável |
| M04 / N, QH-01 decidida | Rótulo da Sala depende do par phase/settlement_status; `ended+settled` deixa de dizer “apurando” | `LotPage.tsx`, `LotBidPanel.tsx`; `LotState.tsx` apenas para extensão opcional de apresentação que não altere o default |
| M05 / N/P | Dar alvos de toque e tokens aos links/cópia de arremates; alinhar título da página aos operacionais; conter título longo sem perder nome acessível ou acesso à Sala | `App.css`, `MyWinsPage.tsx` só para semântica/classe necessária |
| M06 / N, preservar | Carteira, painel e auditoria: conservar composição aprovada; só corrigir defeito concreto revelado nas provas de campo/valor/hash/alvo | Predominantemente CSS; `WalletPage.tsx`, `MyLots.tsx`, `AuditPage.tsx` não são reescritas planejadas |
| M07 / P explicitamente autorizado | Explicação semântica dos dois campos de valor, sem alterar validação nem monetização | `LotForm.tsx`, opção simples em `MoneyField.tsx`, CSS de helper |
| M08 / P explicitamente autorizado | Login demo direto no mesmo fluxo, com exclusão mútua e erros/retorno preservados | `LoginForm.tsx`; `LoginPage.tsx` só se necessário ao agrupamento; CSS local. `api/auth.ts`, `App.tsx` e `route.ts` são contratos a reutilizar |
| M09 / N | Fechar lacunas estruturais de prova reutilizando Chromium, mocks e fixtures existentes | `frontend/e2e/{layout,lot-room,lot-room-ws,audit,wins,session,touch-targets,keyboard}.spec.ts`, novo focal de criação e `support/mockApi.ts` apenas no necessário |
| M10 / X | Endpoint, política, seed, cookie/CSRF, autenticação nova, backend, regra de lance/settlement, paginação, WS novo | Nenhuma alteração autorizada |
| M11 / X | Signup; busca pública 6.5; dark mode 6.7; estorno 6.6; fonte externa, biblioteca ou redesign geral | Só registro da demanda futura |

Se uma medição já passa, preservo a tela. Não consolido todo `App.css` nem
substituo componentes estáveis por preferência estética. Testes novos não são
licença para expandir o produto.

## Hero prioritário da Vitrine

1. **Desktop 1440:** superfície branca/clara, texto institucional conciso à esquerda,
   obra à direita, presença visual da imagem aproximadamente 55–70%, muito respiro,
   poucos divisores e um CTA “Ver lote”. A informação do lote continua inequívoca:
   estado → título/artista → lance inicial → horário → CTA. Uso a marca/descritor
   existentes como base de copy; não invento promessa comercial.
2. Esta orientação humana substitui apenas a lateralidade do esquema antigo do
   blueprint. Preservo seleção do destaque pelo contrato existente, desempate/ordem
   atuais e exclusão do mesmo lote do rail. Sem destaque elegível: vazio verdadeiro,
   sem obra ou urgência fictícia. Sem ao vivo: próximo com “Agendado/Começa…”.
3. **Transição “emergindo”:** proponho pseudo-elemento estático com overlay de branco
   para transparente no espaço de transição do palco da imagem. A composição reserva
   área segura para a obra em `contain`; o overlay não apaga sua região central,
   informação, foco ou CTA, nem captura eventos (`pointer-events:none`). Uso a mesma
   superfície dos dois lados, sem depender do fundo/cor de uma pintura específica.
4. Avaliei mask aplicada à própria imagem: dá fade direto, mas pode ocultar a obra e
   degradar placeholder; descartei como padrão. Overlay isolado é mais fácil de
   restringir ao respiro. Se o efeito não puder preservar a leitura integral de
   obras distintas, reduzo sua faixa ou o omito nesse contexto, mantendo o hero.
   Isso não autoriza alterar bytes, recortar agressivamente ou criar cópias de mídia.
5. **Mobile 375/320:** composição própria, obra cedo em largura útil com altura
   contida, depois estado/título/artista, valor/horário e CTA alcançável. Texto
   institucional é curto e subordinado; não ocupa uma faixa antes da obra.
   Não transfiro a sobreposição desktop para cima de texto/obra no mobile.
   Faço fade discreto ou o desligo; a integridade da imagem tem prioridade.
6. **Tablet 768:** exercito 48 rem já existente. Se 55/45 comprimir texto/valor, uso
   composição vertical curta nessa faixa; não crio breakpoint só para uma matriz.
7. Título pode ter limite visual de linhas, com nome acessível integral e título
   completo alcançável pela Sala existente. Valor e horário não são truncados.
   Provo cenário típico inteiro no primeiro viewport; stress de título+valor máximo
   pode exigir rolagem vertical, mas o hero deve permitir ler dados e alcançar CTA
   sem atravessar texto institucional extenso ou informação decorativa.
8. Confiro paisagem/retrato/quase quadrada, ausência/503, placeholder, carregamento
   lento e efeito desligado. A imagem conserva proporção/caixa estável, eager apenas
   no destaque, lazy nos rails, mesma URL proxy/sem segundo download decorativo.
   Sem imagem: mantenho estado/dados/CTA e aviso atual, sem nuvem sobre o fallback.

Preservo Ao vivo com maior peso; Próximos em rail mais leve; Encerrados densos com
6 iniciais/+6 e foco no primeiro revelado. Nada de coluna com 20 obras grandes,
novos “Ver todos” sem destino ou preço final inventado. A Vitrine pública atual
não recebe settlement, lance atual ou cronômetro; não faço N chamadas às salas
para contornar esse contrato. Seu `LotState` genérico não muda nesta story.

## Sala e telas de consulta

- Sala desktop mantém arte+operação. Timer/valor não devem ficar enterrados por
  título longo; no mobile a ordem fica estado+timer/prazo → obra → título/artista →
  lance → posição → mínimo/saldo/ação → histórico → detalhes. Status de rede,
  avisos e links públicos continuam disponíveis sem dominar o topo.
- Movo a apresentação de **um** `CountdownTimer`, usando a âncora e `onZero`
  existentes; não duplico relógio oculto por CSS, timers, requisições ou callbacks.
  Preservo `role=timer`, `aria-live=off`, contagem monotônica e reconciliação WS/POST.
- Limito a extensão visual do título do topo com acesso ao texto integral na ficha
  abaixo, sem remover conteúdo. Em arremates, nome acessível completo e link
  “Abrir sala” dão acesso ao título integral; não acrescento botão de expansão.
  Valores, cronômetros, aliases e informações técnicas não usam ellipsis.
- Carteira permanece disponível destacado, total/comprometido como apoio e depósito
  abaixo. Painel continua lista/tabela densa, resultados/total/as_of/ações atuais.
  Auditoria mantém documento, todos os eventos, timestamps/aliases e `details`
  para hashes; não escondo informação para caber nem invento paginação.
- Em Meus arremates mantenho todos os estados e links existentes; só vencedores
  liquidados têm comprovante/cópia. No mobile, ações quebram em linhas com área
  acionável próxima de 44 px; sem pseudo-elementos sobrepostos. O input de fallback
  de cópia continua selecionável e dentro da largura útil.

## Novo lote: microcopy autorizada

Junto a cada campo, imediatamente após seu label ou controle e antes da dica de
formato/feedback, acrescento uma descrição persistente, legível sem hover:

| Campo | Texto exato |
| --- | --- |
| Lance inicial | “Valor mínimo aceito para o primeiro lance deste lote.” |
| Incremento mínimo | “Valor mínimo que cada novo lance deverá acrescentar ao lance atual.” |

Opcional, uma vez após o grupo Valores: “Após o primeiro lance, cada nova oferta
deverá respeitar o incremento mínimo definido.” Não duplico a nota se ela aumentar
ruído em 320 px. Uso helper de 14–15 px existente, contraste de texto pequeno e quebra
natural; sem tooltip, badge ou card. Associo a descrição por ID em
`aria-describedby`, somando a dica monetária e o feedback/erro existentes.

Prefiro prop opcional simples em `MoneyField` a duplicá-lo ou alterar sua lógica.
Só `LotForm` fornece a semântica do lote; depósito e lance continuam sem essa copy.
Preservo centavos, parsing, `aria-invalid`, foco do primeiro erro, revisão, rascunho
e payload. Não traduzo incremento como multiplicador ou mudança na primeira oferta.

Não encontrei explicação estática de anti-sniping nesses campos. A mensagem vigente
após aceite (“O prazo do lote foi prorrogado em 2 minutos.”) fica separada e intacta;
não a substituo por explicação de incremento nem invento regra temporal no helper.

## Login demo direto

Proponho grupo discreto “Contas públicas de demonstração”, junto do formulário,
com botões nativos para leiloeiro e licitante 1. O segundo licitante também pode
aparecer como opção simples para demonstrar disputa; não exige novo componente
genérico. Os rótulos deixam demo e papel explícitos: “Entrar como leiloeiro”,
“Entrar como licitante de demonstração”, “Entrar como segundo licitante”.

- Cada botão `type=button` inicia diretamente `login(email, Demo123!)` com as contas
  de `current-state.md`; não se limita a preencher campos nem espera outro clique.
- Extraio dentro do formulário uma rotina de envio compartilhada, com guarda
  síncrona/ref e estado visual comuns. Demo→demo, manual→demo e demo→manual não
  abrem duas tentativas. Enquanto aguarda, campos manuais permanecem legíveis e
  os botões de envio ficam bloqueados; o acionado informa “Entrando…”.
- Sucesso usa o mesmo `onLoggedIn`, limpeza de senha e `App.handleLoggedIn`;
  `safeReturnPath` mantém retorno conhecido e regra por papel. Sem redirecionar
  sempre ao painel, sem salvar token, buscar outra sessão ou chamar GET de login.
- Falha usa classificação/erro normal, anúncio acessível, liberação dos controles
  e foco útil. Credencial pública alterada no banco pode falhar normalmente;
  não altero seed/senha, não tento outra conta nem reenvio automaticamente.
- A tentativa demo não depende do preenchimento/validação dos campos manuais.
  O envio manual continua validando e funcionando. Preservo cookie/CSRF/JSON e
  `credentials:same-origin` dentro do helper existente.

Se essa proposta exigir mudança de backend/auth/sessão/seed/segurança/contrato,
paro o item demo, explico o impedimento e retiro essa implementação do escopo.
Não deixo atalho morto nem finjo sessão autenticada no cliente.

## QH-01 — decisão humana registrada

Encontrei código e teste legado da 4.4 que dizem “apurando” após settled. Apresentei:

| Opção | Consequência / risco / custo |
| --- | --- |
| Corrigir apresentação na 6.2 — recomendada e **escolhida pelo usuário** | Usa status já recebido; elimina mensagem incorreta. Baixo custo; risco é confundir pending ou afrouxar regressão terminal, mitigado por provas dos 2 estados |
| Preservar e adiar — descartada | Menor diff imediato, mantém inconsistência e requer correção futura; não satisfaz a distinção visual completa da Sala |

Contrato aprovado na resposta desta sessão:

| Dados da Sala | Texto |
| --- | --- |
| `phase === 'ended' && settlement_status === 'pending'` | **Encerrado, apurando resultado** |
| `phase === 'ended' && settlement_status === 'settled'` | **Encerrado**, sem “apurando resultado” em qualquer região visível da Sala; informações de resultado já recebidas permanecem separadas |

Não altero genericamente `phaseStatusText('ended')`: pending continua correto e
a Vitrine não tem o mesmo contrato. Aplico a distinção apenas onde a Sala dispõe
de `settlement_status`. Não mudo backend, settlement, arbitragem de snapshots,
ação de lance ou dados recebidos. O teste T22/T23/T40 de `lot-room-ws.spec.ts`
ficou desatualizado em relação ao contrato atual da Sala: altero só a expectativa
de apresentação e acrescento os dois cenários, preservando todos os asserts de
heartbeat/reconexão/terminal/POST. Não atualizo o artefato histórico da 4.4.

## Cadastro: candidata funcional separada

Registrei a demanda futura: “Cadastro”, escolha Licitante/Leiloeiro com descrição
curta dos papéis, Nome/E-mail/Senha, mostrar/ocultar senha, “Criar conta” e
“Já tem conta? Entrar”, sempre na identidade ÁTRIO. Só a estrutura UX da referência
é insumo; não é autorização para implementar.

Hoje não existe endpoint de cadastro. Uma futura spec precisará decidir a revisão
de D2=A (sem cadastro público), contrato/política/erros, persistência de nome e
unicidade/normalização do e-mail, hash de senha e criação de carteira sem saldo,
papéis permitidos e comportamento de sessão. Prováveis áreas: `auth.py`, `users.py`,
`wallet.py`/`ensure_wallets`, eventual migration, políticas/OpenAPI, cliente auth,
rota/página/form de cadastro e testes API/integração/privacidade/papéis/e2e.
Isso é mapeamento superficial, sem desenho de endpoint nem decisão antecipada.

Não crio tela morta, link “Criar conta”, signup ou outra story numerada nesta 6.2.
Não inicio 6.3 nem altero o backlog funcional existente.
