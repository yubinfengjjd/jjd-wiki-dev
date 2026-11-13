"""Runtime contract v2: external tools/resources/hardware are declared conditions.

Old R/Python manifests keep their schema and fingerprints; any substantive new
requirement changes the evidence fingerprint instead of being granted silently.
"""
import hashlib
import json
from pathlib import Path

import pytest

from rwiki.runtime_contract import (closure_hash, fingerprint_mode,
                                    implementation_runtime, read_manifest,
                                    runtime_facts)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_for(asset: Path) -> dict:
    return json.loads((asset / 'runtime.json').read_text(encoding='utf-8'))


def asset(tmp_path: Path, impl=None, kind='method', with_receipt=False):
    root = tmp_path / ('methods/demo' if kind == 'method' else 'templates/demo')
    code = root / 'code'
    code.mkdir(parents=True)
    (code / 'run.R').write_text('run <- function(x) x\n', encoding='utf-8')
    base = {
        'id': 'branch', 'entry': 'code/run.R', 'entry_function': 'run',
        'language': 'R', 'runtime_mode': 'standalone', 'files': ['code/run.R'],
        'resources': [], 'required_packages': {'R': ['Seurat']},
        'optional_packages': {}, 'source': {'package': 'demo', 'license': 'MIT'},
    }
    if impl:
        base.update(impl)
    manifest = {'schema_version': 1, 'kind': kind, 'id': 'demo'}
    if kind == 'method':
        manifest['implementations'] = [base]
    else:
        manifest.update(base)
        manifest['id'] = 'demo'
    if with_receipt:
        item = (manifest['implementations'][0] if kind == 'method' else manifest)
        item['evidence'] = {'portability': 'verification/portability.json'}
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    if with_receipt:
        # closure_hash binds the final manifest bytes, so write the pointer first.
        parsed = read_manifest(root, 'demo', kind)[0]['implementations'][0]
        close = closure_hash(root, parsed)
        receipt = {'schema_version': 1, 'kind': kind, 'implementation': parsed['id'],
                   'state': 'passed', 'scope': 'fixture', 'command': 'Rscript run.R',
                   'checks': ['ok'], 'environment': {'R': '4.5.0'},
                   'closure_hash': close, 'files': {'code/run.R': sha(code / 'run.R')}}
        (root / 'verification').mkdir()
        (root / 'verification/portability.json').write_text(json.dumps(receipt), encoding='utf-8')
    return root


def test_old_manifest_keeps_v1_fingerprint(tmp_path):
    root = asset(tmp_path)
    item = read_manifest(root, 'demo', 'method')[0]['implementations'][0]
    # v1 scheme: sha256(raw manifest bytes + file names + file bytes)
    digest = hashlib.sha256()
    digest.update((root / 'runtime.json').read_bytes())
    digest.update(b'code/run.R')
    digest.update(b'\0')
    digest.update((root / 'code/run.R').read_bytes())
    assert closure_hash(root, item) == digest.hexdigest()
    assert fingerprint_mode(root, item) == 'v1'


def test_empty_v2_fields_do_not_change_fingerprint(tmp_path):
    root = asset(tmp_path)
    manifest = manifest_for(root)
    manifest['implementations'][0].update(
        entry_kind='function', tools=[], external_resources=[], hardware={}, invocation={})
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    item = read_manifest(root, 'demo', 'method')[0]['implementations'][0]
    assert fingerprint_mode(root, item) == 'v1'
    digest = hashlib.sha256()
    digest.update((root / 'runtime.json').read_bytes())
    digest.update(b'code/run.R')
    digest.update(b'\0')
    digest.update((root / 'code/run.R').read_bytes())
    assert closure_hash(root, item) == digest.hexdigest()


def test_substantive_v2_field_changes_fingerprint_and_stales_receipt(tmp_path):
    root = asset(tmp_path, with_receipt=True)
    before = runtime_facts(root, 'demo', 'method')['implementations']['branch']
    assert before['portability']['state'] == 'verified'
    manifest = manifest_for(root)
    manifest['implementations'][0]['tools'] = [
        {'name': 'vina', 'version_constraint': '>=1.2', 'platform': 'linux/win'}]
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    item = read_manifest(root, 'demo', 'method')[0]['implementations'][0]
    assert fingerprint_mode(root, item) == 'v2'
    after = runtime_facts(root, 'demo', 'method')['implementations']['branch']
    assert after['portability']['state'] in ('stale', 'invalid')


