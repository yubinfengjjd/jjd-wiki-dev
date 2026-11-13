"""Explicit bindings: author files stay unchanged; only declared mapping and non-aggregating reshape happen."""
import csv
import hashlib
import json
import os
import subprocess

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from conftest import SKILL_ROOT, run_cli, update_gallery, write_interface
from rwiki.server import create_app
from test_templates import approved, fake_template  # noqa: F401  (shared execution fixtures)
from rwiki.errors import WikiError
from rwiki.input_binding import BindingError, prepare_tables, reshape_records
from rwiki.interfaces import load_interface
from rwiki.spec import check_data, load_spec, requirements_markdown


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def bound(workspace):
    config, _ = workspace
    write_interface(config.wiki_root, 'render-dotplot-long', {
        'group': {'type': 'str', 'description': '细胞类型'},
        'feature': {'type': 'str', 'description': '基因'},
        'avg_expression': {'type': 'float', 'description': '平均表达'},
        'pct_expressed': {'type': 'float', 'description': '阳性细胞百分比，0–100'},
        'target_group': {'type': 'str', 'description': '目标细胞类型', 'required': False},
    })
    columns = load_interface(config.wiki_root, 'render-dotplot-long')['columns']
    spec = {'language': 'r', 'entry': 'code/render.R', 'style': {},
            'tables': {'dotplot': {'interface': 'render-dotplot-long',
                                   'description': '点图', 'columns': columns}}}
    data = config.wiki_root.parent / 'data'
    data.mkdir()
    standard = data / 'render-dotplot-long.csv'
    standard.write_text('group,feature,avg_expression,pct_expressed,target_group\n'
                        'T,A,0.5,40,T\nT,B,0.8,70,B\n', encoding='utf-8')
    external = data / 'my_results.csv'
    external.write_text('cell_type,gene_symbol,mean_expr,positive_percent,target_cell_type\n'
                        'T,A,0.5,40,T\nT,B,0.8,70,B\n', encoding='utf-8')
    bindings = {'tables': {'dotplot': {'file': 'my_results.csv', 'columns': {
        'group': 'cell_type', 'feature': 'gene_symbol', 'avg_expression': 'mean_expr',
        'pct_expressed': 'positive_percent', 'target_group': 'target_cell_type'}}}}
    return config, spec, data, standard, external, bindings


def test_bindings_rewrite_only_the_internal_table(bound, tmp_path):
    config, spec, data, standard, external, bindings = bound
    before = digest(external)
    report = prepare_tables(spec, bindings, data, tmp_path / 'work')[0]
    header, rows = read_csv(tmp_path / 'work/render-dotplot-long.csv')
    assert header == read_csv(standard)[0]
    assert rows == read_csv(standard)[1]
    assert digest(external) == before
    assert report['source_file'] == 'my_results.csv'
    assert report['source_sha256'] == before
    assert report['mapping']['group'] == 'cell_type'
    assert 'numeric_values_parse' in report['checks']
    assert '不验证单位' in report['semantics']


def test_missing_required_field_names_the_gap(bound, tmp_path):
    _, spec, data, _, external, bindings = bound
    external.write_text('cell_type,mean_expr,positive_percent\nT,0.5,40\n', encoding='utf-8')
    bindings['tables']['dotplot']['columns'].pop('feature')
    bindings['tables']['dotplot']['columns'].pop('target_group')
    with pytest.raises(BindingError, match='feature'):
        prepare_tables(spec, bindings, data, tmp_path / 'work')


def test_optional_column_may_be_omitted_only_when_the_interface_declares_it(bound, tmp_path):
    _, spec, data, _, external, bindings = bound
    external.write_text('cell_type,gene_symbol,mean_expr,positive_percent\nT,A,0.5,40\n', encoding='utf-8')
    bindings['tables']['dotplot']['columns'].pop('target_group')
    report = prepare_tables(spec, bindings, data, tmp_path / 'work')[0]
    header, rows = read_csv(tmp_path / 'work/render-dotplot-long.csv')
    assert 'target_group' not in header
    assert report['omitted_optional'] == ['target_group']
    assert rows[0]['avg_expression'] == '0.5'


