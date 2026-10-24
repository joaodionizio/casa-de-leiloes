# FRONTEND-WORKFLOW.md — Processo de trabalho do front-end

> Status: diretriz de processo do projeto.
>
> Este documento responde **"como o Claude Code trabalha no front-end?"**. Ele
> não responde "como o front-end deve parecer": isso pertence a `DESIGN.md`,
> `EXPERIENCE.md` e aos blueprints de tela. Aqui só mando ler essas fontes; não
> repito o conteúdo delas.

## 1. Propósito

Defini este processo para que qualquer sessão do Claude Code ou skill do BMAD
planeje, implemente e revise as stories de front-end do mesmo jeito.

Divisão das fontes:

```text
DESIGN.md                  → como deve parecer
EXPERIENCE.md              → como deve se comportar
VITRINE-BLUEPRINT.md       → composição específica da Vitrine
docs/FRONTEND-WORKFLOW.md  → como planejar, implementar e revisar
```

## 2. Ordem de autoridade

```text
story / enunciado
↓
docs/ARQUITETURA.md
↓
DESIGN.md + EXPERIENCE.md + blueprint específico da tela, quando existir
↓
Figma / protótipos / referências externas
```

Para a Vitrine, `DESIGN.md`, `EXPERIENCE.md` e `VITRINE-BLUEPRINT.md` ficam no
mesmo nível de autoridade dentro do escopo de UX/visual. O blueprint não é
inferior aos outros dois: ele só detalha a composição da Vitrine.

## 3. Fontes obrigatórias

Para qualquer story de front-end:

```text
@CLAUDE.md
@docs/ARQUITETURA.md
@_bmad-output/planning-artifacts/DESIGN.md
@_bmad-output/planning-artifacts/EXPERIENCE.md
```

Se envolver a Vitrine:

```text
@_bmad-output/planning-artifacts/VITRINE-BLUEPRINT.md
```

Se outra tela ganhar um blueprint específico no futuro, ele também passa a ser
leitura obrigatória nas stories dessa tela.

## 4. Fluxo oficial

```text
1. bmad-spec          (Opus)
2. minha revisão/aprovação
3. nova sessão quando apropriado
4. bmad-build         (Sonnet)
5. verify
6. teste manual no navegador, quando houver UI
7. bmad-code-review   (Opus, em sessão diferente da que especificou)
8. minha revisão
9. Git, feito por mim
```

Opus planeja, especifica e revisa; Sonnet implementa. Quem especificou não
revisa o próprio trabalho quando for possível separar as sessões.

As regras do `CLAUDE.md` valem dentro de todas as skills: nenhuma delas executa
Git (nem commit, nem diff, nem status). Quando um passo da skill depender de
Git, ela trabalha sobre o estado atual dos arquivos.

## 5. bmad-spec

Especifica e detalha a tarefa antes da implementação. Deve:

- ler a story/tarefa;
- ler as fontes obrigatórias (seção 3);
- listar os critérios de aceite;
- indicar os arquivos prováveis;
- indicar os estados relevantes;
- indicar os testes;
- apontar as decisões abertas;
- nunca tomar uma decisão que pertence a mim.

Se houver decisão aberta, para e me pergunta antes da implementação.

## 6. bmad-build

Antes de editar, mostra em no máximo 8 linhas:

- arquivos que serão criados/alterados;
- o que será implementado;
- estados cobertos;
- testes/checagens.

Depois:

- implementa somente o escopo aprovado;
- não executa Git;
- não antecipa outra story;
- não cria controles sem funcionalidade;
- roda `verify`;
- mostra a saída real;
- para.

## 7. Teste manual

Quando houver UI, depois do build eu testo no navegador antes do code review.
O Claude pode me entregar um roteiro curto do que validar manualmente.

## 8. bmad-code-review

Revisa contra:

- story e critérios de aceite;
- `docs/ARQUITETURA.md`;
- `DESIGN.md`;
- `EXPERIENCE.md`;
- blueprint específico, quando houver;
- testes;
- responsividade;
- acessibilidade;
- coerência com o estado vindo do servidor;
- ausência de funcionalidades antecipadas.

Lista os achados por gravidade. Não corrige nada automaticamente antes da minha
decisão.

## 9. Prompts-base

### bmad-spec

```text
Especifique somente a story <id>.
Leia as fontes obrigatórias de @docs/FRONTEND-WORKFLOW.md (seção 3), incluindo
o blueprint da tela, se existir.
Liste critérios de aceite, arquivos prováveis, estados, testes e decisões
abertas. Não tome decisões minhas: pergunte e pare.
Não execute Git.
```

### bmad-build

```text
Implemente somente a story <id>, a partir da spec aprovada.
Leia as fontes obrigatórias de @docs/FRONTEND-WORKFLOW.md (seção 3), incluindo
o blueprint da tela, se existir.
Antes de editar, mostre em até 8 linhas: arquivos, o que vai implementar,
estados cobertos e testes/checagens. Espere minha aprovação.
Não execute Git, não antecipe outra story e não crie controles sem função.
Ao terminar, rode verify, mostre a saída real e pare.
```

### bmad-code-review

```text
Revise a story <id> sobre o estado atual dos arquivos, sem Git.
Use como referência as fontes obrigatórias de @docs/FRONTEND-WORKFLOW.md
(seção 3) e os critérios da seção 8.
Liste os achados por gravidade. Não altere código antes da minha decisão.
```
