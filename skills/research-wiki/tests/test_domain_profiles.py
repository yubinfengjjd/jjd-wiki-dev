"""Composable domain evidence/prerequisite profiles on the generic project state.

Profiles are specification fixtures: they declare which evidence a task needs,
not whether the corresponding algorithms are implemented or verified.
"""
from pathlib import Path

import pytest

from rwiki.domain_profiles import evaluate_profile, load_profiles, profile_ids
from rwiki.errors import WikiError
from rwiki.project_state import (
    add_entity, add_object, add_observation, init_project, load_project,
)


def project(tmp_path: Path) -> Path:
    (tmp_path / 'study').mkdir(exist_ok=True)
    return Path(init_project(tmp_path / 'study')['project_root'])


def test_all_named_domains_have_profiles():
    ids = profile_ids()
    for expected in ('bioinformatics_single_cell', 'bioinformatics_bulk_omics',
                     'deep_learning', 'radiomics', 'cadd', 'network_pharmacology',
                     'proteomics', 'metabolomics'):
        assert expected in ids, expected
    profiles = load_profiles()
    for pid, profile in profiles.items():
        assert profile['version'] >= 1
        assert profile['prerequisites'], pid
        assert profile['stage_evidence'], pid
        assert profile['result_checks'], pid


def test_empty_project_reports_unknown_not_unsatisfied(tmp_path):
    root = project(tmp_path)
    state = load_project(root)
    for pid in profile_ids():
        report = evaluate_profile(state, pid)
        assert report['profile'] == pid
        assert all(check['state'] == 'unknown' for check in report['checks']), pid


def test_object_and_observation_checks_satisfy(tmp_path):
    root = project(tmp_path)
    (root / 'data').mkdir()
    (root / 'data/m.rds').write_bytes(b'rds')
    add_object(root, 'expr', 'matrix', path='data/m.rds',
               properties={'assay': 'expression', 'organism': 'human', 'id_system': 'gene_symbol'})
    add_observation(root, 'obs-1', 'design_defined', value='true', basis='author_stated')
    add_observation(root, 'obs-2', 'donor_level_known', value='true', basis='author_stated')
    state = load_project(root)
    report = evaluate_profile(state, 'bioinformatics_single_cell')
    states = {c['id']: c for c in report['checks']}
    assert states['expression_object']['state'] == 'satisfied'
    assert states['expression_object']['basis'] == 'author_stated'
    assert states['design']['state'] == 'satisfied'
    assert states['donor_level']['state'] == 'satisfied'


def test_contradicted_evidence_is_unsatisfied(tmp_path):
    root = project(tmp_path)
    add_observation(root, 'obs-1', 'donor_level_known', value='false', basis='verified',
                    note='pseudobulk only, no donor column')
    state = load_project(root)
    report = evaluate_profile(state, 'bioinformatics_single_cell')
    states = {c['id']: c for c in report['checks']}
    assert states['donor_level']['state'] == 'unsatisfied'
    # Missing evidence remains unknown, not failed.
    assert states['expression_object']['state'] == 'unknown'


def test_verified_basis_outranks_author_stated(tmp_path):
    root = project(tmp_path)
    (root / 'data').mkdir()
    (root / 'data/m.rds').write_bytes(b'rds')
    add_object(root, 'a', 'matrix', path='data/m.rds',
               properties={'assay': 'expression', 'organism': 'human', 'id_system': 'ensg'},
               basis='author_stated')
    add_object(root, 'b', 'matrix', path='data/m.rds',
               properties={'assay': 'expression'}, basis='verified')
    report = evaluate_profile(load_project(root), 'bioinformatics_single_cell')
    expr = {c['id']: c for c in report['checks']}['expression_object']
    assert expr['state'] == 'satisfied'
    assert expr['basis'] == 'verified'


def test_deep_learning_and_radiomics_missing_prereqs(tmp_path):
    root = project(tmp_path)
    (root / 'data').mkdir()
    (root / 'data/imgs').mkdir()
    (root / 'data/imgs/one.png').write_bytes(b'png')
    add_object(root, 'imgs', 'image_set', path='data/imgs',
               properties={'role': 'dataset'})
    state = load_project(root)
    dl = {c['id']: c for c in evaluate_profile(state, 'deep_learning')['checks']}
    assert dl['dataset']['state'] == 'satisfied'
    assert dl['split_defined']['state'] == 'unknown'
    assert dl['model_or_weights']['state'] == 'unknown'
    assert dl['environment_recorded']['state'] == 'unknown'
    radio = {c['id']: c for c in evaluate_profile(state, 'radiomics')['checks']}
    assert radio['images']['state'] == 'satisfied'
    assert radio['roi_or_features']['state'] == 'unknown'


