# Decisões — Story 2.3

Aprovadas pelo Joaodionizio em 24/10/2026. Evidência das chamadas reais em
`aic-contract.md` §1. Na implementação, cada item vai para a story em primeira
pessoa, com a alternativa descartada.

## 1. P1 a P11

**P1 — Rotas.** Decidi `GET /api/catalog/artworks?q=...` e
`GET /api/catalog/artworks/{external_id}`; `catalog` deixa claro que o recurso é
externo e não persistido, e `/api/lots` fica livre para a 2.4. O resumo inclui
`date_display`, porque títulos se repetem na busca ("Water Lily Pond" duas vezes
nos 4 primeiros de "water lilies"). Descartei `/api/artworks/...`, que sugere
recurso nosso.

**P2 — Cliente HTTP.** Decidi promover `httpx` (0.28.1, já no lock, só no grupo
`dev`) para dependência de produção; cliente síncrono em handlers `def`
(threadpool); um `httpx.Client` curto por chamada; transporte injetável, com
`httpx.MockTransport` nos testes; `follow_redirects=False`. Descartei
`urllib.request` (timeouts, erros e teste manuais).

**P3 — Falhas externas.** Decidi 503 `catalog_unavailable` para erro de conexão
(inclui DNS), timeout, 3xx, 403 externo/Cloudflare, 429, 5xx, JSON inválido e
resposta incompatível; qualquer outro status inesperado é resposta incompatível.
Timeout connect 3 s, read 5 s (write 5 s, pool 3 s); sem retry. **Exceção:** o
404 real do endpoint de detalhe da AIC segue a P4 e não vira 503. O 503 sai pela
rota com `error_response`; não entra em `CODE_BY_STATUS`. Descartei códigos
separados (502/504): mais detalhe sem ação diferente para o usuário.

**P4 — Detalhe inelegível.** Decidi 404 `not_found` para obra inexistente, fora
do domínio público ou sem imagem elegível. O motivo interno existe no serviço
para uso futuro, mas não muda o contrato público. Descartei um 422 próprio, que
anteciparia a recusa da 2.4.

**P5 — Sem imagem.** Decidi que obra sem `image_id` (válido) não entra na busca e
não é elegível no detalhe (3058 de 62119 PD não têm). O placeholder continua: com
`image_id` válido e falha de carga do IIIF no navegador, aparece o placeholder
local. Não contradiz o AD-22 (falha ≠ ausência); FR3 pede lote com imagem.
Descartei listar com aviso "sem imagem".

**P6 — IIIF.** Decidi base fixa `https://www.artic.edu/iiif/2/` e URL
`{base}{image_id}/full/843,/0/default.jpg`, com `image_id` validado antes da
composição; nenhuma URL externa é usada. Front com `referrerPolicy="no-referrer"`.
Descartei usar `config.iiif_url` da resposta e montar URL no front. **O transporte
(navegador direto no IIIF) foi revisado pela P6.1 em 24/10/2026; a base fixa, o regex e
a URL upstream seguem valendo, agora só para o servidor.**

**P6.1 — Proxy de imagem same-origin (revisão de 24/10/2026, teste manual).**
A suposição da P6 e do AD-22 de que o navegador carregaria o IIIF direto foi
refutada no teste manual: toda requisição `default.jpg` do navegador deu HTTP 403
(Cloudflare, que exige a identificação que a tag `<img>` não envia). O placeholder
funcionou, mas faria todas as obras ficarem sem imagem. Decidi trocar só o transporte:
`GET /api/catalog/images/{image_id}` no nosso back-end, `AccessPolicy.PUBLIC` (obras
de domínio público, nenhum dado de conta, e a vitrine da 2.5 precisará das mesmas
imagens; descartei `AUCTIONEER` para não mudar o contrato de novo na 2.5). Busca e
detalhe continuam `AUCTIONEER`. O único dado do usuário é `image_id`, validado pelo
regex da P6 (inválido → 422 sem chamada); o servidor monta sozinho
`https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg`, com os cabeçalhos
da P8 e `follow_redirects=False`; devolve os bytes em memória (teto de 5 MiB, tipo e
assinatura JPEG conferidos), sem gravar no filesystem nem no banco e sem cache
(`no-store`, como o resto da story). Upstream 404 → 404 `not_found`; qualquer outra
falha → 503 `catalog_unavailable`, sem expor corpo do upstream. `image_url` do
contrato passa a ser `/api/catalog/images/{image_id}`; `image_id` segue no contrato.
Descartei: proxy genérico (URL, tamanho ou formato escolhidos pelo cliente), baixar e
guardar a imagem (AD-22 original), cache no servidor, `StreamingResponse` e fetch/blob
no navegador. Registrado no AD-22 como revisão da consequência técnica, não do
domínio.

