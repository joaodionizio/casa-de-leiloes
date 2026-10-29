# Re-review independente — Story 6.1 — 28/10/2026

**Veredito vigente: APROVAÇÃO TÉCNICA da implementação da Story 6.1.**
**R6.1-01 — RESOLVIDO. Findings técnicos remanescentes no escopo: 0 BLOCKER /
0 HIGH / 0 MEDIUM / 0 LOW.** CA2 no ambiente publicado continua **PENDENTE**;
aprovação técnica local não comprova publicação nem aceite integral da story.

## Resultado do re-review de R6.1-01

Executei `bmad-code-review` exclusivamente sobre a correção autorizada, sem
participar de sua implementação. Reli o relatório anterior e seu anexo de
comandos, SPEC, security-audit, implementation-evidence, story atual,
`test_csrf.py`, `test_access_policy.py`, `tests/access_policy.py`, `app/access.py`,
`app/main.py` e os registros pertinentes de `docs/uso_de_ia.md`. Também li
`CLAUDE.md`, as ADs pertinentes de `docs/ARQUITETURA.md`, o processo de
fechamento, `config.py`, `conftest.py` e a configuração pytest. Não abri `.env*`.

Montei snapshot atual de cinco arquivos (os dois testes, helper e dois módulos
acima): 1.783 linhas, 65.351 bytes, contra `/dev/null`, sem Git. O snapshot não
é diff histórico de commit. As cinco camadas da skill concluíram com modelo
herdado: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor e
Project Auditor. Executaram em lotes conforme as vagas, somente com leitura.
A coordenação fez as reproduções e a triagem descritas abaixo.

**Causa anterior reconfirmada por execução:** carreguei, em módulo temporário,
o teste original da cópia pré-correção validada. Injetei POST sem política nos
três caminhos com `Route` e `APIRoute`, repetindo os 36 casos originais por
combinação caminho/tipo, incluindo com/sem SPA. Em cada caminho documental,
o app tinha sete escritas, `policy_problems` não denunciava a nova rota e o
mapa continuava com seis: **36 passaram indevidamente**. Em `/api/unexpected`,
o verificador anterior reprovou os 36, como controle. Isso reproduz o finding
original; não infiro sua causa apenas do relato do implementador.

**Correção confirmada:** `http_write_inventory` (`test_csrf.py:555`) extrai
caminho e todos os métodos de `app.routes`, usando tipos públicos. Não consulta
`access_policy`, `AccessPolicy`, `policy_by_route`, `policy_problems`, W1–W6 ou
blacklist documental. `assert_real_write_inventory` (:592) compara o observado
com W1–W6 depois da descoberta. Na matriz (:769), essa comparação precede
ambos os helpers de política. Não encontrei circularidade: a constante fornece
somente o esperado e os parâmetros executados; o observado vem da app real.

## Reprodução focal realmente executada

Criei harnesses somente em `/private/tmp/story-6-1-rereview-o7_rhre2`.
Limpei o ambiente do processo, defini valores fictícios e desativei `env_file`
nos Settings **em memória, antes de importar `app.main`**. Um audit hook
recusou abertura de dotenv/credenciais e conexões de rede/banco. Não executei
lifespan, scheduler ou SQL. As injeções e monkeypatches existiram apenas nas
apps/processos descartáveis, com restauração ao sair de cada contexto.

| POST sem política | Tipos e montagem | Cópia anterior: matriz | Candidato corrigido |
| --- | --- | --- | --- |
| `/api/docs` | Route/APIRoute × com/sem SPA | 36 verdes indevidos por tipo | 4/4: nova escrita observada, CA1 reprova |
| `/api/openapi.json` | Route/APIRoute × com/sem SPA | 36 verdes indevidos por tipo | 4/4: nova escrita observada, CA1 reprova |
| `/api/unexpected` | Route/APIRoute × com/sem SPA | 36 recusados por tipo, controle | 4/4: nova escrita observada, CA1 reprova |

Nos **12/12 cenários corrigidos**, com endpoint sem `access_policy`, confirmei:

1. O POST realmente chega ao novo handler e responde **200** com headers válidos.
2. O inventário bruto contém exatamente W1–W6 mais a sétima escrita.
3. A nova chave método/caminho não pertence ao conjunto esperado literal.
4. Substituí **ambos** os helpers de política no módulo do teste por funções
   que lançam `RuntimeError` se chamadas. Ainda assim, a descoberta retorna
   sete e o validador CA1 lança seu `AssertionError` de inventário.
5. A própria matriz rejeita os 18 casos da respectiva configuração SPA antes
   de consultar política: **216/216 reprovações esperadas**, em chamadas diretas.

Também executei via pytest os **29 testes de regressão** da correção, incluindo
as 12 mutações do implementador, e os **36 casos originais de CA1**:
**65 passed, 220 deselected in 0.58s; exit 0**. Estes 65 são testes realmente
executados neste re-review. As 216 reprovações controladas e a reprodução
da matriz antiga são chamadas diretas, não execuções adicionais de pytest.

O pytest focal usou `--noconftest` e `-p no:cacheprovider`, bytecode desativado,
plugins externos desativados e diretório temporário fora do repo. Isso evita
startup/reset do PostgreSQL para provas de inventário/despacho que não usam
banco; **não alterei `conftest.py` nem arquivos de teste/configuração** e não
apresento esse focal como suíte transacional. Houve apenas o aviso existente
de depreciação Starlette/httpx na importação.

## Inventário, fail-closed e regressões

O factory real com e sem SPA retorna exatamente:

```text
POST /api/auth/login
POST /api/auth/logout
POST /api/lots
POST /api/wallet/deposit
POST /api/lots/{lot_id}/bids
POST /api/lots/{lot_id}/cancel
```