def test_extra_author_columns_are_preserved(bound, tmp_path):
    _, spec, data, _, external, bindings = bound
    external.write_text('cell_type,gene_symbol,mean_expr,positive_percent,target_cell_type,cluster\n'
                        'T,A,0.5,40,T,c1\n', encoding='utf-8')
    report = prepare_tables(spec, bindings, data, tmp_path / 'work')[0]
    header, rows = read_csv(tmp_path / 'work/render-dotplot-long.csv')
    assert header[-1] == 'cluster' and rows[0]['cluster'] == 'c1'
    assert report['extras_preserved'] == ['cluster']


@pytest.mark.parametrize('change, message', [
    ({'file': '../outside.csv'}, '越界'),
    ({'file': 'C:/outside.csv'}, '越界'),
    ({'file': 'https://example.com/x.csv'}, '网络'),
    ({'file': 'missing.csv'}, '不存在'),
    ({'columns': {'bogus': 'cell_type'}}, '未知字段'),
    ({'columns': {'group': 'same', 'feature': 'same'}}, '重复'),
    ({'file': 'my_results.csv', 'extra_key': 1}, '不支持字段'),
])
def test_invalid_bindings_fail_before_execution(bound, tmp_path, change, message):
    _, spec, data, _, _, bindings = bound
    bindings['tables']['dotplot'].update(change)
    with pytest.raises(BindingError, match=message):
        prepare_tables(spec, bindings, data, tmp_path / 'work')


def test_unknown_table_and_duplicate_source_header_fail(bound, tmp_path):
    _, spec, data, _, external, bindings = bound
    bad = {'tables': {'other': bindings['tables']['dotplot']}}
    with pytest.raises(BindingError, match='未知表'):
        prepare_tables(spec, bad, data, tmp_path / 'work')
    (data / 'dup.csv').write_text('a,a\n1,2\n', encoding='utf-8')
    bindings['tables']['dotplot']['file'] = 'dup.csv'
    with pytest.raises(BindingError, match='重复列名'):
        prepare_tables(spec, bindings, data, tmp_path / 'work')


def test_bad_numeric_value_never_becomes_a_silent_zero(bound, tmp_path):
    _, spec, data, _, external, bindings = bound
    external.write_text('cell_type,gene_symbol,mean_expr,positive_percent,target_cell_type\n'
                        'T,A,high,40,T\n', encoding='utf-8')
    with pytest.raises(BindingError, match='mean_expr.*high'):
        prepare_tables(spec, bindings, data, tmp_path / 'work')


def test_percent_scale_is_reported_not_converted(bound, tmp_path):
    _, spec, data, _, external, bindings = bound
    external.write_text('cell_type,gene_symbol,mean_expr,positive_percent,target_cell_type\n'
                        'T,A,0.5,0.4,T\n', encoding='utf-8')
    report = prepare_tables(spec, bindings, data, tmp_path / 'work')[0]
    assert any('0–100' in warning and 'positive_percent' in warning for warning in report['warnings'])
    _, rows = read_csv(tmp_path / 'work/render-dotplot-long.csv')
    assert rows[0]['pct_expressed'] == '0.4'  # never multiplied by 100


def test_0_100_description_does_not_masquerade_as_0_1(bound, tmp_path):
    _, spec, data, _, external, bindings = bound
    external.write_text('cell_type,gene_symbol,mean_expr,positive_percent,target_cell_type\n'
                        'T,A,0.5,40,T\n', encoding='utf-8')
    report = prepare_tables(spec, bindings, data, tmp_path / 'work')[0]
    assert report['warnings'] == []


def test_melt_is_explicit_and_does_not_aggregate():
    header = ['gene', 'g1', 'g2']
    rows = [{'gene': 'A', 'g1': '1', 'g2': '2'}]
    out_header, out_rows, operation = reshape_records(header, rows, {
        'op': 'melt', 'id': ['gene'], 'variables': ['g1', 'g2'],
        'variable_name': 'group', 'value_name': 'value'})
    assert out_header == ['gene', 'group', 'value']
    assert out_rows == [{'gene': 'A', 'group': 'g1', 'value': '1'},
                        {'gene': 'A', 'group': 'g2', 'value': '2'}]
    assert operation['op'] == 'melt' and operation['aggregation'] is False
    assert operation['dropped_columns'] == []
    _, _, dropped = reshape_records(['gene', 'g1', 'note'], [{'gene': 'A', 'g1': '1', 'note': 'x'}], {
        'op': 'melt', 'id': ['gene'], 'variables': ['g1'],
        'variable_name': 'group', 'value_name': 'value'})
    assert dropped['dropped_columns'] == ['note']


