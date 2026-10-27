# Fluxo, estado e composição da sala

Decidi ampliar `LotPage` usando o estado de sessão já carregado em App, sem chamada extra a `/api/me`. Descartei substituir navegação, parser monetário ou padrão de carteira por abstrações novas.

## Propriedades e estado React

`LotPage` recebe `lotId`, `navState`, `navigated`, `viewer` (`checking|visitor|auctioneer|bidder`), `owner` da sessão quando BIDDER e `onSessionExpired`. `owner` reutiliza o email já existente em `/api/me` somente como chave interna, igual à WalletPage; nunca vai ao payload do lance, histórico ou painel. App remonta o conteúdo privado ao trocar owner; o conteúdo público continua público.

Estado necessário, por responsabilidades:

| Estado | Conteúdo |
| --- | --- |
| `detail` | `loading|not_found|failed|ready`, DTO estático existente |
| `room` | `loading|failed|ready`, DTO `/bids`, flag de atualização e falha da última releitura |
| `mine` e `wallet` | `loading|ready|failed` separados, pertencentes ao owner atual |
| `amountText`, `fieldError` | Texto original e erro de formato/422 de validação |
| `submission` | `idle|submitting|accepted|business_rejection|ambiguous`, dados seguros do 201/feedback |
| Âncora do timer | `asOf/placedAt`, `endsAt`, `receivedAtMonotonic` |
| Referências | geração de leitura, versão após POST, validade lot/owner/montagem, ref de foco e callback de sessão |
| Gatilho zero | valores de `ends_at` já consumidos nesta visita à sala; não é estado de domínio |

Não armazeno `is_leading` nem saldo calculado de lance; posição deriva dos DTOs atuais. Não guardo e-mail, token ou segredo em armazenamento persistente. Registro de envio em módulo vive só no processo do browser e sobrevive à remontagem da página, não a um reload completo. Não prometo idempotência após reload, abas ou retry manual.

## Composição e layout

| Arquivo/componente | Responsabilidade |
| --- | --- |
| `LotPage.tsx` | Dados, refresh e cancelamento; navegação/foco/título; composição arte + informação operacional + histórico + ficha |
| `LotBidPanel.tsx` | Valor atual/inicial, mínimo, posição, saldo disponível, mensagens e ação por viewer/fase |
| `BidForm.tsx` | `MoneyField` existente com rótulo “Valor do lance”, atalho mínimo e botão “Dar lance” |
| `BidHistory.tsx` | Lista compacta sequence/alias/valor/hora com segundos, mais recente primeiro; “Você” por alias |
| `Countdown.tsx` | Ticks somente locais e `role=timer`, sem requisições próprias |
| `api/bids.ts` | Tipos/guardas HTTP dos três métodos, resultados discriminados e fetch |
| `bidSubmission.ts` | Barreira síncrona por owner+lote e operação compartilhada entre montagens |
| `bidFeedback.ts`, `bidPosition.ts`, `countdown.ts` | Texto, posição e cálculos/gatilho puros testáveis |

Desktop: obra ampla à esquerda, painel estável à direita; histórico sob a decisão e metadados abaixo. Mobile: estado/tempo, obra, título/artista, valor/mínimo/posição/saldo/formulário, histórico e detalhes. Reorganizo DOM/grid sem duplicar timers, formulários ou regiões live. Não preciso de sticky nesta story. Preservo ArtworkImage e fallback, título da obra, “← Vitrine”, ficha e link da fonte. Nenhuma função financeira depende da imagem.

Uso tokens já presentes em App.css, fundo claro, roxo nas ações e títulos/valores editoriais; sem cards dentro de cards ou chrome que dispute com a arte. Títulos longos, valor MAX_CENTS, alias de 26 caracteres e 50 linhas devem quebrar sem overflow em 320 px. Alvos 44 px, foco visível, label/aria-describedby/aria-invalid do MoneyField, headings coerentes e sucesso em `role=status` persistente; erro em `role=alert`. O timer usa `aria-live=off` para não falar a cada segundo. Focus no h1 em navegação; recusa/erro de formato devolve foco ao campo sem desmontar toda a página.