Nenhum PUT/PATCH/DELETE atual. GET/HEAD/OPTIONS não entram como escrita;
TRACE também é tratado como seguro. WebSockets conhecidos são excluídos.
Route/APIRoute conservam todos os quatro métodos de escrita declarados;
métodos ausentes/vazios e método não suportado falham explicitamente.
Mount inspecionável é percorrido com prefixo, inclusive aninhado; Mount opaco
e tipo desconhecido levantam `ValueError`, sem desaparecer do inventário.
Duplicata de método/caminho, direta ou por Mount, também reprova. As respectivas
regressões fazem parte dos 29 executados; nenhuma API privada foi exigida.

Conferi as **250 fontes permitidas** do manifesto anterior, excluindo nomes de
segredos antes de abrir qualquer arquivo. A cópia anterior corresponde aos
250 hashes originais; na comparação dela com o candidato atual, somente
`backend/tests/test_csrf.py` difere. A cópia pós-correção
`/private/tmp/story-6-1-r6-1-01-validation-jcq_x_zn` corresponde ao candidato
atual em todas as 250 fontes, sem ausentes ou divergências.

Li também o `diff -u` entre as duas versões de `test_csrf.py`: adição do
inventário e regressões, extração da montagem para fixture e troca do início
da matriz. Permanecem os mesmos 36 parâmetros, envelopes 403/415, corpo em
bytes, conferência do header enviado, ausência de despacho/Set-Cookie/CORS e
controle positivo. Assim, confirmei preservação dos casos e sua relevância.

Essa comparação confirma que a correção preservou produção, middleware CSRF,
autenticação, política de acesso, erros, `conftest.py`, frontend e os arquivos
das provas CA2/CA3/CA4. É comparação com cópias locais e manifesto, **não prova
de correspondência com um commit**, nem auditoria histórica completa da story.

## Evidências pós-correção: conferência e limites

`implementation-evidence.md` registra comandos, saídas e exit 0 para:

| Execução registrada pelo implementador | Registro conferido | Corroboração deste re-review |
| --- | --- | --- |
| Regressão `-k write_inventory` | 29 passed, 256 deselected, 0.34s | 29 casos no cache e todos reexecutados dentro do focal de 65 |
| Sete suítes relacionadas | 533 passed, 34.29s, exit 0 | 533 nodeids nos arquivos correspondentes; não reexecutei essas suítes completas |
| `./verify.sh` renovado | 2343 pytest, 192 Node, exit 0, frase final literal | 2343 nodeids e fontes atuais iguais à cópia pós-correção; não reexecutei o gate |
| Demais etapas do verify | Ruff, 110 arquivos formatados, PostgreSQL Healthy, ESLint, TypeScript, Vite e Docker aprovados | Saída e resultados registrados na evidência; não são novas execuções minhas |

Cache comprova coleta/contagens, não aprovação individual, duração ou exit
code histórico. Trato os números históricos como **resultados registrados**,
com a corroboração limitada acima. Os 29 testes novos explicam a diferença
entre 2314 e 2343. Não identifiquei inconsistência que invalide o gate.

Não repeti `./verify.sh`: o focal não alterou fontes, a cópia validada
corresponde ao candidato e não surgiu dúvida material que exija novo gate.
Playwright não foi repetido; a correção não mudou frontend nem CA3. As provas
anteriores continuam com seus limites, sem nova certificação publicada.

Confirmei o registro de `git status --short` em `implementation-evidence.md`
e `docs/uso_de_ia.md`: desvio de processo já documentado, consulta somente
leitura, sem alteração atribuída ao comando. Não o transformei em finding
técnico. Não executei Git/gh para tentar corroborar o próprio registro.

## Triagem das camadas independentes

Verification Gap, Acceptance Auditor e Project Auditor não apontaram lacuna
na correção. Blind Hunter trouxe duas propostas e Edge Case Hunter uma;
avaliei as três separadamente, sem convertê-las em findings para cumprir quota:

- **BH-1 — LOW, rejeitado como endurecimento herdado fora do alvo:** a exceção
  documental do helper ainda pode omitir um GET/WebSocket hipotético sem
  política em caminho documental (`tests/access_policy.py:60`). Esse helper
  não mudou; não há tal handler nosso no app atual. Escritas novas nesses
  caminhos agora reprovam independentemente dele, como demonstrado. Ampliar
  o verificador de superfícies seguras não é necessário para fechar R6.1-01.
- **BH-2 — LOW, rejeitado como endurecimento hipotético:**
  `_declare_policy` (`app/access.py:116`) inspeciona defaults imediatos, não
  dependências conflitantes arbitrariamente aninhadas. Não identifiquei caller
  atual com a contradição proposta; produção é idêntica à cópia anterior.
  Adicionar travessia/novos guards sem ocorrência atual ampliaria o escopo.
- **EC-1 — LOW, rejeitado como endurecimento hipotético:** a mesma inspeção
  não trata `Depends` dentro de `Annotated`. A busca nos registradores atuais
  encontrou Annotated para validação de dados, sem esse padrão de dependência
  conflitante. Não há quebra atual ou regressão demonstrada que justifique
  acrescentar parsing/guards nesta correção.

Não aceitei novo finding MEDIUM/HIGH/BLOCKER nem criei dívida adiada. As
observações não alegam que a descoberta bruta ainda dependa de política.

## Comandos efetivamente executados neste re-review

- Leitura/busca: `pwd`, `rg --files`, `rg -n`, `cat`, `sed -n`, `nl -ba`,
  `wc -l`, `ls` e laço de verificação dos caminhos ancestrais de `AGENTS.md`
  (nenhum encontrado). A tentativa `cat AGENTS.md` retornou arquivo ausente.
- Resolução BMAD: os dois comandos sem cache alternativo abaixo retornaram
  **exit 2**, antes dos scripts, por lock no cache uv. Com o cache temporário,
  resolver/config e a consulta final `on_complete` retornaram **exit 0**.
  Não havia prepend/append nem ação final configurada.