def test_pivot_rejects_duplicate_keys_and_never_averages():
    header = ['gene', 'group', 'value']
    rows = [{'gene': 'A', 'group': 'g1', 'value': '1'},
            {'gene': 'A', 'group': 'g2', 'value': '2'},
            {'gene': 'A', 'group': 'g1', 'value': '3'}]
    with pytest.raises(BindingError, match='重复键'):
        reshape_records(header, rows, {'op': 'pivot', 'index': ['gene'],
                                       'columns': 'group', 'values': 'value'})
    out_header, out_rows, operation = reshape_records(header, rows[:2], {
        'op': 'pivot', 'index': ['gene'], 'columns': 'group', 'values': 'value'})
    assert out_header == ['gene', 'g1', 'g2']
    assert out_rows == [{'gene': 'A', 'g1': '1', 'g2': '2'}]
    assert operation['aggregation'] is False


def test_output_never_overwrites_source_when_work_dir_is_data_root(workspace, tmp_path):
    config, _ = workspace
    columns = {'value': {'type': 'int', 'description': '计数'}}
    spec = {'tables': {'values': {'interface': 'values', 'description': 'x', 'columns': columns}}}
    data = tmp_path / 'data'
    data.mkdir()
    source = data / 'values.csv'
    source.write_text('n\r\n2\r\n', encoding='utf-8', newline='')
    before = source.read_bytes()
    bindings = {'tables': {'values': {'file': 'values.csv', 'columns': {'value': 'n'}}}}
    with pytest.raises(BindingError, match='覆盖源文件'):
        prepare_tables(spec, bindings, data, data)
    assert source.read_bytes() == before
    assert list(data.glob('.binding-stage-*')) == []


def test_output_cannot_alias_source_via_hardlink(workspace, tmp_path):
    config, _ = workspace
    columns = {'value': {'type': 'int', 'description': '计数'}}
    spec = {'tables': {'values': {'interface': 'alias', 'description': 'x', 'columns': columns}}}
    data = tmp_path / 'data'
    data.mkdir()
    source = data / 'values.csv'
    source.write_text('n\n2\n', encoding='utf-8')
    try:
        os.link(source, data / 'alias.csv')
    except OSError:
        pytest.skip('hard links are not available on this filesystem')
    before = source.read_bytes()
    bindings = {'tables': {'values': {'file': 'values.csv', 'columns': {'value': 'n'}}}}
    with pytest.raises(BindingError, match='覆盖源文件'):
        prepare_tables(spec, bindings, data, data)
    assert source.read_bytes() == before


def test_output_never_overwrites_another_tables_source(workspace, tmp_path):
    config, _ = workspace
    columns = {'value': {'type': 'int', 'description': '计数'}}
    spec = {'tables': {
        'first': {'interface': 'first-out', 'description': 'x', 'columns': columns},
        'second': {'interface': 'second-out', 'description': 'x', 'columns': columns},
    }}
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'first.csv').write_text('value\n1\n', encoding='utf-8')
    (data / 'first-out.csv').write_text('value\n2\n', encoding='utf-8')
    bindings = {'tables': {
        'first': {'file': 'first.csv', 'columns': {}},
        'second': {'file': 'first-out.csv', 'columns': {}},
    }}
    before = (data / 'first-out.csv').read_bytes()
    with pytest.raises(BindingError, match='覆盖源文件'):
        prepare_tables(spec, bindings, data, data)
    assert (data / 'first-out.csv').read_bytes() == before


