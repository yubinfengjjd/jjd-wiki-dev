"""Runtime declaration and independent-portability evidence are separate facts."""
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rwiki.runtime_contract import (closure_hash, implementation_runtime,
                                    lint_manifest, read_manifest, runtime_facts)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset(tmp_path: Path, kind='method', mode='standalone', evidence=True):
    root = tmp_path / ('methods/demo' if kind == 'method' else 'templates/demo')
    code = root / 'code'
    code.mkdir(parents=True)
    (code / 'run.R').write_text('run <- function(x) x\n', encoding='utf-8')
    manifest = {
        'schema_version': 1, 'kind': kind, 'id': 'demo',
        'entry': 'code/run.R', 'language': 'R', 'runtime_mode': mode,
        'files': ['code/run.R'], 'resources': [],
        'required_packages': {'R': ['Seurat']},
        'optional_packages': {'R': {'scDblFinder': 'doublet branch'}},
        'evidence': {'portability': 'verification/portability.json'},
        'source': {'package': 'demo', 'version': '1.0', 'license': 'MIT',
                   'functions': ['R/run.R:run']},
    }
    if kind == 'method':
        manifest.update(entry_function='run', implementations=[manifest.copy()])
        for key in ('entry', 'language', 'runtime_mode', 'files', 'resources',
                    'required_packages', 'optional_packages', 'evidence', 'source',
                    'entry_function'):
            manifest.pop(key, None)
        manifest['implementations'][0]['id'] = 'branch'
        manifest['implementations'][0]['entry_function'] = 'run'
        if not evidence:
            manifest['implementations'][0].pop('evidence', None)
        (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
        iid = 'branch'
    else:
        (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
        iid = 'demo'
    if evidence:
        implementation = (manifest['implementations'][0] if kind == 'method'
                          else manifest)
        close = closure_hash(root, implementation)
        receipt = {
            'schema_version': 1, 'kind': kind, 'implementation': iid,
            'state': 'passed', 'scope': 'isolated copy, new process',
            'command': 'Rscript run.R', 'checks': ['returns input'],
            'environment': {'R': '4.5.0'}, 'closure_hash': close,
            'files': {'code/run.R': sha(code / 'run.R')},
        }
        target = root / 'verification' / 'portability.json'
        target.parent.mkdir()
        target.write_text(json.dumps(receipt), encoding='utf-8')
    return root


def test_missing_manifest_is_unknown(tmp_path):
    root = tmp_path / 'methods/demo'
    root.mkdir(parents=True)
    facts = runtime_facts(root, 'demo', 'method')
    assert facts['mode'] == 'unknown'
    assert facts['portability']['state'] == 'unknown'
    assert read_manifest(root, 'demo', 'method') == (None, [])


def test_standalone_without_evidence_is_only_declared(tmp_path):
    root = asset(tmp_path, evidence=False)
    facts = runtime_facts(root, 'demo', 'method')
    branch = facts['implementations']['branch']
    assert branch['mode'] == 'standalone'
    assert branch['portability']['state'] == 'declared'
    assert branch['required_packages'] == {'R': ['Seurat']}
    assert branch['optional_packages'] == {'R': {'scDblFinder': 'doublet branch'}}


def test_passed_evidence_verifies_portability_only(tmp_path):
    root = asset(tmp_path)
    facts = runtime_facts(root, 'demo', 'method')
    branch = facts['implementations']['branch']
    assert branch['portability']['state'] == 'verified'
    assert branch['portability']['closure_hash'] == closure_hash(
        root, read_manifest(root, 'demo', 'method')[0]['implementations'][0])


def test_bundle_and_not_run_modes_are_not_independent(tmp_path):
    root = asset(tmp_path, mode='bundle')
    facts = runtime_facts(root, 'demo', 'method')
    assert facts['implementations']['branch']['portability']['state'] == 'bundle'

    root2 = asset(tmp_path / 'second')
    receipt = root2 / 'verification/portability.json'
    data = json.loads(receipt.read_text(encoding='utf-8'))
    data['state'] = 'not_run'
    data['scope'] = 'missing SingleR'
    receipt.write_text(json.dumps(data), encoding='utf-8')
    facts2 = runtime_facts(root2, 'demo', 'method')
    assert facts2['implementations']['branch']['portability']['state'] == 'not_run'


def test_code_change_makes_portability_stale(tmp_path):
    root = asset(tmp_path)
    (root / 'code/run.R').write_text('run <- function(x) x * 2\n', encoding='utf-8')
    assert runtime_facts(root, 'demo', 'method')['implementations']['branch']['portability']['state'] in (
        'stale', 'invalid')


@pytest.mark.parametrize('change', [
    {'files': ['../outside.R']},
    {'files': ['code/.hidden.R']},
    {'files': ['code/missing.R']},
    {'files': ['code/run.R', 'code/run.R']},
    {'runtime_mode': 'portable'},
    {'entry': 'source/run.R'},
    {'required_packages': {'R': ['Seurat', 'Seurat']}},
    {'optional_packages': {'R': {'scDblFinder': ''}}},
])
def test_invalid_declarations_never_become_unknown_facts(tmp_path, change):
    root = asset(tmp_path)
    manifest = json.loads((root / 'runtime.json').read_text(encoding='utf-8'))
    manifest['implementations'][0].update(change)
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None and issues
    facts = runtime_facts(root, 'demo', 'method')
    assert facts['mode'] == 'unknown'
    assert facts['portability']['state'] == 'unknown'


def test_resource_must_be_in_files_and_hash_must_match(tmp_path):
    root = asset(tmp_path)
    manifest = json.loads((root / 'runtime.json').read_text(encoding='utf-8'))
    manifest['implementations'][0]['resources'] = [
        {'path': 'code/data.txt', 'sha256': '0' * 64, 'role': 'fixture'}]
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None
    assert any('resource' in issue for issue in issues)
    (root / 'code/data.txt').write_text('payload', encoding='utf-8')
    manifest['implementations'][0]['files'].append('code/data.txt')
    manifest['implementations'][0]['resources'][0]['sha256'] = sha(root / 'code/data.txt')
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is not None and not issues
    (root / 'code/data.txt').write_text('changed', encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None and any('resource.sha256' in issue for issue in issues)


def test_python_required_packages_are_in_the_unified_fact(tmp_path):
    root = asset(tmp_path)
    manifest = json.loads((root / 'runtime.json').read_text(encoding='utf-8'))
    manifest['implementations'][0]['required_packages'] = {
        'R': ['Seurat'], 'Python': ['scanpy', 'numpy', 'scvelo']}
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    facts = runtime_facts(root, 'demo', 'method')['implementations']['branch']
    assert facts['required_packages']['Python'] == ['scanpy', 'numpy', 'scvelo']
    assert 'R' in facts['required_packages']


def test_malformed_resources_do_not_raise(tmp_path):
    root = asset(tmp_path)
    manifest = json.loads((root / 'runtime.json').read_text(encoding='utf-8'))
    manifest['implementations'][0]['resources'] = 7
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None and issues
    facts = runtime_facts(root, 'demo', 'method')
    assert facts['mode'] == 'unknown'
    assert facts['portability']['issues']


def test_entry_function_must_exist_in_entry_file(tmp_path):
    root = asset(tmp_path)
    manifest = json.loads((root / 'runtime.json').read_text(encoding='utf-8'))
    manifest['implementations'][0]['entry_function'] = 'missing_function'
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None
    assert any('entry_function' in issue for issue in issues)


def test_page_entrypoint_mismatch_invalidates_portability(tmp_path):
    from rwiki.method_implementations import implementation_status
    root = asset(tmp_path)
    page = tmp_path / 'methods/demo.md'
    page.write_text('''---\ntype: method\nid: demo\ntitle: Demo\nstatus: ready\nmethod_kind: analysis\nsummary: Demo.\ndata_contract: {input: x, output: y}\nimplementations:\n- id: branch\n  title: Branch\n  language: R\n  entrypoint: code/other.R:other\n  dependencies: [Seurat]\n  verification: verification/portability.json\n---\n\n# Demo\n''', encoding='utf-8')
    (root / 'code/other.R').write_text('other <- function(x) x\n', encoding='utf-8')
    status = implementation_status(page)[0]
    assert status['runtime']['portability']['state'] == 'invalid'
    assert any('entrypoint' in issue for issue in status['runtime']['portability']['issues'])


def test_duplicate_implementation_ids_are_rejected(tmp_path):
    root = asset(tmp_path)
    manifest = json.loads((root / 'runtime.json').read_text(encoding='utf-8'))
    manifest['implementations'].append(json.loads(json.dumps(manifest['implementations'][0])))
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None
    assert any('重复' in issue for issue in issues)


def test_runtime_never_grants_algorithm_verification(tmp_path):
    from rwiki.method_implementations import implementation_status
    root = asset(tmp_path)
    page = tmp_path / 'methods/demo.md'
    page.write_text('''---\ntype: method\nid: demo\ntitle: Demo\nstatus: ready\nmethod_kind: analysis\nsummary: Demo.\ndata_contract: {input: x, output: y}\nimplementations:\n- id: branch\n  title: Branch\n  language: R\n  entrypoint: code/run.R:run\n  dependencies: [Seurat]\n---\n\n# Demo\n''', encoding='utf-8')
    status = implementation_status(page)[0]
    assert status['state'] == 'not_run'
    assert status['runtime']['portability']['state'] == 'verified'


def test_malformed_manifest_does_not_break_api(workspace):
    from rwiki.methods import scaffold_method
    from rwiki.server import create_app
    config, _ = workspace
    scaffold_method(config, 'broken', 'Broken runtime', 'MIT', written=True)
    page = config.wiki_root / 'methods/broken.md'
    from rwiki.pages import read_page, write_page
    meta, body = read_page(page)
    meta['implementations'] = [{'id': 'branch', 'title': 'Branch', 'language': 'R',
                                'entrypoint': 'code/run.R:run', 'dependencies': []}]
    write_page(page, meta, body)
    asset = page.with_suffix('')
    (asset / 'code').mkdir(parents=True, exist_ok=True)
    (asset / 'code/run.R').write_text('run <- function(x) x\n', encoding='utf-8')
    (asset / 'runtime.json').write_text(json.dumps({
        'schema_version': 1, 'kind': 'method', 'id': 'broken',
        'implementations': [{
            'id': 'branch', 'entry': 'code/run.R', 'entry_function': 'run',
            'language': 'R', 'runtime_mode': 'standalone', 'files': ['code/run.R'],
            'resources': 7, 'required_packages': {'R': []}, 'optional_packages': {},
            'evidence': {'portability': 'verification/portability.json'},
        }],
    }), encoding='utf-8')
    with TestClient(create_app(config)) as client:
        detail = client.get('/api/page', params={'path': 'methods/broken.md'})
        listing = client.get('/api/pages')
    assert detail.status_code == 200
    assert listing.status_code == 200
    runtime = detail.json()['implementation_status'][0]['runtime']
    assert runtime['mode'] == 'unknown'
    assert runtime['portability']['issues']


def test_lint_reports_declared_but_unverified(tmp_path):
    root = asset(tmp_path, evidence=False)
    findings = lint_manifest(root, 'demo', 'method')
    assert any('独立声明尚无独立性证据' in item for item in findings)


def test_template_api_exposes_same_runtime_fact(layout_workspace):
    config = layout_workspace[0]
    from conftest import ENTRY_ID
    template_id = f'{ENTRY_ID}--bar'
    asset_dir = config.wiki_root / 'templates' / template_id
    (asset_dir / 'code').mkdir(parents=True, exist_ok=True)
    (asset_dir / 'code/run.R').write_text('run <- function(x) x\n', encoding='utf-8')
    manifest = {
        'schema_version': 1, 'kind': 'template', 'id': template_id,
        'entry': 'code/run.R', 'language': 'R', 'runtime_mode': 'standalone',
        'files': ['code/run.R'], 'resources': [],
        'required_packages': {'R': ['ggplot2']}, 'optional_packages': {},
        'evidence': {'portability': 'verification/portability.json'},
    }
    (asset_dir / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    close = closure_hash(asset_dir, manifest)
    (asset_dir / 'verification').mkdir()
    (asset_dir / 'verification/portability.json').write_text(json.dumps({
        'schema_version': 1, 'kind': 'template', 'implementation': template_id,
        'state': 'passed', 'scope': 'isolated copy', 'command': 'Rscript run.R',
        'checks': ['ok'], 'environment': {'R': '4.5.0'}, 'closure_hash': close,
        'files': {'code/run.R': sha(asset_dir / 'code/run.R')},
    }), encoding='utf-8')
    with TestClient(create_app(config)) as client:
        detail = client.get('/api/page', params={'path': f'templates/{template_id}.md'}).json()
    assert detail['runtime']['mode'] == 'standalone'
    assert detail['runtime']['portability']['state'] == 'verified'
    assert detail['runtime']['required_packages'] == {'R': ['ggplot2']}


from rwiki.server import create_app  # noqa: E402  (after helpers, avoids cycles in fixtures)