def test_cadd_and_network_profiles_are_composable(tmp_path):
    root = project(tmp_path)
    (root / 'lib').mkdir()
    (root / 'lib/cmp.sdf').write_bytes(b'sdf')
    add_object(root, 'cmp', 'compound_set', path='lib/cmp.sdf',
               properties={'role': 'compound'})
    add_object(root, 'rec', 'structure', path='lib/cmp.sdf',
               properties={'role': 'receptor', 'prepared': True})
    add_observation(root, 'o1', 'external_tool_declared', value='true', basis='author_stated')
    add_observation(root, 'o2', 'database_version_recorded', value='true', basis='author_stated')
    add_entity(root, 'targets', 'target_set', basis='author_stated')
    state = load_project(root)
    cadd = {c['id']: c for c in evaluate_profile(state, 'cadd')['checks']}
    assert cadd['compounds']['state'] == 'satisfied'
    assert cadd['receptor_or_training_data']['state'] == 'satisfied'
    assert cadd['tool_declared']['state'] == 'satisfied'
    net = {c['id']: c for c in evaluate_profile(state, 'network_pharmacology')['checks']}
    assert net['compounds_or_exposures']['state'] == 'satisfied'
    assert net['targets_or_phenotype']['state'] == 'satisfied'
    assert net['database_version']['state'] == 'satisfied'


def test_proteomics_and_metabolomics_profiles(tmp_path):
    root = project(tmp_path)
    (root / 'ms').mkdir()
    (root / 'ms/run1.mzML').write_bytes(b'mzml')
    (root / 'ms/features.csv').write_text('f,v\n', encoding='utf-8')
    add_object(root, 'pep', 'ms_processed', path='ms/run1.mzML',
               properties={'assay': 'peptide_abundance'})
    add_object(root, 'feat', 'feature_table', path='ms/features.csv',
               properties={'feature_type': 'mz_rt'})
    add_observation(root, 'o1', 'quantification_recorded', value='true', basis='author_stated')
    add_observation(root, 'o2', 'batch_recorded', value='true', basis='author_stated')
    state = load_project(root)
    prot = {c['id']: c for c in evaluate_profile(state, 'proteomics')['checks']}
    assert prot['ms_data_or_matrix']['state'] == 'satisfied'
    assert prot['quantification_info']['state'] == 'satisfied'
    assert prot['sample_batch']['state'] == 'satisfied'
    met = {c['id']: c for c in evaluate_profile(state, 'metabolomics')['checks']}
    assert met['features']['state'] == 'satisfied'
    assert met['annotation_status']['state'] == 'unknown'


def test_profiles_composable_on_one_state(tmp_path):
    root = project(tmp_path)
    state = load_project(root)
    # One project may mix domains; evaluation is per-profile and never merges axes.
    reports = {pid: evaluate_profile(state, pid) for pid in
               ('deep_learning', 'radiomics', 'metabolomics')}
    assert set(reports) == {'deep_learning', 'radiomics', 'metabolomics'}
    assert all('checks' in r for r in reports.values())


def test_unknown_profile_id_is_explicit_error(tmp_path):
    root = project(tmp_path)
    with pytest.raises(WikiError, match='profile|配置'):
        evaluate_profile(load_project(root), 'no_such_domain')


def test_match_properties_and_kind_lists(tmp_path):
    """Property matching: scalar equality, list membership, missing key -> no match."""
    root = project(tmp_path)
    (root / 'x').mkdir()
    (root / 'x/f.csv').write_text('a\n1\n', encoding='utf-8')
    add_object(root, 'feat', 'feature_table', path='x/f.csv',
               properties={'feature_type': 'mz_rt'})
    state = load_project(root)
    checks = {c['id']: c for c in evaluate_profile(state, 'metabolomics')['checks']}
    assert checks['features']['state'] == 'satisfied'
    # kind must match too
    add_object(root, 'plain', 'table', path='x/f.csv',
               properties={'feature_type': 'mz_rt'})
    # 'table' is not in the metabolomics features kind list: still satisfied via 'feat'.
    assert {c['id']: c for c in evaluate_profile(load_project(root), 'metabolomics')['checks']}['features']['state'] == 'satisfied'

# ------------------------------------------------ review-1 regression tests


