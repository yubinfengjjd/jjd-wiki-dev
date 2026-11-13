"""Copyable, stdlib-only table adapter for explicit external-data bindings.

This module is deliberately independent of the Wiki: copy it into a project,
pass the literal spec tables and the project data root, and it writes the
internal ``<interface>.csv`` files. It only maps declared fields and performs
explicit, non-aggregating melt/pivot. It never guesses columns, fills values,
converts units, or reads a network path.
"""
import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path

MISSING = frozenset({'', 'na', 'n/a', 'nan', 'null'})
SEMANTICS = ('只核对字段存在、必填关系与数值可解析；不验证单位、粒度、配对关系或统计含义；'
             '不做 0–1 / 0–100 换算。')


class BindingError(ValueError):
    """A binding problem the caller must fix; never a silent fallback."""


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _missing(value) -> bool:
    return value is None or str(value).strip().lower() in MISSING


def load_bindings(path: Path) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise BindingError(f'bindings 不是可读 JSON: {error}') from error
    return validate_bindings(value)


def validate_bindings(value) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('tables'), dict):
        raise BindingError('bindings.tables 必须为对象')
    unknown = set(value) - {'tables', 'schema_version'}
    if unknown:
        raise BindingError('bindings 不支持字段: ' + ', '.join(sorted(unknown)))
    for key, table in value['tables'].items():
        if not _text(key):
            raise BindingError('bindings.tables 的表键必须为非空字符串')
        if not isinstance(table, dict):
            raise BindingError(f'bindings.tables.{key} 必须为对象')
        unknown = set(table) - {'file', 'columns', 'reshape'}
        if unknown:
            raise BindingError(f'bindings.tables.{key} 不支持字段: ' + ', '.join(sorted(unknown)))
        if not _text(table.get('file')):
            raise BindingError(f'bindings.tables.{key}.file 必须为非空字符串')
        if '://' in table['file']:
            raise BindingError(f'bindings.tables.{key}.file 不允许网络地址')
        if 'columns' in table and not isinstance(table['columns'], dict):
            raise BindingError(f'bindings.tables.{key}.columns 必须为对象')
        if 'reshape' in table and table['reshape'] is not None and not isinstance(table['reshape'], dict):
            raise BindingError(f'bindings.tables.{key}.reshape 必须为对象')
    return value


def _source_path(file: str, data_root: Path) -> Path:
    path = Path(file)
    if path.anchor or path.is_absolute() or any(part == '..' for part in path.parts):
        raise BindingError(f'bindings 路径越界: {file}')
    if any(part.startswith('.') for part in path.parts):
        raise BindingError(f'bindings 路径不可指向隐藏文件: {file}')
    root = Path(data_root).resolve()
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise BindingError(f'bindings 路径越界: {file}')
    if not resolved.is_file():
        raise BindingError(f'bindings 源文件不存在: {file}')
    return resolved


def read_source(path: Path) -> tuple[list[str], list[dict]]:
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header:
            raise BindingError(f'CSV 没有表头: {path.name}')
        if any(not _text(name) for name in header):
            raise BindingError(f'CSV 存在空列名: {path.name}')
        duplicates = sorted({name for name in header if header.count(name) > 1})
        if duplicates:
            raise BindingError(f'CSV 重复列名: {", ".join(duplicates)} ({path.name})')
        rows = []
        for number, values in enumerate(reader, start=2):
            if len(values) != len(header):
                raise BindingError(f'CSV 第 {number} 行列数与表头不一致 ({path.name})')
            rows.append(dict(zip(header, values)))
    return header, rows


def _list(value, name: str, header: list[str], *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not _text(item) for item in value):
        raise BindingError(f'reshape.{name} 必须为字符串列表')
    if not value and not allow_empty:
        raise BindingError(f'reshape.{name} 不得为空')
    missing = [item for item in value if item not in header]
    if missing:
        raise BindingError(f'reshape.{name} 引用不存在的列: ' + ', '.join(missing))
    if len(set(value)) != len(value):
        raise BindingError(f'reshape.{name} 不得重复')
    return list(value)


