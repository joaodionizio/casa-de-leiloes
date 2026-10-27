# SOURCES.md — Obras usadas só neste protótipo

Estas 10 imagens existem **exclusivamente** para avaliação visual do protótipo de UX
(`ux-designs/casa-de-leiloes/`): hero, recorte, proporção, densidade e ritmo do
catálogo. Não são ativos do produto, não podem ser copiadas para `frontend/` e nada na
aplicação depende delas. A produção segue o AD-22: a imagem vem do IIIF do museu pela
rota `GET /api/catalog/images/{image_id}` e **nenhum byte de obra é armazenado**.

Todas têm `is_public_domain=true` na API do Art Institute of Chicago (conferido em
26/10/2026). As imagens foram baixadas do serviço IIIF do museu, com o lado maior de até
1000 px (duas obras, a de Cassatt e o autorretrato de Van Gogh, saíram em 843 px de
largura porque o servidor redireciona originais muito grandes para essa largura). O texto
das fichas vem do campo de metadados da API.

Fonte dos dados: https://api.artic.edu/api/v1/artworks/{id}
Fonte das imagens: `https://www.artic.edu/iiif/2/{image_id}/full/…/0/default.jpg`

| Arquivo | ID | Título | Artista | Data | Crédito | Página da obra |
| --- | --- | --- | --- | --- | --- | --- |
| `art/seurat-grande-jatte.jpg` | 27992 | A Sunday on La Grande Jatte — 1884 | Georges Seurat (francês, 1859–1891) | 1884–86, borda acrescentada em 1888–89 | Helen Birch Bartlett Memorial Collection | https://www.artic.edu/artworks/27992 |
| `art/van-gogh-quarto.jpg` | 28560 | The Bedroom | Vincent van Gogh (holandês, 1853–1890) | 1889 | Helen Birch Bartlett Memorial Collection | https://www.artic.edu/artworks/28560 |
| `art/caillebotte-rua-chuvosa.jpg` | 20684 | Paris Street; Rainy Day | Gustave Caillebotte (francês, 1848–1894) | 1877 | Charles H. and Mary F. S. Worcester Collection | https://www.artic.edu/artworks/20684 |
| `art/monet-meda-de-trigo.jpg` | 64818 | Stacks of Wheat (End of Summer) | Claude Monet (francês, 1840–1926) | 1890–91 | Gift of Arthur M. Wood, Sr. in memory of Pauline Palmer Wood | https://www.artic.edu/artworks/64818 |
| `art/monet-nenufares.jpg` | 16568 | Water Lilies | Claude Monet (francês, 1840–1926) | 1906 | Mr. and Mrs. Martin A. Ryerson Collection | https://www.artic.edu/artworks/16568 |
| `art/cassatt-banho-da-crianca.jpg` | 111442 | The Child's Bath | Mary Cassatt (americana, 1844–1926) | 1893 | Robert A. Waller Fund | https://www.artic.edu/artworks/111442 |
| `art/el-greco-assuncao.jpg` | 87479 | The Assumption of the Virgin | El Greco (grego, ativo na Espanha, 1541–1614) | 1577–79 | Gift of Nancy Atwood Sprague in memory of Albert Arnold Sprague | https://www.artic.edu/artworks/87479 |
| `art/van-gogh-autorretrato.jpg` | 80607 | Self-Portrait | Vincent van Gogh (holandês, 1853–1890) | 1887 | Joseph Winterbotham Collection | https://www.artic.edu/artworks/80607 |
| `art/renoir-duas-irmas.jpg` | 14655 | Two Sisters (On the Terrace) | Pierre-Auguste Renoir (francês, 1841–1919) | 1881 | Mr. and Mrs. Lewis Larned Coburn Memorial Collection | https://www.artic.edu/artworks/14655 |
| `art/cezanne-baia-de-marselha.jpg` | 16487 | The Bay of Marseille, Seen from L'Estaque | Paul Cézanne (francês, 1839–1906) | c. 1885 | Mr. and Mrs. Martin A. Ryerson Collection | https://www.artic.edu/artworks/16487 |

## Proporções (largura × altura em px, como baixadas)

Escolhi obras com formas diferentes de propósito, para testar recorte e enquadramento:
Monet *Stacks of Wheat* 1000×591 (panorâmica), Seurat 1000×670, Van Gogh *Bedroom*
1000×783, Caillebotte 1000×776, Cézanne 1000×801 (paisagens), Monet *Water Lilies*
1000×960 (quase quadrada), Renoir 806×1000, Van Gogh *Self-Portrait* 843×1074, Cassatt
843×1279 (retratos) e El Greco 523×1000 (muito alta).

## Observações

- Os dados de negócio do protótipo (lances, valores, horários, pseudônimos, datas de
  leilão) são **inventados**. Só título, artista, data, crédito e imagem são reais.
- Os títulos ficam em inglês porque é assim que o museu os publica; a interface do
  protótipo está em português.
- Para trocar ou acrescentar uma obra: baixe a imagem, registre-a aqui e em
  `js/data.js` (lista `ARTWORKS`).
