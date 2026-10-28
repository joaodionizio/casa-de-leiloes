# Review independente final — Story 5.1 — 28/10/2026

Decidi aprovar e concluir a Story 5.1 conforme autorização humana: **0 HIGH /
0 MEDIUM / 0 LOW funcional**. Descartei achados cosméticos de cobertura e repetição
de gates sem suspeita concreta. Review estático com revisores Sol (`gpt-6.1-sol`,
raciocínio medium), baseado na SPEC, story, implementation-evidence, arquivos
efetivamente alterados e dependências necessárias para conferir integridade/4.3.

| Risco crítico | Conferência |
| --- | --- |
| 1. Acesso público | `lot_audit.py` registra PUBLIC; `access.py` não exige sessão para essa política. |
| 2. Privacidade | DTOs explícitos permitem apenas contrato público; nenhuma identidade privada, carteira, saldo, HMAC, JWT ou segredo é projetado. Aliases passam pelo formato canônico antes da serialização. |
| 3. SHA-256/canonical v1 | Primitivas existentes reutilizadas, fora dos arquivos alterados; bytes canônicos seguem AD-21. |
| 4. HMAC interna | Verificada no servidor; assinatura/âncora não pertencem ao DTO. |
| 5. Adulteração | Cadeia, HMAC, contagem/hash e vínculos são conferidos antes da projeção; falha retém estado, resultado e histórico. |
| 6. Zero escrita | SELECT com autoflush=False; handler encerra com rollback, sem liquidação, commit ou reparo. |
| 7. API externa | Auditoria lê somente registros locais, sem chamada ao catálogo. |
| 8. Ordem | ORDER BY Bid.sequence; verificador exige sequência contínua e encadeamento. |
| 9. Estados distintos | Fase temporal separada de pending/settled; sold/unsold persistidos e cancelled/not_applicable distintos. |
| 10. Coerência 4.3 | `_structural_conflict` reutilizado; resultado, vencedor, alias, sequência, valor, contagem/hash, HMAC e datas conferidos contra lote/histórico. |
| 11. N+1 | Uma consulta com joins e projeção de colunas; nenhum carregamento ORM implícito ou consulta por bid. |
| 12. Frontend público | Rota renderizada antes do bloqueio de sessão; parser exige chaves públicas exatas e a página exibe só esses campos. |
| 13. Falha segura | Ausente retorna 404, UUID inválido 422, falha operacional 500 genérico; inconsistência retém dados; parser inválido vira erro. |
| 14. Quatro expectativas antigas | Dois guards compartilham mapa que recebeu somente audit/PUBLIC; lista exaustiva OpenAPI acrescenta audit; slices deslocados preservam ordem e acrescentam posição de audit. Nenhuma asserção enfraquecida. |

Conferi os ajustes dos guards contra a baseline local da implementação, sem Git.
Também conferi os testes existentes de adulteração SQL, pureza, contrato público,
estados e navegação anônima. Nenhuma suspeita concreta exigiu execução focal.
Não executei testes, verify, suíte completa ou mutation testing neste review.

Considerei o gate já registrado: backend 2260, frontend 187, Playwright 254,
cinco skips opt-in e Docker aprovado; focais anteriores: 22 PostgreSQL,
23 contrato/rotas, 13 Playwright e 58 políticas/OpenAPI. Esses resultados pertencem
à implementação anterior, não são novas execuções desta sessão.

Concluí somente documentação/tracking: Story/SPEC/sprint 5.1 done; Epic 5
in-progress. Não alterei código ou testes, não executei Git, não li `.env*`,
não fiz deploy nem iniciei Story 5.2/5.3. Permanecem os limites documentados da
HMAC interna e do histórico O(n), sem paginação nesta story.
