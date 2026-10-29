---
status: done
story: '6.2a'
story_key: 6-2a-cadastro-de-usuarios
date: '2026-10-29'
---

# Story 6.2A — Cadastro de usuários

> Estado vigente em 29/10/2026: **done**. Review individual deferido por prazo
> ao agregado independente, posteriormente aprovado com R6-AGG-02 RESOLVED.
> Cadastro dos dois papéis comprovado na 6.4 anterior; fechamento autorizado
> após revalidação publicada focal de R6.4-01. [Registro final](../../docs/FECHAMENTO-EPICO-6.md).
> Estados e pendências abaixo são históricos; não houve review individual novo.

Implementei cadastro público conforme [SPEC](../specs/spec-story-6-2a-cadastro-de-usuarios/SPEC.md) e companion aprovados. Decidi não coletar Nome/não migrar; permitir BIDDER/AUCTIONEER; criar User+Wallet zero atomicamente; usar senha 8–1024/Argon2id e conflito 409 explícito com enumeração aceita. Descartei autologin e coleta sem uso. Chave exata 6-2a-cadastro-de-usuarios, isolada da 6.2 e sem renumeração.

- [x] CA01: User/papel/hash/e-mail e login posterior.
- [x] CA02: carteira zero dos dois papéis, rollback e concorrência PostgreSQL real.
- [x] CA03/04: formulário ÁTRIO, teclado/toque/toggle, barreira síncrona e 1440/375/320 sem overflow.
- [x] CA05: confirmação em login sem cookie no cadastro, returnTo seguro e demos preservados.
- [x] CA06/07: inventário W7, oitava inesperada reprova, bloqueios sem handler/dados/cookie e envelope sanitizado.
- [x] CA08: focais, smoke real, gate completo com E2E e capturas temporárias.
- [x] Review independente atendido pelo agregado final e re-review em outra sessão, conforme exceção humana de prazo; sem inventar review individual.

Resultados e limites em [implementation-evidence.md](../specs/spec-story-6-2a-cadastro-de-usuarios/implementation-evidence.md). SPEC in-review e story/sprint review; não marco done sem review humano. 6.2 done por aceite humano com LOW aceito, 6.1 continua review por CA2 público pendente, épico 6 in-progress e 6.3 backlog. Não fiz Git/gh/deploy nem li .env*.


## Exceção de processo vigente — 29/10/2026, Story 6.3

Por decisão humana de prazo, review independente individual DEFERIDO ao review
agregado final do Épico 6. Gates anteriores permanecem registrados; mantenho
review sem alegar revisão independente. A ausência não bloqueou a 6.3.
