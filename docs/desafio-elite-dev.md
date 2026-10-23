# Teste técnico: Elite Dev na Verzel

> Transcrição fiel do PDF `Teste_tecnico_Elite_Dev_-_Verzel.pdf` (7 páginas,
> sem camada de texto), recebido em 22/10/2026. O texto abaixo reproduz o
> enunciado; nada foi acrescentado. Em caso de dúvida, vale o PDF.

Olá! Que bom ter você nesta etapa. Seu desafio é construir uma Casa de Leilões
online, do jeito que faria no dia a dia de um time de desenvolvimento.

Sumário: 01 O desafio · 02 Front-End · 03 Back-End · 04 Tecnologias e
requisitos · 05 Opcionais · 06 Como enviar

## 01. O desafio (proposta de solução)

Você deve criar uma Casa de Leilões online, onde um leiloeiro coloca itens em
leilão e licitantes disputam cada lote com lances ao vivo. O que será leiloado
é escolha sua: obras de arte, carros, cartas colecionáveis, discos, livros
raros, o que você quiser, desde que os itens venham de uma API pública.

O leiloeiro monta um lote a partir de um item buscado na API externa que você
escolheu, definindo lance inicial, incremento mínimo, horário de início e fim,
e outros campos relevantes. O licitante deposita um saldo simulado na sua
carteira, acompanha os lotes ao vivo, dá lances e, se vencer, recebe um
comprovante de arremate que pode compartilhar por link. Qualquer pessoa, mesmo
sem login, pode auditar o histórico de lances de um lote e verificar que ele
não foi adulterado.

### Requisitos funcionais base

**Deploy:** o deploy da aplicação é **obrigatório**.

**Usuários e Autenticação:** a plataforma possui dois papéis distintos:

| Papel | Descrição |
| --- | --- |
| Leiloeiro (vendedor) | Cria e gerencia os próprios lotes. Não pode dar lances. |
| Licitante (cliente) | Deposita saldo, dá lances e arremata itens. |

**Referências:** para ver como esses fluxos costumam ser resolvidos. Não
copie; use como ponto de partida:

- https://www.catawiki.com/pt
- https://www.liveauctioneers.com/
- https://www.superbid.net/

## 02. Front-End

| Tela | Requisito |
| --- | --- |
| Vitrine de lotes | Interface que exibe os itens leiloados, separando lotes ao vivo, agendados e encerrados. Lotes cancelados não aparecem na vitrine. |
| Painel do leiloeiro | Permite buscar itens na API escolhida e criar um lote a partir deles (com imagem, título, atributos do item, data de início/fim e valor mínimo); cancelar um lote que ainda não recebeu lances; e ver o resultado de cada lote encerrado (se foi arrematado e por quanto) e o total recebido. |
| Sala do lote ao vivo | Exibe o lance atual, histórico de lances, posição do usuário nos lances, contagem regressiva e um indicador claro de "você está ganhando" / "você foi superado". Tudo atualizado sem recarregar a página. |
| Carteira do licitante | Mostra saldo total, saldo comprometido, saldo disponível e opção de depósito simulado. |
| Meus arremates | Interface onde o usuário vê os itens em que deu lance e os lotes vencidos, com o respectivo comprovante e link de compartilhamento. |
| Página de auditoria | Pública e sem login, mostra o histórico completo de lances de um lote e informa se ele está íntegro ou foi adulterado. |
| Mensagens de feedback | Mensagem clara para cada lance recusado, dizendo o motivo (abaixo do mínimo, saldo insuficiente, você já está ganhando, lote ainda não iniciado ou lote encerrado). |

## 03. Back-End

**Gestão da API externa:** APIs têm limites e instabilidades. Sua aplicação
não pode ficar inutilizável por causa disso. A vitrine, as salas, a auditoria e
o comprovante devem continuar funcionando mesmo que a API caia.

**Regras de lance:**

- Só são aceitos em lotes ao vivo (entre início e fim).
- O primeiro lance deve ser ≥ ao lance inicial. Os seguintes devem ser ≥ ao
  lance atual + incremento mínimo.
- O licitante líder não pode cobrir o próprio lance.

| Regra | Descrição |
| --- | --- |
| Saldo comprometido | Saldo disponível = saldo total - comprometido. Quando o licitante lidera, o valor fica comprometido; se superado, volta ao disponível imediatamente. O lance só é aceito se couber no disponível. |
| Prorrogação (anti-sniping) | Lance aceito nos últimos 2 minutos estende o fim do lote para +2 minutos. |
| Liquidação | Ao encerrar, debita-se o valor do vencedor e credita-se ao leiloeiro, gerando o comprovante. Lotes sem lances fecham sem vencedor. |
| Histórico à prova de adulteração | Qualquer alteração, remoção ou inserção posterior no histórico (mesmo direto no banco de dados) deve ser detectada pela auditoria. A técnica é escolha sua; explique-a. |
| Privacidade | A auditoria e o comprovante identificam licitantes sem expor dados pessoais. |

## 04. Tecnologias e requisitos

### Tecnologias obrigatórias

- **Front-End:** React, com ou sem framework (Next.js, Vite, Remix ou o que
  preferir).
- **Back-End:** NodeJS ou Python. Fique à vontade com o framework (NestJS,
  Express, FastAPI, Django, etc.).
- **Banco de Dados:** PostgreSQL, MySQL ou um banco NoSQL (como MongoDB).
  Certifique-se de incluir no README instruções claras sobre como configurar e
  utilizá-lo.

### Requisitos não funcionais

- **Prazo:** você tem 7 dias corridos a partir do recebimento deste desafio
  para completá-lo.
- **Dados de teste:** deixe semeados um leiloeiro, dois clientes e ao menos um
  lote publicado com lances abertos, para que possamos percorrer o fluxo sem
  montar tudo do zero.
- **Documentação:** o projeto deve incluir um README detalhado explicando o
  passo a passo para configurar e executar a aplicação. Funcionalidades com
  comportamento inesperado devem ser mencionadas. A ausência de explicações
  impactará negativamente na nota final.

## 05. Opcionais

Nenhum dos itens abaixo é obrigatório, mas todos são considerados na avaliação.

- [ ] Busca e filtro de lotes.
- [ ] Cancelamento de lote com estorno automático.
- [ ] Docker Compose.
- [ ] Testes automatizados.
- [ ] Dark Mode: interface com suporte a tema claro e escuro.

**Não precisa fazer:** nota fiscal, revenda entre usuários, aplicativo nativo
ou recuperação de senha.

## 06. Como enviar

Envie pelo formulário https://elitedev.verzel.com.br/?elite-dev-2026-2
preenchendo os campos assim:

| Campo | Conteúdo |
| --- | --- |
| Nome completo e E-mail | Seus dados de contato. |
| Repositório | O link do repositório público no GitHub com a aplicação. |
| Tem mais de um repositório? | Se front e back estiverem separados, informe os dois. |
| Deploy | O link público da aplicação (**obrigatório**). |
| Onde e como você usou IA | Usar IA é permitido. Conte onde e como usou e o que revisou ou ajustou. Se não usou, conte isso também. |

Boa sorte e bom código!
