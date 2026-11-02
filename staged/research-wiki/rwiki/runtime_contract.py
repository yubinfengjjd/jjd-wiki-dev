"""Read-only runtime contract and independent-portability facts.

A `runtime.json` asset is a declaration, not execution evidence. This module
validates the declaration against the files actually present, derives the
runtime mode, and binds it to a separate portability receipt. Algorithm
verification stays in `verification/*.json` and is never granted here.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path, PurePosixPath, PureWindowsPath

from .confine import confined

MANIFEST_NAME = 'runtime.json'
SCHEMA_VERSION = 1
RUNTIME_MODES = ('standalone', 'bundle', 'unknown')
PORTABILITY_STATES = ('verified', 'declared', 'not_run', 'stale', 'invalid', 'unknown', 'bundle')
_SAFE_ID = re.compile(r'[a-z0-9][a-z0-9_-]*')
ENTRY_KINDS = ('function', 'script', 'external_program')
_TOOL_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._+-]*')
_ACCELERATORS = ('cpu', 'gpu', 'tpu')
_HARDWARE_KEYS = ('accelerator', 'min_memory_gb', 'min_vram_gb', 'min_cpu_cores',
                  'condition', 'notes')
_V2_KEYS = ('tools', 'external_resources', 'hardware', 'invocation')


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _relative(value, what='路径') -> PurePosixPath:
    if not _text(value) or '\\' in value or ':' in value:
        raise ValueError(f'{what}须为资产目录内的相对路径')
    path = PurePosixPath(value)
    if (path.is_absolute() or PureWindowsPath(value).anchor
            or any(part in ('', '.', '..') or part.startswith('.') for part in path.parts)):
        raise ValueError(f'{what}不可越界、重复分隔或指向隐藏文件')
    return path


def _file(asset: Path, value, what='路径') -> Path:
    part = _relative(value, what)
    path = asset.joinpath(*part.parts)
    if not confined(path, asset, asset.parent.parent):
        raise ValueError(f'{what}越过资产目录')
    if not path.is_file():
        raise FileNotFoundError(f'{what}不存在: {value}')
    return path


def _package_map(value, where: str) -> dict:
    """Validate a {language: [package, ...]} object."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f'{where} 必须为对象')
    result = {}
    for language, packages in value.items():
        if language not in ('R', 'Python'):
            raise ValueError(f'{where} 语言只允许 R 或 Python')
        if not isinstance(packages, list):
            raise ValueError(f'{where}.{language} 必须为列表')
        clean = []
        for package in packages:
            if not _text(package) or any(char in package for char in ('/', '\\', ':')):
                raise ValueError(f'{where}.{language} 含非法包名')
            if package in clean:
                raise ValueError(f'{where}.{language} 含重复包名: {package}')
            clean.append(package)
        result[language] = clean
    return result


def _optional_map(value, where: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f'{where} 必须为对象')
    result = {}
    for language, packages in value.items():
        if language not in ('R', 'Python'):
            raise ValueError(f'{where} 语言只允许 R 或 Python')
        if not isinstance(packages, dict):
            raise ValueError(f'{where}.{language} 必须为“包名: 用途”对象')
        clean = {}
        for package, purpose in packages.items():
            if not _text(package) or any(char in package for char in ('/', '\\', ':')):
                raise ValueError(f'{where}.{language} 含非法包名')
            if not _text(purpose):
                raise ValueError(f'{where}.{language}.{package} 必须说明用途')
            if package in clean:
                raise ValueError(f'{where}.{language} 含重复包名: {package}')
            clean[package] = purpose
        result[language] = clean
    return result


def _string_list(value, where: str, *, allow_duplicates: bool = False) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not _text(item) for item in value):
        raise ValueError(f'{where} 必须为字符串列表')
    if not allow_duplicates and len(set(value)) != len(value):
        raise ValueError(f'{where} 含重复项')
    return list(value)


def _source(value, where: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f'{where} 必须为对象')
    for key in ('package', 'version', 'commit', 'license'):
        if key in value and not _text(value[key]):
            raise ValueError(f'{where}.{key} 必须为非空字符串')
    for key in ('functions', 'modifications'):
        if key in value:
            _string_list(value[key], f'{where}.{key}')
    return value


