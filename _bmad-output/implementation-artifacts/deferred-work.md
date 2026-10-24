# Trabalho adiado

## Deferred from: code review of 2-1-formato-de-erros-e-validacao-de-origin.md (24/10/2026)

- O traceback de um 500 pode conter parâmetros de consulta do SQLAlchemy no log do servidor. Avaliar `create_engine(..., hide_parameters=True)` em `backend/app/db.py` quando houver dados de usuário (a partir da 2.2). Pré-existente (1.2).
- O `loc` do 422 pode ecoar chaves escolhidas pelo cliente em modelos `dict[str, ...]` ou `extra="forbid"`, e `details` não tem limite de itens. Inalcançável com as rotas atuais; mudar o conteúdo do `loc` exige rever a D1 da 2.1.
- `sprint-status.yaml` ainda registra `epic-1: in-progress` e a 1.4 como `review`. Pré-existente; fechar quando o épico 1 for formalmente encerrado.
