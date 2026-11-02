"""Read-only implementation evidence bound to current local code, never execution."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from .confine import confined
from .pages import read_page

METHOD_KINDS = ('analysis', 'workflow', 'technical')


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _relative(value):
    if not _text(value) or '\\' in value or ':' in value:
        raise ValueError('路径须为资产目录内的相对路径')
    path = PurePosixPath(value)
    if (path.is_absolute() or PureWindowsPath(value).anchor
            or any(part.startswith('.') for part in path.parts) or not path.parts):
        raise ValueError('路径不可越界或指向隐藏文件')
    return path


def _asset_file(asset, relative):
    part = _relative(relative)
    path = asset.joinpath(*part.parts)
    if not confined(path, asset, asset.parent.parent):
        raise ValueError('路径越过方法资产目录')
    if not path.is_file():
        raise FileNotFoundError(relative)
    return path


def implementation_metadata_errors(meta):
    """Old unclassified notes remain readable; an explicit contract must be complete."""
    errors = []
    kind = meta.get('method_kind')
    if kind is not None and kind not in METHOD_KINDS:
        errors.append('method_kind 必须为 analysis、workflow 或 technical')
    if kind is not None or 'data_contract' in meta:
        contract = meta.get('data_contract')
        if not isinstance(contract, dict) or any(not _text(contract.get(key)) for key in ('input', 'output')):
            errors.append('data_contract.input/output 必须为非空对象说明')
    if kind is not None and not _text(meta.get('summary')):
        errors.append('summary 必须为一句非空摘要')
    implementations = meta.get('implementations', [])
    if not isinstance(implementations, list):
        return errors + ['implementations 必须为列表']
    ids = set()
    for item in implementations:
        if not isinstance(item, dict):
            errors.append('implementation 必须为对象')
            continue
        iid = item.get('id')
        if not isinstance(iid, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', iid) or iid in ids:
            errors.append('implementation.id 必须为唯一的安全标识')
        if isinstance(iid, str):
            ids.add(iid)
        for key in ('title', 'language', 'entrypoint'):
            if not _text(item.get(key)):
                errors.append(f'implementation.{key} 必须为非空字符串')
        dependencies = item.get('dependencies')
        if not isinstance(dependencies, list) or any(not _text(dep) for dep in dependencies):
            errors.append('implementation.dependencies 必须为字符串列表')
        try:
            entrypoint = str(item.get('entrypoint', ''))
            if entrypoint.startswith('external:'):
                name = entrypoint[len('external:'):]
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', name):
                    raise ValueError('external: 入口必须为安全工具名')
            else:
                entry, _, function = entrypoint.partition(':')
                if _relative(entry).parts[0] != 'code' or not function.strip():
                    raise ValueError('entrypoint 必须为 code/下文件:函数 或 external:工具名')
            if item.get('verification') is not None:
                _relative(item['verification'])
        except ValueError as error:
            errors.append(str(error))
    if 'implementation_status' in meta:
        errors.append('implementation_status 为只读派生字段，不可持久化')
    return errors


def implementation_status(page: Path, meta=None) -> list[dict]:
    if meta is None:
        meta, _ = read_page(page)
    items = meta.get('implementations', [])
    if not isinstance(items, list):
        return []
    asset = page.with_suffix('')
    result = []
    # The manifest describes every branch. Validate it once per invocation,
    # including file fingerprints; the next invocation always reads fresh bytes.
    from .runtime_contract import runtime_facts
    facts = runtime_facts(asset, page.stem, 'method') if any(isinstance(item, dict) for item in items) else None
    for item in items:
        if not isinstance(item, dict):
            result.append(dict(id='', title='', state='invalid', scope='',
                               runtime={'mode': 'unknown', 'declared': False,
                                        'required_packages': {}, 'optional_packages': {},
                                        'files': [], 'resources': [], 'entry': None,
                                        'entry_kind': None, 'language': None,
                                        'tools': [], 'external_resources': [],
                                        'hardware': {}, 'invocation': {},
                                        'fingerprint_mode': 'unknown',
                                        'portability': {'state': 'unknown', 'scope': '',
                                                        'evidence': None, 'closure_hash': None,
                                                        'issues': ['实现元数据无效']}}))
            continue
        status = dict(id=item.get('id', ''), title=item.get('title', ''), state='not_run', scope='')
        from .runtime_contract import implementation_runtime
        runtime = implementation_runtime(
            asset, page.stem, item.get('id', '') if isinstance(item.get('id'), str) else '', facts=facts)
        if runtime.get('declared'):
            page_entry = str(item.get('entrypoint', ''))
            portability = runtime.setdefault('portability', {})
            issues = portability.setdefault('issues', [])
            if page_entry.startswith('external:'):
                matches = (runtime.get('entry_kind') == 'external_program'
                           and page_entry == f'external:{runtime.get("entry")}'
                           and not runtime.get('entry_function'))
            else:
                entry_name, _, function = page_entry.partition(':')
                matches = (runtime.get('entry') == entry_name
                           and runtime.get('entry_function') == function)
            if not matches:
                portability['state'] = 'invalid'
                issues.append('页面 entrypoint 与 runtime.json 的入口不一致')
            declared = sorted({package for packages in runtime.get('required_packages', {}).values()
                               for package in packages})
            page_dependencies = sorted({str(dep) for dep in (item.get('dependencies') or [])})
            runtime['dependency_match'] = declared == page_dependencies
            if not runtime['dependency_match']:
                issues.append('页面 dependencies 与 runtime.json 的 required_packages 不一致；'
                              '前端使用 runtime.json，页面字段仅作历史兼容')
        status['runtime'] = runtime
        try:
            # Validate each branch independently: one receipt grants no status to another branch.
            if implementation_metadata_errors({'implementations': [item]}):
                raise ValueError('实现元数据无效')
            external = str(item.get('entrypoint', '')).startswith('external:')
            entry = (item['entrypoint'].split(':', 1)[1] if external
                     else item['entrypoint'].partition(':')[0])
            if not external:
                _asset_file(asset, entry)
            pointer = item.get('verification')
            if not pointer:
                result.append(status)
                continue
            try:
                receipt_path = _asset_file(asset, pointer)
            except FileNotFoundError:
                result.append(status)
                continue
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            if (not isinstance(receipt, dict) or type(receipt.get('schema_version')) is not int
                    or receipt['schema_version'] != 1 or receipt.get('implementation') != item['id']):
                raise ValueError('收据版本或实现 id 不匹配')
            if receipt.get('state') == 'not_run':
                status['scope'] = receipt.get('scope', '') if _text(receipt.get('scope')) else ''
                result.append(status)
                continue
            if (receipt.get('state') != 'passed' or not _text(receipt.get('scope'))
                    or not _text(receipt.get('command'))
                    or not isinstance(receipt.get('checks'), list) or not receipt['checks']
                    or any(not _text(check) for check in receipt['checks'])
                    or not isinstance(receipt.get('environment'), dict)):
                raise ValueError('收据缺少验证范围、命令、检查或环境')
            files = receipt.get('files')
            if not isinstance(files, dict) or not files:
                raise ValueError('收据缺少代码指纹')
            # Check path syntax before opening any file; receipts may never read outside assets.
            for name, digest in files.items():
                _relative(name)
                if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', digest):
                    raise ValueError('SHA256 无效')
            code = {p.relative_to(asset).as_posix(): p for p in (asset / 'code').rglob('*')
                    if p.is_file() and '__pycache__' not in p.parts and p.suffix.lower() not in ('.pyc', '.pyo')}
            if not code and not external:
                raise ValueError('收据没有覆盖当前 code/全部源文件')
            if not set(code) <= set(files) or (not external and entry not in files):
                raise ValueError('收据没有覆盖当前 code/全部源文件')
            status.update(state='verified', scope=receipt['scope'])
            for name, digest in files.items():
                try:
                    current = _asset_file(asset, name)
                except FileNotFoundError:
                    status['state'] = 'stale'
                    continue
                if hashlib.sha256(current.read_bytes()).hexdigest() != digest.lower():
                    status['state'] = 'stale'
        except (OSError, ValueError, TypeError, KeyError):
            status.update(state='invalid', scope='')
        result.append(status)
    # Duplicate ids invalidate every ambiguous branch.
    ids = [item.get('id') for item in items if isinstance(item, dict)]
    for status in result:
        if ids.count(status['id']) > 1:
            status.update(state='invalid', scope='')
    return result


def verified_implementations(page, meta=None):
    if meta is None:
        meta, _ = read_page(page)
    verified = {item['id'] for item in implementation_status(page, meta) if item['state'] == 'verified'}
    return [item for item in meta.get('implementations', []) if isinstance(item, dict) and item.get('id') in verified]