def test_script_entry_needs_no_function(tmp_path):
    root = asset(tmp_path, impl={
        'entry_kind': 'script', 'entry': 'code/run.R',
        'language': 'R', 'runtime_mode': 'standalone', 'files': ['code/run.R']})
    root2 = asset(tmp_path / 's2', impl={
        'entry_kind': 'script', 'entry_function': None})
    # script entry: entry_function forbidden if present-but-null acceptable? we forbid the key entirely
    manifest = manifest_for(root2)
    manifest['implementations'][0].pop('entry_function', None)
    (root2 / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root2, 'demo', 'method')
    assert data is not None and not issues
    assert data['implementations'][0]['entry_kind'] == 'script'


def test_script_entry_rejects_entry_function(tmp_path):
    root = asset(tmp_path, impl={'entry_kind': 'script', 'entry_function': 'run'})
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None
    assert any('entry_function' in issue for issue in issues)


def test_external_program_entry_is_a_tool_not_a_file(tmp_path):
    root = asset(tmp_path, impl={
        'entry_kind': 'external_program', 'entry': 'vina', 'entry_function': None,
        'files': [], 'tools': [{'name': 'vina', 'version_constraint': '==1.2.5'}]})
    manifest = manifest_for(root)
    manifest['implementations'][0].pop('entry_function', None)
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is not None and not issues, issues
    impl = data['implementations'][0]
    assert impl['entry_kind'] == 'external_program'
    assert impl['entry'] == 'vina'


def test_external_program_requires_matching_tool(tmp_path):
    root = asset(tmp_path, impl={
        'entry_kind': 'external_program', 'entry': 'vina', 'files': [],
        'tools': [{'name': 'other'}]})
    manifest = manifest_for(root)
    manifest['implementations'][0].pop('entry_function', None)
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None
    assert any('tool' in issue.lower() or '工具' in issue for issue in issues)


