---
status: review
story: '6.2a'
story_key: 6-2a-cadastro-de-usuarios
date: '2026-10-29'
---

# Story 6.2A — Cadastro de usuários

Implementei cadastro público conforme [SPEC](../specs/spec-story-6-2a-cadastro-de-usuarios/SPEC.md) e companion aprovados. Decidi não coletar Nome/não migrar; permitir BIDDER/AUCTIONEER; criar User+Wallet zero atomicamente; usar senha 8–1024/Argon2id e conflito 409 explícito com enumeração aceita. Descartei autologin e coleta sem uso. Chave exata 6-2a-cadastro-de-usuarios, isolada da 6.2 e sem renumeração.

- [x] CA01: User/papel/hash/e-mail e login posterior.
- [x] CA02: carteira zero dos dois papéis, rollback e concorrência PostgreSQL real.
- [x] CA03/04: formulário ÁTRIO, teclado/toque/toggle, barreira síncrona e 1440/375/320 sem overflow.
- [x] CA05: confirmação em login sem cookie no cadastro, returnTo seguro e demos preservados.
- [x] CA06/07: inventário W7, oitava inesperada reprova, bloqueios sem handler/dados/cookie e envelope sanitizado.
- [x] CA08: focais, smoke real, gate completo com E2E e capturas temporárias.
- [ ] Review independente em outra sessão, após inspeção humana das capturas.

Resultados e limites em [implementation-evidence.md](../specs/spec-story-6-2a-cadastro-de-usuarios/implementation-evidence.md). SPEC in-review e story/sprint review; não marco done sem review humano. 6.2 done por aceite humano com LOW aceito, 6.1 continua review por CA2 público pendente, épico 6 in-progress e 6.3 backlog. Não fiz Git/gh/deploy nem li .env*.