```sh
uv run _bmad/scripts/resolve_customization.py --skill .agents/skills/bmad-code-review --project-root . --key workflow
uv run _bmad/scripts/resolve_config.py --project-root .
UV_CACHE_DIR=/private/tmp/casa-review-uv-cache uv run _bmad/scripts/resolve_customization.py --skill .agents/skills/bmad-code-review --project-root . --key workflow
UV_CACHE_DIR=/private/tmp/casa-review-uv-cache uv run _bmad/scripts/resolve_config.py --project-root .
UV_CACHE_DIR=/private/tmp/casa-review-uv-cache uv run _bmad/scripts/resolve_customization.py --skill .agents/skills/bmad-code-review --project-root . --key workflow.on_complete
```

- Heredocs `python3` montaram snapshot com `diff -u /dev/null`, copiaram o pedido
  para claims e conferiram os 250 hashes/caches: **exit 0**. Não copiaram segredos.
  `diff -u /private/tmp/story-6-1-validation-lhq0d6le/backend/tests/test_csrf.py backend/tests/test_csrf.py`
  retornou **1**, resultado esperado por haver diferenças, sem erro de leitura.
- Os harnesses foram escritos com `apply_patch` somente no diretório temporário.
  Executei primeiro o candidato corrigido, depois a reprodução completa do
  teste antigo; a causa anterior já havia sido confirmada na leitura e na
  expressão antiga do primeiro harness. Ambos os comandos abaixo deram
  **exit 0**. Fontes integrais e saídas preservadas no apêndice deste relatório.

```sh
backend/.venv/bin/python -B /private/tmp/story-6-1-rereview-o7_rhre2/probe.py > /private/tmp/story-6-1-rereview-o7_rhre2/probe-output.txt 2>&1
backend/.venv/bin/python -B /private/tmp/story-6-1-rereview-o7_rhre2/legacy_probe.py > /private/tmp/story-6-1-rereview-o7_rhre2/legacy-output.txt 2>&1
```

- Registro documental: `python3 /private/tmp/story-6-1-rereview-o7_rhre2/record_review.py`,
  seguido por conferência dos hashes e dos status. A única escrita no repo
  foi este relatório; não editei story, sprint, SPEC, código, testes ou configuração.
  As camadas fizeram apenas leitura/busca nos arquivos permitidos.

## Veredito técnico, status recomendado e pendência pública

**R6.1-01 está RESOLVIDO e a implementação da Story 6.1 recebe APROVAÇÃO
TÉCNICA.** A nova escrita sem política é descoberta antes de qualquer política,
em todos os 12 cenários obrigatórios. Não há finding técnico remanescente no
escopo. Descartei manter o MEDIUM aberto apenas porque o helper antigo conserva
sua exceção documental: a prova independente agora fecha a falha demonstrada.

**Recomendo manter a story em `review`, com aprovação técnica registrada e
CA2 publicado pendente**, até a decisão humana e a evidência publicada exigida.
Não recomendo `done`/aceite integral por inferência. Mantive story/sprint em
`review`, SPEC `in-review` e Épico 6 `in-progress`, sem alterar status.

Para deploy/Story 6.4 continuam pendentes: identidade do commit efetivamente
publicado e correspondência com o candidato; login HTTPS emitindo o cookie
`__Host-auction_session` com HttpOnly/Secure/SameSite=Lax/Path=/ e sem Domain;
aceitação/envio pelo navegador; logout removendo-o coerentemente; CORS/preflight
e borda/proxy publicados. Registrar somente atributos/resultados, nunca valores.
A matriz pública de `security-audit.md` §7 e os demais gates/smokes de 6.4 e do
fechamento do épico continuam exigidos. Não executei inspeção pública, deploy,
commit/push/merge, nem iniciei 6.2. Encerro este re-review e paro.

## Apêndice — harnesses e saídas deste re-review

Os caminhos temporários dependem deste workspace; preservo as fontes aqui para
que seu desaparecimento não apague o método. A cópia anterior é um snapshot
local conferido pelo manifesto, não uma prova de commit/publicação.

### probe.py

