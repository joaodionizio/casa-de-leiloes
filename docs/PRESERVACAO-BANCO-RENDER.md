# Preservação do PostgreSQL do ÁTRIO na Render

**Prazo informado pela Render:** suspensão em **23/11/2026** para o banco
`casa-de-leiloes-db`. O backup deve ocorrer **antes** da suspensão, e a
restauração precisa ser validada em um banco separado.

A [Render confirma](https://render.com/docs/free) que PostgreSQL gratuito
expira 30 dias após a criação e não tem backups gerenciados. A documentação
de [backups oficiais](https://render.com/docs/postgresql-backups) recomenda
`pg_dump` local para exportar bancos gratuitos. Depois da expiração, há
um período de 14 dias para mudar para plano pago; não conte com ele como
estratégia de backup.

## 1. Escolha a continuidade

- **Sem custo de hospedagem adicional, com exportação e migração:** obtenha
  um dump antes do vencimento, teste a restauração e configure uma nova
  instância persistente adequada ao projeto. A URL da aplicação só muda
  depois de criar e testar o banco de destino.
- **Upgrade na Render:** verifique preços, retenção e condições no
  painel antes de aprovar gastos; o upgrade pode exigir uma breve
  indisponibilidade e não substitui um backup independente.

**Não apague nem restaure sobre o banco de produção.** Conserve o banco
original até a nova aplicação ter sido validada.

## 2. Faça um backup local, privado, no Mac

1. Instale ferramentas PostgreSQL com `pg_dump` compatível com a versão
   do servidor (mesma versão principal ou mais nova). No Mac,
   `brew install libpq` fornece os clientes; coloque seu diretório
   `bin` no `PATH` se necessário.
2. No painel da Render, copie a **External Database URL** da instância
   exata `casa-de-leiloes-db`; ela é um segredo. Não envie por chat,
   não cole em commits e não tire capturas de tela mostrando a senha.
3. No terminal confiável, configure `RENDER_EXTERNAL_DATABASE_URL`
   sem gravar o valor no repositório nem no histórico do shell. Prefira
   o gerenciador de segredos da sua máquina.
4. Da raiz do repositório, rode:

```bash
bash -n scripts/backup-render-postgres.sh
bash scripts/backup-render-postgres.sh
```

O script gera em `backups/` um arquivo `.dump` (formato custom do PostgreSQL),
um manifesto e um SHA-256. A pasta é ignorada pelo Git, e os arquivos
recebem permissões restritas. O script não executa `DROP`, `CREATE`,
restauração ou alterações no banco remoto.

`pg_restore --list` verifica se o sumário do arquivo é legível, **não**
se os dados podem ser efetivamente restaurados. Não considere esta
etapa suficiente.

## 3. Valide a restauração isoladamente

Use um contêiner **descartável**, distinto do PostgreSQL local da
aplicação. Esta sequência cria um banco de testes novo e não aponta
para a Render:

```bash
docker run --rm -d --name atrio-restore-check \
  -e POSTGRES_PASSWORD=only_for_local_verification postgres:18

# Aguarde o pg_isready devolver "accepting connections".
docker exec atrio-restore-check pg_isready -U postgres -d postgres

# Troque o placeholder pelo arquivo local criado na etapa anterior.
docker cp "backups/SEU_ARQUIVO.dump" atrio-restore-check:/tmp/backup.dump

docker exec atrio-restore-check createdb -U postgres atrio_restore_test
docker exec atrio-restore-check pg_restore \
  -U postgres -d atrio_restore_test \
  --no-owner --no-privileges /tmp/backup.dump

docker exec atrio-restore-check psql \
  -U postgres -d atrio_restore_test -c '\dt'

# Ao terminar a verificação, encerre apenas este contêiner descartável.
docker stop atrio-restore-check
```

Se o cliente reclamar que o servidor não está pronto, aguarde e execute
novamente **somente** o comando de prontidão. Não pule erros de `pg_restore`.
Confira a existência das tabelas da aplicação e `alembic_version`,
a consistência de contagens e a possibilidade de login num ambiente
isolado, sem expor informações privadas.

## 4. Migração e validação da aplicação

1. Crie a nova instância PostgreSQL no serviço escolhido, com versão
   compatível, e **restaure somente em banco vazio**.
2. Configure segredos diferentes para ambientes de teste e produção;
   cuide de `JWT_SECRET`, segredos de auditoria/HMAC e pseudônimos já
   persistidos, que também precisam ser preservados com segurança
   quando uma restauração deve manter sua verificabilidade histórica.
3. Faça um deploy temporário que utilize **apenas** o banco migrado.
   Execute saúde, login, carteira, saldo comprometido, lances,
   liquidação e comprovante, além de auditoria do histórico.
4. Planeje uma janela de corte para impedir escrita simultânea
   no banco antigo depois do último dump; gere um backup final,
   restaure e então altere `DATABASE_URL` da aplicação.
5. Após validar a aplicação apontada para o novo banco, só então
   decida o destino do banco antigo.

**Limitações:** este repositório fornece o procedimento e valida a
sintaxe do script no CI. Ele **não** certifica que algum backup real
foi executado nem que a migração aconteceu.

Fontes: [Render Free Postgres](https://render.com/docs/free),
[Render Postgres Recovery and Backups](https://render.com/docs/postgresql-backups).
