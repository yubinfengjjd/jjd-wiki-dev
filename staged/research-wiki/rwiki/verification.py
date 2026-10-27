import json
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from .confine import confined
from .errors import WikiError


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay_inputs(target: Path) -> dict:
    """Execution inputs, excluding generated output and author notes."""
    root = target.parents[1]
    files = {}

    def add(path):
        if not confined(path, root, root) or not path.is_file():
            raise WikiError(f'回放输入不存在或越出 Wiki: {path}')
        files[path.relative_to(root).as_posix()] = digest(path)

    def template(folder):
        add(folder / 'spec.json')
        spec = json.loads((folder / 'spec.json').read_text(encoding='utf-8'))
        for key in ('entry', 'panel'):
            if key in spec:
                add(folder / spec[key])
        for p in sorted((folder / 'code').rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'):
                add(p)
        for table in spec.get('tables', {}).values():
            slug = table['interface']
            from .interfaces import load_interface
            definition = load_interface(root, slug)
            # Only the table contract affects execution, not generated facts or notes.
            files[f'interfaces/{slug}#columns'] = hashlib.sha256(json.dumps(
                definition['columns'], ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    if target.parent.name == 'templates':
        template(target)
    else:
        add(target / 'layout.json')
        layout = json.loads((target / 'layout.json').read_text(encoding='utf-8'))
        for tid in sorted({p['template'] for p in layout['panels']}):
            template(root / 'templates' / tid)
    for p in sorted((target / 'example').rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            add(p)
    return files


def start_replay(target: Path) -> dict:
    out = target / 'verify'
    out.mkdir(exist_ok=True)
    receipt = out / 'verify.json'
    if receipt.is_file():
        history = out / 'history'
        history.mkdir(exist_ok=True)
        shutil.copyfile(receipt, history / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json'))
    receipt.write_text(json.dumps({'schema_version': 2, 'exit_code': 1,
        'timestamp': datetime.now(timezone.utc).isoformat(), 'state': 'not_completed'}), encoding='utf-8')
    return replay_inputs(target)


def replay_available(target: Path) -> bool:
    try:
        receipt = json.loads((target / 'verify/verify.json').read_text(encoding='utf-8'))
        if receipt.get('schema_version') != 2 or receipt.get('exit_code') != 0:
            return False
        if receipt.get('inputs') != replay_inputs(target):
            return False
        outputs = {ext: digest(target / f'verify/figure.{ext}') for ext in ('png', 'pdf', 'svg')
                   if (target / f'verify/figure.{ext}').stat().st_size > 0}
        return (len(outputs) == 3 and outputs == receipt.get('outputs')
                and digest(target / 'preview.png') == outputs['png'])
    except (OSError, ValueError, AttributeError, KeyError, TypeError, WikiError):
        return False


def record_preview(target: Path, mean: float | None = None, *, inputs: dict | None = None,
                   executable=None) -> None:
    current = replay_inputs(target)
    if inputs is not None and current != inputs:
        raise WikiError('回放期间输入发生变化，请重新回放')
    outputs = {ext: digest(target / f'verify/figure.{ext}') for ext in ('png', 'pdf', 'svg')}
    record = {"schema_version": 2, "timestamp": datetime.now(timezone.utc).isoformat(),
              "exit_code": 0, 'inputs': current, 'outputs': outputs,
              'environment': {'executable': str(executable or sys.executable),
                              'controller_python': sys.version,
                              'scope': '当前代码与示例的执行证据；不证明科学有效或任意数据适用'}}
    if mean is not None:
        record["mean_absolute_difference"] = mean
    (target / "verify/verify.json").write_text(json.dumps(record, indent=2) + "\n",
                                             encoding="utf-8", newline="\n")
    shutil.copyfile(target / "verify/figure.png", target / "preview.png")


def compare_images(original: Path, output: Path) -> tuple[float, Path]:
    with Image.open(original) as source, Image.open(output) as rendered:
        left, right = source.convert("RGB"), rendered.convert("RGB")
    height = min(left.height, right.height)
    left = left.resize((round(left.width * height / left.height), height), Image.Resampling.LANCZOS)
    right = right.resize((round(right.width * height / right.height), height), Image.Resampling.LANCZOS)
    compare = Image.new("RGB", (left.width + 24 + right.width, height), "white")
    compare.paste(left, (0, 0))
    compare.paste(right, (left.width + 24, 0))
    path = output.parent / "compare.png"
    compare.save(path)
    difference = ImageChops.difference(left, right.resize(left.size, Image.Resampling.LANCZOS))
    return sum(ImageStat.Stat(difference).mean) / 3, path
