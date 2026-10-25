# Contrato com a API do Art Institute of Chicago

Fonte: documentação em `https://api.artic.edu/docs/` e chamadas reais em
24/10/2026, feitas durante a spec (poucas requisições, só leitura). Só os números
abaixo foram observados; o resto é documentação.

## 1. Fatos observados

| Fato | Evidência |
| --- | --- |
| Identificação | A documentação recomenda `AIC-User-Agent` com nome do projeto e contato. Nos probes: sem `AIC-User-Agent` → 403 HTML do Cloudflare; `User-Agent: python-httpx/0.28.1` + `AIC-User-Agent` → 403; `User-Agent` próprio + `AIC-User-Agent` → 200. Com os cabeçalhos aprovados (P8): busca 200 e IIIF 200 `image/jpeg`. Não é autenticação. |
| `q` não filtra | `q=qxzvkwjq` + filtro PD → `total` 62119 (todas as PD), 20 itens; sem filtro → 133169. |
| Filtro real | `bool.must multi_match operator=and` + filtros (com `q` no topo): "monet" 130 (Monet nos primeiros), "water lilies" 16, "qxzvkwjq" 0, "cézanne" 102, "日本" 4. |
| Firewall por termo | `<script>` e `"cat" AND (dog OR` → 403 HTML. JSON com `\uXXXX` (ASCII) → 403 para "日本"; em UTF-8 → 200. |
| Obras PD sem imagem | 3058 de 62119. |
| Detalhe inexistente | `GET /artworks/999999999` → 404 `{"status":404,"error":"Not found","detail":"..."}`. |
| Id inválido | `/artworks/abc`, `/artworks/0` → 400 `{"status":400,"error":"Invalid syntax",...}`. |
| Obra não PD | `id` 129884 ("Starry Night and the Astronauts") → `is_public_domain: false`, com `image_id`. |
| Configuração | `config.iiif_url` = `https://www.artic.edu/iiif/2` (sem barra final); `config.website_url` = `https://www.artic.edu`. |
| Página da obra | `https://www.artic.edu/artworks/27992` → 301 (URL com slug). |
| Latência | busca com 20 itens: 0,37–0,98 s. |
| Imagem no navegador | Teste manual de 24/10/2026: toda requisição `default.jpg` feita pelo `<img>` do navegador deu **HTTP 403** (Cloudflare). O mesmo URL pedido pelo servidor com os cabeçalhos aprovados deu 200 `image/jpeg` (smoke: 197727 bytes para a obra 27992). Há relato público de Cloudflare/`Cross-Origin-Resource-Policy` nas imagens IIIF apesar de a documentação ainda falar em hotlink. Daí o proxy (P6.1). |
| Documentação | 60 req/min por IP anônimo; `limit` ≤ 100; ≤ 10.000 registros por busca; recomendam `params` em JSON para produção, `fields=` e `/full/843,/0/default.jpg`. |

## 2. Requisições que o servidor faz

Base `ARTIC_API_BASE_URL = "https://api.artic.edu/api/v1"`. Cabeçalhos em toda
chamada:

```text
User-Agent: casa-de-leiloes/1.0
AIC-User-Agent: casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)
Accept: application/json
```

**Busca** — `GET {base}/artworks/search?params={json}`, único parâmetro.
O servidor constrói o objeto abaixo; `term` é o `q` validado e entra só nos dois
valores marcados; nenhuma outra parte depende do usuário. Serialização:
`json.dumps(obj, separators=(",", ":"), ensure_ascii=False)`.

```json
{"q":"<term>","query":{"bool":{"must":[{"multi_match":{"query":"<term>","operator":"and"}}],"filter":[{"term":{"is_public_domain":true}},{"exists":{"field":"image_id"}}]}},"limit":20,"fields":"id,title,artist_display,date_display,image_id,is_public_domain"}
```

O filtro vem de `must` + `filter`; o `q` do topo só ordena por relevância
(P7.1).

**Detalhe** — `GET {base}/artworks/{external_id}?fields=id,title,artist_display,date_display,medium_display,dimensions,department_title,artwork_type_title,image_id,is_public_domain,credit_line`.
`external_id` já validado como `int`, formatado com `str(int)`.

**Imagem (proxy, P6.1)** — `GET https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg`,
sem parâmetros, com `User-Agent` e `AIC-User-Agent` acima e `Accept: */*`. Só pelo
`ArticClient.get_image(image_id)`, com `image_id` já validado pelo regex da P6. Host,
esquema, caminho, tamanho e formato fixos; sem redirecionamento.

Nenhuma outra chamada. `config`, `info`, `pagination`, `_score` e `thumbnail`
são ignorados.

## 3. Classificação da resposta

