# Cronograma de Implementação — Casa de Leilões

Prazo final: 29/10/2026.
28/10 é o último dia planejado de desenvolvimento.
29/10 é buffer para smoke test, correções pequenas, documentação final e envio.

## Princípio
Fluxo vertical primeiro. A cada dia deve existir uma entrega demonstrável e integrada.

## Dia 1 — 22/10 — Arquitetura — concluído
AD-1 a AD-30, CLAUDE.md e regras do processo fechadas.

## Dia 2 — 23/10 — Fundação + primeiro deploy
Resultado esperado:
- monorepo;
- FastAPI;
- React/Vite/TypeScript;
- PostgreSQL;
- migrations;
- GET /health;
- frontend mínimo;
- banco de desenvolvimento e teste separados;
- configuração de ambiente sem segredos;
- Dockerfile multi-stage;
- primeiro deploy no Render com PostgreSQL.

Não fazer neste dia:
- autenticação completa;
- motor de lances;
- auditoria;
- telas sofisticadas.

## Dia 3 — 24/10 — Autenticação + lotes + API externa
- AUCTIONEER/BIDDER;
- login/logout;
- seed;
- integração Art Institute of Chicago;
- criação de lotes;
- snapshot da obra;
- vitrine e detalhe.

## Dia 4 — 25/10 — Carteira + motor de lances
- wallets;
- depósito;
- saldo comprometido;
- transação do lance;
- locks;
- clock_timestamp();
- concorrência;
- anti-sniping;
- testes críticos em PostgreSQL real.

## Dia 5 — 26/10 — Tempo real + encerramento
- WebSocket;
- snapshot e reconexão;
- heartbeat;
- scheduler;
- fechamento;
- liquidação;
- comprovante;
- idempotência.

## Dia 6 — 27/10 — Auditoria + fluxos finais
- pseudônimos;
- serialização canônica;
- SHA-256 encadeado;
- HMAC;
- auditoria pública;
- meus arremates;
- comprovante compartilhável;
- integração visual.

## Dia 7 — 28/10 — Hardening + UX + entrega
- verify completo;
- segurança;
- erros;
- responsividade;
- README;
- docs/uso_de_ia.md;
- testes no deploy;
- opcionais somente se o obrigatório estiver verde.

## 29/10 — Buffer
Somente:
- smoke test;
- correções pequenas;
- validação do deploy;
- documentação;
- submissão.

Nenhuma feature estrutural nova.

## Regra de corte
Nunca cortar:
- autenticação e papéis;
- lotes;
- carteira e saldo;
- motor de lances;
- concorrência;
- anti-sniping;
- encerramento e liquidação;
- comprovante;
- auditoria;
- seed;
- deploy;
- README.

Podem ser cortados primeiro:
- dark mode;
- animações;
- refinamentos visuais;
- extras de painel;
- opcionais baratos.