def test_equal_tier_contradiction_is_conflicted_not_satisfied(tmp_path):
    root = project(tmp_path)
    # Same-tier positive/negative evidence must surface as conflicted with refs.
    add_observation(root, 'pos', 'design_defined', value='true', basis='author_stated')
    add_observation(root, 'neg', 'design_defined', value='false', basis='author_stated')
    check = {c['id']: c for c in
             evaluate_profile(load_project(root), 'bioinformatics_single_cell')['checks']}['design']
    assert check['state'] == 'conflicted'
    assert 'observation:pos' in check['evidence'] and 'observation:neg' in check['evidence']


def test_author_stated_positive_does_not_beat_verified_negative(tmp_path):
    root = project(tmp_path)
    (root / 'ev.txt').write_text('checked: no donor column', encoding='utf-8')
    add_observation(root, 'pos', 'design_defined', value='true', basis='author_stated')
    add_observation(root, 'neg', 'design_defined', value='false', basis='verified',
                    evidence='ev.txt')
    check = {c['id']: c for c in
             evaluate_profile(load_project(root), 'bioinformatics_single_cell')['checks']}['design']
    assert check['state'] == 'unsatisfied'
    assert 'observation:neg' in check['evidence']


def test_observation_about_other_object_is_not_universal_proof(tmp_path):
    root = project(tmp_path)
    (root / 'data').mkdir(exist_ok=True)
    (root / 'data/m.bin').write_bytes(b'x')
    (root / 'data/o.bin').write_bytes(b'y')
    add_object(root, 'matrix', 'matrix', path='data/m.bin',
               properties={'assay': 'expression'})
    add_object(root, 'other', 'matrix', path='data/o.bin')
    add_observation(root, 'other-design', 'design_defined', about='object:other',
                    value='true', basis='author_stated')
    report = evaluate_profile(load_project(root), 'bioinformatics_single_cell')
    check = {c['id']: c for c in report['checks']}['design']
    assert check['state'] != 'satisfied'
    # Scoped to 'other' the observation counts; scoped to 'matrix' it does not.
    scoped = evaluate_profile(load_project(root), 'bioinformatics_single_cell',
                              subject='object:other')
    assert {c['id']: c for c in scoped['checks']}['design']['state'] == 'satisfied'
    scoped_m = evaluate_profile(load_project(root), 'bioinformatics_single_cell',
                                subject='object:matrix')
    assert {c['id']: c for c in scoped_m['checks']}['design']['state'] != 'satisfied'


def test_subject_scope_keeps_context_coherent(tmp_path):
    root = project(tmp_path)
    (root / 'a.bin').write_bytes(b'a')
    (root / 'b.bin').write_bytes(b'b')
    # Two unrelated objects each holding complementary metadata: they must not
    # compose into a fake complete dataset under a scoped evaluation.
    add_object(root, 'mat', 'matrix', path='a.bin',
               properties={'assay': 'expression', 'organism': 'mouse'})
    add_object(root, 'side', 'matrix', path='b.bin',
               properties={'assay': 'expression', 'id_system': 'symbol'})
    scoped = evaluate_profile(load_project(root), 'bioinformatics_single_cell',
                              subject='object:mat')
    checks = {c['id']: c for c in scoped['checks']}
    # context_keys needs organism+id_system on the SAME subject object.
    assert checks['context_keys']['state'] != 'satisfied'


def test_deleted_object_no_longer_satisfies(tmp_path):
    root = project(tmp_path)
    (root / 'm.bin').write_bytes(b'x')
    add_object(root, 'mat', 'matrix', path='m.bin',
               properties={'assay': 'expression'}, basis='verified')
    (root / 'm.bin').unlink()
    report = evaluate_profile(load_project(root), 'bioinformatics_single_cell')
    assert {c['id']: c for c in report['checks']}['expression_object']['state'] != 'satisfied'


def test_declared_stages_are_not_evidence(tmp_path):
    root = project(tmp_path)
    report = evaluate_profile(load_project(root), 'deep_learning')
    assert report['declared_stages']
    assert all(s['evidence_state'] == 'not_recorded' for s in report['stage_evidence'])