def test_failed_write_leaves_no_partial_canonical_output(workspace, tmp_path, monkeypatch):
    import rwiki.input_binding as binding
    config, _ = workspace
    columns = {'value': {'type': 'int', 'description': '计数'}}
    spec = {'tables': {
        'a': {'interface': 'a-out', 'description': 'x', 'columns': columns},
        'b': {'interface': 'b-out', 'description': 'x', 'columns': columns},
    }}
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'a.csv').write_text('value\n1\n', encoding='utf-8')
    (data / 'b.csv').write_text('value\n2\n', encoding='utf-8')
    work = tmp_path / 'work'
    bindings = {'tables': {'a': {'file': 'a.csv', 'columns': {}},
                           'b': {'file': 'b.csv', 'columns': {}}}}
    original = binding.os.replace
    calls = {'count': 0}

    def failing(source, target):
        calls['count'] += 1
        if calls['count'] == 2:
            raise OSError('simulated write failure')
        return original(source, target)

    monkeypatch.setattr(binding.os, 'replace', failing)
    with pytest.raises(OSError, match='simulated'):
        prepare_tables(spec, bindings, data, work)
    assert not (work / 'a-out.csv').exists()
    assert not (work / 'b-out.csv').exists()
    assert (data / 'a.csv').read_text(encoding='utf-8') == 'value\n1\n'
    assert (data / 'b.csv').read_text(encoding='utf-8') == 'value\n2\n'
    assert list(work.glob('.binding-stage-*')) == []


def test_effective_mapping_cannot_reuse_one_source_column(tmp_path):
    columns = {'group': {'type': 'str', 'description': '分组'},
               'feature': {'type': 'str', 'description': '基因'}}
    with pytest.raises(BindingError, match='同一来源列'):
        from rwiki.input_binding import map_records
        map_records(['feature'], [{'feature': 'CD3'}], columns, {'group': 'feature'})


def test_pivot_preserves_index_values_including_carriage_return_and_empty():
    header = ['a', 'b', 'group', 'value']
    rows = [{'a': 'x\ry', 'b': 'z', 'group': 'g1', 'value': '1'},
            {'a': '', 'b': 'q', 'group': 'g1', 'value': '2'}]
    out_header, out_rows, operation = reshape_records(header, rows, {
        'op': 'pivot', 'index': ['a', 'b'], 'columns': 'group', 'values': 'value'})
    assert out_header == ['a', 'b', 'g1']
    assert out_rows == [{'a': 'x\ry', 'b': 'z', 'g1': '1'},
                        {'a': '', 'b': 'q', 'g1': '2'}]
    assert operation['missing_cells'] == 0
    with pytest.raises(BindingError, match='重复键'):
        reshape_records(header, rows + [rows[0]], {'op': 'pivot', 'index': ['a', 'b'],
                                                   'columns': 'group', 'values': 'value'})
    with pytest.raises(BindingError, match='空值'):
        reshape_records(header, [{'a': 'x', 'b': 'z', 'group': '', 'value': '1'}],
                        {'op': 'pivot', 'index': ['a', 'b'], 'columns': 'group', 'values': 'value'})
    missing_header, missing_rows, _ = reshape_records(
        header, [{'a': None, 'b': 'm', 'group': 'g1', 'value': '3'}],
        {'op': 'pivot', 'index': ['a', 'b'], 'columns': 'group', 'values': 'value'})
    assert missing_rows == [{'a': None, 'b': 'm', 'g1': '3'}]


def test_unknown_reshape_options_fail(bound):
    _, _, _, _, _, _ = bound
    with pytest.raises(BindingError, match='reshape'):
        reshape_records(['a'], [{'a': '1'}], {'op': 'melt', 'id': [], 'variables': ['a'],
                                              'variable_name': 'k', 'value_name': 'v', 'aggregate': 'mean'})


def test_standard_entry_still_needs_no_bindings(bound, tmp_path):
    _, spec, data, _, _, _ = bound
    check_data(spec, data)  # standard <interface>.csv path unchanged
    assert not (tmp_path / 'work').exists()


def test_optional_table_can_be_absent_but_required_table_cannot(workspace, tmp_path):
    config, _ = workspace
    write_interface(config.wiki_root, 'values', {'value': {'type': 'int', 'description': '计数'}})
    columns = load_interface(config.wiki_root, 'values')['columns']
    spec = {'tables': {
        'required': {'interface': 'values', 'description': '必需', 'columns': columns},
        'extra': {'interface': 'values-extra', 'description': '可选', 'required': False,
                  'columns': {'value': {'type': 'int', 'description': '计数'}}},
    }}
    data = config.wiki_root.parent / 'data'
    data.mkdir()
    (data / 'values.csv').write_text('value\n2\n', encoding='utf-8')
    reports = prepare_tables(spec, {'tables': {'required': {'file': 'values.csv', 'columns': {}}}},
                             data, tmp_path / 'work')
    assert [item['table_key'] for item in reports] == ['required']
    with pytest.raises(BindingError, match='required'):
        prepare_tables(spec, {'tables': {}}, data, tmp_path / 'work2')


