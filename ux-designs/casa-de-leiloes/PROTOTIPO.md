# PROTOTIPO.md — Protótipo navegável de referência do front-end ÁTRIO

Gerado em 26/10/2026. HTML, CSS e JavaScript simples, sem build e sem dependência: abra
`index.html` no navegador (funciona por `file://`).

## O que é, e o que não é

É uma referência para **validar a experiência**, avaliar visual e responsividade e apoiar as
stories de front-end. Não é código de produção e **não deve ser copiado para `frontend/`**.
Nada na aplicação depende dele.

Ordem de autoridade (não foi sobrescrita): story/enunciado > `docs/ARQUITETURA.md` >
`DESIGN.md` + `EXPERIENCE.md` + `VITRINE-BLUEPRINT.md` > este protótipo > referências
externas. Onde o protótipo precisou de algo que esses documentos não definem, está em
"Achados" abaixo e **não** virou decisão.

Regras que o protótipo respeita:

- O navegador nunca decide estado do lote, anti-sniping, vencedor, saldo, fechamento nem
  integridade. Todo estado é um **cenário de UX simulado**, escolhido por querystring.
- Não há API, autenticação, relógio real nem WebSocket. Cronômetros são texto estático.
- JavaScript só para navegação, cenários, menu, rails, passos da criação, recolher/expandir
  e copiar link.
- Nenhum controle de busca/filtro de lotes (OPT1), cancelamento com estorno (OPT2) nem dark
  mode (OPT5). Nenhum link sem destino funcional ("Ver todos", "Ver agenda", "Ver arquivo").
- Idioma: interface em português; títulos das obras ficam em inglês, como o museu publica.

## Como usar

| Quero | Faço |
| --- | --- |
| Avaliar com a mesa | Abrir `index.html`: telas e cenários na lateral; papel, moldura e imagens na barra |
| Comparar larguras | Moldura "Comparar as 4": 1280, 820, 390 e 320 lado a lado (reduzidas para caber) |
| Abrir uma tela direto | `vitrine.html`, `sala.html` etc., com cenário na URL |
| Ver qual story entrega cada elemento | Painel "Entrega por story" do hub (nunca dentro das telas) |

A `ScenarioBar` e as indicações de story existem **só** no hub. As telas simuladas não as
mostram. Aberta direto, cada tela mostra apenas uma linha discreta no rodapé dizendo que é
protótipo.

### Parâmetros de cenário

| Tela | Parâmetros |
| --- | --- |
| Todas | `papel=visitante\|licitante\|leiloeiro`, `imagens=algumas\|quebradas`, `frame=1` (oculta o rodapé de protótipo) |
| `vitrine.html` | `vivo`, `prox`, `enc` (quantidades), `variante=carregando\|erro\|longos` |
| `sala.html` | `obra`, `fase=agendado\|aovivo\|apurando\|vencedor\|sem-lances`, `pos=neutro\|ganhando\|superado`, `msg=abaixo\|saldo\|ja-ganhando\|nao-iniciado\|encerrado\|aceito\|prorrogado`, `tempo=normal\|final\|zero\|prorrogado`, `rede=reconectando`, `lances`, `valor=alto` |
| `login.html` | `c=erro\|enviando` |
| `meus-lotes.html` | `n`, `c=confirmar`, `variante=longos` |
| `criar-lote.html` | `passo=1..5`, `c=inicio\|resultados\|vazio\|erro\|carregando`, `obra` |
| `carteira.html` | `c=vazia\|deposito-ok\|erro\|enviando`, `valor=alto` |
| `meus-arremates.html` | `n` |
| `comprovante.html` | `c=adulterado`, `obra`, `n` |
| `auditoria.html` | `c=adulterado`, `n`, `obra` |

## Mapa das telas (11 pedidas viram 9 arquivos)

