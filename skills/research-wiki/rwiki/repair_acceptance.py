"""Owner confirmation of an evidenced repair, separate from original-source gates."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile

from .errors import WikiError
from .pages import read_page
from .read_cache import read_session, remember


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _digest(path: Path) -> str:
    # Only a caller's read session can memoise hashes; no process-wide cache.
    return remember(('repair-hash', path.resolve()), lambda: _hash_file(path))


def _inside(path: Path, root: Path) -> None:
    if path.is_symlink():
        raise WikiError('修补证据不允许通过符号链接越过所属目录。')
    if not path.resolve().is_relative_to(root.resolve()):
        raise WikiError('修补证据路径超出所属目录。')


def _object(path: Path, root: Path) -> dict:
    _inside(path, root)
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise WikiError(f'修补证据必须为 JSON 对象：{path.name}')
    return value


def _relative(value) -> PurePosixPath:
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise WikiError('修补证据必须使用所属目录中的相对路径。')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != value:
        raise WikiError('修补证据必须使用所属目录中的规范相对路径。')
    return path


def _tree(directory: Path) -> dict:
    if not directory.is_dir():
        raise WikiError('缺少 repair/ 修补文件树。')
    files = {}
    for path in sorted(directory.rglob('*')):
        _inside(path, directory)
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = _digest(path)
        elif not path.is_dir():
            raise WikiError('修补文件树包含缺失或不支持的文件。')
    return files


def validate_repair(config, path, *, require_approval=False) -> dict:
    """Validate current repair evidence, optionally including owner confirmation.

    This does not approve a page or change its original-source eligibility.
    """
    report = {'valid': False, 'errors': []}
    try:
        path = Path(path)
        root = config.wiki_root
        _inside(path, root / 'recipes')
        meta, _ = read_page(path)
        if meta.get('type') != 'recipe' or meta.get('id') != path.stem:
            raise WikiError('修补确认仅适用于 ID 匹配的配方页面。')
        asset = path.with_suffix('')
        _inside(asset, root)
        manifest_path = asset / 'repair.json'
        manifest = _object(manifest_path, asset)
        expected = {'schema_version': 1, 'kind': 'recipe-repair', 'id': meta['id'],
                    'execution_tree': 'repair/', 'latest_scope': 'repair', 'latest_state': 'pass'}
        if any(manifest.get(key) != value for key, value in expected.items()):
            raise WikiError('修补清单的 ID、类型、文件树或当前运行范围/状态不匹配。')
        files = manifest.get('files')
        if not isinstance(files, dict) or not files:
            raise WikiError('修补清单缺少完整文件哈希。')
        for name, digest in files.items():
            _relative(name)
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
                raise WikiError('修补清单包含无效文件哈希。')
        directory = asset / 'repair'
        _inside(directory, asset)
        current_files = _tree(directory)
        if current_files != files:
            raise WikiError('repair/ 当前完整文件树与修补清单不一致。')
        receipt_name = _relative(manifest.get('latest_run'))
        if (len(receipt_name.parts) < 2 or receipt_name.parts[0] != 'repair-runs'
                or receipt_name.suffix != '.json'):
            raise WikiError('修补运行收据必须位于 repair-runs/。')
        receipt_path = asset / receipt_name.as_posix()
        _inside(asset / 'repair-runs', asset)
        receipt = _object(receipt_path, asset / 'repair-runs')
        run_expected = {'schema_version': 2, 'kind': 'run', 'id': meta['id'],
                        'scope': 'repair', 'state': 'pass'}
        if any(receipt.get(key) != value for key, value in run_expected.items()):
            raise WikiError('修补运行收据的 ID、类型、范围或通过状态不匹配。')
        if type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0:
            raise WikiError('修补运行收据没有成功退出。')
        if receipt.get('code') != current_files or receipt.get('missing_outputs') != []:
            raise WikiError('修补运行收据的文件哈希过期或输出不完整。')
        report.update(id=meta['id'], scope='repair', execution_tree='repair/', files=current_files,
                      manifest_sha256=_digest(manifest_path), receipt=receipt_name.as_posix(),
                      receipt_sha256=_digest(receipt_path))
        if require_approval:
            approval = _object(asset / 'repair-acceptance.json', asset)
            bound = {key: report[key] for key in ('id', 'scope', 'execution_tree', 'files',
                                                 'manifest_sha256', 'receipt', 'receipt_sha256')}
            bound.update(schema_version=1, kind='recipe-repair-acceptance',
                         owner_instruction='全部改为通过')
            if (approval.get('owner_confirmed') is not True
                    or any(approval.get(key) != value for key, value in bound.items())):
                raise WikiError('作者修补确认与当前清单、收据或完整文件树不一致。')
        report['valid'] = True
    except (WikiError, OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        report['errors'].append(str(error))
    return report


def record_repair_acceptance(config, path) -> dict:
    """Record explicit owner confirmation only for an existing current repair pass."""
    from .asset_checkout import assert_writable
    assert_writable(config)
    # A write must validate fresh evidence even inside an earlier read snapshot.
    with read_session():
        report = validate_repair(config, path)
    if not report['valid']:
        raise WikiError('修补确认未通过：' + '；'.join(report['errors']))
    record = {key: value for key, value in report.items() if key not in ('valid', 'errors')}
    record.update(schema_version=1, kind='recipe-repair-acceptance',
                  checked_at=datetime.now(timezone.utc).isoformat(),
                  owner_confirmed=True, owner_instruction='全部改为通过')
    target = Path(path).with_suffix('') / 'repair-acceptance.json'
    _inside(target, target.parent)
    temporary = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                prefix='.repair-acceptance-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return record
