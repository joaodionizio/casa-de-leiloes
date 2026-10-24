# Casa de Leilões

Leilões online (Desafio Elite Dev, Verzel). Este README ainda é mínimo: cobre só
o banco local. O roteiro completo de avaliação vem em story futura.

## Banco de dados local

Requer Docker com Compose v2. Um contêiner PostgreSQL 18 com dois bancos,
`casa_de_leiloes_dev` e `casa_de_leiloes_test`:

```bash
docker compose up -d --wait postgres
```

Variáveis (veja `backend/.env.example`, valores fictícios):

```bash
export DATABASE_URL=postgresql://casa:casa_local_dev@127.0.0.1:5432/casa_de_leiloes_dev
export TEST_DATABASE_URL=postgresql://casa:casa_local_dev@127.0.0.1:5432/casa_de_leiloes_test
```

Aplicar as migrations no banco de desenvolvimento:

```bash
cd backend && uv run alembic upgrade head
```

Rodar os testes (o banco `_test` é recriado a cada sessão) e a verificação completa:

```bash
cd backend && uv run pytest
./verify.sh
```

O `./verify.sh` fornece URLs locais padrão para `DATABASE_URL` e
`TEST_DATABASE_URL` quando elas não estão definidas no ambiente; valores já
exportados no shell têm precedência. Por isso o verify não depende de
`backend/.env`.

Recriar o volume do zero (apaga os dois bancos; o script de criação só roda com
volume vazio):

```bash
docker compose down -v
```