## Requests permitidos e fonte única

| Gatilho | Requisições, uma rodada por ação |
| --- | --- |
| Abertura/troca de lote | Em paralelo detalhe e `/bids`; quando viewer resolver BIDDER, também `/bids/mine` e carteira |
| “Atualizar sala” / retry de carga | Detalhe + `/bids`, e `/mine` + carteira só para BIDDER; o retry pode refazer apenas o recurso que falhou |
| 201 válido | Aplicar 201 imediatamente; depois `/bids` e `/mine`; carteira já veio no 201 e não precisa GET |
| Recusa de negócio, 409 de integridade ou erro ambíguo | Uma rodada `/bids`, `/mine` e carteira; nenhum POST adicional |
| 0:00 em fase live | Uma rodada `/bids`, e `/mine` + carteira só para BIDDER, por valor de `ends_at` |
| 401 de chamada autenticada | Encerrar fluxo privado e ir ao login; não continuar rodada privada nem reenviar lance |

Sem refresh por foco da aba, reconexão, intervalo, starts_at, animação, digitação ou mudança de renderização. Tick local do countdown não é polling de rede. Agendado permanece agendado até uma leitura explícita receber live.

`phase`, `as_of`, `ends_at` e todas as linhas de “Termina”, “Terminou” e “Término” passam a usar `/bids` (ou o overlay seguro de fim do 201). Ignoro fase/fim do detalhe inclusive após atualização manual. Detalhe fornece obra, termos estáticos e `starts_at`. Sem room válido, mostro detalhe e erro da sala com “Tentar novamente”; fase/fim/minimum não fazem fallback ao detalhe antigo.

Cada rodada tem AbortController, geração crescente e identidade lote+owner capturadas. Resultados abortados/antigos são descartados. Iniciar POST invalida leituras anteriores; confirmar POST sobe versão antes de aplicar 201 e iniciar a releitura. Apenas rodada atual aplica respostas; uma leitura anterior não restaura mínimo, fim, carteira ou posição antigos. Atualizações manuais em andamento são coalescidas, sem fila de retries. Enquanto houver POST de lance pendente (`submitting`), “Atualizar sala” fica desabilitado, como o botão de lance, para não disputar a atualização visual com o resultado; ao fim do POST volta ao normal; isso não é bloqueio por mínimo/saldo. Se zero for atingido durante envio, consumo o gatilho e junto a necessidade à única rodada pós-POST, sem duas rodadas iguais.

As duas rotas de sala não compartilham transação: agregados próprios e estado público são fotografias independentes e podem observar um lance concorrente em momentos diferentes. A sala não promete tempo real. Aguardo ambos da rodada para apresentar posição; em falha de um oculto posição e mostro indisponibilidade, sem inferir ausência de participação. Não crio loop corretivo nem campo `is_leading`.

## Formulário e deduplicação

Formulário existe apenas para BIDDER e room `phase=live`, mesmo com `0:00`, ganhando, saldo zero/insuficiente, mínimo null ou leitura privada indisponível. “Verificando sua sessão…” evita piscar formulário durante checking. Falha privada não transforma usuário em visitante; mostra “Não foi possível carregar sua participação.” ou “Não foi possível carregar a carteira.” e permite refresh. Ausência inicial de room válido não permite decidir fase, portanto não mostra formulário até resolver room.

Uso `noValidate`, MoneyField e `parseReaisToCents`; somente formato, vazio, positivo, casas e tamanho até MAX_CENTS impedem request. Não adiciono atributo HTML `min`, comparação de saldo/mínimo ou bloqueio por liderança. Botão só se desabilita por envio pendente quando formulário existe. Valor inválido pode ser enviado ao handler local para exibir erro, sem POST. Nenhum valor válido digitado é reformatado ou substituído ao chegar snapshot novo.