@pytest.mark.r
def test_r_and_python_adapters_agree_on_the_same_fixture(bound, tmp_path):
    config, spec, data, _, external, bindings = bound
    external.write_text('cell_type,gene_symbol,mean_expr,positive_percent,target_cell_type,cluster\n'
                        'T,A,0.5,40,T,c1\nT,B,0.8,70,B,c1\n', encoding='utf-8')
    driver = __import__('pathlib').Path(__file__).with_name('r_input_binding_driver.R')
    for mode, without in (('full', None), ('optional', 'target_group')):
        declared = json.loads(json.dumps(bindings))
        if without:
            declared['tables']['dotplot']['columns'].pop(without)
        prepare_tables(spec, declared, data, tmp_path / f'python-{mode}')
        result = subprocess.run(
            [str(config.rscript_exe), str(driver), str(SKILL_ROOT / 'assets/input_binding.R'),
             str(data), str(tmp_path / f'r-{mode}'), mode],
            capture_output=True, text=True, encoding='utf-8', env=dict(os.environ))
        assert result.returncode == 0, result.stderr
        python_header, python_rows = read_csv(tmp_path / f'python-{mode}/render-dotplot-long.csv')
        r_header, r_rows = read_csv(tmp_path / f'r-{mode}/render-dotplot-long.csv')
        assert python_header == r_header
        assert python_rows == r_rows


@pytest.mark.r
@pytest.mark.parametrize('mode', ['overwrite', 'effective', 'pivot', 'boundary'])
def test_r_helper_rejects_the_review_cases(workspace, tmp_path, mode):
    config, _ = workspace
    probe = __import__('pathlib').Path(__file__).with_name('r_input_binding_probe.R')
    result = subprocess.run(
        [str(config.rscript_exe), str(probe), str(SKILL_ROOT / 'assets/input_binding.R'),
         mode, str(tmp_path / mode)],
        capture_output=True, text=True, encoding='utf-8', env=dict(os.environ))
    assert result.returncode == 0, result.stderr
    assert f'OK {mode}' in result.stdout


@pytest.mark.r
def test_r_without_fs_safely_replaces_hardlinked_output(workspace, tmp_path):
    config, _ = workspace
    root = tmp_path / 'root'
    out = tmp_path / 'out'
    root.mkdir()
    out.mkdir()
    source = root / 'source.csv'
    source.write_text('n\n2\n', encoding='utf-8')
    try:
        os.link(source, out / 'values.csv')
    except OSError:
        pytest.skip('hard links are not available on this filesystem')
    before = source.read_bytes()
    probe = __import__('pathlib').Path(__file__).with_name('r_input_binding_probe.R')
    env = dict(os.environ)
    env['RWIKI_DISABLE_FS'] = '1'
    result = subprocess.run(
        [str(config.rscript_exe), str(probe), str(SKILL_ROOT / 'assets/input_binding.R'),
         'nofs-hardlink', str(tmp_path)],
        capture_output=True, text=True, encoding='utf-8', env=env)
    assert result.returncode == 0, result.stderr
    assert 'OK nofs-hardlink' in result.stdout
    assert source.read_bytes() == before
    header, rows = read_csv(out / 'values.csv')
    assert header == ['value'] and rows == [{'value': '2'}]
    assert list(out.glob('*backup*')) == []


@pytest.mark.r
def test_r_pivot_matches_python_for_cr_and_empty_index_values(workspace, tmp_path):
    config, _ = workspace
    probe = __import__('pathlib').Path(__file__).with_name('r_input_binding_probe.R')
    work = tmp_path / 'pivot'
    result = subprocess.run(
        [str(config.rscript_exe), str(probe), str(SKILL_ROOT / 'assets/input_binding.R'),
         'pivot', str(work)],
        capture_output=True, text=True, encoding='utf-8', env=dict(os.environ))
    assert result.returncode == 0, result.stderr
    header = ['a', 'b', 'group', 'value']
    rows = [{'a': 'x\ry', 'b': 'z', 'group': 'g1', 'value': '1'},
            {'a': '', 'b': 'q', 'group': 'g1', 'value': '2'},
            {'a': 'dup', 'b': 'dup', 'group': 'g1', 'value': '3'}]
    python_header, python_rows, _ = reshape_records(header, rows, {
        'op': 'pivot', 'index': ['a', 'b'], 'columns': 'group', 'values': 'value'})
    r_header, r_rows = read_csv(work / 'pivot.csv')
    assert r_header == python_header
    assert r_rows == python_rows


