"""Project-local state/evidence layer: atomic single-writer, three-basis evidence.

All fixtures are project directories under tmp_path; no Wiki save is involved.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

from rwiki.errors import WikiError
from rwiki.project_state import (
    add_data_root, add_decision, add_entity, add_object, add_observation,
    add_route, add_task, check_project, impact_analysis, init_project,
    load_project, mark_stale, project_status, record_run, update_project,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(tmp_path: Path, title='Demo project') -> Path:
    root = tmp_path / 'study'
    root.mkdir()
    (root / 'data').mkdir()
    return init_project(root, title=title)['project_root'] and root or root


def base_state(root: Path) -> dict:
    return json.loads((root / 'wiki-use/_project/project.json').read_text(encoding='utf-8'))


def test_init_creates_state_and_summary(tmp_path):
    root = tmp_path / 'study'
    root.mkdir()
    state = init_project(root, title='Glaucoma pilot')
    assert state['schema_version'] == 1
    assert state['revision'] == 1
    assert state['project_id']
    assert (root / 'wiki-use/_project/project.json').is_file()
    summary = (root / 'wiki-use/_project/summary.md').read_text(encoding='utf-8')
    assert 'Glaucoma pilot' in summary
    # A second init must not silently overwrite existing state.
    with pytest.raises(WikiError):
        init_project(root)


def test_init_preserves_legacy_wiki_use_contexts(tmp_path):
    root = tmp_path / 'study'
    old = root / 'wiki-use' / '2026-10-01-first'
    old.mkdir(parents=True)
    (old / 'context.json').write_text('{"question": "legacy"}', encoding='utf-8')
    state = init_project(root)
    assert any('2026-10-01-first' in item['path'] for item in state['legacy_contexts'])
    assert json.loads((old / 'context.json').read_text())


def test_state_write_never_requires_wiki_config(tmp_path):
    # The project layer works without a Wiki Config object and never calls save.
    (tmp_path / 'study').mkdir()
    root = Path(init_project(tmp_path / 'study')['project_root'])
    add_entity(root, 'donors', 'subject', count=3)
    assert base_state(root)['entities']['donors']['kind'] == 'subject'


def test_atomic_revision_conflict_preserves_state(tmp_path):
    root = Path(project(tmp_path))
    state = load_project(root)
    rev = state['revision']

    def stale_writer(_state):
        return load_project(root)  # would be a stale write if applied

    # Simulate a second session writing after our read.
    add_entity(root, 'donors', 'subject', count=2)
    with pytest.raises(WikiError, match='revision|修订'):
        update_project(root, lambda s: dict(s, entities={**s['entities'], 'x': {}}),
                       expected_revision=rev)
    after = load_project(root)
    assert after['revision'] == rev + 1
    assert 'x' not in after['entities']


def test_failed_update_leaves_no_half_state(tmp_path):
    root = Path(project(tmp_path))
    before = base_state(root)

    def bad(state):
        state = dict(state)
        state['objects']['bad'] = {'id': 'wrong'}   # invalid record
        return state, ('register', 'bad object')

    with pytest.raises(WikiError):
        update_project(root, bad)
    assert base_state(root) == before
    assert not (root / 'wiki-use/_project/project.lock').exists()


def test_corrupt_state_fails_closed(tmp_path):
    root = Path(project(tmp_path))
    target = root / 'wiki-use/_project/project.json'
    target.write_text('{broken json', encoding='utf-8')
    with pytest.raises(WikiError):
        load_project(root)
    with pytest.raises(WikiError):
        add_entity(root, 'x', 'sample')


def test_object_paths_stay_inside_project_or_registered_roots(tmp_path):
    root = Path(project(tmp_path))
    (root / 'data/mat.csv').write_text('a,b\n1,2\n', encoding='utf-8')
    add_object(root, 'mat', 'matrix', path='data/mat.csv', native_type='csv',
               properties={'assay': 'expression'})
    with pytest.raises(WikiError, match='路径|越界'):
        add_object(root, 'escape', 'matrix', path='../outside.csv')
    outside = tmp_path / 'elsewhere.txt'
    outside.write_text('x', encoding='utf-8')
    with pytest.raises(WikiError, match='数据根|未登记|root'):
        add_object(root, 'ext', 'table', external=str(outside))
    external_root = tmp_path / 'reference'
    external_root.mkdir()
    (external_root / 'ref.fa').write_text('>seq\nACGT\n', encoding='utf-8')
    add_data_root(root, str(external_root), access='read')
    state = add_object(root, 'ref', 'reference', external=str(external_root / 'ref.fa'),
                       basis='verified')
    assert state['objects']['ref']['sha256'] == sha(external_root / 'ref.fa')


def test_verified_basis_requires_real_file(tmp_path):
    root = Path(project(tmp_path))
    with pytest.raises(WikiError, match='verified|存在'):
        add_object(root, 'ghost', 'matrix', path='data/missing.csv', basis='verified')


def test_partial_evidence_stays_unknown(tmp_path):
    root = Path(project(tmp_path))
    add_object(root, 'mat', 'matrix', path='data/m.csv', basis='author_stated')
    add_observation(root, 'obs-anno', 'annotation_correct', about='object:mat',
                    value='unknown', basis='unknown', note='annotation column exists; correctness not checked')
    report = check_project(root)
    assert report['objects']['mat']['state'] == 'missing'
    assert report['observations']['obs-anno']['basis'] == 'unknown'


def test_check_detects_stale_and_missing(tmp_path):
    root = Path(project(tmp_path))
    (root / 'data/a.csv').write_text('x\n1\n', encoding='utf-8')
    add_object(root, 'a', 'table', path='data/a.csv')
    report = check_project(root)
    assert report['objects']['a']['state'] == 'current'
    (root / 'data/a.csv').write_text('x\n2\n', encoding='utf-8')
    assert check_project(root)['objects']['a']['state'] == 'stale'
    (root / 'data/a.csv').unlink()
    assert check_project(root)['objects']['a']['state'] == 'missing'


def test_record_run_registers_artifacts_and_dedups(tmp_path):
    root = Path(project(tmp_path))
    (root / 'data/mat.csv').write_text('a,b\n1,2\n', encoding='utf-8')
    add_object(root, 'mat', 'matrix', path='data/mat.csv')
    add_task(root, 'qc', family_id='cell-quality-control', implementation_id='scp-runcellqc',
             role='main', inputs=['object:mat'])
    out = root / 'analysis/qc_report.csv'
    out.parent.mkdir()
    out.write_text('cell,mt\na,0.1\n', encoding='utf-8')
    # An implementation_id names a branch; actual code provenance is declared
    # via --code and is required for any equivalent-run reuse.
    (root / 'scripts').mkdir()
    (root / 'scripts/qc.R').write_text('# qc v1\n', encoding='utf-8')
    result = record_run(root, 'run-001', 'qc', status='completed',
                        command='Rscript scripts/qc.R data/mat.csv analysis/qc_report.csv',
                        inputs=['object:mat'], outputs=['analysis/qc_report.csv'],
                        code=['file:scripts/qc.R'],
                        checks=['输出表 1 行', 'mt 列在 0-1 范围'],
                        params={'mt_max': 0.2})
    assert result['duplicate_of'] is None
    state = load_project(root)
    assert state['runs']['run-001']['status'] == 'completed'
    artifact = next(a for a in state['artifacts'].values() if a['path'] == 'analysis/qc_report.csv')
    assert artifact['freshness']['state'] == 'current'
    assert artifact['sha256'] == sha(out)
    # Work completion is not algorithm verification; no 'verified' flag may appear.
    assert 'verified' not in state['runs']['run-001']
    assert 'verified' not in artifact
    # Same task + same command + same code/input/param fingerprints => dedup.
    again = record_run(root, 'run-002', 'qc', status='completed',
                       command='Rscript scripts/qc.R data/mat.csv analysis/qc_report.csv',
                       inputs=['object:mat'],
                       outputs=['analysis/qc_report.csv'], code=['file:scripts/qc.R'],
                       checks=['same'], params={'mt_max': 0.2})
    assert again['duplicate_of'] == 'run-001'
    assert 'run-002' not in load_project(root)['runs']
    # A different command is a different computation — never a silent duplicate.
    other = record_run(root, 'run-003', 'qc', status='completed',
                       command='Rscript scripts/qc-v2.R data/mat.csv analysis/qc_report.csv',
                       inputs=['object:mat'],
                       outputs=['analysis/qc_report.csv'], code=['file:scripts/qc.R'],
                       checks=['same'], params={'mt_max': 0.2})
    assert other['duplicate_of'] is None
    assert load_project(root)['runs']['run-003']['status'] == 'completed'


def test_completed_run_requires_evidence(tmp_path):
    root = Path(project(tmp_path))
    add_task(root, 'qc')
    with pytest.raises(WikiError, match='输出|checks|检查'):
        record_run(root, 'run-1', 'qc', status='completed', command='x')
    failed = record_run(root, 'run-1', 'qc', status='failed', command='x',
                        checks=[])
    assert failed['duplicate_of'] is None
    # A failed record leaves task status failed and no artifacts.
    state = load_project(root)
    assert state['tasks']['qc']['status'] == 'failed'
    assert not state['artifacts']


def test_run_id_immutable_once_completed(tmp_path):
    root = Path(project(tmp_path))
    add_task(root, 'qc')
    out = root / 'analysis/r.csv'
    out.parent.mkdir()
    out.write_text('x\n1\n', encoding='utf-8')
    record_run(root, 'run-1', 'qc', status='completed', command='x',
               outputs=['analysis/r.csv'], checks=['ok'])
    with pytest.raises(WikiError, match='run-1|已存在'):
        record_run(root, 'run-1', 'qc', status='completed', command='y',
                   outputs=['analysis/r.csv'], checks=['ok'])


def test_running_then_completed_updates_same_run(tmp_path):
    root = Path(project(tmp_path))
    add_task(root, 'qc')
    record_run(root, 'run-1', 'qc', status='running', command='x')
    assert load_project(root)['tasks']['qc']['status'] == 'running'
    out = root / 'analysis/r.csv'
    out.parent.mkdir(exist_ok=True)
    out.write_text('x\n1\n', encoding='utf-8')
    record_run(root, 'run-1', 'qc', status='completed', command='x',
               outputs=['analysis/r.csv'], checks=['ok'])
    state = load_project(root)
    assert state['tasks']['qc']['status'] == 'completed'
    assert state['runs']['run-1']['status'] == 'completed'


def test_impact_marks_direct_indirect_and_unknown(tmp_path):
    root = Path(project(tmp_path))
    (root / 'data/mat.csv').write_text('a,b\n1,2\n', encoding='utf-8')
    add_object(root, 'mat', 'matrix', path='data/mat.csv')
    add_task(root, 'qc', inputs=['object:mat'])
    add_task(root, 'score', inputs=['file:analysis/qc.csv'])
    add_task(root, 'explore')  # no declared inputs: impact must stay conservative
    (root / 'analysis').mkdir()
    (root / 'analysis/qc.csv').write_text('x\n1\n', encoding='utf-8')
    (root / 'analysis/score.csv').write_text('y\n2\n', encoding='utf-8')
    record_run(root, 'r1', 'qc', status='completed', command='c',
               inputs=['object:mat'], outputs=['analysis/qc.csv'], checks=['ok'])
    record_run(root, 'r2', 'score', status='completed', command='c',
               inputs=['file:analysis/qc.csv'], outputs=['analysis/score.csv'], checks=['ok'])
    report = impact_analysis(root, ['object:mat'])
    direct = {item['id'] for item in report['direct']}
    indirect = {item['id'] for item in report['indirect']}
    tasks = {item['id'] for item in report['tasks']}
    assert any('qc.csv' in item['path'] for item in report['direct'])
    assert any('score.csv' in item['path'] for item in report['indirect'])
    assert 'qc' in tasks and 'score' in tasks
    assert 'explore' in {item['id'] for item in report['unknown']}
    # Unrelated untouched artifact would not appear; here both are reachable.
    marked = mark_stale(root, report, reason='mat changed')
    artifacts = marked['artifacts']
    stale = {a['path'] for a in artifacts.values() if a['freshness']['state'] == 'stale'}
    assert stale == {'analysis/qc.csv', 'analysis/score.csv'}


def test_native_non_table_objects_first_class(tmp_path):
    root = Path(project(tmp_path))
    weights = root / 'models/unet.pt'
    weights.parent.mkdir()
    weights.write_bytes(b'weights-bytes')
    image = root / 'img/patient01.png'
    image.parent.mkdir()
    image.write_bytes(b'png-bytes')
    add_object(root, 'unet-weights', 'model_weights', path='models/unet.pt',
               native_type='pytorch', basis='verified')
    add_object(root, 'img-01', 'image', path='img/patient01.png',
               native_type='png', properties={'patient': 'p01'})
    state = load_project(root)
    assert state['objects']['unet-weights']['sha256'] == sha(weights)
    assert state['objects']['img-01']['native_type'] == 'png'
    report = check_project(root)
    assert report['objects']['unet-weights']['state'] == 'current'
    assert report['objects']['img-01']['state'] == 'current'


def test_external_impact_refuses_unregistered_paths(tmp_path):
    root = Path(project(tmp_path))
    with pytest.raises(WikiError):
        impact_analysis(root, ['external:C:/nowhere/file.bin'])


def test_status_summarizes_axes_separately(tmp_path):
    root = Path(project(tmp_path))
    add_route(root, 'route-a', 'Which cells expand?', decision='pending')
    add_decision(root, 'd-1', 'route', 'author picked route-a', scope='route-a')
    add_task(root, 'qc')
    record_run(root, 'r1', 'qc', status='failed', command='x')
    status = project_status(root)
    assert status['revision'] >= 1
    assert status['counts']['tasks'].get('failed') == 1
    assert 'route-a' in {r['id'] for r in status['routes']}
    assert status['counts']['decisions'] == 1
    # summary.md stays regenerable and reflects latest revision
    summary = (root / 'wiki-use/_project/summary.md').read_text(encoding='utf-8')
    assert 'route-a' in summary

# ------------------------------------------------ review-1 regression tests


def _analysis_project(tmp_path):
    root = Path(project(tmp_path))
    (root / 'input.bin').write_bytes(b'input-v1')
    (root / 'out.csv').write_text('x\n1\n', encoding='utf-8')
    add_object(root, 'matrix', 'matrix', path='input.bin', basis='verified',
               properties={'assay': 'expression', 'organism': 'mouse', 'id_system': 'symbol'})
    add_task(root, 'analyze', inputs=['object:matrix'])
    return root


def test_record_run_defaults_to_declared_inputs_and_rejects_omission(tmp_path):
    root = _analysis_project(tmp_path)
    # Omitted --in falls back to the task's declared inputs.
    result = record_run(root, 'r1', 'analyze', status='completed', command='c',
                        outputs=['out.csv'], checks=['ok'])
    assert result['duplicate_of'] is None
    receipt = json.loads(
        (root / 'wiki-use/_project/runs/r1/receipt.json').read_text(encoding='utf-8'))
    assert 'object:matrix' in receipt['inputs']
    # An explicit list missing a declared dependency is rejected.
    with pytest.raises(WikiError, match='声明|matrix'):
        record_run(root, 'r2', 'analyze', status='completed', command='c',
                   inputs=[], outputs=['out.csv'], checks=['ok'])


def test_record_run_rejects_output_input_alias_and_duplicate_outputs(tmp_path):
    root = _analysis_project(tmp_path)
    with pytest.raises(WikiError, match='同一文件|alias|输入'):
        record_run(root, 'r1', 'analyze', status='completed', command='c',
                   inputs=['object:matrix'], outputs=['input.bin'], checks=['ok'])
    with pytest.raises(WikiError, match='重复'):
        record_run(root, 'r1', 'analyze', status='completed', command='c',
                   outputs=['out.csv', 'out.csv'], checks=['ok'])
    with pytest.raises(WikiError, match='不存在'):
        record_run(root, 'r1', 'analyze', status='completed', command='c',
                   inputs=['object:missing'], outputs=['out.csv'], checks=['ok'])


def test_stale_prior_run_is_not_a_reusable_duplicate(tmp_path):
    root = _analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='completed', command='c',
               outputs=['out.csv'], checks=['ok'])
    (root / 'out.csv').unlink()
    with pytest.raises(WikiError, match='输出文件不存在'):
        record_run(root, 'r2', 'analyze', status='completed', command='c',
                   outputs=['out.csv'], checks=['ok'])
    # An altered input makes the old receipt's fingerprints unverifiable too:
    (root / 'out.csv').write_text('x\n1\n', encoding='utf-8')
    (root / 'input.bin').write_bytes(b'input-v2')
    result = record_run(root, 'r3', 'analyze', status='completed', command='c',
                        outputs=['out.csv'], checks=['ok'])
    assert result['duplicate_of'] is None


def test_revision_conflict_preserves_running_receipt(tmp_path):
    root = _analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='running', command='initial')
    receipt = root / 'wiki-use/_project/runs/r1/receipt.json'
    before = receipt.read_bytes()
    with pytest.raises(WikiError, match='修订号冲突'):
        record_run(root, 'r1', 'analyze', status='completed', command='c',
                   outputs=['out.csv'], checks=['ok'], expected_revision=0)
    assert receipt.read_bytes() == before
    assert load_project(root)['runs']['r1']['status'] == 'running'


def test_dependency_cycle_is_rejected_at_write(tmp_path):
    root = _analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='completed', command='c',
               outputs=['out.csv'], checks=['ok'])
    aid = next(iter(load_project(root)['artifacts']))
    add_task(root, 'feed', inputs=[f'artifact:{aid}'])
    (root / 'loop.csv').write_text('x\n1\n', encoding='utf-8')
    artifacts = dict(load_project(root)['artifacts'])
    artifacts['a-loop'] = {'id': 'a-loop', 'path': 'loop.csv', 'kind': 'file',
                           'sha256': sha(root / 'loop.csv'), 'produced_by': 'r1',
                           'inputs': [],
                           'freshness': {'state': 'current', 'checked_at': 't', 'reason': ''}}
    def inject(state):
        state = dict(state)
        state['artifacts'] = artifacts
        tasks = dict(state['tasks'])
        t = dict(tasks['analyze'])
        t['inputs'] = ['artifact:a-loop']
        tasks['analyze'] = t
        state['tasks'] = tasks
        return state, ('task', 'inject cycle')

    # a-loop is produced by r1 whose task is analyze; analyze inputs a-loop => cycle.
    with pytest.raises(WikiError, match='环路|校验未通过'):
        update_project(root, inject)


def test_check_project_propagates_stale_to_consumers_and_tasks(tmp_path):
    root = _analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='completed', command='c',
               outputs=['out.csv'], checks=['ok'])
    parent = next(iter(load_project(root)['artifacts']))
    add_task(root, 'plot', inputs=[f'artifact:{parent}'])
    (root / 'plot.png').write_bytes(b'png')
    record_run(root, 'r2', 'plot', status='completed', command='render',
               inputs=[f'artifact:{parent}'], outputs=['plot.png'], checks=['ok'])
    (root / 'input.bin').write_bytes(b'input-v2')
    report = check_project(root)
    by_path = {a['path']: a for a in report['artifacts'].values()}
    assert by_path['out.csv']['freshness'] == 'stale'
    # Child bytes unchanged but freshness must not stay current.
    assert by_path['plot.png']['freshness'] != 'current'
    assert report['tasks']['plot']['state'] != 'ok'
    assert report['tasks']['analyze']['state'] == 'at_risk'


def test_impact_file_alias_reaches_object_consumers(tmp_path):
    root = _analysis_project(tmp_path)
    report = impact_analysis(root, ['file:input.bin'])
    assert 'analyze' in {item['id'] for item in report['tasks']}


def test_external_path_rejects_relative_input(tmp_path):
    root = _analysis_project(tmp_path)
    add_data_root(root, str(Path.cwd()))
    from rwiki.project_state import external_path
    with pytest.raises(WikiError, match='绝对路径'):
        external_path(load_project(root), 'relative.csv')
    with pytest.raises(WikiError, match='绝对路径'):
        external_path(load_project(root), r'..\evil.bin')


def test_malformed_nested_record_is_schema_error(tmp_path):
    root = _analysis_project(tmp_path)
    path = root / 'wiki-use/_project/project.json'
    state = load_project(root)
    state['objects']['matrix'] = 'corrupt record'
    path.write_text(json.dumps(state), encoding='utf-8')
    with pytest.raises(WikiError, match='结构不合法|必须为对象记录'):
        load_project(root)


def test_copied_state_requires_explicit_relocate(tmp_path):
    import shutil
    root = _analysis_project(tmp_path)
    target = tmp_path / 'moved'
    shutil.copytree(root, target)
    with pytest.raises(WikiError, match='relocate|不一致'):
        load_project(target)
    from rwiki.project_state import relocate_project
    state = relocate_project(target)
    assert Path(state['project_root']).resolve() == target.resolve()
    assert load_project(target)['project_id'] == state['project_id']


def test_chinese_root_names_get_distinct_project_ids(tmp_path):
    a, b = tmp_path / '课题一', tmp_path / '课题二'
    a.mkdir()
    b.mkdir()
    sa = init_project(a)
    sb = init_project(b)
    assert sa['project_id'] != sb['project_id']
    assert sa['project_id'].startswith('project-')


def test_verified_observation_needs_inspectable_evidence(tmp_path):
    root = _analysis_project(tmp_path)
    # verified + evidence file that does not exist is rejected at write time.
    with pytest.raises(WikiError, match='证据|检查'):
        add_observation(root, 'o1', 'design_defined', value='true',
                        basis='verified', evidence='missing.txt')
    # verified without any evidence is recorded but downgraded in evaluation.
    add_observation(root, 'o2', 'design_defined', value='true', basis='verified')
    from rwiki.domain_profiles import _obs_rank
    item = load_project(root)['observations']['o2']
    assert _obs_rank(item, load_project(root), root) == 2


def test_register_profile_binds_spec_hash_and_surfaces_mismatch(tmp_path):
    from rwiki.domain_profiles import (evaluate_profile, load_profiles,
                                       profile_fingerprint)
    from rwiki.project_state import register_profile
    root = _analysis_project(tmp_path)
    spec = load_profiles()['bioinformatics_single_cell']
    register_profile(root, 'bioinformatics_single_cell', spec['version'],
                     spec_sha256=profile_fingerprint(spec))
    report = evaluate_profile(load_project(root), 'bioinformatics_single_cell')
    assert report['registration']['matches_current'] is True
    # A stale registration (wrong hash) must surface, not pass silently.
    path = root / 'wiki-use/_project/project.json'
    state = load_project(root)
    state['profile_refs'][0]['spec_sha256'] = '0' * 64
    path.write_text(json.dumps(state), encoding='utf-8')
    report = evaluate_profile(load_project(root), 'bioinformatics_single_cell')
    assert report['registration']['matches_current'] is False
    assert report['registration']['warning']


def test_object_inspection_is_explicit_not_implied_by_filename(tmp_path):
    root = _analysis_project(tmp_path)
    (root / 'm.rds').write_bytes(b'rds')
    add_object(root, 'seu', 'object', path='m.rds', native_type='SeuratObject')
    obj = load_project(root)['objects']['seu']
    assert obj['native_type'] == 'SeuratObject'
    assert obj['inspected'] is False
    with pytest.raises(WikiError, match='adapter'):
        add_object(root, 'seu2', 'object', path='m.rds', inspected=True)


# --- review-2: shared freshness/provenance/commit-boundary regressions ---

def _impl_analysis_project(tmp_path):
    """Fixture with a bound implementation AND declared code file, so each test
    exercises the intended guard (receipt structure / stale mark) rather than
    the missing-provenance shortcut."""
    root = Path(project(tmp_path))
    (root / 'input.bin').write_bytes(b'input-v1')
    (root / 'out.csv').write_text('x\n1\n', encoding='utf-8')
    (root / 'analysis.R').write_text('# stable computation\n', encoding='utf-8')
    add_object(root, 'matrix', 'matrix', path='input.bin', basis='verified',
               properties={'assay': 'expression'})
    add_task(root, 'analyze', implementation_id='impl-x', inputs=['object:matrix'])
    return root


CODE = ['file:analysis.R']


def test_changed_observation_evidence_invalidates_verified_claim(tmp_path):
    root = _analysis_project(tmp_path)
    (root / 'design.txt').write_text('design v1', encoding='utf-8')
    add_observation(root, 'o1', 'design_defined', value='true',
                    basis='verified', evidence='design.txt')
    assert check_project(root)['observations']['o1']['evidence'] == 'resolves'
    (root / 'design.txt').write_text('design v2 - changed bytes', encoding='utf-8')
    # One shared resolver: check reports the same stale state evaluate sees.
    assert check_project(root)['observations']['o1']['evidence'] == 'stale'
    from rwiki.domain_profiles import _obs_rank
    item = load_project(root)['observations']['o1']
    assert _obs_rank(item, load_project(root), root) == 1
    # A missing evidence file drops the same way, not to author-stated truth.
    (root / 'design.txt').unlink()
    assert _obs_rank(item, load_project(root), root) == 1
    assert check_project(root)['observations']['o1']['evidence'] == 'missing'


def test_same_command_without_provenance_never_silently_dedups(tmp_path):
    root = _analysis_project(tmp_path)
    (root / 'analysis.R').write_text('# v1', encoding='utf-8')
    first = record_run(root, 'r1', 'analyze', status='completed',
                       command='Rscript analysis.R', outputs=['out.csv'], checks=['ok'])
    assert first['duplicate_of'] is None
    (root / 'analysis.R').write_text('# corrected v2', encoding='utf-8')
    again = record_run(root, 'r2', 'analyze', status='completed',
                       command='Rscript analysis.R', outputs=['out.csv'], checks=['ok'])
    # Same command text proves nothing without recorded code provenance —
    # conservative non-equivalence, never a silent duplicate.
    assert again['duplicate_of'] is None


def test_explicit_code_refs_enable_and_bind_dedup(tmp_path):
    root = _analysis_project(tmp_path)
    (root / 'analysis.R').write_text('# v1', encoding='utf-8')
    record_run(root, 'r1', 'analyze', status='completed', command='Rscript analysis.R',
               code=['file:analysis.R'], outputs=['out.csv'], checks=['ok'])
    same = record_run(root, 'r2', 'analyze', status='completed', command='Rscript analysis.R',
                      code=['file:analysis.R'], outputs=['out.csv'], checks=['ok'])
    assert same['duplicate_of'] == 'r1'
    # Recorded code bytes changing must break the identity, not be ignored.
    (root / 'analysis.R').write_text('# corrected v2', encoding='utf-8')
    changed = record_run(root, 'r3', 'analyze', status='completed', command='Rscript analysis.R',
                         code=['file:analysis.R'], outputs=['out.csv'], checks=['ok'])
    assert changed['duplicate_of'] is None
    # A different recorded code identity never merges into the same run.
    (root / 'other.R').write_text('# v3', encoding='utf-8')
    other = record_run(root, 'r4', 'analyze', status='completed', command='Rscript analysis.R',
                       code=['file:other.R'], outputs=['out.csv'], checks=['ok'])
    assert other['duplicate_of'] is None


def test_structurally_invalid_receipt_is_never_reused(tmp_path):
    root = _impl_analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='completed', command='c',
               code=CODE, outputs=['out.csv'], checks=['ok'])
    receipt = root / 'wiki-use/_project/runs/r1/receipt.json'
    receipt.write_text('{}', encoding='utf-8')
    again = record_run(root, 'r2', 'analyze', status='completed', command='c',
                       code=CODE, outputs=['out.csv'], checks=['ok'])
    assert again['duplicate_of'] is None
    # Identity/status/inputs/outputs/timestamps are all required, not just JSON.
    receipt2 = root / 'wiki-use/_project/runs/r2/receipt.json'
    receipt2.write_text(json.dumps({'run_id': 'r2', 'status': 'completed'}),
                        encoding='utf-8')
    result = record_run(root, 'r3', 'analyze', status='completed', command='c',
                        code=CODE, outputs=['out.csv'], checks=['ok'])
    assert result['duplicate_of'] is None


def test_explicit_stale_artifact_blocks_reuse_even_when_bytes_match(tmp_path):
    root = _impl_analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='completed', command='c',
               code=CODE, outputs=['out.csv'], checks=['ok'])
    # Bytes still match, but the artifact was explicitly invalidated upstream.
    mark_stale(root, impact_analysis(root, ['object:matrix']), reason='known invalidation')
    again = record_run(root, 'r2', 'analyze', status='completed', command='c',
                       code=CODE, outputs=['out.csv'], checks=['ok'])
    assert again['duplicate_of'] is None


def test_file_alias_consumers_inherit_upstream_staleness(tmp_path):
    root = _analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='completed', command='c',
               outputs=['out.csv'], checks=['ok'])
    add_task(root, 'plot', inputs=['file:out.csv'])
    (root / 'plot.png').write_bytes(b'plot-v1')
    record_run(root, 'r2', 'plot', status='completed', command='render',
               inputs=['file:out.csv'], outputs=['plot.png'], checks=['ok'])
    (root / 'input.bin').write_bytes(b'input-v2')
    report = check_project(root)
    by_path = {a['path']: a for a in report['artifacts'].values()}
    assert by_path['out.csv']['freshness'] == 'stale'
    # file:<artifact-path> must propagate exactly like artifact:<id>.
    assert by_path['plot.png']['freshness'] != 'current'


def test_derived_failure_commits_consistently_with_explicit_warning(tmp_path, monkeypatch):
    root = _analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='running', command='initial')
    import rwiki.project_state as ps
    original = ps.os.replace

    def fail_summary(source, target):
        if Path(target).name == 'summary.md':
            raise OSError('simulated summary rename failure')
        return original(source, target)
    monkeypatch.setattr(ps.os, 'replace', fail_summary)
    result = record_run(root, 'r1', 'analyze', status='completed', command='c',
                        outputs=['out.csv'], checks=['ok'])
    # Derived-file failure is a recoverable gap: state and receipt still agree,
    # and the gap is explicit in the result — never a false rollback report.
    assert result['derived_warnings']
    state = load_project(root)
    receipt = json.loads(
        (root / 'wiki-use/_project/runs/r1/receipt.json').read_text(encoding='utf-8'))
    assert state['runs']['r1']['status'] == receipt['status'] == 'completed'


# --- review-3: identity/atomicity/subject-freshness regressions ---

def test_unhashed_material_is_never_current(tmp_path):
    root = _analysis_project(tmp_path)
    import rwiki.project_state as ps
    state = load_project(root)
    # Presence without a recorded fingerprint cannot establish unchanged bytes.
    assert ps.material_state(state, root, path=root / 'input.bin',
                             recorded_sha=None) == 'unhashed'
    (root / 'adir').mkdir()
    assert ps.material_state(state, root, path=root / 'adir',
                             recorded_sha=None) == 'unhashed'
    assert ps.material_state(state, root, path=root / 'gone.bin',
                             recorded_sha=None) == 'missing'


def test_receipt_output_without_hash_is_never_reused(tmp_path):
    root = _impl_analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='completed', command='c',
               code=CODE, outputs=['out.csv'], checks=['ok'])
    receipt_path = root / 'wiki-use/_project/runs/r1/receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    for output in receipt['outputs']:
        output.pop('sha256', None)
    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
    # Explicit code provenance is present, so the missing-hash guard is what
    # must block reuse — an absent hash is not equivalent to a matching hash.
    again = record_run(root, 'r2', 'analyze', status='completed', command='c',
                       code=CODE, outputs=['out.csv'], checks=['ok'])
    assert again['duplicate_of'] is None


def test_implementation_id_alone_never_proves_code_identity(tmp_path):
    root = _impl_analysis_project(tmp_path)
    # Bound branch id but NO recorded code refs: same command proves nothing.
    record_run(root, 'r1', 'analyze', status='completed', command='Rscript analysis.R',
               outputs=['out.csv'], checks=['ok'])
    (root / 'analysis.R').write_text('# corrected v2\n', encoding='utf-8')
    again = record_run(root, 'r2', 'analyze', status='completed', command='Rscript analysis.R',
                       outputs=['out.csv'], checks=['ok'])
    assert again['duplicate_of'] is None


def test_bound_implementation_still_dedups_with_real_code_provenance(tmp_path):
    root = _impl_analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='completed', command='Rscript analysis.R',
               code=CODE, outputs=['out.csv'], checks=['ok'])
    again = record_run(root, 'r2', 'analyze', status='completed', command='Rscript analysis.R',
                       code=CODE, outputs=['out.csv'], checks=['ok'])
    assert again['duplicate_of'] == 'r1'


def test_failed_state_commit_restores_published_derived_views(tmp_path, monkeypatch):
    root = _analysis_project(tmp_path)
    record_run(root, 'r1', 'analyze', status='running', command='initial')
    folder = root / 'wiki-use/_project'
    before = {name: (folder / name).read_bytes()
              for name in ('project.json', 'summary.md', 'runs/r1/receipt.json')}
    import rwiki.project_state as ps
    original = ps.os.replace

    def fail_state(source, target):
        if Path(target).name == 'project.json':
            raise OSError('simulated authoritative state commit failure')
        return original(source, target)
    monkeypatch.setattr(ps.os, 'replace', fail_state)
    with pytest.raises((OSError, WikiError)):
        record_run(root, 'r1', 'analyze', status='completed', command='c',
                   outputs=['out.csv'], checks=['ok'])
    # Old authoritative state must not sit under a future-revision summary or
    # a completed receipt it never committed.
    for name, data in before.items():
        assert (folder / name).read_bytes() == data, name


def test_observation_about_replaced_object_is_not_current_proof(tmp_path):
    root = _analysis_project(tmp_path)
    (root / 'design.txt').write_text('design inspected for input v1', encoding='utf-8')
    add_observation(root, 'scoped-design', 'design_defined', about='object:matrix',
                    value='true', basis='verified', evidence='design.txt')
    (root / 'input.bin').write_bytes(b'replaced-data-version-two')
    # check and evaluate agree through the same subject freshness resolver.
    entry = check_project(root)['observations']['scoped-design']
    assert entry['subject'] == 'stale'
    from rwiki.domain_profiles import evaluate_profile
    report = evaluate_profile(load_project(root), 'bioinformatics_single_cell',
                              subject='object:matrix')
    check = next(c for c in report['checks'] if c['id'] == 'design')
    assert check['state'] != 'satisfied'
    # Conservativeness, not falsehood: the replaced subject invalidates the
    # claim but never invents a negative one.
    assert check['state'] != 'unsatisfied'