Atalho único “Usar o mínimo ({R$})”: aparece se mínimo numérico atual e campo vazio/inválido, nunca durante envio; preenche em reais por conversão textual de centavos (sem `R$`, sem float), sem enviar e com foco no campo. Some para entrada válida, enquanto mínimo atualiza ou é null. Para null mostro “Não há valor possível acima do lance atual.”; formulário permanece, servidor recusará `below_minimum`.

`bidSubmission.ts` mantém registro por owner e UUID do lote. `startBid` verifica/cria barreira sincronamente antes de aguardar fetch; duplo clique, Enter e remontagem recebem o mesmo pending, sem iniciar outro POST. Entry carrega quantia e texto original para restaurar campo da montagem que acompanha. Capturo a própria entry pendente na primeira renderização (não só um booleano), e o efeito acompanha essa mesma promise mesmo se ela terminar antes do efeito; isso evita o LOW conhecido da carteira que deixava o botão preso. Região status fica sempre montada, inclusive durante carga privada. Captura owner no início: sair/entrar com outra conta não muda dono do request. POST não é abortado para supor que não gravou; se componente desmonta, resultado não toca outra tela/conta. Registro remove pending ao resolver POST; a coordenação compartilha a rodada de releitura vinculada à operação para nenhuma montagem duplicá-la. Não há registry de transporte nem interface para WebSocket futuro.

## 201 e releitura

1. Validar status 201 e schema seguro completo, inclusive consistência da wallet e igualdade `bid.amount_cents == lot.current_bid_cents`. Corpo inválido → ambíguo.
2. Imediatamente mostrar `lot.current_bid_cents`, `lot.ends_at`, três saldos do 201 (disponível destacado) e “✓ Lance de {R$} registrado.”; se `anti_sniping_applied`, acrescentar “Prazo prorrogado em 2 minutos.”. O browser só reflete a flag.
3. Limpar entrada após aceite confirmado, não depois de recusa/ambíguo. Ancorar contagem no `bid.placed_at` e no novo fim recebido. Invalidar mínimo e posição anteriores; mínimo “atualizando…”. Histórico/total prévios podem ficar visíveis com “Atualizando histórico…”, nunca adicionar linha/count calculados pelo cliente.
4. Uma releitura pública + própria restaura mínimo, histórico, total e posição. A leitura pode mostrar que outro usuário já superou o lance aceito; sucesso do POST permanece como recibo da tentativa, posição reflete snapshot posterior.
5. Falha da releitura mantém os dados do 201; mínimo “Mínimo indisponível”, posição sem afirmação, histórico marcado desatualizado. Texto “Lance aceito, mas não foi possível atualizar a sala.” + botão “Atualizar sala”. Falha de `/mine` sozinha mantém snapshot público novo e indisponibilidade da participação; não revoga sucesso.

## Classificação HTTP e mensagens

Fetch usa URL com `encodeURIComponent(lotId)`, `credentials=same-origin`, GET com AbortSignal; POST JSON `{amount_cents}`, sem Idempotency-Key, sem retry. Guardas verificam shape, arrays até 50, enums, alias, timestamps parseáveis com fuso e centavos seguros; extras são ignorados ao ler e nunca espalhados em JSX. Não implementam domínio nem verificam cadeia. Os contadores/sequência usados em JS precisam ser inteiros seguros; não crio teto persistido novo.

201 seguro é o único aceite. Rede, 5xx, corpo 201 incompleto/inválido/não JSON e status não previsto fora de 4xx → ambíguo. Recusas requerem status e code da tabela, nunca `message`; outro 4xx segue rejeição técnica genérica. 403 `forbidden` é papel, 403 `csrf_*` é técnico. 404 exibe lote não encontrado. 422 `validation_error` vai ao campo. 409 específico é integridade, sem expor categoria interna. GET com corpo inválido/5xx/rede vira erro de leitura, sem mexer no resultado do POST.