def test_template_page_api_exposes_required_and_optional_contract(fake_template):
    config, _, target = fake_template
    write_interface(config.wiki_root, 'values', {
        'value': {'type': 'int', 'description': '计数'},
        'note': {'type': 'str', 'description': '备注', 'required': False}})
    with TestClient(create_app(config)) as client:
        page = client.get('/api/page', params={'path': f'templates/{target.name}.md'}).json()
    contract = page['input_contract']
    assert contract['bindings'] is True and len(contract['tables']) == 1
    table = contract['tables'][0]
    assert table['key'] == 'values' and table['interface'] == 'values' and table['required'] is True
    assert {column['name']: column['required'] for column in table['columns']} == {
        'value': True, 'note': False}


def test_cli_bindings_match_standard_python_render(fake_template, tmp_path):
    config, config_path, target = fake_template
    write_interface(config.wiki_root, 'values', {'value': {'type': 'int', 'description': '计数'},
                                                 'note': {'type': 'str', 'description': '备注', 'required': False}})
    standard_out = tmp_path / 'standard'
    run_cli(config_path, 'render', target.name, '--data', str(target / 'example'), '--out', str(standard_out))
    external = tmp_path / 'author'
    external.mkdir()
    (external / 'my_counts.csv').write_text('n\n2\n', encoding='utf-8')
    bindings = tmp_path / 'bindings.json'
    bindings.write_text(json.dumps({'tables': {'values': {'file': 'my_counts.csv',
                                                          'columns': {'value': 'n'}}}}), encoding='utf-8')
    bound_out = tmp_path / 'bound'
    result = run_cli(config_path, 'render', target.name, '--data', str(external),
                     '--bindings', str(bindings), '--out', str(bound_out))
    assert result.returncode == 0, result.stderr
    with Image.open(standard_out / 'figure.png') as a, Image.open(bound_out / 'figure.png') as b:
        assert a.size == b.size and a.tobytes() == b.tobytes()
    report = json.loads((bound_out / 'bindings-report.json').read_text(encoding='utf-8'))
    assert report['tables'][0]['mapping'] == {'value': 'n'}
    assert report['tables'][0]['omitted_optional'] == ['note']


@pytest.mark.r
def test_cli_bindings_match_standard_r_render(fake_template, tmp_path):
    config, config_path, target = fake_template
    spec_path = target / 'spec.json'
    spec = json.loads(spec_path.read_text(encoding='utf-8'))
    spec.update(entry='code/render.R', language='r')
    spec.pop('panel')
    spec_path.write_text(json.dumps(spec), encoding='utf-8')
    (target / 'code/render.R').write_text('''args <- commandArgs(trailingOnly=TRUE)
data <- args[match("--data", args) + 1]
out <- args[match("--out", args) + 1]
tab <- read.csv(file.path(data, "values.csv"), check.names=FALSE, stringsAsFactors=FALSE)
for (ext in c("png", "pdf", "svg")) writeLines(as.character(tab$value[1]), file.path(out, paste0("figure.", ext)))
''', encoding='utf-8')
    standard_out = tmp_path / 'r-standard'
    run_cli(config_path, 'render', target.name, '--data', str(target / 'example'), '--out', str(standard_out))
    external = tmp_path / 'r-author'
    external.mkdir()
    (external / 'counts.csv').write_text('n,notes\n2,ok\n', encoding='utf-8')
    bindings = tmp_path / 'r-bindings.json'
    bindings.write_text(json.dumps({'tables': {'values': {'file': 'counts.csv', 'columns': {'value': 'n'}}}}),
                        encoding='utf-8')
    bound_out = tmp_path / 'r-bound'
    result = run_cli(config_path, 'render', target.name, '--data', str(external),
                     '--bindings', str(bindings), '--out', str(bound_out))
    assert result.returncode == 0, result.stderr
    assert (standard_out / 'figure.svg').read_text() == (bound_out / 'figure.svg').read_text() == '2\n'