```python
import os
import sys
import fnmatch
import itertools
import tempfile
from pathlib import Path

ROOT = Path('/Users/joaodionizio/GitHub/casa-de-leiloes')
HERE = Path(__file__).parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'backend'))

def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        name = Path(os.fsdecode(args[0])).name
        patterns = ('.env*', '*.pem', '*.key', '*.p12', '*.pfx', 'id_rsa*',
                    'credentials.json', 'credentials.yaml', 'credentials.yml',
                    'service-account*.json', 'service_account*.json')
        if any(fnmatch.fnmatch(name, p) for p in patterns):
            raise AssertionError('Forbidden file access')
    if event == 'socket.connect':
        raise AssertionError('Network/database connections forbidden in review probe')

sys.addaudithook(audit)
os.environ.clear()
os.environ.update(
    APP_ORIGIN='https://casa.example',
    JWT_SECRET='review-fictitious-j-' + 'j' * 40,
    AUDIT_HMAC_SECRET='review-fictitious-a-' + 'a' * 40,
    PSEUDONYM_SECRET='review-fictitious-p-' + 'p' * 40,
    PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
)
from app import config
for cls in (config.Settings, config.SpaSettings, config.OriginSettings,
            config.AuthSettings, config.AuditSettings, config.IntegritySettings):
    cls.model_config['env_file'] = None

import pytest
from fastapi import Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.routing import Route
from starlette.responses import JSONResponse
from tests import test_csrf as target
from tests.access_policy import policy_by_route, policy_problems

EXPECTED = {
    ('POST', '/api/auth/login'), ('POST', '/api/auth/logout'),
    ('POST', '/api/lots'), ('POST', '/api/wallet/deposit'),
    ('POST', '/api/lots/{lot_id}/bids'), ('POST', '/api/lots/{lot_id}/cancel'),
}
SCENARIOS = [
    ('https://evil.example', 'application/json', 403, 'csrf_origin_mismatch'),
    (target.ALLOWED_ORIGIN, None, 415, 'unsupported_media_type'),
    (target.ALLOWED_ORIGIN, 'text/plain', 415, 'unsupported_media_type'),
]

def make_app(folder, monkeypatch, with_spa):
    # Execute the actual fixture body, retaining test-local patch restoration.
    return target.real_write_app.__wrapped__(folder, monkeypatch, with_spa)

def legacy_inventory(app):
    # The former observed-set expression, reconstructed from the original review.
    return {(verb, path) for path, verb, kind in policy_by_route(app.routes)
            if kind == 'http' and verb in target.WRITE_METHODS}

async def new_write(request: Request):
    return JSONResponse({'executed': True})

for with_spa in (False, True):
    with tempfile.TemporaryDirectory() as folder, pytest.MonkeyPatch.context() as mp:
        app = make_app(Path(folder), mp, with_spa)
        observed = target.http_write_inventory(app.routes)
        assert observed == EXPECTED
        assert app.debug is False
        print(f'CURRENT spa={with_spa}: {sorted(observed)}; PUT/PATCH/DELETE=0')

for path, route_type, with_spa in itertools.product(
        ['/api/docs', '/api/openapi.json', '/api/unexpected'],
        [Route, APIRoute], [False, True]):
    with tempfile.TemporaryDirectory() as folder, pytest.MonkeyPatch.context() as mp:
        app = make_app(Path(folder), mp, with_spa)
        injected = route_type(path, new_write, methods=['POST'])
        assert not hasattr(injected.endpoint, 'access_policy')
        app.routes.append(injected)
        raw = target.http_write_inventory(app.routes)
        assert raw == EXPECTED | {('POST', path)}
        assert ('POST', path) not in EXPECTED
        old = legacy_inventory(app)
        assert old == EXPECTED
        old_problems = policy_problems(app.routes)
        assert old_problems == ([] if path != '/api/unexpected'
                                else ['sem política: /api/unexpected'])
        # Prove a reachable HTTP write, not just inert metadata.
        response = TestClient(app, base_url=target.ALLOWED_ORIGIN).post(
            path, headers=target.JSON_HEADERS, content=b'{}')
        assert response.status_code == 200
        assert response.json() == {'executed': True}
        # Poison both policy helpers: discovery and rejection must not call them.
        def forbidden(*args, **kwargs):
            raise RuntimeError('Policy helper must not participate in raw inventory')
        with pytest.MonkeyPatch.context() as poisoned:
            poisoned.setattr(target, 'policy_by_route', forbidden)
            poisoned.setattr(target, 'policy_problems', forbidden)
            assert target.http_write_inventory(app.routes) == raw
            try:
                target.assert_real_write_inventory(app)
            except AssertionError as error:
                assert str(error) == 'inventário CA1 diverge das escritas W1–W6'
            else:
                raise AssertionError('CA1 accepted an unprotected seventh write')
            rejected = 0
            for (method, real_path), scenario in itertools.product(sorted(EXPECTED), SCENARIOS):
                try:
                    target.test_every_real_write_is_refused_before_route_dispatch(
                        app, mp, method, real_path, *scenario)
                except AssertionError as error:
                    assert str(error) == 'inventário CA1 diverge das escritas W1–W6'
                    rejected += 1
            assert rejected == 18
        print(f'MUTATION {route_type.__name__} spa={with_spa} POST {path}: '
              f'dispatch=200 raw=7 legacy=6 legacy_policy_problems={len(old_problems)}; '
              f'poisoned-policy discovery=7; CA1=REJECTED; matrix rejected={rejected}/18')

print('12/12 mutations: real write -> raw inventory -> outside W1-W6 -> CA1 rejected; '
      'matrix rejection=216/216; no policy helper called by discovery/validation')

# Execute the unchanged regression tests and the 36 original CA1 cases via pytest.
# No conftest/lifespan/database is needed for this inventory and dispatch-only focal.
exit_code = pytest.main([
    '--noconftest', '-p', 'no:cacheprovider',
    '--basetemp=' + str(HERE / 'pytest-temp'),
    str(ROOT / 'backend/tests/test_csrf.py'),
    '-k', 'write_inventory or every_real_write_is_refused_before_route_dispatch',
    '-q',
])
print(f'REREVIEW_PYTEST_EXIT_CODE={int(exit_code)}')
raise SystemExit(exit_code)
```

Saída real, exit 0:

```text
/Users/joaodionizio/GitHub/casa-de-leiloes/backend/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
CURRENT spa=False: [('POST', '/api/auth/login'), ('POST', '/api/auth/logout'), ('POST', '/api/lots'), ('POST', '/api/lots/{lot_id}/bids'), ('POST', '/api/lots/{lot_id}/cancel'), ('POST', '/api/wallet/deposit')]; PUT/PATCH/DELETE=0
CURRENT spa=True: [('POST', '/api/auth/login'), ('POST', '/api/auth/logout'), ('POST', '/api/lots'), ('POST', '/api/lots/{lot_id}/bids'), ('POST', '/api/lots/{lot_id}/cancel'), ('POST', '/api/wallet/deposit')]; PUT/PATCH/DELETE=0
MUTATION Route spa=False POST /api/docs: dispatch=200 raw=7 legacy=6 legacy_policy_problems=0; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION Route spa=True POST /api/docs: dispatch=200 raw=7 legacy=6 legacy_policy_problems=0; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION APIRoute spa=False POST /api/docs: dispatch=200 raw=7 legacy=6 legacy_policy_problems=0; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION APIRoute spa=True POST /api/docs: dispatch=200 raw=7 legacy=6 legacy_policy_problems=0; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION Route spa=False POST /api/openapi.json: dispatch=200 raw=7 legacy=6 legacy_policy_problems=0; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION Route spa=True POST /api/openapi.json: dispatch=200 raw=7 legacy=6 legacy_policy_problems=0; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION APIRoute spa=False POST /api/openapi.json: dispatch=200 raw=7 legacy=6 legacy_policy_problems=0; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION APIRoute spa=True POST /api/openapi.json: dispatch=200 raw=7 legacy=6 legacy_policy_problems=0; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION Route spa=False POST /api/unexpected: dispatch=200 raw=7 legacy=6 legacy_policy_problems=1; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION Route spa=True POST /api/unexpected: dispatch=200 raw=7 legacy=6 legacy_policy_problems=1; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION APIRoute spa=False POST /api/unexpected: dispatch=200 raw=7 legacy=6 legacy_policy_problems=1; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
MUTATION APIRoute spa=True POST /api/unexpected: dispatch=200 raw=7 legacy=6 legacy_policy_problems=1; poisoned-policy discovery=7; CA1=REJECTED; matrix rejected=18/18
12/12 mutations: real write -> raw inventory -> outside W1-W6 -> CA1 rejected; matrix rejection=216/216; no policy helper called by discovery/validation
.................................................................        [100%]
65 passed, 220 deselected in 0.58s
REREVIEW_PYTEST_EXIT_CODE=0
```