**P7 — Termo.** Decidi `q` com `strip`, mínimo 1, máximo 100; `limit` 20; sem
paginação nesta story. Descartei paginação e `limit` escolhido pelo cliente.

**P7.1 — Filtro do termo.** Decidi não depender só de `q`: o servidor constrói
uma consulta `bool` com `must: multi_match` (termo, `operator: and`) e
`filter`: `is_public_domain=true` e `exists image_id`, serializada no parâmetro
`params` do GET. O `q` no topo fica só para a ordenação por relevância
(observado: com ele, Monet aparece primeiro em "monet"; sem ele, a ordem é pelo
destaque do acervo). Nenhuma DSL ou JSON do usuário é incorporado. "Nenhum
resultado" passa a ser real ("qxzvkwjq" → 0). Descartei só `q`, que devolve as
62119 obras PD para qualquer termo.

**P7.2 — Firewall por termo (registro).** O Cloudflare recusa alguns termos
(`<script>`, aspas com `AND`/parênteses) com 403 → 503 pela P3. Não filtro
caracteres no servidor; a mensagem da interface sugere outro termo.

**P8 — Cache e identificação.** Decidi sem cache; `Cache-Control: no-store` nas
respostas 200, 404 e 503 das rotas (401/403 já saem assim). Toda chamada envia
`User-Agent: casa-de-leiloes/1.0` e
`AIC-User-Agent: casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)`.
A documentação oficial recomenda identificação; os probes desta story observaram
403 do Cloudflare sem identificação adequada (sem `AIC-User-Agent`, ou com o
`User-Agent` padrão do httpx). Não é autenticação da AIC. Descartei cache em
memória com TTL. Confirmado em 24/10/2026 com esses dois cabeçalhos exatos:
busca 200 e IIIF 200 `image/jpeg`.

**P8.1 — Contato.** Decidi a URL pública do Render como identificação; sem
e-mail pessoal.

**P9 — Smoke e Q7.** Decidi o script manual `backend/scripts/smoke_artic.py`
(`cd backend && uv run python -m scripts.smoke_artic`), fora do `verify`, sem
banco, login, segredo nem escrita, cobrindo os seis itens do AD-23; a
indisponibilidade obrigatória é a falha controlada e determinística em
`127.0.0.1:9`. Timeout por endereço não roteável não entra no smoke (o timeout
já é coberto pelo `pytest` com transporte falso). Descartei `pytest -m smoke` e
deixar a indisponibilidade só no `pytest`. Resolução da Q7 registrada em
`docs/ARQUITETURA.md` na implementação.

**P10 — Front-end.** Decidi sem React Router e sem biblioteca de teste nova;
desktop ≥ 64rem com lista e detalhe lado a lado; abaixo disso, troca de vista;
sem botão "Criar lote", nem habilitado nem desabilitado. Descartei introduzir o
roteador agora (2.5).

**P11 — Campos extras.** Decidi `dimensions: string | null` no detalhe. Não
incluo o `alt_text` da AIC no contrato nesta story.

## 2. Conflitos

| # | Conflito | Resolução |
| --- | --- | --- |
| C1 | A documentação da AIC recomenda não fixar `config.iiif_url`; a regra de host controlado pede base fixa. | Base fixa (P6). O smoke compara `config.iiif_url` com a base, sem a barra final, e acusa deriva. |
| C2 | "Nenhum resultado" era inalcançável só com `q`. | P7.1. |
| C3 | A opção sem identificação (P8 c da story) é inviável: 403 observado. | P8. |
| C4 | O 422 do handler global da 2.1 sai sem `no-store`. | Aceito: não crio mecanismo especial; o 422 não contém dado do catálogo. |
| C5 | A P6/AD-22 previam o IIIF direto do navegador; o teste manual de 24/10/2026 deu 403 em todas as imagens. | P6.1: proxy same-origin controlado, bytes não guardados; AD-22 revisado em `docs/ARQUITETURA.md`. |

Conferências sem conflito: P5 × AD-22; EXPERIENCE §4 (OPT1 trata de lotes da
vitrine, não do catálogo do FR2); "no painel" do `epics.md` (sem painel nesta
story); AD-23 item 6 (resolvido pela Q7).
