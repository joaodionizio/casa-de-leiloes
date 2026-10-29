# Verification commands actually executed — Story 6.1 review

Read-only inspection by the verification-gap reviewer. These commands were
executed once during review; this record was written afterward without rerunning
them. Both `exec_command` calls completed with `exit_code: 0`. No Git/gh,
test execution, dotenv access, credential files, or baseline mutation was used.

## 250 SHA-256 comparisons

Exact shell command:

```sh
python3 - <<'PY'
from pathlib import Path
import json,hashlib,fnmatch
source=Path('/Users/joaodionizio/GitHub/casa-de-leiloes')
target=Path('/private/tmp/story-6-1-validation-lhq0d6le')
manifest=json.loads(Path('/private/tmp/story-6-1-validation-manifest.json').read_text())
blocked_dirs={'.git','.agents','.codex','.aws','node_modules','.venv'}
blocked_patterns=('.env*','*.pem','*.key','*.p12','*.pfx','id_rsa*','credentials*','service-account*','service_account*','*cookie*','*token*')
blocked=[]
missing=[]
mismatches=[]
checked=0
for relative,expected in manifest.items():
 rel=Path(relative)
 if rel.is_absolute() or '..' in rel.parts or any(p in blocked_dirs for p in rel.parts) or any(fnmatch.fnmatch(rel.name,p) for p in blocked_patterns) or rel.parts[0] not in {'verify.sh','compose.yaml','Dockerfile','.dockerignore','backend','frontend','docker'}:
  blocked.append(relative)
  continue
 paths=[source/rel,target/rel]
 if any(p.is_symlink() or not p.is_file() for p in paths):
  missing.append(relative)
  continue
 digests=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
 if digests != [expected,expected]:
  mismatches.append(relative)
 checked+=1
print(json.dumps({'manifest_count':len(manifest),'checked_source_and_copy':checked,'blocked_count':len(blocked),'missing':missing,'mismatches':mismatches},indent=2))
PY
```

Actual output (`exec_command` chunk `40ceef`, exit 0):

```text
{
  "manifest_count": 250,
  "checked_source_and_copy": 250,
  "blocked_count": 0,
  "missing": [],
  "mismatches": []
}
```

## Cached pytest counts and Playwright result

Exact shell command:

```sh
python3 - <<'PY'
import json
from pathlib import Path
root=Path('/private/tmp/story-6-1-validation-lhq0d6le')
ids=json.loads((root/'backend/.pytest_cache/v/cache/nodeids').read_text())
print('pytest cached nodeids:',len(ids))
groups=[['tests/test_csrf.py','tests/test_csrf_auth.py','tests/test_access_policy.py','tests/test_errors.py','tests/test_config.py','tests/test_security.py','tests/integration/test_auth_flow.py','tests/integration/test_roles.py'],['tests/integration/test_lot_creation.py','tests/integration/test_wallet_routes.py','tests/integration/test_bid_routes.py','tests/integration/test_lot_cancellation.py'],['tests/integration/test_public_lots.py','tests/integration/test_bid_reads.py','tests/integration/test_lot_room_ws.py','tests/integration/test_lot_audit.py','tests/integration/test_lot_receipt.py','tests/test_artic.py','tests/test_catalog_image_route.py']]
for i,group in enumerate(groups,1):
 print('focal',i,'cached nodeids:',sum(s.split('::')[0] in group for s in ids))
last=json.loads((root/'frontend/test-results/.last-run.json').read_text())
print('playwright last-run status:',last.get('status'))
print('playwright last-run failedTests count:',len(last.get('failedTests',[])))
print('playwright last-run keys:',list(last))
PY
```

Actual output (`exec_command` chunk `3b6a6b`, exit 0):

```text
pytest cached nodeids: 2314
focal 1 cached nodeids: 477
focal 2 cached nodeids: 197
focal 3 cached nodeids: 234
playwright last-run status: passed
playwright last-run failedTests count: 0
playwright last-run keys: ['status', 'failedTests']
```

