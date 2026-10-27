# DESIGN.md — Direção visual do front-end

> Status: **APROVADO como direção visual** em 24/10/2026.
>
> Este documento detalha a AD-15. Ele não substitui `docs/ARQUITETURA.md`, o
> enunciado nem os critérios de aceite das stories. Em caso de conflito, vale:
> **enunciado/story > ARQUITETURA.md > DESIGN.md/EXPERIENCE.md > protótipos**.

## 1. Decisão visual

Decidi seguir com a identidade visual derivada da marca roxa já presente no
repositório, preservando a direção de **catálogo de museu / casa de leilões de
arte** da AD-15.

O protótipo do Figma é uma referência de exploração anterior, não uma
especificação pixel a pixel e não deve ser copiado como arquitetura de front-end.

O protótipo roxo feito durante a exploração também **não representa a página
final**. Ele serviu somente para testar a nova identidade.

### Feedback incorporado

- A identidade roxa e a marca foram aprovadas.
- A aparência "produto tech / curso / SaaS / Alura" foi rejeitada.
- A composição em que as **obras ocupam mais espaço** foi percebida como mais convincente.
- Uma interface excessivamente baseada em padrões genéricos pode parecer gerada por IA.

**Regra prática:** roxo é a assinatura da marca; **a obra é a protagonista**.

## 2. Marca

### Identidade ÁTRIO (decidida em 25/10/2026)

Decidi chamar o produto de **ÁTRIO — Leilões de Arte** e adotar a identidade visual da
referência "ÁTRIO — Leilões de Arte" que escolhi. Isto substitui o nome de trabalho
"Casa de Leilões" e o símbolo anterior (que era o ícone padrão do template do Vite, não
uma marca do projeto). O parágrafo "Decisão visual" acima, escrito antes, permanece como
histórico: a direção (catálogo de museu, obra protagonista, roxo como assinatura) não
mudou.

- **Referência principal: ÁTRIO.** Identidade, logo, atmosfera, hierarquia, hero, cards e
  mobile.
- **Referência complementar: AURA.** Só organização, densidade, polimento dos cards,
  ficha do lote e composição. Não copiar nome, logo, textos, imagens nem layout pixel a
  pixel. As imagens das referências não são ativos do projeto e não ficam no repositório.
- **Direção:** sofisticada, editorial, acolhedora, centrada na obra; premium sem
  ostentação; limpa e contemporânea; inspirada em catálogo/galeria/casa de leilões. Muito
  branco e tons claros, roxo como cor da marca e das ações, títulos serifados fortes,
  obras como protagonistas, respiro intencional, cards refinados e hierarquia tipográfica
  clara.
- **Evitar:** dashboard corporativo, UI excessivamente técnica, excesso de caixas, densidade
  sem hierarquia, copiar literalmente AURA ou qualquer concorrente.
- **Não antecipar funcionalidade.** As referências mostram "Dar lance", contagem
  regressiva, lance atual, favoritos, compartilhar, busca pública, filtros, artistas,
  "Como funciona", criação de conta, carteira e histórico. Nada disso entra antes da
  story correspondente (a regra "não renderize controle sem funcionalidade" vale).
- **Novas stories já seguem esta linguagem.** O refinamento visual fino (logotipo
  incluído) fica para a rodada visual final, depois das funcionalidades críticas
  (Story 6.2).

**Implementação inicial do logotipo (interpretação vetorial minha, não arte final):**

- Símbolo: `frontend/src/AtrioMark.tsx` (SVG inline, `aria-hidden`) e
  `frontend/public/favicon.svg` (mesma geometria e mesmas cores; um teste de navegador
  compara os dois). Conferi contra a referência ampliada. Quatro traços definem a
  identidade e não podem se perder:
  1. **silhueta alta e fina** (28 × 38), de duas pernas verticais e **topo pontudo**
     (portal gótico), nunca um arco semicircular nem `border-radius`;
  2. **duas faces**: esquerda lilás `#a77bf6`, direita violeta intenso `#6c35e6`,
     divididas por uma vertical que sai do ápice; sem gradiente contínuo;
  3. **abertura interna assimétrica**: parede esquerda vertical, topo arredondado e lado
     direito em diagonal;
  4. só `path`, sem raster, sem imagem remota e sem dependência; legível em 16 px.
  A primeira versão (um arco semicircular simétrico, parecido com ∩ ou uma ferradura)
  **não foi aprovada** e foi descartada por não ter essas quatro características.
- Palavra: texto real "ÁTRIO" (não imagem), fonte de UI do sistema, `font-weight: 300` e
  espaçamento `0.18em`, em `--color-ink`. Descartei a serifa (a referência usa sans leve e
  espaçada; a serifa fica para obras e valores, §4) e o peso 500 da primeira versão
  (pesado demais). O acento de "Á" é preservado. A fonte definitiva da marca fica para o
  polimento final.