| Pedida | Arquivo | Observação |
| --- | --- | --- |
| 1 Vitrine | `vitrine.html` | Destaque, Ao vivo, Próximos lotes, Encerrados |
| 2 Login | `login.html` | Sem contas semeadas na tela |
| 3 Meus lotes | `meus-lotes.html` | Tabela densa; blocos no tablet e no mobile |
| 4 + 5 Busca e criação | `criar-lote.html` | Um fluxo de 5 passos: buscar, conferir, condições, revisão, publicado |
| 6 + 7 Sala | `sala.html` | Um papel por vez: visitante, licitante, leiloeiro |
| 8 Carteira | `carteira.html` | |
| 9 Meus arremates | `meus-arremates.html` | |
| 10 Comprovante | `comprovante.html` | Documento, com `@media print` |
| 11 Auditoria | `auditoria.html` | Documento/linha do tempo |

Não criei `arquivo.html` (D4 = C).

## Decisões aplicadas

- **D1 = C.** Sala do licitante mostra `✓ Você está ganhando` / `↑ Você foi superado`,
  "Seu último lance", "Seus lances neste lote" e `Você` no histórico. **Não** defini
  endpoint, payload nem camada que fornece esses dados: pertencem à Story 4.1 e à arquitetura.
- **D2 = A.** Com `tempo=zero` aparece `00:00` e "Confirmando encerramento com o
  servidor…". O botão de lance fica presente e desabilitado. O estado continua "Ao vivo":
  não declaro encerrado, vencedor nem liquidação.
- **D3 = B.** 10 obras de domínio público do Art Institute of Chicago em `art/`, registradas
  em `SOURCES.md`. Existem **somente** para avaliação visual: não vão para `frontend/` e o
  AD-22 segue integral na aplicação real (IIIF pelo proxy, sem armazenar bytes). Os dados de
  negócio (lances, valores, horários, pseudônimos, hashes) são inventados.
- **D4 = C.** A Vitrine renderiza 10 encerrados e mostra "Mostrando 10 de N lotes
  encerrados", sem link.
- **D5 = A.** Produto planejado até a Story 5.3. A informação de story fica só no hub e
  neste documento.
- **Login.** Nenhuma conta ou credencial na tela. O hub só diz que o login não autentica.

## Identidade: confronto com DESIGN.md

- `favicon.svg`, `AtrioMark.tsx` e `DESIGN.md` §2 usam as mesmas duas cores do símbolo,
  `#a77bf6` (face esquerda) e `#6c35e6` (face direita), e a mesma geometria. **Não há
  divergência.** Essas duas cores não estão na paleta de §3; por isso o protótipo as
  declara como `--mark-face-light` e `--mark-face-strong`, de uso exclusivo do símbolo.
- Todas as cores de interface e as duas fontes usam os mesmos nomes e valores de §3 e §4
  (também iguais a `frontend/src/index.css`). Nenhuma paleta nova.
- O CSS de produção (`App.css`) não usa hexadecimais soltos: só variáveis.

## Arquivos

```text
index.html           hub (mesa de avaliação)
PROTOTIPO.md  SOURCES.md
css/  tokens.css  base.css  components.css  screens.css  hub.css
js/   data.js  scenarios.js  chrome.js  ui.js  hub.js  page-*.js (um por tela)
art/  10 obras + favicon.svg (cópia do símbolo)
*.html  as 9 telas
```

## Checagens executadas (26/10/2026, Chromium via Playwright)

Script temporário, fora do repositório. Carregou **71 combinações de tela e cenário em 320,
390, 820 e 1280 px (284 carregamentos)**. Em cada uma verificou: erro de console/página,
requisição que falha (exceto a imagem quebrada de propósito), rolagem horizontal global,
elementos que vazam do viewport, `lang`, um único `h1`, `alt` em toda imagem, campos e
controles com nome acessível, `id` duplicado, alvos de toque de pelo menos 44 px (links dentro
de texto e links esticados dos itens de lote ficam de fora) e contraste de texto (4,5:1; 3:1
para texto grande) calculado dos estilos.