### legacy_probe.py

```python
from pathlib import Path
from types import ModuleType

# Reuse only the protected bootstrap, never execute the current probe again.
here = Path(__file__).parent
bootstrap = (here / 'probe.py').read_text().split('for with_spa in (False, True):')[0]
exec(compile(bootstrap, str(here / 'probe.py'), 'exec'), globals())
old_path = Path('/private/tmp/story-6-1-validation-lhq0d6le/backend/tests/test_csrf.py')
legacy = ModuleType('legacy_csrf')
legacy.__file__ = str(old_path)
exec(compile(old_path.read_text(), str(old_path), 'exec'), legacy.__dict__)
original_factory = legacy.create_app
for path, route_type in itertools.product(
        ['/api/docs', '/api/openapi.json', '/api/unexpected'], [Route, APIRoute]):
    def factory(*args, **kwargs):
        app = original_factory(*args, **kwargs)
        app.routes.append(route_type(path, new_write, methods=['POST']))
        return app
    passed = rejected = 0
    for with_spa, (method, real_path), scenario in itertools.product(
            [False, True], sorted(EXPECTED), SCENARIOS):
        with tempfile.TemporaryDirectory() as folder, pytest.MonkeyPatch.context() as mp:
            mp.setattr(legacy, 'create_app', factory)
            try:
                legacy.test_every_real_write_is_refused_before_route_dispatch(
                    Path(folder), mp, with_spa, method, real_path, *scenario)
            except AssertionError:
                rejected += 1
            else:
                passed += 1
    assert (passed, rejected) == ((0, 36) if path == '/api/unexpected' else (36, 0))
    print(f'LEGACY {route_type.__name__} POST {path}: raw=7; '
          f'original matrix passed={passed}, rejected={rejected} (with/without SPA)')
print('LEGACY_REPRODUCTION_EXIT_CODE=0; original documentary-path failure confirmed')
```

Saída real, exit 0:

```text
/Users/joaodionizio/GitHub/casa-de-leiloes/backend/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
LEGACY Route POST /api/docs: raw=7; original matrix passed=36, rejected=0 (with/without SPA)
LEGACY APIRoute POST /api/docs: raw=7; original matrix passed=36, rejected=0 (with/without SPA)
LEGACY Route POST /api/openapi.json: raw=7; original matrix passed=36, rejected=0 (with/without SPA)
LEGACY APIRoute POST /api/openapi.json: raw=7; original matrix passed=36, rejected=0 (with/without SPA)
LEGACY Route POST /api/unexpected: raw=7; original matrix passed=0, rejected=36 (with/without SPA)
LEGACY APIRoute POST /api/unexpected: raw=7; original matrix passed=0, rejected=36 (with/without SPA)
LEGACY_REPRODUCTION_EXIT_CODE=0; original documentary-path failure confirmed
```

---

# Histórico — review original e registro do implementador

**Os vereditos pendentes abaixo descrevem o estado anterior à correção e são
preservados como histórico. O veredito vigente é o re-review acima: R6.1-01
RESOLVIDO e aprovação técnica, com CA2 publicado ainda pendente.**

# Review independente — Story 6.1 — 28/10/2026

**Status do review: PENDENTE DE CORREÇÃO OU DECISÃO HUMANA.**
**Veredito: 0 BLOCKER / 0 HIGH / 1 MEDIUM / 0 LOW.** Não recomendo retirar
a 6.1 de `review` neste estado. Além do finding, CA2 publicado permanece
pendente para deploy/Story 6.4; este relatório não declara aceite integral.

## Sessão, candidato e limites

Executei `bmad-code-review` em nova sessão Codex, sem participação na
especificação ou implementação. O identificador comercial exato do modelo e
seu nível de raciocínio não foram expostos pelo runtime; não atribuo uma
variante sem confirmação. As cinco camadas usaram agentes com modelo herdado
da sessão: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance
Auditor e Project Auditor. Todos concluíram; três executaram em paralelo,
seguidos pelas camadas restantes conforme a disponibilidade de vagas.

Adotei a base **informada** `8a460d26bb280e5a35379254a82b73c3224813a1` e o
candidato como o estado vivo local descrito no pedido, na branch informada
`epico-6-entrega-robustez-documentacao-e-opcionais`. Não confirmei branch/HEAD
nem publicação. Não executei Git/gh. Não recebi comparação histórica manual,
nem localizei `.diff`/`.patch` no repositório pela busca de nomes permitidos.

Montei um snapshot de leitura de 13 arquivos declarados, como conteúdo
completo contra `/dev/null`: 6.324 linhas e 362.371 bytes. Isso **não é um
diff histórico**. A lista da implementação coincide com os sete testes e os
seis documentos indicados abaixo. Não encontrei discrepância entre as listas;
sem comparação de base não consigo garantir que sejam todos os arquivos
efetivamente modificados, nem comprovar a alegação histórica de que nenhum
código de produção mudou. Não trato essa limitação como finding inventado.

## Finding confirmado

### R6.1-01 — MEDIUM — Nova escrita pode desaparecer do inventário CA1

- **Local principal:** `backend/tests/test_csrf.py:572` (confronto em :577).
- **Causa auxiliar:** `backend/tests/access_policy.py:60` e :86.
- **Problema:** a descoberta de escritas usa `policy_by_route`, que só inclui
  rotas com política efetiva. O verificador complementar abre exceção por
  caminho para `/api/docs` e `/api/openapi.json`, sem restringir método ou
  identidade da rota documental do framework. Um POST novo, sem política,
  em qualquer desses caminhos passa por `policy_problems` e fica ausente do
  mapa. O confronto continua enxergando as seis escritas anteriores.