| Condição | Texto exato (símbolo fora do texto acessível quando decorativo) |
| --- | --- |
| 422 `below_minimum` | Seu lance está abaixo do mínimo para este lote. Confira o valor mínimo acima. |
| 422 `insufficient_balance` | Saldo disponível insuficiente para este lance. + link “Ir para a carteira” |
| 422 `already_winning` | Você já está ganhando este lote. |
| 422 `lot_not_started` | Este lote ainda não começou. |
| 422 `lot_ended` | Este lote já foi encerrado. |
| 409 `lot_integrity_conflict` | Não foi possível verificar a integridade deste lote. O lance não foi registrado. |
| 422 `validation_error` | Informe um valor válido em reais. |
| 403 `forbidden` | Esta área é só para a conta de licitante. |
| Outro 4xx | Não foi possível enviar o lance. Recarregue a página e tente novamente. |
| Ambíguo com releitura completa bem-sucedida | Não foi possível confirmar o lance. O estado abaixo é o atual do servidor; confira antes de tentar de novo. |
| Ambíguo com releitura parcial/falha | Não foi possível confirmar o lance nem atualizar todos os dados da sala. Use Atualizar sala e confira antes de tentar de novo. |

Recusa conhecida: preservar texto digitado, mostrar símbolo ✕ + mensagem em alert, focar campo quando ainda existe, fazer uma rodada de sincronização. Recusas temporais não mudam phase pelo código; aguardam snapshot. 401 não vira recusa visual: chama fluxo de sessão expirada. Em 404 removo formulário e exibo “Lote não encontrado”. Rejeição técnica/validação não implica retry automático.

Ambíguo: símbolo !, entrada preservada, uma única rodada segura e nenhum segundo POST. Se releitura der certo, mostrar somente estado atual, sem usar presença do alias, contagem ou mudança de carteira para declarar que a tentativa foi aceita. Se falhar, não afirmar “estado atual”; mantenho dados anteriores marcados como desatualizados. Botão manual é “Atualizar sala”, não “Reenviar lance”. Sem idempotência, nova tentativa manual ainda pode gravar outro lance se as regras permitirem; documento a limitação sem induzir retry cego.

## Countdown e trigger em zero

`remainingMs = max(0, (ends_at - as_of) - (monotonicNow - receivedAt))`. Parser de data só usa os instantes recebidos; monotonicNow é `performance.now()` injetável. Não uso `Date.now()` nem `new Date()` sem argumento. No 201 uso `bid.placed_at` no lugar de `as_of` até a releitura. Essa âncora é aproximada: o instante do servidor nasce antes de a resposta chegar, então o erro eventual é só para mais (a contagem pode superestimar o restante, nunca subestimar); ela nunca é autoridade de encerramento, e o próximo snapshot a corrige. A sala mostra “Situação atualizada às HH:MM:SS” com o `as_of` de `/bids` (nunca o do detalhe da 2.5), formatado com segundos; é texto estático, sem timer, polling, `visibilitychange`, foco, detecção de suspensão ou WebSocket. Assim, se o aparelho dormir e o relógio monotônico ficar velho, a pessoa percebe a idade do snapshot. Isso convive com a frase fixa “A sala não se atualiza sozinha; use Atualizar.”

`ceil(remainingMs/1000)` evita mostrar zero com 1 ms restante. Abaixo de 1 h: minutos (dois dígitos, exceto zero `0:00`) e segundos; de 1 h a menos de 24 h: `HH:MM:SS`; >=24 h: `{d} d {HH} h` (horas restantes após dias). Limites: zero `0:00`, 1 ms `00:01`, 2 min `02:00`, 1 h `01:00:00`, 2 d 4 h `2 d 04 h`. Tick local de até 1 s; limpar timer ao desmontar/mudar âncora. Aba suspensa volta calculando elapsed monotônico, sem descontar por quantidade de ticks.