def _tool_name(value, where: str) -> str:
    if not isinstance(value, str) or not _TOOL_NAME.fullmatch(value):
        raise ValueError(f'{where} 必须为安全工具名（字母数字开头，可含 ._+-）')
    return value


def _tools(value) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError('tools 必须为列表')
    result = []
    seen = set()
    for tool in value:
        if not isinstance(tool, dict):
            raise ValueError('tool 必须为对象')
        name = _tool_name(tool.get('name'), 'tool.name')
        if name in seen:
            raise ValueError(f'tool.name 重复: {name}')
        seen.add(name)
        unknown = set(tool) - {'name', 'version_constraint', 'platform', 'condition', 'notes'}
        if unknown:
            raise ValueError('tool 未知字段: ' + ', '.join(sorted(unknown)))
        entry = {'name': name}
        for key in ('version_constraint', 'platform', 'condition', 'notes'):
            if key in tool:
                if not _text(tool[key]):
                    raise ValueError(f'tool.{key} 必须为非空字符串')
                entry[key] = tool[key]
        result.append(entry)
    return result


def _external_resources(value) -> list:
    """External weights/reference/configs: declared, never opened or verified here."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError('external_resources 必须为列表')
    result = []
    seen = set()
    for resource in value:
        if not isinstance(resource, dict):
            raise ValueError('external_resource 必须为对象')
        unknown = set(resource) - {'name', 'role', 'source', 'sha256'}
        if unknown:
            raise ValueError('external_resource 未知字段: ' + ', '.join(sorted(unknown)))
        name = resource.get('name')
        if not _text(name):
            raise ValueError('external_resource.name 必须为非空字符串')
        if name in seen:
            raise ValueError(f'external_resource.name 重复: {name}')
        seen.add(name)
        if not _text(resource.get('role')):
            raise ValueError(f'external_resource {name}: role 必须说明资源用途')
        entry = {'name': name, 'role': resource['role']}
        if resource.get('source') is not None:
            if not _text(resource['source']):
                raise ValueError(f'external_resource {name}: source 须为非空字符串')
            entry['source'] = resource['source']
        digest = resource.get('sha256')
        if digest is not None:
            if not (isinstance(digest, str) and re.fullmatch(r'[0-9a-fA-F]{64}', digest)):
                raise ValueError(f'external_resource {name}: sha256 无效')
            entry['sha256'] = digest.lower()
        result.append(entry)
    return result


def _hardware(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('hardware 必须为对象')
    unknown = set(value) - set(_HARDWARE_KEYS)
    if unknown:
        raise ValueError('hardware 未知字段: ' + ', '.join(sorted(unknown)))
    result = {}
    accelerator = value.get('accelerator')
    if accelerator is not None:
        if accelerator not in _ACCELERATORS:
            raise ValueError('hardware.accelerator 只允许 ' + '、'.join(_ACCELERATORS))
        result['accelerator'] = accelerator
    for key in ('min_memory_gb', 'min_vram_gb', 'min_cpu_cores'):
        if key in value:
            amount = value[key]
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) \
                    or not math.isfinite(amount) or amount <= 0:
                raise ValueError(f'hardware.{key} 必须为有限正数')
            result[key] = amount
    for key in ('condition', 'notes'):
        if key in value:
            if not _text(value[key]):
                raise ValueError(f'hardware.{key} 必须为非空字符串')
            result[key] = value[key]
    return result


def _invocation(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('invocation 必须为对象')
    unknown = set(value) - {'command', 'args', 'env', 'notes'}
    if unknown:
        raise ValueError('invocation 未知字段: ' + ', '.join(sorted(unknown)))
    result = {}
    for key in ('command', 'notes'):
        if key in value:
            if not _text(value[key]):
                raise ValueError(f'invocation.{key} 必须为非空字符串')
            result[key] = value[key]
    if 'args' in value:
        # argv, not a file set: repeated flags/values are legitimate.
        result['args'] = _string_list(value['args'], 'invocation.args',
                                      allow_duplicates=True)
    if 'env' in value:
        env = value['env']
        if not isinstance(env, dict) or any(not _text(k) or not _text(v) for k, v in env.items()):
            raise ValueError('invocation.env 必须为“名: 值”非空对象')
        result['env'] = dict(env)
    return result


def _implementation(asset: Path, item: dict, kind: str) -> dict:
    if not isinstance(item, dict):
        raise ValueError('implementation 必须为对象')
    iid = item.get('id')
    if not isinstance(iid, str) or not _SAFE_ID.fullmatch(iid):
        raise ValueError('implementation.id 必须为唯一的安全标识')
    entry_kind = item.get('entry_kind') or 'function'
    if entry_kind not in ENTRY_KINDS:
        raise ValueError('entry_kind 必须为 function、script 或 external_program')
    entry = item.get('entry')
    function = item.get('entry_function')
    language = item.get('language')
    if not _text(language):
        raise ValueError('implementation.language 必须为非空字符串')
    tools = _tools(item.get('tools'))
    if entry_kind == 'external_program':
        # The entry is a tool name, not an asset file; declaration only.
        entry = _tool_name(entry, 'implementation.entry')
        if function is not None:
            raise ValueError('external_program 入口不得声明 entry_function')
        if not any(tool['name'] == entry for tool in tools):
            raise ValueError(f'external_program 入口须在 tools 中声明同名工具: {entry}')
        entry_path = None
    else:
        entry_path = _file(asset, entry, 'implementation.entry')
        if not _relative(entry).parts[0] == 'code':
            raise ValueError('implementation.entry 必须位于 code/')
        if entry_kind == 'script':
            if function is not None:
                raise ValueError('script 入口不得声明 entry_function')
        elif kind == 'method':
            if not _text(function):
                raise ValueError('implementation.entry_function 必须为非空字符串')
        elif function is not None and not _text(function):
            raise ValueError('implementation.entry_function 必须为非空字符串')
    mode = item.get('runtime_mode')
    if mode not in RUNTIME_MODES:
        raise ValueError('runtime_mode 必须为 standalone、bundle 或 unknown')
    files = _string_list(item.get('files'), 'implementation.files')
    if entry_kind == 'external_program':
        if entry in files:
            raise ValueError('external_program 入口是工具名，不得列入 files')
    else:
        if not files:
            raise ValueError('implementation.files 不可为空')
        if entry not in files:
            raise ValueError('implementation.files 必须包含入口文件')
    for name in files:
        _file(asset, name, 'implementation.files')
    if kind == 'method' and entry_kind == 'function':
        source = entry_path.read_text(encoding='utf-8', errors='replace')
        if language.strip().lower().startswith('python'):
            pattern = r'(?m)^\s*(?:async\s+)?def\s+' + re.escape(function) + r'\s*\('
        else:
            pattern = (r'(?m)^\s*' + re.escape(function)
                       + r'\s*<-\s*(?:local\s*\(\s*\{|function\s*\()')
        if not re.search(pattern, source):
            raise ValueError(f'entry_function 未在入口文件中定义: {function}')
    resources_value = item.get('resources')
    if resources_value is None:
        resources_value = []
    if not isinstance(resources_value, list):
        raise ValueError('resources 必须为列表')
    resources = []
    seen = set()
    for resource in resources_value:
        if not isinstance(resource, dict):
            raise ValueError('resource 必须为对象')
        path = resource.get('path')
        _file(asset, path, 'resource.path')
        if path in seen:
            raise ValueError('resource.path 重复')
        seen.add(path)
        if path not in files:
            raise ValueError(f'resource 必须同时列入 files: {path}')
        digest = resource.get('sha256')
        if digest is not None:
            if not (isinstance(digest, str) and re.fullmatch(r'[0-9a-fA-F]{64}', digest)):
                raise ValueError('resource.sha256 无效')
            current = hashlib.sha256(_file(asset, path, 'resource.path').read_bytes()).hexdigest()
            if current != digest.lower():
                raise ValueError(f'resource.sha256 与当前文件不一致: {path}')
        if not _text(resource.get('role')):
            raise ValueError('resource.role 必须说明资源用途')
        resources.append({'path': path, 'sha256': digest.lower() if digest else None,
                          'role': resource['role']})
    evidence = item.get('evidence') or {}
    if not isinstance(evidence, dict):
        raise ValueError('evidence 必须为对象')
    pointer = evidence.get('portability')
    if pointer is not None:
        _relative(pointer, 'evidence.portability')
    return {
        'id': iid,
        'entry': entry,
        'entry_kind': entry_kind,
        'entry_function': function if entry_kind == 'function' else None,
        'language': language,
        'runtime_mode': mode,
        'files': files,
        'resources': resources,
        'tools': tools,
        'external_resources': _external_resources(item.get('external_resources')),
        'hardware': _hardware(item.get('hardware')),
        'invocation': _invocation(item.get('invocation')),
        'required_packages': _package_map(item.get('required_packages'), 'required_packages'),
        'optional_packages': _optional_map(item.get('optional_packages'), 'optional_packages'),
        'python': _string_list(item.get('python'), 'python'),
        'source': _source(item.get('source'), 'source'),
        'evidence': {'portability': pointer} if pointer else {},
    }


def read_manifest(asset: Path, entry_id: str, kind: str) -> tuple[dict | None, list[str]]:
    """Return (manifest, issues). A malformed declaration never becomes a fact."""
    path = asset / MANIFEST_NAME
    if not path.is_file():
        return None, []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [f'runtime.json 无法读取: {error}']
    issues = []
    if not isinstance(data, dict):
        return None, ['runtime.json 必须为对象']
    if type(data.get('schema_version')) is not int or data['schema_version'] != SCHEMA_VERSION:
        issues.append(f'runtime.json schema_version 必须为 {SCHEMA_VERSION}')
    if data.get('kind') != kind:
        issues.append(f'runtime.json kind 必须为 {kind}')
    if data.get('id') != entry_id:
        issues.append('runtime.json id 与页面 id 不一致')
    implementations = data.get('implementations') if kind == 'method' else [data]
    if not isinstance(implementations, list) or not implementations:
        return None, issues + ['runtime.json 缺少实现声明']
    clean = []
    ids = []
    for item in implementations:
        try:
            parsed = _implementation(asset, item, kind)
        except (ValueError, TypeError, FileNotFoundError, OSError) as error:
            issues.append(str(error))
            continue
        if parsed['id'] in ids:
            issues.append(f'implementation.id 重复: {parsed["id"]}')
            continue
        ids.append(parsed['id'])
        clean.append(parsed)
    if issues:
        return None, issues
    return {'schema_version': SCHEMA_VERSION, 'kind': kind, 'id': entry_id,
            'implementations': clean}, []


def fingerprint_mode(asset: Path, implementation: dict) -> str:
    """v1 = package-map manifests only; v2 = any substantive declared condition.

    Empty/absent optional fields stay v1 so old manifests and receipts keep
    their fingerprints. A substantive condition (non-function entry, tool,
    external resource, hardware or invocation) upgrades the fingerprint scheme.
    """
    if implementation.get('entry_kind', 'function') != 'function':
        return 'v2'
    if any(implementation.get(key) for key in _V2_KEYS):
        return 'v2'
    return 'v1'


def closure_hash(asset: Path, implementation: dict) -> str | None:
    digest = hashlib.sha256()
    manifest = asset / MANIFEST_NAME
    try:
        digest.update(manifest.read_bytes())
    except OSError:
        return None
    if fingerprint_mode(asset, implementation) == 'v2':
        # Bind the canonical conditions explicitly so the scheme is self-describing;
        # the manifest bytes already make any condition change alter the digest.
        conditions = {key: implementation.get(key) for key in
                      ('entry_kind',) + _V2_KEYS}
        digest.update(b'v2\0')
        digest.update(json.dumps(conditions, sort_keys=True, ensure_ascii=False,
                                 separators=(',', ':')).encode('utf-8'))
    for name in sorted(implementation['files']):
        try:
            digest.update(name.encode('utf-8'))
            digest.update(b'\0')
            digest.update(_file(asset, name).read_bytes())
        except (OSError, ValueError, FileNotFoundError):
            return None
    return digest.hexdigest()


def _evidence(asset: Path, implementation: dict, expected_hash: str) -> dict:
    pointer = implementation.get('evidence', {}).get('portability')
    if not pointer:
        return {'state': 'declared', 'scope': '', 'evidence': None,
                'closure_hash': expected_hash, 'issues': []}
    try:
        path = _file(asset, pointer, 'evidence.portability')
    except (FileNotFoundError, ValueError) as error:
        return {'state': 'invalid', 'scope': '', 'evidence': pointer,
                'closure_hash': expected_hash, 'issues': [str(error)]}
    try:
        receipt = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {'state': 'invalid', 'scope': '', 'evidence': pointer,
                'closure_hash': expected_hash, 'issues': [f'独立性收据无法读取: {error}']}
    issues = []
    if not isinstance(receipt, dict):
        return {'state': 'invalid', 'scope': '', 'evidence': pointer,
                'closure_hash': expected_hash, 'issues': ['独立性收据必须为对象']}
    if receipt.get('schema_version') != 1:
        issues.append('独立性收据 schema_version 必须为 1')
    if receipt.get('implementation') != implementation['id']:
        issues.append('独立性收据 implementation 与声明不一致')
    if receipt.get('kind') not in (None, 'method', 'template'):
        issues.append('独立性收据 kind 无效')
    if receipt.get('closure_hash') != expected_hash:
        issues.append('独立性收据绑定的闭包已变化')
    state = receipt.get('state')
    scope = receipt.get('scope') if _text(receipt.get('scope')) else ''
    if state not in ('passed', 'not_run'):
        issues.append('独立性收据 state 只允许 passed 或 not_run')
    if state == 'passed':
        if not scope:
            issues.append('独立性收据缺少 scope')
        if not _text(receipt.get('command')):
            issues.append('独立性收据缺少 command')
        checks = receipt.get('checks')
        if not isinstance(checks, list) or not checks or any(not _text(check) for check in checks):
            issues.append('独立性收据缺少检查项')
        if not isinstance(receipt.get('environment'), dict):
            issues.append('独立性收据缺少 environment')
        files = receipt.get('files')
        if not isinstance(files, dict) or not files:
            issues.append('独立性收据缺少文件指纹')
        else:
            for name, value in files.items():
                try:
                    _relative(name)
                except ValueError as error:
                    issues.append(str(error))
                    break
                if not (isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{64}', value)):
                    issues.append('独立性收据 SHA256 无效')
                    break
            else:
                for name, value in files.items():
                    try:
                        if hashlib.sha256(_file(asset, name).read_bytes()).hexdigest() != value.lower():
                            issues.append(f'独立性收据文件指纹不匹配: {name}')
                    except (OSError, ValueError, FileNotFoundError):
                        issues.append(f'独立性收据文件缺失: {name}')
                missing = [name for name in implementation['files'] if name not in files]
                if missing:
                    issues.append('独立性收据未覆盖声明闭包: ' + ', '.join(missing))
    if issues:
        return {'state': 'invalid', 'scope': scope, 'evidence': pointer,
                'closure_hash': expected_hash, 'issues': issues}
    return {'state': 'verified' if state == 'passed' else 'not_run', 'scope': scope,
            'evidence': pointer, 'closure_hash': expected_hash, 'issues': []}


def runtime_facts(asset: Path, entry_id: str, kind: str) -> dict:
    """Derived runtime view for one method implementation or one template."""
    try:
        return _runtime_facts(asset, entry_id, kind)
    except Exception as error:  # a malformed manifest must never break the page/API
        return {'mode': 'unknown', 'declared': False,
                'required_packages': {}, 'optional_packages': {}, 'files': [],
                'resources': [], 'entry': None, 'entry_kind': None, 'language': None,
                'tools': [], 'external_resources': [], 'hardware': {}, 'invocation': {},
                'fingerprint_mode': 'unknown',
                'portability': {'state': 'unknown', 'scope': '', 'evidence': None,
                                'closure_hash': None,
                                'issues': [f'运行清单解析失败: {error}']},
                'issues': [f'运行清单解析失败: {error}']}


def _runtime_facts(asset: Path, entry_id: str, kind: str) -> dict:
    manifest, issues = read_manifest(asset, entry_id, kind)
    if manifest is None:
        return {'mode': 'unknown', 'declared': False,
                'required_packages': {}, 'optional_packages': {}, 'files': [],
                'resources': [], 'entry': None, 'entry_kind': None, 'language': None,
                'tools': [], 'external_resources': [], 'hardware': {}, 'invocation': {},
                'fingerprint_mode': 'unknown',
                'portability': {'state': 'unknown', 'scope': '',
                                'evidence': None, 'closure_hash': None, 'issues': issues},
                'issues': issues}
    base = {'id': entry_id, 'declared': True, 'entry': manifest['implementations'][0]['entry'],
            'language': manifest['implementations'][0]['language'], 'issues': []}
    if kind == 'template':
        item = manifest['implementations'][0]
        expected = closure_hash(asset, item)
        mode = item['runtime_mode']
        portability = ({'state': 'bundle', 'scope': '', 'evidence': None,
                        'closure_hash': expected, 'issues': []}
                       if mode == 'bundle' else _evidence(asset, item, expected))
        return {**base, 'mode': mode,
                'entry_kind': item['entry_kind'],
                'required_packages': item['required_packages'],
                'optional_packages': item['optional_packages'],
                'files': item['files'], 'resources': item['resources'],
                'tools': item['tools'], 'external_resources': item['external_resources'],
                'hardware': item['hardware'], 'invocation': item['invocation'],
                'fingerprint_mode': fingerprint_mode(asset, item),
                'source': item['source'], 'portability': portability}
    return {**base, 'implementations': {
        item['id']: {
            'id': item['id'],
            'declared': True,
            'mode': item['runtime_mode'],
            'entry': item['entry'], 'entry_kind': item['entry_kind'],
            'entry_function': item['entry_function'],
            'language': item['language'], 'files': item['files'],
            'resources': item['resources'],
            'tools': item['tools'], 'external_resources': item['external_resources'],
            'hardware': item['hardware'], 'invocation': item['invocation'],
            'fingerprint_mode': fingerprint_mode(asset, item),
            'required_packages': item['required_packages'],
            'optional_packages': item['optional_packages'],
            'source': item['source'],
            'portability': ({'state': 'bundle', 'scope': '', 'evidence': None,
                             'closure_hash': closure_hash(asset, item), 'issues': []}
                            if item['runtime_mode'] == 'bundle'
                            else _evidence(asset, item, closure_hash(asset, item))),
        } for item in manifest['implementations']
    }}


def implementation_runtime(asset: Path, entry_id: str, implementation_id: str, *, facts=None) -> dict:
    if facts is None:
        facts = runtime_facts(asset, entry_id, 'method')
    return deepcopy(facts.get('implementations', {}).get(implementation_id, {
        'id': implementation_id, 'declared': False,
        'mode': 'unknown', 'entry': None, 'entry_kind': None, 'entry_function': None,
        'language': None, 'files': [], 'resources': [],
        'tools': [], 'external_resources': [], 'hardware': {}, 'invocation': {},
        'fingerprint_mode': 'unknown',
        'required_packages': {}, 'optional_packages': {},
        'source': {}, 'portability': {'state': 'unknown', 'scope': '', 'evidence': None,
                                      'closure_hash': None,
                                      'issues': facts.get('portability', {}).get('issues', [])}
    }))


def lint_manifest(asset: Path, entry_id: str, kind: str) -> list[str]:
    """Human-readable findings for lint; unknown never becomes an ERROR."""
    manifest, issues = read_manifest(asset, entry_id, kind)
    if manifest is None:
        if issues:
            return [f'{kind} {entry_id}: ' + issue for issue in issues]
        return []
    findings = []
    facts = runtime_facts(asset, entry_id, kind)
    items = ([facts['implementations'][key] for key in facts['implementations']]
             if kind == 'method' else [facts])
    for item in items:
        iid = item.get('id') or (entry_id if kind == 'template' else '')
        portability = item['portability']
        if item['mode'] == 'bundle':
            findings.append(f'{kind} {entry_id} / {iid}: 仍需完整来源库（bundle），不独立')
        elif item['mode'] == 'standalone' and portability['state'] == 'declared':
            findings.append(f'{kind} {entry_id} / {iid}: 独立声明尚无独立性证据')
        elif item['mode'] == 'standalone' and portability['state'] == 'not_run':
            findings.append(f'{kind} {entry_id} / {iid}: 独立声明未运行（not_run）')
        elif item['mode'] == 'standalone' and portability['state'] in ('stale', 'invalid'):
            findings.append(f'{kind} {entry_id} / {iid}: 独立性证据 {portability["state"]}'
                            + (': ' + '; '.join(portability.get('issues') or []) if portability.get('issues') else ''))
    return findings