- Descritor "Leilões de Arte": menor, peso 400, `--color-muted`. Descartei um cinza mais
  claro porque reduziria o contraste do texto pequeno abaixo de AA.
- Lockup: símbolo + "ÁTRIO" + "Leilões de Arte". O descritor só aparece a partir de
  64 rem; em 375 px e 320 px ficam símbolo e nome, para não apertar Vitrine, Criar lote,
  Meus lotes e Entrar/Sair.
- Acessibilidade: o link da marca se chama **"ÁTRIO — Leilões de Arte — ir para a
  vitrine"**, para conter todo o texto visível (Label in Name, WCAG 2.5.3) e só acrescentar
  o destino; o SVG é decorativo (`aria-hidden`), então a marca não é anunciada em
  duplicidade. Alvos de toque do header e de "← Vitrine" com ~44 px de área acionável
  (pseudo-elemento transparente, sem aumentar a fonte).
- Nome e título da aba: `frontend/src/brand.ts` (`PRODUCT_NAME`, `documentTitle`),
  formato "{página} — ÁTRIO".

### Marca anterior (histórico)

Ativo antes de 25/10/2026: `frontend/public/favicon.svg` (substituído).

Cores extraídas do SVG anterior (as cores de marca seguem valendo; o azul fica como token
sem uso no símbolo novo):

```css
--brand-violet: #863bff;
--brand-violet-strong: #7e14ff;
--brand-lilac: #ede6ff;
--brand-blue: #47bfff;
```

Essas cores são ponto de partida, não autorização para pintar grandes áreas da interface de roxo.

## 3. Sistema de cores

```css
:root {
  --color-brand: #863bff;
  --color-brand-strong: #7e14ff;
  --color-brand-soft: #ede6ff;
  --color-brand-blue: #47bfff;

  --color-ink: #18131f;
  --color-text: #29242f;
  --color-muted: #716a78;

  --color-canvas: #f8f7f5;
  --color-surface: #ffffff;
  --color-surface-subtle: #f4f1f8;
  --color-border: #ddd7e2;

  --color-success: #2d7552;
  --color-warning: #8b6418;
  --color-danger: #9b2c2c;
}
```

### Uso do roxo

Usar principalmente em marca, ação primária, foco/seleção, links importantes e pequenos indicadores.

Evitar página inteira em roxo, hero roxo escuro por padrão, glow, gradientes decorativos e aparência de curso/SaaS/fintech.

## 4. Tipografia

Combinar:

- sans-serif de UI para navegação, botões, formulários, estados e textos operacionais;
- serif editorial para títulos de obras, artistas, valores de grande destaque e peças curatoriais.

Tokens iniciais:

```css
--font-ui: system-ui, -apple-system, "Segoe UI", sans-serif;
--font-display: Georgia, "Times New Roman", serif;
```

## 5. Princípios de composição

### Arte antes do chrome

Prioridade visual:

1. obra;
2. título/artista;
3. estado do leilão;
4. valor;
5. tempo;
6. ação;
7. metadados;
8. decoração.

Se a interface chamar mais atenção que a obra, está errada.

### Conteúdo primeiro

No primeiro viewport da Vitrine deve ser possível perceber obra em destaque, estado, valor, tempo/horário e acesso ao lote.

### Profundidade sem AI slop

Usar escala, crop, espaço, tipografia, divisores e contraste.

Evitar cards arredondados para tudo, cards dentro de cards, sombras, pills, badges, gradientes, glow e ícones decorativos.

### Nem tudo é card

- lote visual: imagem + ficha editorial;
- histórico: lista;
- Meus lotes: tabela/lista densa;
- carteira: números e movimentos;
- auditoria: documento/linha temporal;
- comprovante: documento/certificado;
- formulário: campos e divisores.

## 6. Como usar as referências

### Disney+ — composição e descoberta

Extrair:
- hero orientado ao conteúdo;
- imagem aparecendo imediatamente;
- coleções/rails horizontais;
- várias obras visíveis sem perder protagonismo;
- parte do próximo item visível quando útil;
- pesos diferentes entre destaque, coleção e arquivo;
- navegação adaptada ao dispositivo.

Não copiar branding, fundo azul/escuro, formato exato de poster ou animações pesadas.

### Mercado Livre — descoberta e escala

Extrair:
- busca fácil de localizar;
- filtros objetivos;
- grande catálogo;
- leitura rápida dos atributos que determinam decisão;
- densidade maior em procura/comparação;
- listas administrativas eficientes.

Não copiar amarelo, varejo, promoções, banners ou linguagem comercial.

Busca/filtro é opcional: não renderizar controle morto antes da story correspondente.

### Catawiki — decisão de lance e confiança