Apenas fase live arma auto-refresh em zero. Marco `ends_at` consumido ANTES de pedir releitura; persistência por visita no dono da sala evita rearmar no rerender e na remontagem de Countdown. Mesmo fim após releitura, refresh manual, erro ou troca de as_of não rearma. Novo `ends_at` diferente arma uma vez para esse valor; conjunto de valores consumidos evita repetir valor já visto. Nova visita à rota pode fazer sua própria leitura inicial e seu próprio trigger.

Em zero com phase ainda live: “Confirmando encerramento com o servidor…”; formulário continua usável. Releitura com ended remove formulário e posição; live com mesmo fim mantém confirmação e só ação manual relê; live com fim posterior recalcula contagem. Em falha mantém confirmação mais erro, sem reagendar. Sem polling, loop, mudança local de phase ou “lote encerrado” decidido pelo relógio do browser.

## Matriz de visibilidade e posição

| Estado | UI |
| --- | --- |
| Visitante | Sala pública, “Entrar para dar lance” com retorno ao lote; zero GET privado/formulário |
| AUCTIONEER | Sala pública, “Sua conta é de leiloeiro: você acompanha o lote, mas não dá lances.”; zero GET privado/formulário |
| BIDDER sem lance | Alias próprio, saldo e formulário live; posição neutra sem badge |
| BIDDER ganhando | `current_bid_cents != null` e alias próprio == alias do primeiro lance → “✓ Você está ganhando” |
| BIDDER superado | `my_bid_count > 0` e alias próprio != alias líder → “↑ Você foi superado”, mesmo fora dos 50 |
| Loading | “Carregando lote…”/“Carregando sala…” em status; não inventa números ou neutro |
| Submitting | “Enviando lance…”, botão desabilitado, campo readOnly, aria-busy |
| Accepted | Dados imediatos do 201 + sucesso; mínimo/histórico em sincronização |
| Business rejection | ✕ + código traduzido, entrada preservada, releitura única |
| Ambiguous network error | ! + texto neutro conforme releitura, entrada preservada, nenhum retry |
| Scheduled | “Os lances abrem em {início}”; sem formulário; hora absoluta |
| Live | Countdown/valor/mínimo/histórico, formulário BIDDER |
| Ended | “Encerrado, apurando resultado”; sem formulário/posição/vencedor; próprio último lance quando não null |
| Empty history | “Nenhum lance ainda.”, “Sem lances ainda” com lance inicial separado |
| Minimum null | Texto de limite; formulário live permanece, sem atalho |

Precedência da posição: se ended, sem DTO próprio/público atual ou atualização pendente, ocultar; com dado válido aplicar ganhando, superado, neutro conforme regras acima. `last_bid_cents` nunca substitui `my_bid_count` para decidir participação. Linha própria é alias igual ao `/mine` validado, com texto “Você”; não buscar email nem UUID nas linhas. Se há mais de 50 no total, mostrar “50 mais recentes de {N}”; caso contrário “{N} lances” (singular para 1). Toda lista permanece compacta e sem link falso para auditoria futura.

## Sessão e retorno seguro

Em App, `handleSessionExpired` passa a preservar `routePath(route)` se rota restrita OU `route.kind=lot`. `replaceRoute('/login',{returnTo,notice:'expired'})`, e login continua usando `safeReturnPath(returnTo,user.role)`. CTA do visitante usa navegação existente com o mesmo returnTo interno. SafeReturnPath já aceita `/lots/{uuid}` para ambos os papéis: não precisa aceitar path livre nem query externa nova.

Qualquer 401 de POST, `/mine` ou wallet da sala atual desencadeia uma navegação, aborta leituras privadas restantes e elimina estado privado da montagem. Callback capturado de um request antigo só pode atuar se lote/owner/rota ainda forem os atuais; resposta da conta anterior não expira sessão de outra conta nem redireciona quem já saiu da sala. Público continua público; não torno `/lots/{id}` rota restrita. URL absoluta, `//host`, `/login`, UUID inválido e path desconhecido continuam rejeitados pela lista existente.
