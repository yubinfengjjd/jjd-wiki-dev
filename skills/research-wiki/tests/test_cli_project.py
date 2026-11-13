"""CLI wiring for the project-state commands and discover-methods.

Every mutation prints the revision + event; read views print JSON. Project
commands must work without a Wiki config.
"""
import json
from pathlib import Path

import pytest

from rwiki.cli import main


def run(argv, capsys) -> dict:
    assert main(argv) == 0
    return json.loads(capsys.readouterr().out)


def base_project(tmp_path: Path, capsys) -> Path:
    root = tmp_path / 'study'
    root.mkdir()
    run(['project', 'init', '--root', str(root)], capsys)
    return root


def test_project_init_status_check_roundtrip(tmp_path, capsys):
    root = tmp_path / 'study'
    root.mkdir()
    out = run(['project', 'init', '--root', str(root)], capsys)
    assert out['project_id'] == 'study' and out['revision'] == 1
    status = run(['project', 'status', '--root', str(root)], capsys)
    assert status['project_id'] == 'study' and status['revision'] == 1
    report = run(['project', 'check', '--root', str(root)], capsys)
    assert report['schema_ok'] is True and report['objects'] == {}


def test_project_requires_existing_state(tmp_path, capsys):
    assert main(['project', 'status', '--root', str(tmp_path / 'nope')]) == 1
    assert 'project' not in capsys.readouterr().out


def test_add_and_record_run_via_cli(tmp_path, capsys):
    root = base_project(tmp_path, capsys)
    (root / 'data.csv').write_text('a,b\n', encoding='utf-8')
    (root / 'out.txt').write_text('ok\n', encoding='utf-8')
    run(['project', 'add-object', '--root', str(root), '--id', 'raw',
         '--kind', 'table', '--path', 'data.csv', '--basis', 'verified'], capsys)
    run(['project', 'add-task', '--root', str(root), '--id', 't1',
         '--role', 'main', '--in', 'object:raw'], capsys)
    (root / 'analysis.py').write_text('# v1\n', encoding='utf-8')
    result = run(['project', 'record-run', '--root', str(root), '--run', 'r1',
                  '--task', 't1', '--status', 'completed', '--command', 'x y',
                  '--in', 'object:raw', '--out', 'out.txt', '--check', 'exit0',
                  '--code', 'file:analysis.py',
                  '--param', 'k=1', '--env', 'py=3.12'], capsys)
    assert result['status'] == 'completed' and result['duplicate_of'] is None
    import json
    receipt = json.loads(
        (root / 'wiki-use/_project/runs/r1/receipt.json').read_text(encoding='utf-8'))
    assert receipt['code_refs'] == ['file:analysis.py']
    assert 'file:analysis.py' in receipt['inputs']
    status = run(['project', 'status', '--root', str(root)], capsys)
    assert status['counts']['runs'] == 1 and status['counts']['tasks']['completed'] == 1


def test_record_run_completed_needs_real_evidence(tmp_path, capsys):
    root = base_project(tmp_path, capsys)
    run(['project', 'add-task', '--root', str(root), '--id', 't1'], capsys)
    # 退出码/调用方布尔不授予完成：无命令、无产物、无检查 -> 拒绝
    assert main(['project', 'record-run', '--root', str(root), '--run', 'r1',
                 '--task', 't1', '--status', 'completed']) == 1
    err = capsys.readouterr().err
    assert '命令' in err or '检查' in err or '输出' in err


def test_impact_marks_stale_via_cli(tmp_path, capsys):
    root = base_project(tmp_path, capsys)
    (root / 'data.csv').write_text('a,b\n', encoding='utf-8')
    (root / 'out.txt').write_text('ok\n', encoding='utf-8')
    for argv in (
        ['project', 'add-object', '--root', str(root), '--id', 'raw',
         '--kind', 'table', '--path', 'data.csv', '--basis', 'verified'],
        ['project', 'add-task', '--root', str(root), '--id', 't1',
         '--in', 'object:raw'],
        ['project', 'record-run', '--root', str(root), '--run', 'r1',
         '--task', 't1', '--status', 'completed', '--command', 'x',
         '--in', 'object:raw', '--out', 'out.txt', '--check', 'ok'],
    ):
        run(argv, capsys)
    report = run(['project', 'impact', '--root', str(root),
                  '--changed', 'object:raw'], capsys)
    assert report['tasks'] and 'applied' not in report
    applied = run(['project', 'impact', '--root', str(root),
                   '--changed', 'object:raw', '--apply'], capsys)
    assert applied['applied']['revision'] > 1


def test_evaluate_profile_via_cli(tmp_path, capsys):
    root = base_project(tmp_path, capsys)
    report = run(['project', 'evaluate', '--root', str(root),
                  '--profile', 'radiomics'], capsys)
    assert report['radiomics']['checks']
    # 空课题全部前提 unknown，不当作满足或拒绝
    assert all(c['state'] == 'unknown' for c in report['radiomics']['checks'])


def test_discover_methods_cli(workspace, capsys):
    config, config_path = workspace
    from rwiki.methods import scaffold_method
    scaffold_method(config, 'dm', 'dm', 'MIT', written=True)
    page = config.wiki_root / 'methods/dm.md'
    from rwiki.pages import read_page, write_page
    meta, body = read_page(page)
    meta.update(method_kind='analysis', summary='x', cite=['s'],
                data_contract={'input': 'i', 'output': 'o'},
                implementations=[{'id': 'b', 'title': 'b', 'language': 'R',
                                  'entrypoint': 'code/x.R:f', 'dependencies': []}])
    write_page(page, meta, body)
    code = page.with_suffix('') / 'code'
    code.mkdir(parents=True)
    (code / 'x.R').write_text('f <- function(x) x\n', encoding='utf-8')
    out = run(['--config', str(config_path), 'discover-methods'], capsys)
    cand = next(c for c in out['candidates'] if c['id'] == 'dm')
    assert cand['executable'] is False and cand['readiness']['not_run'] == ['b']
