# Contrato de autorização e privacidade

Preservo AD-11/29 e a policy AUCTIONEER registrada por api_route. Não amplio
acesso com base em URL, query string ou dados do frontend.

## Listagem privada aprovada

| Solicitante/situação | Resultado esperado |
| --- | --- |
| AUCTIONEER proprietário | 200 com seus lotes/resultados e soma dos seus sold |
| Outro AUCTIONEER | 200 com seus próprios lotes/soma; lote alheio omitido, nunca item privado alheio |
| AUCTIONEER sem lotes | 200 items=[] e total=0, com as_of |
| BIDDER autenticado | 403 forbidden, sem leitura de resultados |
| Não autenticado, cookie inválido/expirado | 401 unauthorized, sem dado privado |
| lot_id inexistente | Listagem não recebe lot_id; item ausente, sem 404 da coleção |
| Query user_id/auctioneer_id/lot_id alheio | Não pode mudar owner; só user.id validado do cookie é autoridade |

`resolve_session_user` confere token e usuário/papel atual no banco; JWT só no
cookie HttpOnly, same-origin, sem localStorage, Authorization ou token em URL.
Não introduzo policy administrativa/global nem confio no papel informado pelo browser.
`Cache-Control: no-store` em todo caminho privado, inclusive falhas.

## Whitelist de privacidade

Resultado expõe apenas pseudônimo público persistido, valor, count, instante
e outcome; metadados atuais do próprio lote permanecem. QH-10 decidiu somente
pseudônimo persistido. Não há endpoint de detalhe nem identificação privada nova.

Nunca serializar winner_user_id, nome/email real do vencedor, bidder_id, wallet,
saldos, anchor_hmac/HMAC, segredos, objeto ORM, IDs de receipt/settlement ou tokens de
share. Não fazer join users/wallets para montar resultado/total. A consulta fixa de
User para autenticar não é consulta da identidade do vencedor. O email do próprio
usuário em /api/me já existe e não deve ser confundido com vazamento do vencedor.

Testar chaves exatas e marcadores de valores privados no JSON e DOM, inclusive
objetos aninhados/erro. Logs operacionais novos não contêm linhas/DTOs crus, SQL,
valores privados ou texto bruto da exceção. Não prometer apagar logs históricos.

## Zero efeitos e sessão

GET/HEAD/OPTIONS não liquidam; métodos sem rota podem receber 405, permanecendo
puros. Não registrar HEAD/OPTIONS com side-effects para facilitar teste. A API só
lê e encerra a transação; autenticação não cria usuário/carteira/receipt.
No logout/troca de conta/desmontagem, invalidar reads pendentes e dados privados;
resposta antiga da conta A não pode aparecer no painel de B. Falha 401 usa fluxo
atual de sessão expirada; 403 não deve deixar retry automático contínuo.