def test_tool_names_reject_paths_and_colons(tmp_path):
    for index, name in enumerate(('../x', 'a/b', 'a\\b', 'a:b', '')):
        root = asset(tmp_path / f'c{index}',
                     impl={'entry_kind': 'external_program', 'entry': 'vina', 'files': [],
                           'tools': [{'name': 'vina'}, {'name': name}]})
        manifest = manifest_for(root)
        manifest['implementations'][0].pop('entry_function', None)
        (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
        data, issues = read_manifest(root, 'demo', 'method')
        assert data is None, name
        assert issues


def test_external_resources_and_hardware_validated(tmp_path):
    root = asset(tmp_path, impl={
        'external_resources': [{'role': 'docking box', 'name': 'grid.txt',
                                'source': 'prepared locally', 'sha256': '0' * 64}],
        'hardware': {'accelerator': 'gpu', 'min_memory_gb': 8}})
    manifest = manifest_for(root)
    manifest['implementations'][0]['external_resources'][0]['sha256'] = 'not-hex'
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None and any('sha256' in issue for issue in issues)
    manifest['implementations'][0]['external_resources'][0]['sha256'] = '0' * 64
    manifest['implementations'][0]['hardware'] = {'accelerator': 'quantum'}
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None and any('accelerator' in issue for issue in issues)


def test_external_resource_requires_role(tmp_path):
    root = asset(tmp_path, impl={'external_resources': [{'name': 'weights.pt'}]})
    manifest = manifest_for(root)
    (root / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is None
    assert any('role' in issue for issue in issues)


def test_facts_expose_conditions_without_granting(tmp_path):
    root = asset(tmp_path, impl={
        'tools': [{'name': 'vina'}],
        'external_resources': [{'role': 'weights', 'name': 'w.pt'}],
        'hardware': {'accelerator': 'gpu'}})
    facts = runtime_facts(root, 'demo', 'method')['implementations']['branch']
    assert facts['tools'] == [{'name': 'vina'}]
    assert facts['external_resources'] == [{'role': 'weights', 'name': 'w.pt'}]
    assert facts['hardware'] == {'accelerator': 'gpu'}
    assert facts['fingerprint_mode'] == 'v2'
    # Declared conditions never grant verification.
    assert facts['portability']['state'] == 'declared'


def test_python_function_entry_allowed(tmp_path):
    root = tmp_path / 'methods/demo'
    code = root / 'code'
    code.mkdir(parents=True)
    (code / 'run.py').write_text('def run(x):\n    return x\n', encoding='utf-8')
    (root / 'runtime.json').write_text(json.dumps({
        'schema_version': 1, 'kind': 'method', 'id': 'demo',
        'implementations': [{'id': 'b', 'entry': 'code/run.py', 'entry_function': 'run',
                             'language': 'Python', 'runtime_mode': 'standalone',
                             'files': ['code/run.py'], 'resources': []}]}), encoding='utf-8')
    data, issues = read_manifest(root, 'demo', 'method')
    assert data is not None and not issues, issues


def test_implementation_runtime_fallback_has_v2_keys(tmp_path):
    facts = implementation_runtime(tmp_path / 'nowhere', 'demo', 'branch')
    for key in ('entry_kind', 'tools', 'external_resources', 'hardware', 'invocation'):
        assert key in facts


def test_page_entrypoint_external_form(workspace):
    """external:<name> page entrypoint matches an external_program manifest branch."""
    from rwiki.method_implementations import (implementation_metadata_errors,
                                              implementation_status)
    config, _ = workspace
    from rwiki.methods import scaffold_method
    from rwiki.pages import read_page as rp, write_page as wp
    scaffold_method(config, 'dock', 'dock', 'MIT', written=True)
    page = config.wiki_root / 'methods/dock.md'
    meta, body = rp(page)
    meta.update(method_kind='analysis', summary='x', cite=['src'],
                data_contract={'input': 'i', 'output': 'o'},
                implementations=[{'id': 'v', 'title': 'vina', 'language': 'shell',
                                  'entrypoint': 'external:vina', 'dependencies': []}])
    wp(page, meta, body)
    assert implementation_metadata_errors(meta) == []
    asset = page.with_suffix('')
    asset.mkdir(exist_ok=True)
    (asset / 'runtime.json').write_text(json.dumps({
        'schema_version': 1, 'kind': 'method', 'id': 'dock',
        'implementations': [{'id': 'v', 'entry_kind': 'external_program', 'entry': 'vina',
                             'language': 'shell', 'runtime_mode': 'standalone',
                             'files': [], 'tools': [{'name': 'vina'}],
                             'resources': []}]}), encoding='utf-8')
    status = implementation_status(page)[0]
    assert status['runtime']['portability']['state'] == 'declared'
    assert not any('entrypoint' in issue for issue in status['runtime']['portability']['issues'])


def test_invocation_args_allow_repeated_flags(tmp_path):
    """argv is positional: '--input a --input b' is legitimate, not a duplicate."""
    root = asset(tmp_path, impl={'entry_kind': 'external_program', 'entry': 'example-tool',
                                 'entry_function': None,
                                 'language': 'CLI', 'files': [], 'required_packages': {},
                                 'tools': [{'name': 'example-tool'}],
                                 'invocation': {'command': 'example-tool',
                                                'args': ['--input', 'a', '--input', 'b']}})
    manifest, issues = read_manifest(root, 'demo', 'method')
    assert manifest is not None, issues
    item = manifest['implementations'][0]
    assert item['invocation']['args'] == ['--input', 'a', '--input', 'b']


def test_hardware_rejects_nan_and_infinite(tmp_path):
    for bad in (float('nan'), float('inf'), -1, 'lots'):
        root = asset(tmp_path / str(bad).replace('.', '_'), impl={'hardware': {'min_memory_gb': bad}})
        manifest, issues = read_manifest(root, 'demo', 'method')
        assert manifest is None, (bad, issues)


def test_hardware_condition_marks_per_option_requirements(tmp_path):
    root = asset(tmp_path, impl={'hardware': {'accelerator': 'gpu', 'min_vram_gb': 8,
                                              'condition': '仅 batch 推理分支需要'}})
    manifest, issues = read_manifest(root, 'demo', 'method')
    assert manifest is not None, issues
    hw = manifest['implementations'][0]['hardware']
    assert hw['condition'] == '仅 batch 推理分支需要'