def test_conditional_prerequisite_eval_only_deep_learning(tmp_path):
    root = project(tmp_path)
    (root / 'pred.csv').write_text('yhat\n1\n', encoding='utf-8')
    add_object(root, 'preds', 'table', path='pred.csv',
               properties={'role': 'predictions'})
    report = evaluate_profile(load_project(root), 'deep_learning')
    checks = {c['id']: c for c in report['checks']}
    assert checks['model_or_weights']['state'] == 'not_applicable'
    # And without predictions (training context), the requirement still applies.
    root2 = tmp_path / 'p2'
    root2.mkdir()
    init_project(root2)
    (root2 / 'tr.csv').write_text('y\n1\n', encoding='utf-8')
    add_object(root2, 'tr', 'dataset', path='tr.csv',
               properties={'role': 'dataset'})
    report2 = evaluate_profile(load_project(root2), 'deep_learning')
    assert {c['id']: c for c in report2['checks']}['model_or_weights']['state'] == 'unknown'


def test_ligand_only_cadd_waives_receptor_only_when_declared(tmp_path):
    root = project(tmp_path)
    (root / 'lib.sdf').write_bytes(b'sdf')
    add_object(root, 'cmp', 'compound_set', path='lib.sdf',
               properties={'role': 'compound'})
    report = evaluate_profile(load_project(root), 'cadd')
    assert {c['id']: c for c in report['checks']}['receptor_or_training_data']['state'] == 'unknown'
    add_observation(root, 'lo', 'ligand_only_declared', value='true', basis='author_stated')
    report = evaluate_profile(load_project(root), 'cadd')
    assert {c['id']: c for c in report['checks']}['receptor_or_training_data']['state'] == 'not_applicable'


# ------------------------------------------------ review-2 regression tests

def _conditional_profile(tmp_path):
    import yaml
    profile = dict(load_profiles()['deep_learning'])
    profile['prerequisites'] = [
        {'id': 'conditional_weights', 'type': 'object',
         'match': {'kind': 'weights'},
         'when': {'type': 'observation', 'match': {'claim': 'training_requested'}}}]
    spec = tmp_path / 'profiles.yaml'
    spec.write_text(yaml.safe_dump(
        {'schema_version': 1, 'profiles': {'conditional_test': profile}}),
        encoding='utf-8')
    return spec


def test_when_gate_never_exempts_on_unknown_evidence(tmp_path):
    """Unknown ``when`` evidence leaves the prerequisite evaluated
    conservatively; it is never treated as not_applicable."""
    root = project(tmp_path)
    spec = _conditional_profile(tmp_path)
    check = evaluate_profile(load_project(root), 'conditional_test',
                             profiles_path=spec)['checks'][0]
    assert check['state'] == 'unknown'


def test_when_gate_never_exempts_on_conflicted_evidence(tmp_path):
    """Conflicted condition evidence is not an explicit false either."""
    root = project(tmp_path)
    spec = _conditional_profile(tmp_path)
    add_observation(root, 'w1', 'training_requested', value='true', basis='author_stated')
    add_observation(root, 'w2', 'training_requested', value='false', basis='author_stated')
    check = evaluate_profile(load_project(root), 'conditional_test',
                             profiles_path=spec)['checks'][0]
    assert check['state'] != 'not_applicable'


def test_when_gate_exempts_only_on_explicit_false(tmp_path):
    root = project(tmp_path)
    spec = _conditional_profile(tmp_path)
    add_observation(root, 'w3', 'training_requested', value='false', basis='author_stated')
    check = evaluate_profile(load_project(root), 'conditional_test',
                             profiles_path=spec)['checks'][0]
    assert check['state'] == 'not_applicable'
    # Explicit truth keeps the requirement applicable (still unknown, not exempt).
    root2 = tmp_path / 'p2'
    root2.mkdir()
    init_project(root2)
    add_observation(root2, 'w4', 'training_requested', value='true', basis='author_stated')
    check = evaluate_profile(load_project(root2), 'conditional_test',
                             profiles_path=spec)['checks'][0]
    assert check['state'] == 'unknown'


def test_stale_observation_evidence_drops_verified_claim(tmp_path):
    """Changed evidence bytes invalidate a verified observation — the same
    freshness check_project reports; evaluate and check must agree."""
    root = project(tmp_path)
    (root / 'ev.txt').write_text('design v1', encoding='utf-8')
    add_observation(root, 'o1', 'design_defined', value='true',
                    basis='verified', evidence='ev.txt')
    state = {c['id']: c for c in evaluate_profile(
        load_project(root), 'bioinformatics_single_cell')['checks']}['design']['state']
    assert state == 'satisfied'
    (root / 'ev.txt').write_text('design v2 - replaced', encoding='utf-8')
    check = {c['id']: c for c in evaluate_profile(
        load_project(root), 'bioinformatics_single_cell')['checks']}['design']
    assert check['state'] != 'satisfied'