def reshape_records(header: list[str], rows: list[dict], reshape) -> tuple[list[str], list[dict], dict | None]:
    """Explicit melt/pivot only; no aggregation, no implicit key completion with values."""
    if reshape is None:
        return list(header), list(rows), None
    op = reshape.get('op')
    if op not in ('melt', 'pivot'):
        raise BindingError('reshape.op 必须为 melt 或 pivot')
    carry = _list(reshape.get('carry', []), 'carry', header, allow_empty=True)
    if op == 'melt':
        allowed = {'op', 'id', 'variables', 'variable_name', 'value_name', 'carry'}
        unknown = set(reshape) - allowed
        if unknown:
            raise BindingError('reshape 不支持字段: ' + ', '.join(sorted(unknown)))
        ids = _list(reshape.get('id', []), 'id', header, allow_empty=True)
        variables = _list(reshape.get('variables'), 'variables', header)
        variable_name, value_name = reshape.get('variable_name'), reshape.get('value_name')
        if not _text(variable_name) or not _text(value_name) or variable_name == value_name:
            raise BindingError('reshape.variable_name/value_name 必须为不同的非空字符串')
        if set(ids) & set(variables) or set(carry) & (set(ids) | set(variables)):
            raise BindingError('reshape 的 id/variables/carry 列不得重叠')
        out_header = ids + [variable_name, value_name] + carry
        if len(set(out_header)) != len(out_header):
            raise BindingError('reshape 输出列名重复')
        out = []
        for row in rows:
            for variable in variables:
                item = {name: row[name] for name in ids}
                item[variable_name], item[value_name] = variable, row[variable]
                item.update({name: row[name] for name in carry})
                out.append(item)
        return out_header, out, {'op': 'melt', 'id': ids, 'variables': variables,
                                 'variable_name': variable_name, 'value_name': value_name,
                                 'carry': carry, 'aggregation': False,
                                 'dropped_columns': [name for name in header
                                                     if name not in set(ids) | set(variables) | set(carry)]}
    allowed = {'op', 'index', 'columns', 'values', 'carry'}
    unknown = set(reshape) - allowed
    if unknown:
        raise BindingError('reshape 不支持字段: ' + ', '.join(sorted(unknown)))
    index = _list(reshape.get('index'), 'index', header)
    columns, values = reshape.get('columns'), reshape.get('values')
    if not _text(columns) or not _text(values):
        raise BindingError('reshape.columns/values 必须为非空字符串')
    if columns in index or values in index or columns == values:
        raise BindingError('reshape 的 index/columns/values 列不得重叠')
    if columns not in header or values not in header:
        raise BindingError('reshape.columns/values 引用不存在的列')
    if set(carry) & (set(index) | {columns, values}):
        raise BindingError('reshape 的 index/columns/values/carry 列不得重叠')
    if any(row[columns] is None or str(row[columns]) == '' for row in rows):
        raise BindingError('reshape pivot 列含空值/缺失值，无法确定稳定列名；请先明确处理')
    seen, pivot_values, carried = {}, [], {}
    for row in rows:
        key = tuple(row[name] for name in index)
        if (key, row[columns]) in seen:
            raise BindingError(f'reshape pivot 重复键: {key} / {row[columns]}')
        seen[(key, row[columns])] = row[values]
        if row[columns] not in pivot_values:
            pivot_values.append(row[columns])
        for name in carry:
            if key in carried and carried[key][name] != row[name]:
                raise BindingError(f'reshape carry 列 {name} 在同一 index 下不唯一')
            carried.setdefault(key, {})[name] = row[name]
    out_header = index + pivot_values + carry
    if len(set(out_header)) != len(out_header):
        raise BindingError('reshape 输出列名重复')
    out = []
    for key in {tuple(row[name] for name in index): None for row in rows}:
        item = dict(zip(index, key))
        for value in pivot_values:
            item[value] = seen.get((key, value), '')
        item.update(carried.get(key, {}))
        out.append(item)
    return out_header, out, {'op': 'pivot', 'index': index, 'columns': columns,
                             'values': values, 'carry': carry, 'aggregation': False,
                             'missing_cells': len(out) * len(pivot_values) - len(seen),
                             'dropped_columns': [name for name in header
                                                 if name not in set(index) | {columns, values} | set(carry)]}