- **Por que importa:** CAP-1 e a evidência da implementação (:30) prometem que
  nova escrita sem cobertura reprova o inventário. Nesse caso há sete POSTs
  reais, mas nenhum dos três negativos é executado para o sétimo. A proteção
  global existente continua atuando; o finding é uma falha da garantia de
  cobertura e também da checagem de política, não uma exploração demonstrada
  nas seis rotas atuais.
- **Evidência executada:** em apps descartáveis criados pelo factory real,
  injetei separadamente `@app.post('/api/docs')` e
  `@app.post('/api/openapi.json')`. Para cada mutação, os 36 casos completos
  da matriz passaram, `policy_problems == []`, o mapa continuou exatamente
  `EXPECTED_POLICIES` e o novo handler respondeu 200 com headers válidos.
  Controle: um POST sem política em `/api/review-new-write` foi recusado
  pelo inventário nos 36 casos. Resultado literal na seção de comandos.
- **Recomendação mínima:** inventariar escritas diretamente das rotas e
  métodos, independentemente da política, ou fechar a exceção documental de
  modo que ela só aceite as rotas/métodos efetivos do framework. Acrescentar
  regressão para nova escrita nos dois caminhos documentais; preservar
  recusa de Mount/tipo desconhecido e método + caminho sem colisão.
- **Origem/triagem:** suspeita da coordenação, confirmada por Edge Case Hunter
  e Acceptance Auditor. Consolidei como um único finding. O helper é anterior
  no contexto documental, mas a prova adotada pela 6.1 depende dele; não
  atribuo a introdução histórica sem diff. Não adio a falha da nova garantia.
- **Decisão humana:** pendente. **Correção:** não aplicada.

## Resultado por foco

| Foco | Conclusão e limite |
| --- | --- |
| CA1 atual | Seis POST: login, logout, criação, depósito, lance e cancelamento; nenhum PUT/PATCH/DELETE atual identificado. A lista esperada é literal, enquanto a descoberta vem de rotas runtime: não há tautologia de comparar duas estruturas da mesma constante. Há a exceção incompleta de R6.1-01. |
| Três recusas por rota | Executei diretamente os 36 casos atuais: origem divergente → 403 `csrf_origin_mismatch`; Content-Type ausente/text/plain → 415 `unsupported_media_type`; com/sem SPA. Corpo em bytes e header efetivo conferido. Cada caso inclui controle positivo no mesmo método/caminho. |
| Autenticação/payload/404 | A sentinela substitui o despacho da rota antes das dependências. O positivo alcança essa sentinela; os negativos exigem o envelope específico do guard. Portanto, 401/403 de papel, 422 de payload e 404/405 não explicam o resultado. |
| Sem efeitos | A matriz prova ausência de despacho das seis rotas, Set-Cookie e CORS. Por estrutura do middleware atual, não executa dependências/handler, logo não alcança banco/AIC/sessão dessas rotas. Isso não equivale a 36 novas comparações transacionais de banco. As provas autenticadas existentes verificam banco/AIC/ausência de cookie nos cenários específicos preservados. Nenhuma escrita nova é executada pela reprodução do finding contra banco. |
| Inventário/escopo | Métodos seguros não entram como escrita; helper mantém chave caminho + método + tipo e recusa duplicata. Mount é percorrido; Mount sem rotas e tipo desconhecido são denunciados por `policy_problems`. Nova escrita comum é detectada no controle. A exceção documental impede a garantia universal. |
| CA2 local | Código de login/logout e testes existentes conferem `__Host-auction_session`, HttpOnly, Secure, Lax, Path=/ e ausência de Domain em HTTPS, inclusive ao apagar cookie. Não há middleware CORS na montagem lida. Testes locais verificam negativas/preflight sem headers permissivos. Não reexecutei autenticação em PostgreSQL nesta sessão. |
| CA2 publicado | SPEC, auditoria, evidência, story e uso de IA deixam cookie/borda/proxy/logout/CORS publicados pendentes. Não encontrei alegação documental de observação pública sem prova. Nenhuma inspeção publicada realizada neste review. |
| CA3 vitrine | Teste compara respostas saudáveis/falhas com relógio fixo, exige 200 antes dos bytes iguais e zero requests externas. Código de leitura usa snapshot local; `image_url_for` só compõe caminho. Browser exige placeholder, título, valor e navegação. |
| CA3 sala | Teste cria lance persistido, lê detalhe/REST, usa snapshot WS/read model reais, compara conteúdo exceto `as_of`, confere ping/pong, query e Session encerrada. Instala `ArticClient` real com MockTransport ConnectError: negócio faz zero requests; pedido posterior da imagem chega ao mesmo transporte uma vez e retorna 503. Não substitui `read_room` nesse cenário. |
| CA3 auditoria/comprovante | Testes PostgreSQL existentes usam cliente AIC sem capacidades, mantendo consulta e dados reais; não criam uma dependência externa artificial para provar ausência. Receipt é confrontado com campos persistidos. Browser de receipt a 320/1280 mantém título/artista/alias/valor/data/bid_count/hash/link, conta request da imagem, e navega à auditoria íntegra com histórico. Auditoria não mostra imagem. |
| CA4 | Três testes exigem envelope 500 literal e ausência de sentinelas fictícias. A app sintética é construída pelo factory real com os mesmos handlers/middleware; adicionalmente li falhas de commit/criação/lance em rotas reais com rollback e 500 genérico. Os testes de inventário exigem `debug is False` com/sem SPA e mapa exato sem rotas de crash. Não encontrei endpoint sintético de produção. |
| Regressões | Monkeypatch e listeners do cenário ampliado têm restauração/`finally`; scheduler é controlado pela fixture existente, e o engine WS aponta ao teste. Não identifiquei nova dependência da internet, ordem, banco de desenvolvimento ou alteração da baseline 4.2 nas fontes apresentadas. Sem baseline histórico, não certifico preservação byte a byte da 4.2 desde a base. |