Extrair:
- obra e lance no mesmo contexto;
- estado e lance atual inequívocos;
- CTA de licitar claro;
- feedback rápido;
- posição do usuário clara;
- histórico como prova de transparência.

Não copiar regras temporais da Catawiki. Vale AD-5 (revisada novamente em 27/10/2026): **lance válido na janela inclusiva soma 2 min ao `ends_at` vigente**. A decisão intermediária de renovação a partir do lance foi revogada; preservada no histórico da AD-5.

### Superbid — muitos lotes ao vivo

Usar como stress test:
- foto;
- descrição;
- valor;
- cronômetro;
- estado;
- atualização em tempo real;
- leitura rápida de vários lotes.

Não copiar a densidade do BidTV para toda a aplicação.

## 7. Vitrine

A Vitrine é a tela que mais define a identidade.

### Hero

Deve ser image-led.

Preferência:
- obra ocupa aproximadamente 55–70% da presença visual;
- texto e dados na área restante ou sobreposição controlada;
- overlay apenas quando necessário;
- estado, título, artista, valor e tempo claros;
- um CTA primário.

A frase institucional pode existir, mas não deve esconder os lotes.

### Ao vivo

Mostrar apenas:
- imagem;
- estado;
- título;
- artista;
- lance atual;
- tempo restante.

### Próximos

Catálogo/rail mais leve que Ao vivo.

### Encerrados

Peso visual menor; preferir grid compacto, lista editorial ou paginação.

## 8. Cards de lote

O lote não é uma caixa decorativa.

- sem sombra padrão;
- raio mínimo ou nenhum;
- imagem ocupa 65–80% da presença;
- informação crítica fora da imagem;
- título longo trunca sem perder acesso ao nome completo;
- valores altamente legíveis.

## 9. Sala do lote

A Sala equilibra **arte + decisão**.

Desktop:
- obra maior;
- painel operacional estável;
- painel pode ser sticky se fizer sentido;
- cronômetro e valor não ficam enterrados.

Hierarquia:
1. estado;
2. cronômetro;
3. lance atual;
4. posição do usuário;
5. próximo mínimo;
6. saldo;
7. ação;
8. histórico;
9. metadados.

Mobile:
- estado + tempo;
- obra;
- título/artista;
- lance;
- posição;
- CTA;
- histórico;
- detalhes.

CTA inferior sticky é aceitável enquanto houver ação válida.

## 10. Outras telas

### Carteira
Três números primeiro: total, comprometido, disponível. Sem gráfico decorativo.

### Painel do leiloeiro
Tabela/lista densa. Evitar um card grande por lote.

### Meus arremates
Lista visual compacta.

### Auditoria
Documento técnico/linha temporal. Sem card por evento.

### Comprovante
Documento/certificado digital, legível se impresso.

## 11. Imagens e performance

Conforme AD-22:
- imagem via IIIF;
- tamanho adequado ao contexto;
- lazy loading fora do primeiro viewport;
- `aspect-ratio` ou dimensões estáveis;
- placeholder local;
- fallback;
- nenhuma função de negócio depende da imagem.

Evitar imagens em resolução máxima e shimmer chamativo.

## 12. Escalabilidade visual

Validar mentalmente ou por fixture:
- 5 ao vivo;
- 20 próximos;
- 50 encerrados;
- 30 lotes no painel;
- 20 arremates;
- 100+ eventos;
- títulos longos;
- valores grandes;
- imagens variadas ou ausentes.

Pergunta obrigatória: **como essa tela se comporta com 50 registros?**

## 13. Responsividade

Não fazer desktop apenas empilhado.

Desktop: destaque amplo, rails/grids controlados, Sala lado a lado.
Tablet: reduzir itens simultâneos e manter valor/tempo prioritários.
Mobile: imagem ganha largura, rails horizontais, ação alcançável, sem scroll horizontal global.

## 14. Acessibilidade

Estados nunca dependem só de cor:
- `● Ao vivo`;
- `✓ Você está ganhando`;
- `↑ Você foi superado`;
- `Encerrado`;
- `Encerrado, apurando resultado`.

Também foco visível, contraste, controles semânticos, `aria-live` quando necessário e alt text.

## 15. Critérios de reprovação visual

Retrabalhar se:
- lembrar curso/SaaS/fintech;
- a marca competir com a obra;
- parecer coleção de componentes prontos;
- depender de sombra/radius para hierarquia;
- lotes ativos não forem escaneáveis;
- mobile for desktop empilhado;
- 20–50 registros quebrarem a composição;
- houver controles sem funcionalidade;
- parecer AI slop.

## 16. Protótipos

Figma e explorações inline são **referência**, não contrato.

Não copiar estado fake, dados demonstrativos, horários simulados, autenticação fake ou regra de domínio para o cliente.
