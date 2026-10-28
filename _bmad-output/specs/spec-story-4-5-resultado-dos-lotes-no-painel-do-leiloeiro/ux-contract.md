# Contrato final de UX

Quero acrescentar resultado à lista densa existente, preservando miniatura, título,
artista, termos e cancelamento funcional. QH-01–13 estão decididas; não redesenho
o painel. Resultado e total aparecem na mesma listagem.

## Estado textual final

| Persistência/fase | Label aprovado | Dados e ações |
| --- | --- | --- |
| Não cancelado, sem settlement, scheduled | Agendado | Termos/contagem atuais; cancelamento só conforme regras existentes |
| Não cancelado, sem settlement, live | Ao vivo | Mesma regra de apresentação atual |
| ended sem settlement | Encerrado, apurando resultado | Sem vencedor/valor final/receipt; abrir ou atualizar não liquida |
| Settlement sold coerente | Vendido | Pseudônimo, Valor final em BRL, Apurado em settled_at, count congelado |
| Settlement unsold coerente | Sem arremate | Apurado em settled_at e count=0; sem vencedor/preço final artificial |
| cancelled_at presente, sem settlement | Cancelado | Prevalece sobre fase/ausência de lances; sem resultado vendido/unsold |
| Par/Lot contraditórios ou contrato desconhecido | Erro de leitura integral | Nunca label econômico inventado; sem tentativa de reparo |

Não apresento pending técnico como Apurando para lotes agendados/ao vivo/cancelados.
Não adiciono phase sold/unsold/cancelled; a UI compõe eixos server-side já validados.
Hash técnico e receipt ficam ausentes por QH-03/04. Não exibo
botão/link morto, badge decorativo em pill ou nova página de resultado por antecipação.

## Linha vendida e total aprovado

Hierarquia: miniatura/obra → estado → valor final → vencedor por alias →
instante de apuração → metadados/contagem. Nomear `Vencedor`, `Valor final`, `Apurado em`;
`Término` continua ends_at vigente. Settlement tardio pode ocorrer depois do término;
não substituir uma data pela outra ou chamar settled_at de hora do commit. Uso
formatCents e formatDateTime existentes, UTC recebido e fuso do navegador explicitado.
Não invento America/Maceio como fuso fixo do produto.

QH-13 decidiu **Total recebido**, uma única cifra simples, formatada do agregado do
backend, próxima ao título/contagem. Não é saldo de carteira, previsão, gráfico ou
estatística adicional. Com zero vendas válidas, R$ 0, 00 é legítimo para o agregado;
continua proibido usar zero como preço de arremate unsold. Não renderizar total=0
por falha/loading/contrato antigo. Em erro de atualização, marcar total anterior
como parte do mesmo snapshot desatualizado.

Mostro count na linha, onde já existe, usando count congelado após apuração.
Não duplicar duas contagens ou mostrar maior bid como valor final. Mantenho
ordem created_at DESC/id DESC e nenhum filtro novo por QH-07/08.

## Loading, erro, vazio e atualização

| Estado da leitura | Comportamento final |
| --- | --- |
| Carregamento inicial | Texto Carregando seus lotes… em região status; sem placeholders de resultado/total fictício |
| Erro inicial | Não foi possível carregar seus lotes.; Tentar novamente, salvo 403; sem lista vazia falsa |
| Lista vazia válida | Você ainda não criou lotes.; Criar lote funcional; total recebido R$ 0, 00 |
| Atualizando com dados conhecidos | Conservar lista/total e interação; indicação Atualizando… sem roubar foco |
| Atualização falhou | Conservar snapshot e indicar Não foi possível atualizar a lista. Os dados exibidos podem estar desatualizados.; permitir nova tentativa manual |
| 401 | Fluxo existente de sessão expirada; invalidar dados/requests da conta |
| 403 | Mensagem de acesso; parar tentativas automáticas e não preservar dados privados de sessão inválida |
| Inconsistência | QH-11: erro integral seguro, sem resultado/total parcial; snapshot anterior só com aviso de desatualização |

Backend não converte erro em settlement ausente. Frontend também não usa fallback de
union/enum para unsold/ended. Num refetch com erro, um pending antigo permanece como
fotografia anterior identificada; não afirmar que ainda está sendo processado agora.
Guardo/exibo as_of via linha Situação atualizada, para qualificar a idade
da fotografia, usando formato de hora existente. Não depende do relógio local para
confirmar expiração ou resultado. Botão manual se chama Atualizar, com estado Atualizando… durante a leitura.

## Layout, acessibilidade e regressões

Lista/tabela editorial densa, divisores/tokens existentes, roxo como assinatura.
Status sempre em texto, sem depender de cor, com contraste/foco visível. Atualização
não move foco nem reabre confirmação de cancelamento; mudanças resumidas numa região
status discreta, sem ler todos os lotes repetidamente. Retry acessível por teclado.

Validar 320/375px e desktop, 30/50 lotes, título/alias longos, valor máximo, datas com
fuso e imagem falha. Mobile usa blocos densos por linha, sem scroll horizontal global,
miniaturas com dimensões/fallback e ações com alvo ~44px. Não criar card grande por lote.
Preservar cancelamento inline/confirmar/voltar, foco, double-submit guard e criação.
Não inventar edição de lote para satisfazer regressão de uma função não localizada.