def map_records(header: list[str], rows: list[dict], columns: dict, mapping: dict):
    """Map internal semantic fields to author columns; extras keep their original names."""
    if not isinstance(mapping, dict) or any(not _text(value) for value in mapping.values()):
        raise BindingError('bindings columns 必须为“内部字段 → 作者列”的字符串映射')
    unknown = set(mapping) - set(columns)
    if unknown:
        raise BindingError('bindings 映射含未知字段: ' + ', '.join(sorted(unknown)))
    counts = {}
    for external in mapping.values():
        counts[external] = counts.get(external, 0) + 1
    duplicates = [external for external, count in counts.items() if count > 1]
    if duplicates:
        raise BindingError('bindings 映射重复: ' + ', '.join(sorted(duplicates)))
    for internal, external in mapping.items():
        if external not in header:
            raise BindingError(f'映射的外部列不存在: {internal} → {external}')
    included, missing = [], []
    for internal, definition in columns.items():
        external = mapping.get(internal, internal)
        if external in header:
            included.append(internal)
        elif definition.get('required', True):
            missing.append(internal)
    if missing:
        raise BindingError('缺少必需字段: ' + ', '.join(missing))
    # Check the complete effective mapping (explicit plus same-name fallback):
    # two internal fields must never consume the same author column.
    effective = {name: mapping.get(name, name) for name in included}
    by_source = {}
    for internal, external in effective.items():
        by_source.setdefault(external, []).append(internal)
    for external, internals in by_source.items():
        if len(internals) > 1:
            raise BindingError('同一来源列被多个内部字段消费: '
                               f'{external} → {", ".join(internals)}')
    consumed = set(effective.values())
    extras = [name for name in header if name not in consumed]
    out_header = list(included)
    for name in extras:
        if name in out_header:
            raise BindingError(f'输出列名冲突: {name}')
        out_header.append(name)
    out = []
    for row in rows:
        item = {name: row[effective[name]] for name in included}
        item.update({name: row[name] for name in extras})
        out.append(item)
    return out_header, out, {'mapping': dict(mapping), 'included_columns': included,
                             'omitted_optional': [name for name in columns if name not in included],
                             'extras_preserved': extras}


def _numeric_checks(header: list[str], rows: list[dict], columns: dict, mapping: dict):
    missing, ranges, warnings = {}, {}, []
    for name, definition in columns.items():
        if name not in header or definition.get('type') not in ('float', 'int'):
            continue
        values = []
        missing[name] = 0
        for number, row in enumerate(rows, start=1):
            raw = row[name]
            if _missing(raw):
                missing[name] += 1
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError) as error:
                raise BindingError(f'列 {name}（{mapping.get(name, name)}）第 {number} 行不是有效数值: {raw}') from error
            if not math.isfinite(value):
                raise BindingError(f'列 {name}（{mapping.get(name, name)}）第 {number} 行不是有限数值: {raw}')
            values.append(value)
        if values:
            ranges[name] = [min(values), max(values)]
            description = str(definition.get('description') or '')
            external = mapping.get(name, name)
            if re.search(r'0\s*[–-]\s*100', description) and min(values) >= 0 and max(values) <= 1:
                warnings.append(f'{external} 声明为 0–100 百分比，但观测值均在 0–1；请确认是否为比例，'
                                '本工具不自动换算')
            elif re.search(r'0\s*[–-]\s*1(?!\d)', description) and max(values) > 1:
                warnings.append(f'{external} 声明为 0–1，但观测值超过 1；请确认单位，本工具不自动换算')
    if any(missing.values()):
        warnings.append('存在空值/NA：未填补，按原样写入规范表')
    return {'missing_values': {name: count for name, count in missing.items() if count},
            'observed_ranges': ranges, 'warnings': warnings}


def _write(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _same_path(left: Path, right: Path) -> bool:
    if os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve())):
        return True
    try:
        return left.exists() and right.exists() and os.path.samefile(left, right)
    except OSError:
        return False


