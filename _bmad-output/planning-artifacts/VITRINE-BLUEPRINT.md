# VITRINE-BLUEPRINT.md — Arquitetura visual da Vitrine

> Status: **APROVADO como arquitetura visual da Vitrine** em 24/10/2026.
>
> Base obrigatória: `DESIGN.md`, `EXPERIENCE.md`, AD-15 e AD-22.
> Este arquivo detalha a composição da Vitrine. Ele complementa `DESIGN.md` e
> `EXPERIENCE.md`, não os substitui, e não cria regras de domínio.
>
> Ordem de autoridade: **story/enunciado > `docs/ARQUITETURA.md` >
> DESIGN.md + EXPERIENCE.md + VITRINE-BLUEPRINT.md > Figma/protótipos/referências
> externas**.
>
> Tempo e classificação do lote (ao vivo, agendado, encerrado, "Encerrado,
> apurando resultado") vêm sempre do servidor (AD-6, AD-19). O countdown no
> navegador só exibe o `ends_at` recebido; chegar a 00:00 no cliente não
> reclassifica o lote.
>
> Links e ações sem destino implementado (`Ver todos`, `Ver agenda`,
> `Ver arquivo`, âncoras do header) são **condicionais**: só aparecem quando a
> story correspondente entregar o destino. Até lá, não são renderizados.

## Nomenclatura: "Próximos lotes"

Decidi usar **Próximos lotes** como rótulo de interface da categoria funcional
de lotes agendados (FR6 e story 2.5 usam "agendados" para descrever o estado).
Isso não altera o estado nem o contrato técnico. Se algum critério de aceite
futuro exigir literalmente outro texto de interface, a story prevalece.

# 1. Objetivo da Vitrine

A Vitrine precisa parecer uma **casa de leilões de arte contemporânea que usa tecnologia**.

Ela deve responder, no primeiro contato:

1. Qual obra/lote merece atenção agora?
2. O que está ao vivo?
3. O que começa depois?
4. O que já encerrou?
5. Como abro um lote?

A interface não deve parecer marketplace de varejo, streaming ou SaaS, embora use aprendizados desses produtos.

---

# 2. Mapa das referências

| Bloco | Referência principal | O que extrair |
| --- | --- | --- |
| Header | Mercado Livre | navegação previsível e descoberta |
| Destaque | Disney+ | conteúdo dominante, imagem cedo, hierarquia |
| Ao vivo | Catawiki + Disney+ | decisão rápida + coleção visual |
| Próximos | Disney+ | rail de catálogo e continuidade |
| Encerrados | Mercado Livre + Superbid | densidade e escala |
| Estados/tempo/preço | Catawiki + Superbid | scanabilidade |
| Responsividade | Disney+ | recomposição real, não desktop empilhado |

Nenhuma referência define a identidade. A marca e a AD-15 definem.

---

# 3. Estrutura desktop

```text
┌──────────────────────────────────────────────────────────────────────┐
│ LOGO     Vitrine   Ao vivo   Próximos                  Entrar/Conta │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DESTAQUE / HERO IMAGE-LED                                           │
│                                                                      │
│  ┌───────────────────────────────────────┬────────────────────────┐   │
│  │                                       │ AO VIVO                │   │
│  │                                       │ Título da obra         │   │
│  │              OBRA                     │ Artista                 │   │
│  │                                       │                        │   │
│  │                                       │ Lance atual            │   │
│  │                                       │ R$ 18.450              │   │
│  │                                       │ 01:42                  │   │
│  │                                       │ [ Entrar na sala ]     │   │
│  └───────────────────────────────────────┴────────────────────────┘   │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ AO VIVO                                                   Ver todos │
│                                                                      │
│ [ OBRA ] [ OBRA ] [ OBRA ] [ OBRA ] [ parte da próxima → ]          │
│ título   título   título   título                                   │
│ R$+tempo R$+tempo R$+tempo R$+tempo                                 │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ PRÓXIMOS LOTES                                            Ver agenda │
│                                                                      │
│ [ OBRA ] [ OBRA ] [ OBRA ] [ OBRA ] [ parte da próxima → ]          │
│ data     data     data     data                                      │
│ título   título   título   título                                   │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ ENCERRADOS                                                Ver arquivo│
│                                                                      │
│ obra/título           resultado final                                │
│ obra/título           resultado final                                │
│ obra/título           resultado final                                │
│ ...                                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

# 4. Header

## Sem OPT1

Mostrar apenas:

- marca;
- Vitrine;
- Ao vivo;
- Próximos;
- autenticação/conta.

Não colocar busca fake.

## Com OPT1 implementado

A busca passa a ter presença real no header ou imediatamente abaixo dele.

Referência funcional: Mercado Livre.

Regras:

- campo fácil de localizar;
- não ocupar visualmente mais espaço que a obra;
- busca por título/artista/lote conforme contrato real;
- filtros abaixo/ao lado somente se funcionarem;
- não criar uma faixa de chips decorativos.

---

# 5. Destaque principal

É a maior diferença em relação ao Figma antigo.

## Composição

Desktop recomendado:

- 60–65% imagem;
- 35–40% informação;
- altura aproximada suficiente para dominar o primeiro viewport sem escondê-lo inteiro.

A obra deve aparecer sem o usuário rolar.

Não usar fundo roxo como área principal.

Roxo entra em:

- marca;
- CTA;
- pequenos estados;
- foco;
- detalhes.

## Conteúdo

Somente:

- estado;
- título;
- artista;
- lance atual ou inicial;
- countdown/horário;
- CTA principal.

Evitar:

- texto institucional longo;
- vários CTAs;
- badges redundantes;
- descrição curatorial extensa.

## Seleção do destaque

Decidido em 24/10/2026.

**Decidi:**

1. Quando houver um ou mais lotes ao vivo, o destaque é o lote ao vivo cujo
   `ends_at` está mais próximo. É simples, útil e orientado à urgência.
2. Se não houver lote ao vivo, o destaque é o próximo lote agendado; o estado
   diz claramente `Começa em...`.
3. Se não houver lote elegível, uso o estado vazio editorial previsto na UX;
   nunca hero falso.

Essa seleção é uma **regra de apresentação da Vitrine** e não altera nenhuma
regra de domínio do leilão.

**Descartei:**

- **Primeiro lote retornado pela API:** a ordem da API passaria a controlar o
  design implicitamente.
- **Campo/curadoria `featured`:** daria controle editorial, mas adiciona campo,
  regra e persistência fora do escopo atual.

**Pendente para a story correspondente:**

- a camada em que essa ordenação é calculada: segue os contratos disponíveis;
  se houver decisão arquitetural real, ela é perguntada antes de implementar;
- o desempate quando dois lotes ao vivo têm o mesmo `ends_at` ou dois
  agendados têm o mesmo `starts_at`.

---

# 6. Ao vivo

## Objetivo

Comparar rapidamente os lotes que exigem decisão agora.

## Item

Imagem ocupa aproximadamente 70% da presença.

Abaixo:

```text
● Ao vivo                         01:42
Título da obra
Artista

Lance atual                  R$ 18.450
```

Não precisa de caixa de fundo.

Não precisa de sombra.

Estado não depende só de cor.

## Quantidade

### 1 ao vivo

- hero já representa o lote;
- a seção pode ser omitida para evitar duplicação OU mostrar uma área mínima de contexto;
- não repetir uma imagem gigante duas vezes.

### 2–5 ao vivo

- rail/grid visual;
- 3–4 itens completos no desktop;
- próxima peça parcialmente visível quando houver continuação.

### >5 ao vivo

- rail horizontal;
- `Ver todos`;
- não carregar imagens gigantes de todos no primeiro viewport.

---

# 7. Próximos lotes

Referência de composição: Disney+.

Objetivo: gerar descoberta, não urgência.

Mostrar:

- imagem;
- início;
- título;
- artista;
- lance inicial se fizer sentido no contrato.

Menos peso visual que Ao vivo.

## Quantidade

### até 4

- grid/rail simples.

### 5–20

- rail horizontal;
- navegação lateral no desktop;
- scroll-snap natural no mobile.

### >20

- rail inicial limitado;
- `Ver agenda` / página de listagem quando existir;
- não renderizar 20 imagens grandes em sequência vertical.

---

# 8. Encerrados

Aqui a referência de escala pesa mais que a de streaming.

Objetivo:

- provar atividade;
- permitir consulta;
- não competir com lotes ativos.

Preferência desktop:

```text
miniatura   Título / artista              R$ final
miniatura   Título / artista              R$ final
miniatura   Título / artista              Sem vencedor
```

Pode evoluir para grid compacto se ficar melhor com as obras reais.

Não usar grandes cards Disney-like para 50 encerrados.

---

# 9. Densidade por estado

```text
AO VIVO        alta presença visual + informação transacional
PRÓXIMOS       média presença visual + descoberta
ENCERRADOS     baixa presença visual + consulta
```

Isso evita uma home em que todas as seções parecem igualmente importantes.

---

# 10. Responsividade

## Desktop >= 1200px

- header horizontal;
- hero 60/40;
- 4 lotes aproximadamente visíveis no rail;
- encerrados densos.

## Tablet 768–1199px

- hero aproximadamente 55/45 ou composição vertical curta;
- 2–3 itens no rail;
- navegação simplificada;
- títulos e valores não comprimidos.

## Mobile <= 767px

Ordem:

```text
HEADER
OBRA DO DESTAQUE
estado + título + artista
valor + tempo
CTA
AO VIVO → rail 78–85vw
PRÓXIMOS → rail 78–85vw
ENCERRADOS → lista compacta
```

Não usar overlay textual pesado sobre a obra.

Mostrar parte do próximo item no rail para indicar continuidade.

Nenhuma informação essencial depende de hover.

---

# 11. Imagens

A obra real vem do IIIF conforme AD-22.

Regras de implementação:

- primeiro hero pode carregar eager/prioritário;
- imagens abaixo do fold: lazy;
- solicitar resolução IIIF coerente com o tamanho;
- reservar proporção antes da resposta;
- fallback local;
- `object-fit` escolhido por contexto;
- não assumir que todas as obras têm mesma proporção.

Nunca cortar uma obra de forma agressiva só para imitar poster de streaming.

---

# 12. Performance percebida

Com 50+ lotes:

- não buscar imagem full-resolution;
- evitar montar todos os encerrados;
- limitar render inicial;
- paginar/carregar depois conforme endpoint/story;
- WebSocket não atualiza a Vitrine inteira se a arquitetura não pedir;
- mudança de preço/tempo não pode causar layout shift.

---

# 13. Estados da Vitrine

A composição precisa prever:

- carregando;
- vazio;
- erro de API do próprio sistema;
- imagem IIIF quebrada;
- nenhum ao vivo;
- nenhum próximo;
- nenhum encerrado;
- lote em `Encerrado, apurando resultado`;
- usuário visitante;
- usuário autenticado.

Não preencher espaços vazios com conteúdo fake.

---

# 14. Anti-AI-slop aplicado à Vitrine

Reprovar se aparecer:

- hero com gradiente roxo decorativo sem necessidade;
- três ou mais botões no destaque;
- cada lote dentro de uma caixa arredondada com sombra;
- ícone em cada metadado;
- dezenas de chips;
- títulos genéricos de marketing;
- seção institucional entre cada grupo de lotes;
- animações em todos os cards;
- mesma composição repetida em todas as seções.

Preferir irregularidade editorial controlada:

- um destaque grande;
- um rail;
- outro rail mais leve;
- um arquivo denso.

---

# 15. Stress test

Antes de aprovar CSS/componente, testar visualmente:

```text
ao vivo:      0 / 1 / 5 / 12
próximos:     0 / 3 / 20
encerrados:   0 / 8 / 50

títulos:
- curtos;
- 2 linhas;
- excessivamente longos.

valores:
R$ 850
R$ 18.450
R$ 1.250.000

imagens:
- paisagem;
- retrato;
- quase quadrada;
- indisponível.
```

---

# 16. Componentes sugeridos

Manter poucos componentes.

```text
<AppHeader />

<FeaturedLot />

<LotSection>
  <LiveLotItem />
</LotSection>

<UpcomingLotItem />

<ClosedLotRow />

<ArtworkImage />
<LotState />
<MoneyValue />
<Countdown />
```

Não criar um design system enorme.

Um `LotCard` universal para todos os estados pode ser uma abstração ruim:
Ao vivo, Próximo e Encerrado têm densidades diferentes.

---

# 17. O que entra em cada referência

## Disney+

**Sim**
- hero;
- rails;
- continuidade;
- hierarquia de coleção;
- image-first.

**Não**
- fundo escuro global;
- posters iguais;
- animações pesadas.

## Mercado Livre

**Sim**
- descoberta;
- busca;
- filtros;
- escala;
- scanabilidade.

**Não**
- varejo;
- banners;
- promoções;
- grade comercial genérica.

## Catawiki

**Sim**
- preço;
- tempo;
- estado;
- confiança para abrir/licitar.

## Superbid

**Sim**
- teste com muitos lotes;
- densidade transacional;
- informação crítica visível.

---

# 18. Critério de saída

A Vitrine só está pronta se:

1. obra aparece no primeiro viewport;
2. usuário identifica ao vivo/próximos/encerrados;
3. preço e tempo de ativos são escaneáveis;
4. 5 lotes ao vivo não quebram a composição;
5. 50 encerrados não geram uma página absurda;
6. mobile não é apenas desktop empilhado;
7. roxo reforça a marca sem disputar com a arte;
8. não há controles mortos;
9. a página não lembra Alura/SaaS/fintech;
10. a página parece uma casa de leilões antes de parecer um app.
