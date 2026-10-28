# Registro de correções do code review — Story 4.4

## F44-01 — LOW: reconciliação final

Resolvido por cobertura: o E2E SOLD parte de histórico defasado, exige o GET público após `lot_closed`, confere os três lances e o preço final e verifica terminal sem reconexão nem mensagens de heartbeat. O cenário de falha exige o aviso existente de histórico possivelmente desatualizado e um GET 503, preservando o terminal.

## F44-02 — LOW: retry órfão

Resolvido no scheduler: cada ciclo consulta até 50 IDs do próprio mapa de retries e remove apenas os que têm settlement persistido; os demais são rotacionados sem mudar seu backoff. O teste usa COMMIT real, simula perda de confirmação e confirma ausência de segunda transferência, settlement, receipt ou publicação. Outro lote pendente conserva e aumenta o backoff.

## Mutações focais

- Sem a leitura final, o E2E SOLD falhou: permaneceu `1 lance` em vez de `3 lances`.
- Sem remover o retry liquidado, o teste de ACK perdido falhou porque a entrada permaneceu no mapa.

As mutações foram revertidas. Este registro documenta correções; não constitui uma nova revisão independente. A Story 4.4 continua em review.

Validação final: E2E focado 2/2; regressão focada F44-02 1/1; suíte backend 4.4 41/41; regressões direcionadas 4.1–4.3 153/153. `./verify.sh`: 2207 backend e 179 frontend aprovados. `VERIFY_E2E=1 ./verify.sh`: os mesmos totais, mais 227 E2E aprovados e 5 skips existentes. Ambos terminaram com sucesso após corrigir um erro de lint detectado na primeira tentativa protegida.

## Correções do re-review focal

F44-R01 resolvido: o E2E exige o valor final no próprio `.bid-current`, além de verificar histórico, contagem, GET final e estado terminal. Ao impedir temporariamente a atualização do preço e preservar o histórico, a asserção do preço falhou com R$ 110,00 em vez de R$ 130,00. Restaurei o arquivo de produção.

F44-R02 resolvido: o teste de ACK perdido captura o objeto pending, `delay` e `next_attempt_at`, e verifica sua preservação após o pruning; a evolução de 2 para 4 segundos continua verificada na falha seguinte. Mutações que recriaram o objeto ou alteraram seu prazo foram detectadas nas respectivas asserções e revertidas.

Um teste determinístico com 60 retries confirma que as duas janelas alcançam todos os IDs, removem os dois settled e preservam os demais objetos e prazos. A Story permanece em review; este registro não substitui uma revisão independente.

Validação desta correção: os três testes focais passaram isoladamente; suíte 4.4 **42 passed**, regressões 4.1–4.3 **153 passed**. `./verify.sh`: **2208 backend e 179 frontend**; `VERIFY_E2E=1 ./verify.sh`: **2208 backend, 179 frontend, 227 Playwright e 5 skips**. Ambos passaram com as guardas contra dotenv ativas.


## Gate final — 28/10/2026

O review inicial foi **APROVADO COM LOWS**, sem HIGH ou MEDIUM. Todos os LOWs
foram resolvidos: F44-01, F44-02, F44-R01 e F44-R02. A rotação com mais de
50 retries também foi comprovada com 60 IDs. As mutações focais foram detectadas
e os arquivos de produção restaurados byte a byte. Não permanece defeito
funcional de produção conhecido.

Validação final: 42 testes 4.4, 153 regressões 4.1–4.3; ambos os verifies
exit 0 com 2208 backend e 179 frontend, e o verify com E2E também com 227
Playwright e 5 skips preexistentes. Lint, typecheck e builds aprovados.
**Gate final aprovado; Story 4.4 segura para `done`.** Os incidentes de processo
registrados historicamente não são findings funcionais.