| Resposta | Busca | Detalhe |
| --- | --- | --- |
| 200 JSON no formato abaixo | itens | obra |
| 404 | incompatível → 503 | **não é falha**: "inexistente" (P4 → 404 `not_found`) |
| 3xx | 503 (`redirect`), sem seguir | idem |
| 403, 429, 5xx, qualquer outro status | 503 (`http_<status>`) | idem |
| `Content-Type` não JSON ou corpo inválido | 503 (`not_json`) | idem |
| JSON fora do formato | 503 (`bad_shape`) | idem |

Imagem (`get_image`): 200 com `Content-Type` `image/jpeg` e corpo que começa com a
assinatura JPEG (`FF D8 FF`), até 5 MiB → bytes; 404 → `None` (inexistente); 3xx →
`redirect`; qualquer outro status → `http_<status>`; tipo ou assinatura diferentes →
`not_image`; corpo acima do teto → `bad_shape`; timeout e conexão como acima.

Formato aceito:

- Corpo objeto. Busca: `data` é lista. Detalhe: `data` é objeto com `data.id`
  igual ao pedido.
- Por item: `id` deve ser `int` (não `bool`) e > 0; senão, na busca o item é
  descartado e no detalhe é `bad_shape`.
- Textos (`title`, `artist_display`, `date_display`, `medium_display`,
  `dimensions`, `department_title`, `artwork_type_title`, `credit_line`): string
  → `strip()`; vazia, ausente, `null` ou outro tipo → `None`. Sem truncar.
- `is_public_domain`: mantido só se for `bool`; outro tipo → `None`.
- `image_id`: string que casa o regex da P6 → mantida; senão `None`.

## 4. Mapeamento AIC → modelo nosso

| AIC | Nosso | Onde |
| --- | --- | --- |
| `id` | `external_id: int` | resumo e detalhe |
| `title` | `title: str \| None` | resumo e detalhe |
| `artist_display` | `artist_display: str \| None` | resumo e detalhe |
| `date_display` | `date_display: str \| None` | resumo e detalhe |
| `image_id` | `image_id: str` | resumo e detalhe |
| (derivado de `image_id`) | `image_url: str` = `/api/catalog/images/{image_id}` (same-origin, P6.1) | resumo e detalhe |
| `medium_display` | `medium_display: str \| None` | detalhe |
| `dimensions` | `dimensions: str \| None` (P11) | detalhe |
| `department_title` | `department_title: str \| None` | detalhe |
| `artwork_type_title` | `artwork_type_title: str \| None` | detalhe |
| `credit_line` | `credit_line: str \| None` (crédito/origem do AD-23) | detalhe |
| (derivado de `id`) | `source_url: str` = `https://www.artic.edu/artworks/{external_id}` | detalhe |
| `is_public_domain` | não exposto (sempre `true` no que sai) | — |

`source_url` é sempre derivável do `id`; a AIC redireciona para a URL com slug
(301 observado), o que só o navegador segue.

## 5. Fixtures versionadas

`backend/tests/fixtures/artic/`, JSON escritos à mão no formato do §1–§3 (dados
do acervo são CC0; sem dado pessoal; nenhum arquivo baixado no build):

| Arquivo | Conteúdo |
| --- | --- |
| `search_monet.json` | `pagination`, `data` com 8 itens: 2 válidos completos (16568 "Water Lilies", 16571); 1 válido com `date_display: null` e `artist_display` com `\n`; 1 `is_public_domain: false`; 1 sem a chave `is_public_domain`; 1 com `image_id: null`; 1 com `image_id: "../evil"`; 1 com `id: "16568"` (string). Resultado esperado: 3 itens, na ordem da AIC. `info`, `config` e `_score` presentes. |
| `search_empty.json` | `pagination.total: 0`, `data: []` (termo sem correspondência). |
| `artwork_27992.json` | detalhe completo de "A Sunday on La Grande Jatte — 1884" (valores da chamada real). |
| `artwork_missing_fields.json` | PD com imagem; `medium_display`, `dimensions`, `department_title` ausentes; `credit_line: ""`; `title: "  Study  "`. |
| `artwork_not_public_domain.json` | `id` 129884, `is_public_domain: false`. |
| `artwork_no_image.json` | PD com `image_id: null`. |
| `not_found.json` | corpo 404 da AIC. |
| `image_sample.jpg` | JPEG de 8×8 px (775 bytes) para o proxy de imagem; binário versionado. |

Falhas sem arquivo são simuladas no handler do `MockTransport`:
`httpx.ConnectTimeout`, `httpx.ReadTimeout`, `httpx.ConnectError`, 301 com
`Location` para outro host, 403 HTML, 429, 500, 502, 503, 400, 404 na busca,
corpo `"<html>"` com `application/json`, `Content-Type: text/html`, JSON `[]`,
`{"data": "x"}`, `data` ausente, detalhe com `data.id` diferente.
