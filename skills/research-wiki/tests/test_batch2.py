"""Batch-2 capabilities: chunked hashing, scoped save, lessons, analysis-only
use registration, claim-based stage evidence, change classes, recovery.

All fixtures are isolated under tmp_path; no formal Wiki writes, no network.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import run_cli
from rwiki.errors import WikiError
from rwiki.project_state import (
    _sha, add_decision, add_lesson, add_object, add_observation, add_task,
    check_project, impact_analysis, init_project, load_project, mark_stale,
    project_status, record_run, recover_project, review_lesson, state_dir,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(tmp_path: Path) -> Path:
    root = tmp_path / 'study'
    root.mkdir()
    init_project(root, title='Batch2 fixture')
    return root


def seed_run(root: Path, task='t1', run='r1', data='data.csv', out='out.csv',
             stage=None, code='scripts/run.R', family=None, impl=None):
    """A completed run with real code provenance and a real output file."""
    (root / 'data').mkdir(exist_ok=True)
    (root / 'scripts').mkdir(exist_ok=True)
    (root / data).parent.mkdir(parents=True, exist_ok=True)
    (root / data).write_text('v1\n', encoding='utf-8')
    (root / code).parent.mkdir(parents=True, exist_ok=True)
    (root / code).write_text('# fixture code\n', encoding='utf-8')
    add_task(root, task, inputs=[f'file:{data}'], stage=stage,
             family_id=family, implementation_id=impl)
    (root / out).write_text(f'{run}-output\n', encoding='utf-8')
    return record_run(root, run, task, status='completed', command='Rscript run.R',
                      code=[f'file:{code}'], outputs=[out],
                      checks=['output file exists'])


# ---------------------------------------------------------------- chunked sha

def test_sha_chunked_digest_matches_whole_file(tmp_path):
    root = tmp_path / 'blob'
    payload = bytes(range(256)) * 37 + b'tail'  # 9476 bytes, many 4-byte chunks
    root.write_bytes(payload)
    whole = hashlib.sha256(payload).hexdigest()
    assert _sha(root) == whole
    # Tiny chunk size proves the streaming loop works and preserves digests.
    assert _sha(root, chunk_size=4) == whole
    assert _sha(root, chunk_size=1) == whole


def test_chunked_sha_bounded_reads(monkeypatch, tmp_path):
    """Reads must be bounded blocks, never one whole-file read."""
    root = tmp_path / 'blob'
    root.write_bytes(b'x' * 5000)
    expected = sha(root)  # compute before spying; read_bytes uses read(-1)
    reads = []
    real_open = Path.open

    def spy(self, *a, **k):
        handle = real_open(self, *a, **k)
        if 'rb' in (a[0] if a else k.get('mode', 'r')):
            real_read = handle.read
            def counted(n=-1):
                reads.append(n)
                return real_read(n)
            handle.read = counted
        return handle

    monkeypatch.setattr(Path, 'open', spy)
    assert _sha(root, chunk_size=1024) == expected
    assert reads and all(0 < n <= 1024 for n in reads)
    assert len(reads) >= 5  # 5000 bytes never read in one gulp


def test_object_records_fingerprint_scope_and_bytes(tmp_path):
    root = project(tmp_path)
    (root / 'big.bin').write_bytes(b'payload' * 100)
    add_object(root, 'blob', 'binary', path='big.bin')
    item = load_project(root)['objects']['blob']
    assert item['sha256'] == sha(root / 'big.bin')
    assert item['bytes'] == (root / 'big.bin').stat().st_size
    assert 'sha256' in item['fingerprint_scope']


# ---------------------------------------------------------------- lessons

def test_lesson_requires_evidence(tmp_path):
    root = project(tmp_path)
    with pytest.raises(WikiError, match='证据'):
        add_lesson(root, 'l1', '无据经验', evidence=[], applies_to='fixture')


def test_lesson_draft_dedup_merges_evidence(tmp_path):
    root = project(tmp_path)
    seed_run(root)
    first = add_lesson(root, 'l1', 'Seurat AP1 scoring needs Seurat runtime',
                       evidence=['run:r1'], applies_to='single-cell scoring')
    assert first['lesson_id'] == 'l1' and not first['deduplicated']
    assert load_project(root)['lessons']['l1']['status'] == 'pending'
    (root / 'out2.csv').write_text('r2-output\n', encoding='utf-8')
    add_task(root, 't2', inputs=['file:data.csv'])
    record_run(root, 'r2', 't2', status='completed', command='Rscript run.R',
               code=['file:scripts/run.R'], outputs=['out2.csv'], checks=['ok'])
    # Dangling evidence is rejected — a lesson must cite real records.
    with pytest.raises(WikiError, match='不存在'):
        add_lesson(root, 'l3', 'same claim', evidence=['observation:ghost'])
    # Same claim+scope -> merge evidence into the existing draft, no new record.
    second = add_lesson(root, 'l2', 'Seurat  AP1  scoring needs Seurat runtime',
                        evidence=['run:r2', 'task:t1'],
                        applies_to='single-cell  scoring')
    assert second['deduplicated'] and second['lesson_id'] == 'l1'
    lessons = load_project(root)['lessons']
    assert set(lessons) == {'l1'}
    assert set(lessons['l1']['draft']['evidence_refs']) == {'run:r1', 'run:r2', 'task:t1'}


def test_lesson_links_method_ids_without_creating_family(tmp_path):
    root = project(tmp_path)
    seed_run(root)
    result = add_lesson(root, 'l1', 'ridge render keeps native palette',
                        evidence=['run:r1'], links=['scp-cell-density'],
                        applies_to='native ridge render')
    draft = load_project(root)['lessons']['l1']['draft']
    assert draft['links'] == ['method:scp-cell-density']
    assert result['status'] == 'pending'


def test_lesson_review_requires_named_reviewer_and_explicit_state(tmp_path):
    root = project(tmp_path)
    seed_run(root)
    add_lesson(root, 'l1', 'draft claim', evidence=['run:r1'],
               applies_to='fixture scope')
    with pytest.raises(WikiError, match='reviewed_by'):
        review_lesson(root, 'l1', 'accepted', reviewed_by='')
    with pytest.raises(WikiError, match='评审状态'):
        review_lesson(root, 'l1', 'approved', reviewed_by='test-review（隔离夹具）')
    review_lesson(root, 'l1', 'deferred', reviewed_by='test-review（隔离夹具）')
    assert load_project(root)['lessons']['l1']['status'] == 'deferred'
    review_lesson(root, 'l1', 'rejected', reviewed_by='test-review（隔离夹具）')
    assert load_project(root)['lessons']['l1']['status'] == 'rejected'
    # 'accepted' requires a registered author decision — a reviewer signature
    # alone (or a bare boolean) can never push a draft to accepted.
    with pytest.raises(WikiError, match='--decision'):
        review_lesson(root, 'l1', 'accepted', reviewed_by='test-review（隔离夹具）')
    assert load_project(root)['lessons']['l1']['status'] == 'rejected'
    with pytest.raises(WikiError, match='decision 记录'):
        review_lesson(root, 'l1', 'accepted', reviewed_by='test-review（隔离夹具）',
                      decision='run:r1')
    with pytest.raises(WikiError, match='仅 accepted'):
        review_lesson(root, 'l1', 'deferred', reviewed_by='test-review（隔离夹具）',
                      decision='decision:d1')
    add_decision(root, 'd1', 'other', '作者批准该经验进入正式评审（隔离夹具）')
    review_lesson(root, 'l1', 'accepted', reviewed_by='test-review（隔离夹具）',
                  decision='decision:d1')
    item = load_project(root)['lessons']['l1']
    assert item['status'] == 'accepted'
    assert item['reviewed_by'] == 'test-review（隔离夹具）'
    assert item['decision_ref'] == 'decision:d1'
    status = project_status(root)
    assert status['counts']['lessons']['accepted'] == 1


# ------------------------------------------- analysis-only use registration

def _write_method(wiki_root: Path, method_id: str, status='ready'):
    from rwiki.pages import write_page
    write_page(wiki_root / f'methods/{method_id}.md', {
        'type': 'method', 'id': method_id, 'title': method_id, 'status': status,
        'method_kind': 'analysis', 'purposes': [], 'summary': 'fixture',
        'data_contract': {'input': 'x', 'output': 'y'},
        'implementations': [{'id': 'impl'}], 'tags': [], 'inputs': [], 'outputs': [],
        'source': {'kind': 'project', 'path': 'source'}, 'license': 'MIT',
        'cite': [], 'favorite': False,
    }, f'# {method_id}\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n'
       '## 使用记录\n\n<!-- user:start -->\n<!-- user:end -->\n')


def test_record_method_use_registers_run_without_figure(workspace, tmp_path):
    from rwiki.pages import read_page
    from rwiki.usage import record_method_use
    config, _ = workspace
    _write_method(config.wiki_root, 'score-method')
    root = project(tmp_path)
    seed_run(root, family='score-method', impl='impl')
    record_method_use(config, 'score-method', 'study-a', 'Study A',
                      project_root=root, run_id='r1', note='fixture note')
    meta, body = read_page(config.wiki_root / 'projects/study-a.md')
    assert 'score-method' in meta['methods']
    assert '分析运行 `r1`' in body and '仅分析登记，无配图' in body
    _, method_body = read_page(config.wiki_root / 'methods/score-method.md')
    assert '[[projects/study-a|Study A]]（分析 `r1`）' in method_body
    # No figure/template page was invented for the analysis-only record.
    assert not list((config.wiki_root / 'templates').glob('*.md'))
    # Idempotent: a second identical call does not duplicate the record.
    record_method_use(config, 'score-method', 'study-a', 'Study A',
                      project_root=root, run_id='r1')
    _, body = read_page(config.wiki_root / 'projects/study-a.md')
    assert body.count('分析运行 `r1`') == 1


def test_record_method_use_rejects_unsuccessful_or_stale_runs(workspace, tmp_path):
    from rwiki.usage import record_method_use
    config, _ = workspace
    _write_method(config.wiki_root, 'score-method')
    root = project(tmp_path)
    seed_run(root, family='score-method', impl='impl')
    add_task(root, 't2', inputs=['file:data.csv'],
             family_id='score-method', implementation_id='impl')
    record_run(root, 'r2', 't2', status='running')
    with pytest.raises(WikiError, match='状态为 running'):
        record_method_use(config, 'score-method', 's', 'S',
                          project_root=root, run_id='r2')
    with pytest.raises(WikiError, match='未登记'):
        record_method_use(config, 'score-method', 's', 'S',
                          project_root=root, run_id='ghost')
    # Output bytes changed after the run -> artifact stale -> cannot claim use.
    (root / 'out.csv').write_text('tampered\n', encoding='utf-8')
    with pytest.raises(WikiError, match='新鲜度|文件状态|指纹'):
        record_method_use(config, 'score-method', 's', 'S',
                          project_root=root, run_id='r1')
    assert not (config.wiki_root / 'projects/s.md').exists()


def test_record_method_use_rejects_deleted_output(workspace, tmp_path):
    from rwiki.usage import record_method_use
    config, _ = workspace
    _write_method(config.wiki_root, 'score-method')
    root = project(tmp_path)
    seed_run(root, family='score-method', impl='impl')
    (root / 'out.csv').unlink()
    with pytest.raises(WikiError):
        record_method_use(config, 'score-method', 's', 'S',
                          project_root=root, run_id='r1')
    assert not (config.wiki_root / 'projects/s.md').exists()


def test_record_method_use_requires_matching_family_and_impl(workspace, tmp_path):
    from rwiki.usage import record_method_use
    config, _ = workspace
    _write_method(config.wiki_root, 'score-method')
    _write_method(config.wiki_root, 'other-method')
    root = project(tmp_path)
    seed_run(root, family='other-method', impl='impl')
    with pytest.raises(WikiError, match='绑定家族'):
        record_method_use(config, 'score-method', 's', 'S',
                          project_root=root, run_id='r1')
    # Bound to an impl the page never declares -> still not attributable.
    seed_run(root, task='t2', run='r2', out='out2.csv',
             family='other-method', impl='ghost-impl')
    with pytest.raises(WikiError, match='绑定实现'):
        record_method_use(config, 'other-method', 's', 'S',
                          project_root=root, run_id='r2')
    # An unbound task can never be attributed to a family.
    seed_run(root, task='t9', run='r9', out='out9.csv')
    with pytest.raises(WikiError, match='绑定家族'):
        record_method_use(config, 'other-method', 's', 'S',
                          project_root=root, run_id='r9')
    assert not (config.wiki_root / 'projects/s.md').exists()


def test_record_method_use_requires_code_provenance_and_hash_agreement(
        workspace, tmp_path):
    from rwiki.usage import _verified_current_run
    root = project(tmp_path)
    # Run recorded without --code: implementation_id alone is not provenance.
    seed_run(root, family='score-method', impl='impl')
    (root / 'out2.csv').write_text('r2-out\n', encoding='utf-8')
    add_task(root, 't2', inputs=['file:data.csv'])
    record_run(root, 'r2', 't2', status='completed', command='Rscript run.R',
               outputs=['out2.csv'], checks=['ok'])
    with pytest.raises(WikiError, match='代码来源'):
        _verified_current_run(root, 'r2')
    # Receipt output hash disagreeing with the artifact record rejects.
    state = load_project(root)
    receipt_path = state_dir(root) / state['runs']['r1']['receipt']
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['outputs'][0]['sha256'] = 'f' * 64
    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(WikiError, match='不一致'):
        _verified_current_run(root, 'r1')


def test_record_method_use_rejects_unhashed_object_input(workspace, tmp_path):
    from rwiki.usage import _verified_current_run
    root = project(tmp_path)
    # Object registered while its file is absent -> no baseline fingerprint.
    add_object(root, 'input', 'native', path='ghost.bin')
    (root / 'ghost.bin').write_bytes(b'later material')
    (root / 'scripts').mkdir(exist_ok=True)
    (root / 'scripts/run.R').write_text('# c\n', encoding='utf-8')
    add_task(root, 't1', inputs=['object:input'])
    (root / 'out.csv').write_text('out\n', encoding='utf-8')
    record_run(root, 'r1', 't1', status='completed', command='Rscript run.R',
               code=['file:scripts/run.R'], outputs=['out.csv'], checks=['ok'])
    with pytest.raises(WikiError, match='基线指纹'):
        _verified_current_run(root, 'r1')


def test_lesson_merge_reopens_reviewed_draft(tmp_path):
    root = project(tmp_path)
    seed_run(root)
    add_lesson(root, 'l1', 'same claim', applies_to='scope', evidence=['run:r1'])
    add_decision(root, 'd1', 'other', 'fixture disposition, not real approval')
    review_lesson(root, 'l1', 'accepted', reviewed_by='fixture reviewer',
                  decision='decision:d1')
    add_observation(root, 'o2', 'more evidence', value='true')
    # New evidence reopens the accepted draft to pending; prior review is kept.
    result = add_lesson(root, 'l2', 'same claim', applies_to='scope',
                        evidence=['observation:o2'])
    assert result['deduplicated'] and result['status'] == 'pending'
    item = load_project(root)['lessons']['l1']
    assert item['status'] == 'pending' and item['reviewed_by'] is None
    prior = item['previous_reviews'][0]
    assert prior['status'] == 'accepted'
    assert prior['reviewed_by'] == 'fixture reviewer'
    assert prior['decision_ref'] == 'decision:d1'
    assert prior['evidence_refs'] == ['run:r1']
    # An idempotent retry (no new evidence) does not disturb the draft state.
    review_lesson(root, 'l1', 'deferred', reviewed_by='fixture reviewer')
    add_lesson(root, 'l3', 'same claim', applies_to='scope',
               evidence=['observation:o2'])
    item = load_project(root)['lessons']['l1']
    assert item['status'] == 'deferred' and len(item['previous_reviews']) == 1


# ------------------------------------------------ stage evidence (claim-based)

def _profiles_fixture(tmp_path, stages):
    payload = {'schema_version': 1, 'profiles': {
        'demo': {'version': 1, 'domain': 'demo', 'label': 'demo',
                 'entity_kinds': [], 'object_kinds': [], 'context_fields': [],
                 'prerequisites': [], 'stage_evidence': stages,
                 'result_checks': []}}}
    path = tmp_path / 'profiles.yaml'
    import yaml
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding='utf-8')
    return path


def test_stage_evidence_maps_registered_claims(tmp_path):
    from rwiki.domain_profiles import evaluate_profile
    root = project(tmp_path)
    profiles = _profiles_fixture(tmp_path, ['qc', 'clustering'])
    seed_run(root, stage='qc')
    add_observation(root, 'o1', 'clustering reviewed', stage='clustering',
                    basis='author_stated', value='true')
    state = load_project(root)
    result = evaluate_profile(state, 'demo', profiles_path=profiles)
    by_stage = {e['stage']: e for e in result['stage_evidence']}
    assert by_stage['qc']['evidence_state'] == 'recorded'
    qc_claims = by_stage['qc']['claims']
    assert any(c['ref'] == 'task:t1' and c['runs'][0]['status'] == 'completed'
               for c in qc_claims)
    assert by_stage['clustering']['evidence_state'] == 'recorded'
    assert any(c['ref'] == 'observation:o1' for c in by_stage['clustering']['claims'])
    # Nothing is asserted complete; claims are reported verbatim.
    assert '不据此认定' in by_stage['qc']['note']


def test_undeclared_stage_claims_surface_separately(tmp_path):
    from rwiki.domain_profiles import evaluate_profile
    root = project(tmp_path)
    profiles = _profiles_fixture(tmp_path, ['qc'])
    add_task(root, 't1', stage='unlisted-stage')
    result = evaluate_profile(load_project(root), 'demo', profiles_path=profiles)
    assert result['stage_evidence'][0]['evidence_state'] == 'not_recorded'
    assert result['undeclared_stage_claims'] == ['unlisted-stage']


# ------------------------------------------------- honest summary wording

def test_summary_separates_declared_from_rechecked(tmp_path):
    root = project(tmp_path)
    (root / 'ev.txt').write_text('evidence bytes\n', encoding='utf-8')
    add_observation(root, 'o1', 'qc passed', basis='verified', evidence='ev.txt',
                    value='true')
    summary = (state_dir(root) / 'summary.md').read_text(encoding='utf-8')
    assert '声明依据：verified 1' in summary
    assert '当前复核' in summary and '证据可核对 1' in summary
    assert '声明≠已核查' in summary
    # A raw basis count must never be rendered as "已核查".
    assert '已核查 1' not in summary
    # Evidence bytes changed after registration -> recheck reports it.
    (root / 'ev.txt').write_text('changed\n', encoding='utf-8')
    add_observation(root, 'o2', 'second', basis='unknown')
    summary = (state_dir(root) / 'summary.md').read_text(encoding='utf-8')
    assert '证据字节已变化 1' in summary


# --------------------- observations see computed upstream artifact freshness

def test_observation_about_artifact_uses_propagated_freshness(tmp_path):
    root = project(tmp_path)
    seed_run(root)  # r1/t1: data.csv -> out.csv (artifact a1)
    artifact = next(a for a in load_project(root)['artifacts'].values()
                    if a['path'] == 'out.csv')
    (root / 'ev.txt').write_text('ok\n', encoding='utf-8')
    add_observation(root, 'o1', 'downstream output verified',
                    about=f"artifact:{artifact['id']}", basis='verified',
                    evidence='ev.txt', value='true')
    # Upstream data change -> a1 stale -> observation subject is *computed* stale,
    # not the artifact's unchanged bytes.
    (root / 'data.csv').write_text('v2-changed\n', encoding='utf-8')
    report = check_project(root)
    assert report['observations']['o1']['subject'] == 'stale'
    # And evaluate_profile demotes the claim below authoritative for the
    # observation checker (via the same computed report).
    from rwiki.domain_profiles import _obs_rank
    rank = _obs_rank(load_project(root)['observations']['o1'],
                     load_project(root), root, report=report)
    assert rank <= 1


# ------------------------------------------------------- change classes

def test_impact_style_only_vs_compute(tmp_path):
    root = project(tmp_path)
    seed_run(root)  # t1/r1: data.csv -> out.csv
    (root / 'style.json').write_text('{"palette": "native"}\n', encoding='utf-8')
    add_object(root, 'style-cfg', 'style', path='style.json',
               properties={'role': 'style'})
    add_task(root, 'render', inputs=['file:out.csv', 'object:style-cfg'])
    (root / 'fig.png').write_text('png-bytes\n', encoding='utf-8')
    record_run(root, 'r2', 'render', status='completed',
               command='Rscript render.R', code=['file:scripts/run.R'],
               outputs=['fig.png'], checks=['png written'])
    # Style-only change: render is affected for re-render, analysis untouched.
    report = impact_analysis(root, ['object:style-cfg'])
    effects = {t['id']: t['effect'] for t in report['tasks']}
    assert effects == {'render': 'style_only'}
    classes = {d['id']: d['change_class'] for d in report['direct']}
    assert all(v == 'style' for v in classes.values())
    state = mark_stale(root, report)
    fig = next(a for a in state['artifacts'].values() if a['path'] == 'fig.png')
    assert fig['freshness']['state'] == 'stale'
    assert '样式类输入' in fig['freshness']['reason']
    out = next(a for a in state['artifacts'].values() if a['path'] == 'out.csv')
    assert out['freshness']['state'] == 'current'  # analysis output unaffected


def test_impact_data_change_marks_compute(tmp_path):
    root = project(tmp_path)
    seed_run(root)
    (root / 'style.json').write_text('{}\n', encoding='utf-8')
    add_object(root, 'style-cfg', 'style', path='style.json',
               properties={'role': 'style'})
    add_task(root, 'render', inputs=['file:out.csv', 'object:style-cfg'])
    (root / 'fig.png').write_text('png\n', encoding='utf-8')
    record_run(root, 'r2', 'render', status='completed',
               command='Rscript render.R', code=['file:scripts/run.R'],
               outputs=['fig.png'], checks=['ok'])
    report = impact_analysis(root, ['file:data.csv'])
    effects = {t['id']: t['effect'] for t in report['tasks']}
    assert effects.get('t1') == 'compute'
    assert effects.get('render') == 'compute'
    # Mixed style+data change is never downgraded to style_only.
    report = impact_analysis(root, ['file:data.csv', 'object:style-cfg'])
    effects = {t['id']: t['effect'] for t in report['tasks']}
    assert effects.get('render') == 'compute'


# ---------------------------------------------------------------- recovery

def _dead(pid):
    return 'dead'


def _live(pid):
    return 'live'


def _unknown(pid):
    return None


def test_recover_reports_and_repairs_with_verified_dead_lock(monkeypatch, tmp_path):
    from rwiki import project_state as ps
    monkeypatch.setattr(ps, '_pid_liveness', _dead)
    root = project(tmp_path)
    directory = state_dir(root)
    (directory / 'project.lock').write_text('424242', encoding='utf-8')
    (directory / 'project.json.tmp').write_text('{}', encoding='utf-8')
    orphan = directory / 'runs' / 'ghost'
    orphan.mkdir(parents=True)
    (orphan / 'receipt.json').write_text('{"run_id": "ghost"}', encoding='utf-8')
    # Read-only default: inspects and changes nothing.
    report = recover_project(root)
    assert report['lock']['present'] and report['lock']['pid'] == 424242
    assert report['lock']['liveness'] == 'dead'
    assert 'project.json.tmp' in report['staging_tmps']
    assert report['orphan_receipts'][0]['dir'].endswith('ghost')
    assert (directory / 'project.lock').is_file() and orphan.is_dir()
    # Repairs: lock released only with a verifiably dead pid; evidence kept.
    report = recover_project(root, release_lock=True)
    assert not (directory / 'project.lock').exists()
    assert any('释放锁' in a for a in report['actions'])
    report = recover_project(root, clean_staging=True, clean_orphans=True)
    quarantine = directory / '_quarantine'
    assert quarantine.is_dir()  # retained, inspectable — never deleted
    assert list(quarantine.rglob('project.json.tmp'))
    assert list(quarantine.rglob('receipt.json'))
    assert not orphan.is_dir()


def test_recover_refuses_release_when_live_or_unknown(monkeypatch, tmp_path):
    from rwiki import project_state as ps
    root = project(tmp_path)
    directory = state_dir(root)
    for liveness in (_live, _unknown):
        monkeypatch.setattr(ps, '_pid_liveness', liveness)
        (directory / 'project.lock').write_text('1234', encoding='utf-8')
        report = recover_project(root, release_lock=True)
        assert (directory / 'project.lock').is_file()
        assert any('拒绝释放锁' in c for c in report['cautions'])
        (directory / 'project.lock').unlink()


def test_recover_refuses_malformed_and_nonpositive_locks(tmp_path):
    root = project(tmp_path)
    directory = state_dir(root)
    for content in ('garbage', '', '-1', '0'):
        (directory / 'project.lock').write_text(content, encoding='utf-8')
        report = recover_project(root, release_lock=True)
        assert (directory / 'project.lock').is_file(), content
        assert report['lock']['liveness'] == 'unknown'
        assert any('拒绝释放锁' in c for c in report['cautions'])
        (directory / 'project.lock').unlink()


def test_recover_aborts_when_lock_replaced_mid_check(monkeypatch, tmp_path):
    from rwiki import project_state as ps
    monkeypatch.setattr(ps, '_pid_liveness', _dead)
    root = project(tmp_path)
    directory = state_dir(root)
    (directory / 'project.lock').write_text('111', encoding='utf-8')
    # Simulate a replacement: swap content between the two identity reads.
    real_read = Path.read_bytes
    calls = [0]

    def swap(self):
        calls[0] += 1
        if calls[0] == 2 and self.name == 'project.lock':
            return b'222'
        return real_read(self)

    monkeypatch.setattr(Path, 'read_bytes', swap)
    report = recover_project(root, release_lock=True)
    assert (directory / 'project.lock').is_file()
    assert any('被替换' in c or '拒绝释放' in c for c in report['cautions'])


def test_recover_running_run_blocks_all_mutations(monkeypatch, tmp_path):
    from rwiki import project_state as ps
    monkeypatch.setattr(ps, '_pid_liveness', _dead)
    root = project(tmp_path)
    (root / 'data.csv').write_text('v1\n', encoding='utf-8')
    add_task(root, 't1', inputs=['file:data.csv'])
    record_run(root, 'r1', 't1', status='running')
    directory = state_dir(root)
    (directory / 'project.lock').write_text('4242', encoding='utf-8')
    (directory / 'x.tmp').write_text('{}', encoding='utf-8')
    report = recover_project(root, release_lock=True, clean_staging=True)
    assert report['running_runs'][0]['run'] == 'r1'
    assert (directory / 'project.lock').is_file()   # lock untouched
    assert (directory / 'x.tmp').is_file()          # staging untouched
    assert any('running' in c and '拒绝' in c for c in report['cautions'])
    assert load_project(root)['runs']['r1']['status'] == 'running'


def test_recover_refuses_cleanup_under_held_lock(tmp_path):
    root = project(tmp_path)
    directory = state_dir(root)
    (directory / 'project.lock').write_text('1', encoding='utf-8')
    (directory / 'x.tmp').write_text('{}', encoding='utf-8')
    report = recover_project(root, clean_staging=True)
    assert (directory / 'x.tmp').is_file()
    assert any('锁文件仍存在' in c or '拒绝清理' in c for c in report['cautions'])


def test_recover_read_only_leaves_bytes_unchanged(tmp_path):
    root = project(tmp_path)
    directory = state_dir(root)
    (directory / 'project.lock').write_text('999999', encoding='utf-8')
    before = {p: p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    report = recover_project(root)  # no repair flags -> must not modify state
    after = {p: p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    assert before == after
    assert report['lock']['present']


def test_recover_skips_symlinked_cleanup_targets(tmp_path, monkeypatch):
    root = project(tmp_path)
    directory = state_dir(root)
    outside = tmp_path / 'outside.txt'
    outside.write_text('keep me\n', encoding='utf-8')
    link = directory / 'escape.tmp'
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip('symlink creation not permitted on this platform')
    report = recover_project(root, clean_staging=True)
    assert outside.read_text() == 'keep me\n'  # external target untouched
    assert link.is_symlink()                   # link not followed/deleted
    assert any('越界或为链接' in c for c in report['cautions'])


def test_recover_reports_missing_summary(tmp_path):
    root = project(tmp_path)
    (state_dir(root) / 'summary.md').unlink()
    report = recover_project(root)
    assert report['summary_present'] is False
    assert any('summary.md' in c for c in report['cautions'])


def test_recover_preserves_replacement_writer_lock(monkeypatch, tmp_path):
    """A 'dead' verdict scoped to the recorded pid must never release a lock
    that a *different* owner wrote during the liveness probe itself."""
    from rwiki import project_state as ps
    root = project(tmp_path)
    lock = state_dir(root) / 'project.lock'
    lock.write_text('12345', encoding='utf-8')

    def probe(pid):
        lock.write_text('54321', encoding='utf-8')  # replacement writer arrives
        return 'dead'  # refers only to the recorded 12345
    monkeypatch.setattr(ps, '_pid_liveness', probe)
    report = recover_project(root, release_lock=True)
    assert lock.is_file() and lock.read_text() == '54321'
    assert any('被替换' in c or '拒绝释放' in c for c in report['cautions'])


def test_recover_quarantine_is_idempotent(tmp_path):
    """Retained evidence must not be re-classified as active staging."""
    root = project(tmp_path)
    directory = state_dir(root)
    (directory / 'uncommitted.tmp').write_text('retain evidence', encoding='utf-8')
    report = recover_project(root, clean_staging=True)
    assert not report['staging_tmps']
    retained = list((directory / '_quarantine').rglob('*.tmp'))
    assert len(retained) == 1 and retained[0].read_text() == 'retain evidence'
    before = {str(p.relative_to(directory)): p.read_bytes() for p in retained}
    recover_project(root, clean_staging=True)
    after = {str(p.relative_to(directory)): p.read_bytes()
             for p in (directory / '_quarantine').rglob('*.tmp')}
    assert after == before


def test_recover_reloads_state_under_lock(monkeypatch, tmp_path):
    """A run committed between the initial read and lock acquisition must not
    have its receipt quarantined as orphan."""
    from rwiki import project_state as ps
    root = project(tmp_path)
    (root / 'input.csv').write_text('v\n1\n', encoding='utf-8')
    (root / 'code.R').write_text('# fixture\n', encoding='utf-8')
    (root / 'out.csv').write_text('v\n2\n', encoding='utf-8')
    add_task(root, 'task1', inputs=['file:input.csv'])
    original = ps.load_project
    fired = [False]

    def scheduled_load(path):
        state = original(path)
        if not fired[0]:
            fired[0] = True
            record_run(root, 'legit', 'task1', status='completed',
                       command='Rscript code.R', code=['file:code.R'],
                       outputs=['out.csv'], checks=['fixture checked'])
        return state

    monkeypatch.setattr(ps, 'load_project', scheduled_load)
    recover_project(root, clean_orphans=True)
    monkeypatch.undo()
    state = original(root)
    receipt = state_dir(root) / state['runs']['legit']['receipt']
    assert receipt.is_file(), 'receipt committed mid-recovery was quarantined'


def test_task_scope_cannot_borrow_unrelated_objects(tmp_path):
    """A task with only file: inputs must not satisfy object prerequisites by
    borrowing every project object."""
    from rwiki.domain_profiles import evaluate_profile
    root = project(tmp_path)
    seed_run(root)
    (root / 'unrelated.bin').write_bytes(b'unrelated expression dataset')
    add_object(root, 'unrelated', 'matrix', path='unrelated.bin',
               basis='verified',
               properties={'assay': 'expression', 'organism': 'mouse',
                           'id_system': 'symbol'})
    report = evaluate_profile(load_project(root), 'bioinformatics_single_cell',
                              subject='task:t1')
    check = next(c for c in report['checks'] if c['id'] == 'expression_object')
    assert check['state'] != 'satisfied'


def test_observation_object_alias_respects_upstream_stale(tmp_path):
    """An object sharing a produced artifact's path inherits the artifact's
    computed staleness — upstream change cannot hide behind unchanged bytes."""
    from rwiki.domain_profiles import evaluate_profile
    root = project(tmp_path)
    seed_run(root)  # r1: data.csv -> out.csv artifact
    add_object(root, 'outalias', 'matrix', path='out.csv', basis='verified')
    add_task(root, 'downstream', inputs=['object:outalias'])
    (root / 'evidence.txt').write_text('design inspected for original output',
                                      encoding='utf-8')
    add_observation(root, 'design', 'design_defined', about='object:outalias',
                    basis='verified', value='true', evidence='evidence.txt')
    (root / 'data.csv').write_text('v\n99\n', encoding='utf-8')
    report = evaluate_profile(load_project(root), 'bioinformatics_single_cell',
                              subject='task:downstream')
    check = next(c for c in report['checks'] if c['id'] == 'design')
    assert check['state'] != 'satisfied'


# ---------------------------------------------------------------- save scope

def test_save_commits_only_wiki_subtree(workspace, tmp_path):
    """A wiki living inside a dirty outer repo must never commit siblings."""
    config, _ = workspace
    wiki = config.wiki_root
    # Convert the standalone wiki repo into a subdir of a larger repo.
    (wiki / '.git').rename(tmp_path / 'removed-git')
    (tmp_path / '.gitignore').write_text('removed-git/\n', encoding='utf-8')
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t',
                    'commit', '-qm', 'baseline'], cwd=tmp_path, check=True)
    # Sibling work outside the wiki: one staged, one untracked, one modified.
    (tmp_path / 'tracked.md').write_text('base\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'tracked.md'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t',
                    'commit', '-qm', 'baseline2'], cwd=tmp_path, check=True)
    (tmp_path / 'plan.md').write_text('planning\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'plan.md'], cwd=tmp_path, check=True)
    (tmp_path / 'tracked.md').write_text('modified\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'tracked.md'], cwd=tmp_path, check=True)
    (tmp_path / 'scratch.txt').write_text('untracked\n', encoding='utf-8')
    # New wiki page + save: only wiki/* enters the commit.
    (wiki / 'projects').mkdir(exist_ok=True)
    (wiki / 'projects' / 'p.md').write_text('# p\n', encoding='utf-8')
    from rwiki.store import save
    save(config, 'scoped save')
    out = subprocess.check_output(['git', 'status', '--porcelain'],
                                  cwd=tmp_path, text=True)
    # Sibling staged work stays staged-and-uncommitted; untracked stays untracked.
    assert 'A  plan.md' in out and 'M  tracked.md' in out
    assert '?? scratch.txt' in out
    shown = subprocess.check_output(
        ['git', 'show', '--name-only', '--format=', 'HEAD'],
        cwd=tmp_path, text=True)
    paths = [l for l in shown.splitlines() if l.strip()]
    assert paths and all(p.startswith('wiki/') for p in paths)
    assert 'wiki/projects/p.md' in paths


def test_save_noop_when_only_siblings_dirty(workspace, tmp_path):
    config, _ = workspace
    wiki = config.wiki_root
    (wiki / '.git').rename(tmp_path / 'removed-git')
    (tmp_path / '.gitignore').write_text('removed-git/\n', encoding='utf-8')
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t',
                    'commit', '-qm', 'baseline'], cwd=tmp_path, check=True)
    from conftest import commit_count
    (tmp_path / 'outside.md').write_text('sibling work\n', encoding='utf-8')
    from rwiki.store import save
    save(config, 'nothing wiki-side')
    # No wiki-subtree change -> no commit, and the sibling stays untracked.
    assert commit_count(wiki) == 1
    out = subprocess.check_output(['git', 'status', '--porcelain'],
                                  cwd=tmp_path, text=True)
    assert '?? outside.md' in out


# ---------------------------------------------------------------- CLI smoke

def test_cli_lessons_and_recover(workspace, tmp_path):
    config, config_path = workspace
    root = project(tmp_path)
    seed_run(root)
    result = run_cli(config_path, 'project', 'add-lesson', '--root', str(root),
                     '--id', 'l1', '--claim', 'dedup keeps one draft',
                     '--evidence', 'run:r1')
    # scoped drafts require --applies-to (argparse rejects before any write)
    assert result.returncode != 0 and '--applies-to' in result.stderr
    result = run_cli(config_path, 'project', 'add-lesson', '--root', str(root),
                     '--id', 'l1', '--claim', 'dedup keeps one draft',
                     '--evidence', 'run:r1',
                     '--applies-to', 'this fixture only')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['lesson_id'] == 'l1'
    result = run_cli(config_path, 'project', 'lesson-review', '--root', str(root),
                     '--id', 'l1', '--state', 'deferred',
                     '--by', 'test-review（隔离夹具）')
    assert result.returncode == 0, result.stderr
    # accepted via CLI requires a registered decision record.
    result = run_cli(config_path, 'project', 'lesson-review', '--root', str(root),
                     '--id', 'l1', '--state', 'accepted',
                     '--by', 'test-review（隔离夹具）')
    assert result.returncode == 1 and '--decision' in result.stderr
    result = run_cli(config_path, 'project', 'add-decision', '--root', str(root),
                     '--id', 'd1', '--kind', 'other',
                     '--text', '作者批准该经验进入正式评审（隔离夹具）')
    assert result.returncode == 0, result.stderr
    result = run_cli(config_path, 'project', 'lesson-review', '--root', str(root),
                     '--id', 'l1', '--state', 'accepted',
                     '--by', 'test-review（隔离夹具）', '--decision', 'decision:d1')
    assert result.returncode == 0, result.stderr
    assert load_project(root)['lessons']['l1']['decision_ref'] == 'decision:d1'
    result = run_cli(config_path, 'project', 'recover', '--root', str(root))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['summary_present'] is True
    result = run_cli(config_path, 'project', 'add-task', '--root', str(root),
                     '--id', 't9', '--stage', 'qc')
    assert result.returncode == 0, result.stderr
    assert load_project(root)['tasks']['t9']['stage'] == 'qc'


def test_cli_record_method_use(workspace, tmp_path):
    config, config_path = workspace
    _write_method(config.wiki_root, 'score-method')
    root = project(tmp_path)
    seed_run(root, family='score-method', impl='impl')
    result = run_cli(config_path, 'record-method-use', '--method', 'score-method',
                     '--project', 'cli-study', '--title', 'CLI study',
                     '--project-root', str(root), '--run', 'r1')
    assert result.returncode == 0, result.stderr
    assert (config.wiki_root / 'projects/cli-study.md').is_file()