- Primeira rodada: **achou problemas reais**, todos corrigidos: estouro horizontal em 320 px
  (destaque agendado e status da Sala), tabela de "Meus lotes" em 820 px, rail colado na borda
  no mobile, resultado dos encerrados espremendo o título no mobile, link "Ver auditoria
  completa" com alvo de 21 px.
- Última rodada: **nenhum problema** nas 284 combinações.

**Não verifiquei:** leitor de tela, navegação completa só por teclado (só o foco visível por
CSS e a ordem do DOM), Firefox e Safari, impressão real do comprovante, toque em dispositivo
físico, nem o desempenho. A checagem de contraste ignora texto sobre imagem.

## Achados fechados (aprovados em 26/10/2026)

Aprovei a etapa do protótipo e registro estas decisões. Elas valem como referência de
apresentação; contratos reais continuam sendo das stories.

1. **Cronômetro.** Abaixo de 1 h: `MM:SS`. Com horas: `HH:MM:SS`. Com dias: formato compacto
   legível, como `2 d 04 h`. É só apresentação: a fonte de verdade é o `ends_at` recebido do
   servidor, e o navegador nunca muda o estado do lote pelo contador local.
2. **Destaque da Vitrine.** O lote que já aparece como destaque principal sai do rail
   "Ao vivo", para evitar repetição visual imediata. A story da Vitrine preserva isso, salvo
   conflito com critério de aceite posterior.
3. **Carteira.** Sem histórico de movimentos. O requisito cobre saldo total, comprometido,
   disponível e depósito simulado. Não invento funcionalidade sem story.
4. **Auditoria adulterada.** Enquanto o contrato da Story 5.1 não definir granularidade maior,
   a interface informa que a integridade falhou sem afirmar qual lance divergiu. Não invento
   diagnóstico que o backend ainda não promete.
5. **Tipografia dinâmica.** Sans-serif com numerais tabulares para cronômetros e valores
   operacionais que mudam dinamicamente. A serifa editorial continua onde o `DESIGN.md`
   determina protagonismo editorial.
6. **Sala no tablet.** Duas colunas a partir de cerca de 768 px ficam aprovadas como
   referência do protótipo. Na implementação real podem ser ajustadas se os dados reais
   mostrarem falta de espaço, sem alterar a hierarquia do `DESIGN.md` e do `EXPERIENCE.md`.
7. **Conteúdo fictício.** Textos, rotas, hashes e demais valores criados só para demonstrar
   estados continuam explicitamente não vinculantes. As stories correspondentes definem os
   contratos reais.

## Achados ainda abertos

1. **Auditoria com volume maior.** Renderizei todos os lances (120 no cenário de escala),
   porque a Story 5.1 pede histórico completo. Para volume bem maior, paginação ou
   carregamento progressivo é decisão da 5.1.
2. **Cabeçalho no mobile** usa o botão "Menu", que abre a lista. `DESIGN.md` §2 só define o
   lockup; como os itens se organizam em 320/375 px é detalhe da implementação.
3. **`00:00` sem confirmação do servidor** (D2): a Sala permanece "Ao vivo" até o servidor
   mudar a fase. Quanto tempo isso pode durar e como a interface se recupera é assunto das
   Stories 4.1 e 4.4.
4. **Imagens.** Duas das dez obras (Cassatt e o autorretrato de Van Gogh) só saíram em 843 px
   de largura: o IIIF redireciona originais muito grandes para essa largura, coerente com o
   tamanho fixo do proxy do AD-22. As obras se repetem nos cenários de volume (10 obras para
   50 lotes). O fallback de imagem é desenhado em CSS, não é o `artwork-placeholder.svg` de
   produção.
5. **Link "Entrar" para visitante na Sala** (premissa aprovada). O leiloeiro não recebe
   nenhuma ação de lance.
6. **Q10** segue aberta para as rotas do comprovante e do link compartilhável; as do
   protótipo são fictícias. O hash do protótipo não é SHA-256 real.
