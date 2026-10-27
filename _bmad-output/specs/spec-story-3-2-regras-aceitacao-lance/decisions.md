
> **Nova revisão humana da AD-5 — 27/10/2026 (antes da Story 4.3).** Decidi voltar à regra cumulativa: com `0 < ends_at - now <= 2 minutos`, cada lance válido acrescenta 2 minutos ao término vigente (`ends_at vigente + 2 minutos`), inclusive com exatamente 2:00 restantes (flag verdadeira). A decisão intermediária `now + 2 minutos` foi revogada. Preservo abaixo o texto original como registro histórico; fórmulas e notas anteriores devem ser lidas na sua data. Lote encerrado nunca reabre; frontend/WebSocket apenas aplicam o `ends_at` persistido. Ver AD-5 em `docs/ARQUITETURA.md`.

# Decisões — Story 3.2

> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

## 1. Decisões do Joaodionizio (P1 a P13 e C1, fechadas em 25/10/2026; não reabrir)

Registro completo, com as alternativas descartadas, em
`_bmad-output/implementation-artifacts/3-2-regras-de-aceitação-do-lance-com-hora-injetada.md`
("Decisões fechadas"). Onde a story tem texto histórico ("Questões abertas", "C1 —
registro histórico"), vale a tabela abaixo.

| # | Decisão | Descartado |
| --- | --- | --- |
| P1 + C1 | Dataclasses congeladas puras `CurrentBid`, `LotBidState`, `BidAttempt(bidder_id, amount_cents)` (sem saldo), `BidAccepted`; `evaluate_bid(lot, attempt, available_balance_cents, now) -> BidAccepted \| BidRefusal` | parâmetros soltos; Pydantic; método no ORM; saldo dentro de `BidAttempt` |
| P2 | `StrEnum` com exatamente `lot_not_started`, `lot_ended`, `below_minimum`, `already_winning`, `insufficient_balance`; fora de `errors.py`/`MESSAGES` | outros nomes; catálogo já na 3.2 |
| P3 | Ordem do AD-7: período → mínimo → líder → saldo → aceite; líder abaixo do mínimo recebe `below_minimum` | líder antes do mínimo (exigiria mudar o AD-7); saldo antes do mínimo; ordem implícita |
| P4 | `current: CurrentBid \| None`; valor e líder inseparáveis | dois opcionais; sentinela `0` |
| P5 | `BidAccepted(ends_at, anti_sniping_applied)`, `ends_at` efetivo sempre presente | `new_ends_at: None`; aceite vazio |
| P6 | Mínimo `int \| None`; `None` quando `current + increment > MAX_CENTS` → `below_minimum` | sexto motivo; clamp; inteiro acima do teto |
| P7 | Estado inválido = `ValueError`, nunca recusa de negócio; lote agendado com `current` → `lot_not_started` | `assert`; recusa no lugar da exceção |
| P8 | `LotPhase`/`lot_phase` em `app/lot_time.py`, reexportados por `app.lots`; `lot_phase` recusa horários sem fuso e `starts_at >= ends_at`; semântica intocada | importar de `app.lots`; fase pronta; reescrever |
| P9 | `app/bid_rules.py` puro; `app/bids.py` é da 3.4 | módulo único; pacote |
| P10 | Validação na construção; funções públicas validam argumentos soltos; sem repetir tabelas | só `now`; `assert`; repetir |
| P11 | Etapa pré-carteira reutilizável (período → mínimo → líder); `evaluate_bid` a reutiliza | só `evaluate_bid`; duas implementações |
| P12 | Cancelamento fora da 3.2 | campo agora |
| P13 | Questão 5 já decidida no `ARQUITETURA.md`; a 3.2 concretiza a parte pura; `ARQUITETURA.md` e `CLAUDE.md` não mudam | registrar "resolvida em parte" |

## 2. Detalhamento técnico desta spec (D1 a D14)

Resolvidos na spec, dentro das decisões acima. Nenhum muda uma AD ou uma P.

| # | Decisão | Por quê | Descartado |
| --- | --- | --- | --- |
| D1 | **API pública.** `app.lot_time`: `LotPhase`, `lot_phase`, `require_aware`, `check_lot_window`. `app.bid_rules`: `BidRefusal`, `CurrentBid`, `LotBidState`, `BidAttempt`, `BidAccepted`, `EligibleBid`, `ANTI_SNIPING_WINDOW`, `ANTI_SNIPING_EXTENSION`, `minimum_bid_cents`, `evaluate_pre_wallet`, `evaluate_post_wallet`, `evaluate_bid` | "pré/pós-carteira" nomeia o ponto do fluxo da 3.4 (antes/depois de travar carteiras); `require_aware` e `check_lot_window` são compartilhados entre os dois módulos e não devem ser importados com `_` | `check_bid_terms`; `settle_*` (colide com "liquidação") |
| D2 | **Composição.** `evaluate_pre_wallet(lot, attempt, now) -> EligibleBid \| BidRefusal`; `evaluate_post_wallet(eligible, available_balance_cents) -> BidAccepted \| BidRefusal`; `evaluate_bid` = valida o saldo → `evaluate_pre_wallet` → se recusa, devolve → `evaluate_post_wallet`. É **literalmente** o caminho da 3.4, então a equivalência é estrutural, não só testada | uma única implementação de cada regra; nenhuma regra roda duas vezes no caminho da 3.4 | intermediário privado (a 3.4 precisaria importar nome com `_`); pré-carteira devolvendo `None` (a etapa de saldo teria de receber `lot`, `attempt`, `now` de novo e poderia ser chamada sem a pré); flag booleana; segunda cópia das regras |
| D3 | **`EligibleBid` só nasce na pré-carteira.** Campos `amount_cents`, `ends_at`, `now` (os dois em UTC), mais um `InitVar` `issued` que precisa ser o token privado do módulo; construção direta ou `dataclasses.replace` → `ValueError` (conferido em Python 3.13) | torna impossível, por acidente, chegar ao saldo sem passar pela pré-carteira; carrega só o que a etapa seguinte usa | carregar `lot`/`attempt` inteiros (dados irrelevantes); confiar só no tipo; classe sem dataclass |
| D4 | **Validação por dono.** `lot_time.require_aware` (é `datetime`, tem offset) e `lot_time.check_lot_window` (os dois com fuso, início antes do fim). Em `bid_rules`, privados: `_require_cents(name, value, lowest)` e `_require_user_id(name, value)`. Tabela de quem chama o quê em `domain-contract.md` §4 | cada regra existe uma vez; `lot_phase` e `LotBidState` usam a mesma checagem de janela | repetir as checagens em cada função |
| D5 | **IDs** são `uuid.UUID`; `str`, `int`, `None` → `ValueError` | `users.id` é `UUID`; comparação de líder por igualdade de `UUID` é exata | `str`; aceitar qualquer hashable |
| D6 | **`@dataclass(frozen=True, kw_only=True)`** em todos os tipos de domínio | impede trocar `starts_at`/`ends_at` ou valor/ID por posição (o motivo de a P1 descartar parâmetros soltos) | construção posicional |
| D7 | **Instantes em UTC.** `lot_phase`, `check_lot_window` e o anti-sniping comparam/subtraem depois de `astimezone(UTC)`; `EligibleBid` e `BidAccepted.ends_at` saem em UTC | o Python compara e subtrai pelo relógio de parede quando os dois `datetime` têm o **mesmo** `tzinfo`, ignorando `fold` e offset (conferido); a semântica documentada já é "compara instantes", então isto a torna exata, sem mudar nenhum resultado com offsets fixos | comparar os objetos crus (falha numa hora ambígua com o mesmo fuso) |
| D8 | **Saldo validado na entrada** de `evaluate_bid` (antes do período) e de `evaluate_post_wallet`. No aceite de `evaluate_bid` o mesmo auxiliar roda duas vezes | saldo corrompido nunca se esconde atrás de `lot_ended` (P7); a dupla checagem de um inteiro é o custo da equivalência estrutural de D2 | validar só na pós-carteira (esconderia corrupção em lote encerrado); `evaluate_bid` chamar uma função privada sem validação (quebraria a equivalência estrutural) |
| D9 | **Exceção única:** todo erro de programação é `ValueError`, inclusive tipo errado; mensagem em inglês com o nome do campo e sem o valor. `lot_phase` valida `starts_at`, `ends_at`, a ordem e depois `now`; a mensagem `"now must be timezone-aware"` se mantém | o chamador da 3.4 trata uma só classe; precedente F-09 da 3.1; `test_naive_now_is_refused` continua passando | `TypeError` para tipo; `assert` |
| D10 | **Testes:** `tests/test_lot_time.py`, `tests/test_bid_rules.py` (construtores no próprio arquivo), `tests/test_domain_purity.py`; `tests/test_lot_phase.py` intocado | o arquivo antigo, importando de `app.lots`, é a prova da reexportação | editar `test_lot_phase.py`; módulo de suporte separado |
| D11 | **Precedência à prova de acaso:** passos numerados no código, docstring que declara a ordem como contrato, 36 linhas escritas à mão, 8 testes nomeados e mutações M1–M11 obrigatórias | a ordem é verificada por testes que quebram se ela mudar, não pela leitura do código | lista de regras iterada (indireção sem ganho); tabela derivada do código |
| D12 | **Execução única provada por spy:** `monkeypatch` de `bid_rules.lot_phase`, `bid_rules.minimum_bid_cents` e `bid_rules.evaluate_post_wallet`, contando chamadas | prova objetiva de "uma vez por caminho" e "recusa pré-carteira nunca chega ao saldo" | inspeção manual |
| D13 | **Guarda de relógio:** AST com allowlist de imports e atributos proibidos (`test-plan.md` §9) + teste comportamental 2000 × 2100 | simples, sem framework | `freezegun`; patch global do relógio |
| D14 | `ANTI_SNIPING_WINDOW = timedelta(minutes=2)` e `ANTI_SNIPING_EXTENSION = timedelta(minutes=2)` | o AD-5 descreve dois conceitos (janela e extensão) | uma constante só |

## 3. Incompatibilidades com o código e observações

Nenhuma bloqueante. Nenhuma decisão reaberta.

| Ponto | Código hoje | Tratamento |
| --- | --- | --- |
| `lot_phase` só valida `now` | `starts_at`/`ends_at` sem fuso dão `TypeError`; `starts_at >= ends_at` devolve fase | P8, D4, D9 |
| Mesmo `tzinfo` em hora ambígua | `lot_phase` compararia pelo relógio de parede | D7 (refinamento dentro da semântica "compara instantes"); só muda resultado nesse caso exótico |
| `app.money` importa `pydantic` | `bid_rules` carrega `pydantic` de forma transitiva | aceito: a P9/CA13 trata de imports **diretos**; `bid_rules` usa só `MAX_CENTS` |
| `LotPhase` gera o schema do OpenAPI | `test_openapi.py` fixa o `enum` | a classe é movida com o mesmo nome, valores e docstring |
| `CLAUDE.md` lista a questão 5 como aberta | o `ARQUITETURA.md` já a decide | P13: não corrigido nesta story (divergência 4 da story) |
| Dívidas administrativas | `epic-1: in-progress`; `deferred-work.md` cita a 1.4 em `review` | fora do escopo (divergência 9 da story) |
