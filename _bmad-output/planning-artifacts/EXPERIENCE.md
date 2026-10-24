# EXPERIENCE.md — Experiência e comportamento das telas

> Status: **APROVADO como orientação de UX** em 24/10/2026.
>
> Complementa `DESIGN.md` e AD-15. Não cria regras de domínio.

## 1. Objetivo

A experiência deve transmitir:
1. curadoria;
2. confiança;
3. urgência controlada.

Resultado desejado: **uma casa de leilões de arte contemporânea que usa tecnologia**, e não um produto tech que por acaso vende arte.

## 2. Regra por story

Só mostrar controles que funcionam naquele momento.

Exemplos:
- sem busca antes de OPT1;
- sem compartilhar antes de link público;
- sem cancelamento se endpoint/política não existem;
- sem fingir WebSocket no cliente.

## 3. Vitrine pública

Responder rapidamente:
- o que está ao vivo?
- o que começa depois?
- o que terminou?
- qual obra vale abrir?

Estrutura preferida:
1. header;
2. destaque visual;
3. ao vivo;
4. próximos;
5. encerrados.

Se não houver ao vivo, destacar próximo lote deixando estado claro.

### Header

Marca, Vitrine e entrada/conta.

Busca entra quando OPT1 existir.

### Destaque

Dados:
- imagem;
- estado;
- título;
- artista;
- lance atual ou inicial;
- tempo/horário;
- CTA.

Regra de qual lote destacar deve vir da story/decisão, não ser inventada.

### Ao vivo

Com muitos registros, rail/grid controlado.

### Próximos

Em mobile, preferir rail horizontal a coluna enorme.

### Encerrados

Visualmente subordinados.

## 4. Busca e filtro (OPT1)

Quando implementado:
- busca previsível;
- filtros objetivos;
- estado vazio;
- limpar filtro fácil;
- manter estado/preço/tempo visíveis.

Evitar dezenas de chips.

## 5. Login e papéis

Interface: Leiloeiro / Licitante.
Código/API: AUCTIONEER / BIDDER.

Leiloeiro: Vitrine, Meus lotes, Criar lote.
Licitante: Vitrine, Carteira, Meus arremates.

Não promover ação proibida.

## 6. Criação de lote

Etapas:
1. buscar obra;
2. escolher domínio público;
3. conferir dados;
4. início/fim;
5. lance inicial;
6. incremento;
7. revisão;
8. publicar.

Busca da API em lista visual, não cards gigantes.

## 7. Painel do leiloeiro

Preferir tabela/lista com:
- obra;
- estado;
- início;
- fim;
- lance;
- quantidade quando disponível;
- ação permitida.

## 8. Carteira

Topo:
- total;
- comprometido;
- disponível.

Disponível é o valor mais acionável.

Depósito simulado com feedback direto. Sem gráfico decorativo.

## 9. Sala do lote

Ao abrir:
- estado;
- obra;
- título/artista;
- lance atual;
- tempo;
- ação.

Desktop: arte + painel operacional.

Painel:
- estado;
- countdown;
- lance atual;
- mínimo;
- posição;
- saldo;
- campo/ação;
- feedback;
- histórico.

Sugestões de valor são atalhos; nunca sobrescrevem valor válido digitado.

Estados:
- `✓ Você está ganhando`;
- `↑ Você foi superado`;
- neutro.

Recusas: mostrar motivo real do servidor:
- abaixo do mínimo;
- saldo insuficiente;
- já está ganhando;
- não iniciado;
- encerrado.

WebSocket atualiza; lance é POST.
Ao reconectar, snapshot restaura estado.

Anti-sniping: UI apenas reflete `ends_at` do servidor.

## 10. Encerrado, apurando

- remover ação de lance;
- mostrar texto explícito;
- não afirmar vencedor;
- manter histórico consultável.

## 11. Histórico

Sala: recente e compacto.
Auditoria: completo.

Com muito volume, paginação/carregamento progressivo é preferível, mas não inventar endpoint fora da story.

## 12. Encerramento

1. ação some;
2. estado muda;
3. apuração;
4. resultado após liquidação.

Sem lances: encerrado sem vencedor.

## 13. Meus arremates

Cada item:
- imagem pequena;
- título;
- estado;
- resultado;
- comprovante/link quando disponível.

## 14. Comprovante

Documento compartilhável.

Se integridade falhar, nunca dizer "Integridade verificada".

## 15. Auditoria pública

Sem login.

Mostrar:
- lote;
- sequência;
- pseudônimo;
- valor;
- timestamp;
- integridade;
- detalhes técnicos necessários.

Hash não domina a hierarquia.

## 16. Mobile

Vitrine:
- destaque cedo;
- hero menor;
- rails horizontais;
- nada importante depende de hover.

Sala:
- estado/tempo;
- obra;
- valor;
- posição;
- CTA;
- histórico.

Administrativo:
- tabelas viram blocos densos, não cards decorativos.

## 17. Imagem

Estados:
1. espaço reservado;
2. carregando silenciosamente;
3. imagem;
4. fallback.

Se IIIF falhar, todo o resto continua.

## 18. Stress test obrigatório

Revisar com:
- 5 ao vivo;
- 20 próximos;
- 50 encerrados;
- títulos longos;
- valores grandes;
- IIIF lento/quebrado;
- 320px;
- desktop largo.

## 19. Critério final

A obra deve parecer a razão da página existir. A interface serve a obra e a decisão de lance.