O envelope 500 conferido no código/testes é exatamente:

```json
{"status":500,"code":"internal_error","message":"Erro interno. Tente novamente mais tarde."}
```

## Arquivos realmente inspecionados

Li integralmente os sete testes declarados:

- `backend/tests/test_csrf.py`
- `backend/tests/test_access_policy.py`
- `backend/tests/test_errors.py`
- `backend/tests/integration/test_lot_room_ws.py`
- `backend/tests/integration/test_public_lots.py`
- `frontend/e2e/vitrine.spec.ts`
- `frontend/e2e/receipt.spec.ts`

Li os três documentos da spec (`SPEC.md`, `security-audit.md`,
`implementation-evidence.md`), a story atual e o sprint completo; em
`docs/uso_de_ia.md`, examinei as seções de preparação/implementação 6.1.
Fontes vinculantes lidas: `CLAUDE.md`, `docs/ARQUITETURA.md`,
`docs/desafio-elite-dev.md`, Story 6.1 de `epics.md`,
`docs/FECHAMENTO-DE-EPICO.md`, `DESIGN.md`, `EXPERIENCE.md`,
`VITRINE-BLUEPRINT.md` e `docs/FRONTEND-WORKFLOW.md`.

Inspecionei adicionalmente integração e apoio, com leitura integral ou dos
trechos pertinentes (não são afirmações de mudança pela 6.1):

- Backend: `app/main.py`, `app/config.py`, `app/csrf.py`, `app/auth.py`,
  `app/errors.py`, `app/catalog.py`, leituras/registradores em `app/lots.py`,
  `app/bids.py`, `app/lot_room.py`, `app/lot_audit.py`, `app/lot_receipt.py`.
- Apoio: `tests/access_policy.py`, `tests/synthetic_api.py`,
  `tests/conftest.py`, `tests/auth_support.py`, `tests/catalog_support.py`,
  `tests/test_csrf_auth.py`, `tests/integration/test_auth_flow.py`.
- Testes transacionais pertinentes: trechos CSRF/500 de
  `test_lot_creation.py`, `test_wallet_routes.py`, `test_bid_routes.py`,
  `test_lot_cancellation.py`; independência/projeção em `test_lot_audit.py` e
  `test_lot_receipt.py`.
- Frontend: `src/ArtworkImage.tsx`, `src/ReceiptPage.tsx`,
  `e2e/support/mockApi.ts` no transporte de imagens e `playwright.config.ts`.
- Evidência temporária preexistente: scripts
  `/private/tmp/story-6-1-sync-validation.py` e
  `/private/tmp/story-6-1-run-validation.py`, manifesto SHA-256, cache de
  nodeids pytest e `.last-run.json` do Playwright da cópia isolada da 6.1.

## Números e evidências do implementador

Não apresento os números históricos como testes executados por mim.

| Alegação | O que pude corroborar independentemente |
| --- | --- |
| 477 / 197 / 234 pytest focais | Os três comandos estão registrados. O cache de nodeids da cópia contém exatamente essas quantidades ao agrupar pelos arquivos dos comandos. Isso confirma contagem coletada, não aprovação, duração ou exit code histórico. |
| 115 Playwright | Comando das cinco suítes está registrado; cache de último run informa `passed` e zero failedTests, sem total/duração. Não confirmei independentemente os 115 pela saída de execução. |
| Verify: 2.314 pytest / 192 Node / exit 0 | Evidência registra comando, contagens, duração e frase final literal do verify. Cache pytest contém 2.314 nodeids. Não localizei stdout persistido suficiente para revalidar aprovação de todos, os 192 Node ou o exit code do processo histórico. São resultados relatados, não uma nova certificação deste review. |
| Cache uv exit 2 | `implementation-evidence.md:44` descreve tentativa inicial **focal**, antes do pytest. Não a reclassifico como tentativa de verify sem outra evidência. Nesta sessão também houve duas falhas de cache, mas na resolução BMAD, não em testes/verify. |
| 250 fontes SHA-256 | Camada Verification Gap conferiu original e cópia contra o manifesto: 250 entradas verificadas, zero bloqueadas, ausentes ou divergentes. Isso comprova correspondência atual com aquela cópia, não correspondência histórica com o commit base. |

Não há contradição demonstrada nas contagens relatadas. Ausência de log bruto
persistido é uma limitação de corroboração; não inventei finding de execução
fictícia nem repeti o gate completo apenas para reproduzir os números.

## Comandos executados nesta revisão

1. Resolução de skill/config: as duas chamadas abaixo retornaram **exit 2**
   por impossibilidade de criar lock no cache uv, antes de executar o script:

   ```sh
   uv run _bmad/scripts/resolve_customization.py --skill .agents/skills/bmad-code-review --project-root . --key workflow
   uv run _bmad/scripts/resolve_config.py --project-root .
   ```

   Reexecutei com cache temporário permitido, **exit 0** em ambas:

   ```sh
   UV_CACHE_DIR=/private/tmp/casa-review-6-1-uv uv run _bmad/scripts/resolve_customization.py --skill .agents/skills/bmad-code-review --project-root . --key workflow
   UV_CACHE_DIR=/private/tmp/casa-review-6-1-uv uv run _bmad/scripts/resolve_config.py --project-root .
   UV_CACHE_DIR=/private/tmp/casa-review-6-1-uv uv run _bmad/scripts/resolve_customization.py --skill .agents/skills/bmad-code-review --project-root . --key workflow.on_complete
   ```

   O último retornou ação vazia. Não havia passos prepend/append na ativação.

2. Inspeção: `pwd`, `rg --files`, `rg -n`, `cat`, `sed -n`, `nl -ba`,
   `wc -l` nos arquivos enumerados; scripts `python3` para ler nomes permitidos,
   montar snapshot unificado sem Git e consultar metadados do manifesto.
   Nenhum arquivo de segredo foi aberto. Algumas buscas sem correspondência
   não produziram resultados; a busca de logs não encontrou evidência de stdout.