def prepare_tables(spec: dict, bindings: dict, data_root: Path, work_dir: Path) -> list[dict]:
    """Validate and stage every table before touching a canonical output.

    A canonical output may never overwrite an author source (including another
    table's source, aliases and hard links). Source hashes are taken before any
    write; a failure leaves the previous canonical outputs untouched.
    """
    bindings = validate_bindings(bindings)
    tables = spec.get('tables')
    if not isinstance(tables, dict) or not tables:
        raise BindingError('spec.tables 必须为非空对象')
    unknown = set(bindings['tables']) - set(tables)
    if unknown:
        raise BindingError('bindings 含未知表: ' + ', '.join(sorted(unknown)))
    root = Path(data_root).resolve()
    if not root.is_dir():
        raise BindingError(f'数据目录不存在: {root}')
    work = Path(work_dir)
    sources, entries, output_keys = {}, [], {}
    for key, table in tables.items():
        if not isinstance(table, dict) or not _text(table.get('interface')):
            raise BindingError(f'spec.tables.{key}.interface 必须为非空字符串')
        binding = bindings['tables'].get(key)
        if binding is None:
            if table.get('required', True):
                raise BindingError(f'缺少必需表 {key} 的 bindings')
            continue
        interface = table['interface']
        source = _source_path(binding['file'], root)
        sources.setdefault(os.path.normcase(str(source.resolve())), source)
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        header, rows = read_source(source)
        reshaped_header, reshaped_rows, operation = reshape_records(header, rows, binding.get('reshape'))
        columns = table.get('columns') or {}
        if not isinstance(columns, dict) or not columns:
            raise BindingError(f'spec.tables.{key}.columns 缺失，无法核对必填字段')
        out_header, out_rows, mapped = map_records(
            reshaped_header, reshaped_rows, columns, binding.get('columns') or {})
        checks = ['source_inside_data_root', 'header_unique', 'required_columns_present']
        numeric = _numeric_checks(out_header, out_rows, columns, mapped['mapping'])
        checks.append('numeric_values_parse')
        out_path = work / f'{interface}.csv'
        output_key = os.path.normcase(str(out_path.resolve()))
        if output_key in output_keys:
            raise BindingError(f'表 {key} 与 {output_keys[output_key]} 使用同一输出文件: {out_path.name}')
        output_keys[output_key] = key
        entries.append({
            'table_key': key, 'interface': interface, 'source': source,
            'source_digest': source_digest, 'out_header': out_header,
            'out_rows': out_rows, 'mapped': mapped, 'operation': operation,
            'checks': checks, 'numeric': numeric, 'out_path': out_path,
        })
    # No canonical output may alias or overwrite any source from any table.
    for entry in entries:
        for source in sources.values():
            if _same_path(entry['out_path'], source):
                raise BindingError(f'输出文件会覆盖源文件: {entry["out_path"]} 与 {source}')
        if entry['out_path'].exists() and entry['out_path'].is_dir():
            raise BindingError(f'输出路径是目录: {entry["out_path"]}')
    # Stage all writes; only replace canonical outputs after every write succeeded.
    work.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.binding-stage-', dir=work))
    backups, written = {}, []
    try:
        staged = []
        for entry in entries:
            staged_path = staging / f'{entry["interface"]}.csv'
            _write(staged_path, entry['out_header'], entry['out_rows'])
            staged.append((staged_path, entry['out_path']))
        for staged_path, target in staged:
            if target.exists():
                backup = staging / (target.name + '.backup')
                shutil.copyfile(target, backup)
                backups[target] = backup
            os.replace(staged_path, target)
            written.append(target)
    except BaseException:
        for target in written:
            if target in backups:
                shutil.copyfile(backups[target], target)
            else:
                target.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    reports = []
    for entry in entries:
        out_path = entry['out_path']
        reports.append({
            'table_key': entry['table_key'], 'interface': entry['interface'],
            'source_file': entry['source'].relative_to(root).as_posix(),
            'source_sha256': entry['source_digest'],
            'output_file': out_path.name,
            'output_sha256': hashlib.sha256(out_path.read_bytes()).hexdigest(),
            'mapping': entry['mapped']['mapping'],
            'included_columns': entry['mapped']['included_columns'],
            'omitted_optional': entry['mapped']['omitted_optional'],
            'extras_preserved': entry['mapped']['extras_preserved'],
            'reshape': entry['operation'], 'checks': entry['checks'],
            'semantics': SEMANTICS, **entry['numeric'],
        })
    return reports


def report_payload(reports: list[dict]) -> dict:
    return {'schema_version': 1, 'tables': reports,
            'scope': '外部数据到内部标准表的显式适配；不改变原表、不补值、不换算、不做统计。'}