The pytest cache corroborates collection counts, not individual passing outcomes,
durations, or the historical exit code. The Playwright cache corroborates a passed
last run with zero failed test IDs; it does not contain its test count or duration.
The exit 0 above is the inspection command's exit code, not a rerun of the
documented verification commands.

## Harness focal realmente executado pela coordenação

Comando e saída no relatório principal; fonte integral preservada para reprodução.

```python
import os, sys, tempfile, itertools
from pathlib import Path
from contextlib import ExitStack
ROOT = Path('/Users/joaodionizio/GitHub/casa-de-leiloes')
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'backend'))
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        name = Path(os.fsdecode(args[0])).name
        if name.startswith('.env') or name.endswith(('.pem', '.key', '.p12', '.pfx')) or name in ('credentials.json', 'credentials.yaml', 'credentials.yml'):
            raise AssertionError('Forbidden configuration file access')
sys.addaudithook(audit)
os.environ.clear()
os.environ.update(APP_ORIGIN='https://casa.example', JWT_SECRET='review-jwt-fictitious-' + 'j'*40, AUDIT_HMAC_SECRET='review-audit-fictitious-' + 'a'*40, PSEUDONYM_SECRET='review-pseudonym-fictitious-' + 'p'*40)
from app import config
for cls in (config.Settings, config.SpaSettings, config.OriginSettings, config.AuthSettings, config.AuditSettings, config.IntegritySettings):
    cls.model_config['env_file'] = None
import pytest
from app import main
from fastapi.testclient import TestClient
from tests import test_csrf as target
from tests import test_access_policy as access_tests
from tests.access_policy import policy_by_route, policy_problems
scenarios = [('https://evil.example','application/json',403,'csrf_origin_mismatch'),(target.ALLOWED_ORIGIN,None,415,'unsupported_media_type'),(target.ALLOWED_ORIGIN,'text/plain',415,'unsupported_media_type')]
count = 0
for with_spa, (method,path), scenario in itertools.product([False,True], target.REAL_WRITES, scenarios):
    with tempfile.TemporaryDirectory() as folder, pytest.MonkeyPatch.context() as mp:
        target.test_every_real_write_is_refused_before_route_dispatch(Path(folder),mp,with_spa,method,path,*scenario)
        count += 1
print(f'Current matrix: {count} cases passed, each with positive dispatch control; no lifespan/database/network')
original = target.create_app
for injected_path in ['/api/docs','/api/openapi.json','/api/review-new-write']:
    def factory(*args, **kwargs):
        app = original(*args, **kwargs)
        @app.post(injected_path)
        def new_write():
            return {'executed': True}
        return app
    passed, rejected = 0,0
    for with_spa, (method,path), scenario in itertools.product([False,True], target.REAL_WRITES, scenarios):
        with tempfile.TemporaryDirectory() as folder, pytest.MonkeyPatch.context() as mp:
            mp.setattr(target,'create_app',factory)
            try:
                target.test_every_real_write_is_refused_before_route_dispatch(Path(folder),mp,with_spa,method,path,*scenario)
                passed += 1
            except AssertionError:
                rejected += 1
    app = factory(app_origin=target.ALLOWED_ORIGIN)
    real_writes = [(r.path,verb) for r in app.routes for verb in (getattr(r,'methods',None) or []) if verb in target.WRITE_METHODS]
    response = TestClient(app,base_url=target.ALLOWED_ORIGIN).post(injected_path,headers=target.JSON_HEADERS,content=b'{}')
    print(f'Injected POST {injected_path}: raw writes={len(real_writes)}; matrix passed={passed}, rejected={rejected}; dispatch={response.status_code}/{response.json()}')
    if injected_path != '/api/review-new-write':
        assert passed == 36 and rejected == 0
        assert policy_problems(app.routes) == []
        assert policy_by_route(app.routes) == access_tests.EXPECTED_POLICIES
    else:
        assert passed == 0 and rejected == 36
print('Mutation confirms path-only framework exemption bypass; ordinary new path is detected')
```