3. Prova focal do finding, **exit 0**:

   ```sh
   backend/.venv/bin/python -B /private/tmp/story-6-1-review-xj5ddb5o/probe_matrix.py
   ```

   Escrevi o harness apenas em `/private/tmp`. Antes de importar `app.main`,
   limpei o ambiente do processo, forneci valores fictícios e desabilitei
   `env_file` nos tipos Settings em memória. Um audit hook recusou abertura
   de `.env*`/credenciais. Chamei diretamente a função de teste com
   `pytest.MonkeyPatch` e diretório temporário por caso; não executei
   `pytest_sessionstart`, lifespan, scheduler, SQL, Docker ou rede externa.
   A injeção de rota e o patch no factory existiram só no processo descartável.

   Saída literal:

   ```text
   Current matrix: 36 cases passed, each with positive dispatch control; no lifespan/database/network
   Injected POST /api/docs: raw writes=7; matrix passed=36, rejected=0; dispatch=200/{'executed': True}
   Injected POST /api/openapi.json: raw writes=7; matrix passed=36, rejected=0; dispatch=200/{'executed': True}
   Injected POST /api/review-new-write: raw writes=7; matrix passed=0, rejected=36; dispatch=200/{'executed': True}
   Mutation confirms path-only framework exemption bypass; ordinary new path is detected
   ```

   Aviso existente: `StarletteDeprecationWarning` sobre httpx/TestClient.
   São chamadas diretas dos casos, **não uma nova execução de pytest**.

4. Camada Edge Case Hunter: executou um heredoc com
   `backend/.venv/bin/python -B`, audit hook e FastAPI descartável, sem
   instanciar configuração; confirmou que POST documental passa pelo helper
   e responde 200. Exit 0, mesmo aviso. É corroborado pela prova completa acima.

5. Camada Verification Gap: dois heredocs `python3`, ambos **exit 0**,
   para SHA-256 e caches. Comandos e saída exatos preservados em
   `code-review-story-6-1-verification-commands.md` nesta pasta.
   Não modificou a cópia validada nem a baseline histórica da 4.2.

6. Conferência documental final com heredoc `python3`, **exit 0**: preservei
   o registro de comandos e a fonte integral do harness no anexo, conferi
   story/sprint `review`, SPEC `in-review` e os sete testes contra os hashes
   do manifesto. Todos corresponderam. Escritas no repositório nesta sessão
   limitaram-se aos três artefatos documentais de review identificados abaixo.

Não executei pytest completo, Playwright, verify, smoke, Git/gh ou deploy nesta
sessão. Não li `.env*`, cookies/tokens reais, URLs internas ou valores de
segredos. As demais camadas fizeram revisão estática, sem testes.

## Triagem e encerramento

Blind Hunter, Verification Gap e Project Auditor não reportaram outros
findings. Acceptance Auditor inicialmente não apontou a lacuna e, na
reavaliação do caso concreto, confirmou R6.1-01. Não contei a mudança de
parecer como um segundo finding. Não houve proposta descartada como falso
positivo, nem item deferido. O fato de algumas camadas não encontrarem
problema não substitui a reprodução adversarial.

Descartei exigir outro E2E completo ou prova transacional redundante para
cada negativo, pois a composição existente é prevista na SPEC e o mecanismo
de ausência de despacho é verificável. Também descartei afirmar que toda
escrita futura será coberta: a reprodução refutou essa garantia.

Mantive story/sprint em `review`, SPEC em `in-review` e Épico 6 em
`in-progress`. Não corrigi código/testes/configuração e não iniciei 6.2.
Registrei somente este review, seu anexo de comandos e a referência de
Review Findings na story.

**A 6.1 não deve sair de `review` agora:** R6.1-01 exige correção e re-review
pertinente ou decisão humana explícita e fundamentada. CA2 publicado segue
pendente; eventual aprovação técnica local não satisfaz esse aceite público.
Mudança posterior do candidato invalida as evidências afetadas. Aguardo a
decisão do usuário; não inicio correções automaticamente.

## Registro posterior do implementador — correção R6.1-01 — 28/10/2026

**Corrigido pelo implementador; aguardando re-review independente.** Este
adendo preserva o finding, o veredito e os comandos históricos acima. Não
constitui revisão da própria correção nem aprovação pelo reviewer.

Após autorização explícita, usei exclusivamente `bmad-build` para substituir
a descoberta via `policy_by_route` por inventário bruto de `app.routes`, em
`backend/tests/test_csrf.py`. O observado considera todos os métodos HTTP de
escrita, independentemente de política e caminho. Depois confronto W1–W6 e
confiro políticas pelos helpers existentes, sem mudar sua exceção documental.

A regressão controlada injeta POST sem política nos dois caminhos do finding
e em `/api/unexpected`, com/sem SPA e `Route`/`APIRoute`. Nos 12 cenários,
descubro a sétima escrita e exijo falha da mesma validação CA1 usada na matriz.
Nos caminhos documentais o verificador de política continua sem denunciar a
mutação; a validação independente já a reprova. Incluí provas de política
incorreta, métodos múltiplos, tipos/mounts opacos e duplicatas, sem produto novo.

Executei primeiro `-k write_inventory`: **29 passed**, exit 0; depois as suítes
CSRF/políticas/autenticação e escritas CA1: **533 passed**, exit 0. A evidência
CA1 anterior foi invalidada e renovada; novo `./verify.sh` completo **exit 0**:
2343 pytest, 192 Node, Ruff/formato, ESLint, TypeScript, Vite e Docker aprovados.
Comandos, resultados e limites em
[implementation-evidence.md](../specs/spec-story-6-1-revisao-de-seguranca-e-de-erros/implementation-evidence.md#correção-do-implementador--r61-01--28102026).

Mantenho Story/sprint `review`, SPEC `in-review` e Épico 6 `in-progress`.
Playwright CA3 anterior permanece independente. CA2 publicado continua
pendente. Não executei code review, deploy ou outra story nesta correção.
