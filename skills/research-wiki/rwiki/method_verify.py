"""Run a method implementation's local verification script and emit a SHA256 receipt."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .confine import confined
from .config import Config
from .errors import WikiError
from .method_implementations import implementation_status
from .pages import read_page, write_page
from .runtime_contract import read_manifest

_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_UNC_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9:])\\\\[^\s'\"<>|\\]+\\[^\s'\"<>|\\]+"
    r"(?:[\\/][^\s'\"<>|]*|(?:[ \t]+(?=[^\s'\"<>|]*(?:[\\/]|\.[A-Za-z0-9]{1,8}(?:\b|$)))[^\s'\"<>|]+))*"
)
_WIN_DRIVE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"
    r"(?:[^\s'\"<>|]+(?:[ \t]+(?=[^\s'\"<>|]*(?:[\\/]|\.[A-Za-z0-9]{1,8}(?:\b|$)))[^\s'\"<>|]+)*)?"
)
_UNIX_ABS_PATH_RE = re.compile(
    r"(?<![\w.])/(?:Users|home|private/tmp|tmp|var/folders)/[^\s'\"]*"
)


def _is_reparse(path: Path) -> bool:
    return os.path.islink(path) or (hasattr(os.path, "isjunction") and os.path.isjunction(path))


def _assert_no_reparse_in_chain(path: Path, stop_at: Path, label: str) -> None:
    cur = path
    stop_abs = os.path.normcase(os.path.abspath(str(stop_at)))
    while True:
        if os.path.lexists(cur) and _is_reparse(cur):
            raise WikiError(f"禁止符号链接或目录联接: {label}")
        if os.path.normcase(os.path.abspath(str(cur))) == stop_abs:
            break
        parent = cur.parent
        if parent == cur:
            break
        cur = parent


def _validate_output_rel(rel: str) -> str:
    if not isinstance(rel, str) or not rel.strip() or "\\" in rel or ":" in rel or any(ord(ch) < 32 for ch in rel):
        raise WikiError(f"输出产物文件名非法: {rel!r}")
    p = PurePosixPath(rel)
    if (
        p.is_absolute()
        or PureWindowsPath(rel).anchor
        or not p.parts
        or any(part in ("", ".", "..") or part.startswith(".") or part != part.rstrip(" .") for part in p.parts)
    ):
        raise WikiError(f"输出产物文件名非法: {rel!r}")
    return rel


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _sanitize_text(text: str) -> str:
    """Strip any machine-specific UNC, Windows drive (incl. spaces), or Unix home/tmp paths."""
    cleaned = _UNC_PATH_RE.sub("<ABS_PATH>", text)
    cleaned = _WIN_DRIVE_PATH_RE.sub("<ABS_PATH>", cleaned)
    cleaned = _UNIX_ABS_PATH_RE.sub("<ABS_PATH>", cleaned)
    return cleaned


def _probe_runtime_version(config: Config, runtime_lang: str, env: dict[str, str]) -> str | None:
    try:
        if runtime_lang == "Python":
            cmd = [str(config.python_exe), "-c", "import sys; print(sys.version.splitlines()[0])"]
        else:
            cmd = [str(config.rscript_exe), "--vanilla", "-e", "cat(R.version.string)"]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            shell=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return _sanitize_text(proc.stdout.strip().splitlines()[0].strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _locate_verify_script(asset: Path, wiki_root: Path, impl_id: str, language: str) -> tuple[Path, str]:
    example_dir = asset / "example"
    _assert_no_reparse_in_chain(example_dir, asset, f"methods/{asset.name}/example")
    if not example_dir.is_dir():
        raise WikiError(f"方法资产缺少 example/ 目录: methods/{asset.name}/example")
    py_script = example_dir / f"verify_{impl_id}.py"
    r_script = example_dir / f"verify_{impl_id}.R"
    lang_norm = (language or "").strip().lower()
    if lang_norm.startswith("python"):
        candidates = [(py_script, "Python"), (r_script, "R")]
    elif lang_norm == "r":
        candidates = [(r_script, "R"), (py_script, "Python")]
    else:
        candidates = [(py_script, "Python"), (r_script, "R")]

    for script_path, runtime_lang in candidates:
        if os.path.lexists(script_path):
            if _is_reparse(script_path) or not script_path.is_file():
                raise WikiError(f"验证脚本必须为常规文件（禁止符号链接）: example/{script_path.name}")
            if not confined(script_path, example_dir, wiki_root) or not confined(script_path, asset, wiki_root):
                raise WikiError(f"验证脚本越界: example/{script_path.name}")
            return script_path, runtime_lang
    raise WikiError(
        f"未找到实现 {impl_id} 的验证脚本（需要 methods/{asset.name}/example/verify_{impl_id}.py 或 .R）"
    )


def _snapshot_closure_hashes(asset: Path, wiki_root: Path, rel_paths: list[str]) -> dict[str, str]:
    file_hashes: dict[str, str] = {}
    for rel in sorted(set(rel_paths)):
        target_file = asset / rel
        _assert_no_reparse_in_chain(target_file, asset, rel)
        if (
            not confined(target_file, asset, wiki_root)
            or not confined(target_file, wiki_root, wiki_root)
            or not target_file.is_file()
        ):
            raise WikiError(f"闭包声明文件不存在或越界: {rel}")
        file_hashes[rel] = _sha256_file(target_file)
    return file_hashes


def verify_method(
    config: Config,
    method_id: str,
    impl_id: str,
    *,
    timeout: int = 600,
) -> dict[str, Any]:
    """Execute `example/verify_<impl_id>.{py,R}` and write `verification/<impl_id>.json`."""
    if not isinstance(method_id, str) or not _SAFE_ID.fullmatch(method_id):
        raise WikiError(f"method_id 非法（须为小写字母数字及 -_）: {method_id!r}")
    if not isinstance(impl_id, str) or not _SAFE_ID.fullmatch(impl_id):
        raise WikiError(f"impl_id 非法（须为小写字母数字及 -_）: {impl_id!r}")

    methods_dir = config.wiki_root / "methods"
    page = methods_dir / f"{method_id}.md"
    _assert_no_reparse_in_chain(page, methods_dir, f"methods/{method_id}.md")
    if not confined(page, methods_dir, config.wiki_root) or not page.is_file():
        raise WikiError(f"方法页不存在或越界: methods/{method_id}.md")

    meta, body = read_page(page)
    if meta.get("type") != "method":
        raise WikiError(f"目标页面不是 method 类型: {method_id}")

    implementations = meta.get("implementations")
    if not isinstance(implementations, list):
        raise WikiError(f"方法 {method_id} 未声明 implementations 列表")
    impl_meta = next(
        (item for item in implementations if isinstance(item, dict) and item.get("id") == impl_id),
        None,
    )
    if impl_meta is None:
        raise WikiError(f"方法 {method_id} 未声明实现分支: {impl_id}")

    asset = page.with_suffix("")
    _assert_no_reparse_in_chain(asset, methods_dir, f"methods/{method_id}")
    if not confined(asset, methods_dir, config.wiki_root) or not asset.is_dir():
        raise WikiError(f"方法资产目录不存在: methods/{method_id}")

    manifest, manifest_issues = read_manifest(asset, page.stem, "method")
    if manifest is None:
        detail = "；".join(manifest_issues) if manifest_issues else "缺少 runtime.json"
        raise WikiError(f"方法 {method_id} 的 runtime.json 无效或缺失: {detail}")
    rt_impl = next(
        (item for item in manifest.get("implementations", []) if item.get("id") == impl_id),
        None,
    )
    if rt_impl is None:
        raise WikiError(f"runtime.json 中未声明实现分支: {impl_id}")

    script_path, runtime_lang = _locate_verify_script(
        asset,
        config.wiki_root,
        impl_id,
        str(rt_impl.get("language") or impl_meta.get("language") or ""),
    )
    code_dir = asset / "code"
    example_dir = asset / "example"

    closure_rel_paths: list[str] = list(rt_impl.get("files") or [])
    if rt_impl.get("entry_kind") != "external_program":
        entry_rel = rt_impl.get("entry")
        if isinstance(entry_rel, str) and entry_rel and entry_rel not in closure_rel_paths:
            closure_rel_paths.append(entry_rel)

    # Snapshot closure & driver hashes BEFORE execution to eliminate TOCTOU races.
    driver_sha256_before = _sha256_file(script_path)
    file_hashes_before = _snapshot_closure_hashes(asset, config.wiki_root, closure_rel_paths)

    with tempfile.TemporaryDirectory(prefix=f"rwiki-verify-{impl_id}-") as tmp_dir_str:
        tmp_out = Path(tmp_dir_str)
        if runtime_lang == "Python":
            command = [
                str(config.python_exe),
                "-X",
                "utf8",
                str(script_path.resolve()),
                "--code",
                str(code_dir.resolve()),
                "--example",
                str(example_dir.resolve()),
                "--out",
                str(tmp_out.resolve()),
            ]
            command_template = (
                f"<PYTHON> -X utf8 example/{script_path.name} "
                "--code code --example example --out <TMP_OUT>"
            )
            env = {**os.environ, "PYTHONUTF8": "1"}
        else:
            from .recipes import _r_env

            command = [
                str(config.rscript_exe),
                "--vanilla",
                str(script_path.resolve()),
                "--code",
                str(code_dir.resolve()),
                "--example",
                str(example_dir.resolve()),
                "--out",
                str(tmp_out.resolve()),
            ]
            command_template = (
                f"<RSCRIPT> --vanilla example/{script_path.name} "
                "--code code --example example --out <TMP_OUT>"
            )
            env = _r_env(config)

        try:
            proc = subprocess.run(
                command,
                cwd=asset,
                capture_output=True,
                text=True,
                env=env,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WikiError(f"验证脚本超过 {timeout} 秒未结束: example/{script_path.name}") from exc
        except OSError as exc:
            raise WikiError(f"启动验证脚本失败: {exc}") from exc

        if proc.returncode != 0:
            stderr_tail = "\n".join(proc.stderr.splitlines()[-20:])
            stdout_tail = "\n".join(proc.stdout.splitlines()[-10:])
            detail = stderr_tail or stdout_tail or "(无输出)"
            raise WikiError(
                f"验证脚本执行失败（退出码 {proc.returncode}）: example/{script_path.name}\n{detail}"
            )

        checks_file = tmp_out / "checks.json"
        if not os.path.lexists(checks_file):
            raise WikiError(f"验证脚本未生成必需的 checks.json: example/{script_path.name}")
        _assert_no_reparse_in_chain(checks_file, tmp_out, "checks.json")
        if not confined(checks_file, tmp_out, tmp_out) or not checks_file.is_file():
            raise WikiError("checks.json 必须为输出目录内的常规文件")
        try:
            checks_payload = json.loads(checks_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WikiError(f"checks.json 解析失败: {exc}") from exc
        if not isinstance(checks_payload, dict):
            raise WikiError("checks.json 必须为 JSON 对象")
        raw_checks = checks_payload.get("checks")
        raw_scope = checks_payload.get("scope")
        if (
            not isinstance(raw_checks, list)
            or not raw_checks
            or any(not isinstance(item, str) or not item.strip() for item in raw_checks)
        ):
            raise WikiError("checks.json 必须包含非空字符串列表 checks")
        if not isinstance(raw_scope, str) or not raw_scope.strip():
            raise WikiError("checks.json 必须包含非空字符串 scope")

        checks = [_sanitize_text(item.strip()) for item in raw_checks]
        scope = _sanitize_text(raw_scope.strip())
        child_env = checks_payload.get("environment") if isinstance(checks_payload.get("environment"), dict) else {}

        output_hashes: dict[str, str] = {}
        for out_entry in sorted(tmp_out.rglob("*")):
            if _is_reparse(out_entry):
                raise WikiError(f"输出目录禁止包含符号链接或目录联接: {out_entry.name}")
            if out_entry.is_file():
                _assert_no_reparse_in_chain(out_entry, tmp_out, out_entry.name)
                if not confined(out_entry, tmp_out, tmp_out):
                    raise WikiError(f"输出产物越界: {out_entry.name}")
                rel = _validate_output_rel(out_entry.relative_to(tmp_out).as_posix())
                output_hashes[rel] = _sha256_file(out_entry)

    # Re-verify driver & closure hashes AFTER execution to guarantee no concurrent tampering.
    _assert_no_reparse_in_chain(script_path, asset, f"example/{script_path.name}")
    if not script_path.is_file() or _sha256_file(script_path) != driver_sha256_before:
        raise WikiError(f"验证脚本在执行期间被修改（TOCTOU）: example/{script_path.name}")
    file_hashes_after = _snapshot_closure_hashes(asset, config.wiki_root, closure_rel_paths)
    if file_hashes_after != file_hashes_before:
        raise WikiError("闭包源文件在验证执行期间被并发修改（TOCTOU）")
    file_hashes = file_hashes_after

    environment: dict[str, str] = {
        "runtime": runtime_lang,
        "runner": "<PYTHON>" if runtime_lang == "Python" else "<RSCRIPT>",
        "platform": platform.system(),
    }
    version_key = "python_version" if runtime_lang == "Python" else "r_version"
    child_ver = child_env.get(version_key) or child_env.get("runtime_version")
    if isinstance(child_ver, str) and child_ver.strip():
        environment[version_key] = _sanitize_text(child_ver.strip())
    else:
        probed = _probe_runtime_version(config, runtime_lang, env)
        if probed:
            environment[version_key] = probed
        elif runtime_lang == "Python":
            environment["python_version"] = platform.python_version()

    receipt_data = {
        "schema_version": 1,
        "implementation": impl_id,
        "method_id": method_id,
        "state": "passed",
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": scope,
        "command": command_template,
        "driver_sha256": driver_sha256_before,
        "checks": checks,
        "environment": environment,
        "files": file_hashes,
        "output_sha256": output_hashes,
    }

    receipt_rel = f"verification/{impl_id}.json"
    verif_dir = asset / "verification"
    if os.path.lexists(verif_dir):
        _assert_no_reparse_in_chain(verif_dir, asset, f"methods/{method_id}/verification")
    verif_dir.mkdir(parents=True, exist_ok=True)
    _assert_no_reparse_in_chain(verif_dir, asset, f"methods/{method_id}/verification")
    receipt_path = verif_dir / f"{impl_id}.json"
    if os.path.lexists(receipt_path):
        _assert_no_reparse_in_chain(receipt_path, asset, receipt_rel)
    if (
        not confined(receipt_path, verif_dir, config.wiki_root)
        or not confined(receipt_path, asset, config.wiki_root)
        or not confined(receipt_path, config.wiki_root, config.wiki_root)
    ):
        raise WikiError(f"收据路径越界: {receipt_rel}")
    receipt_path.write_text(
        json.dumps(receipt_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    if impl_meta.get("verification") != receipt_rel:
        impl_meta["verification"] = receipt_rel
        write_page(page, meta, body)

    statuses = implementation_status(page)
    matched_status = next((st for st in statuses if st.get("id") == impl_id), None)
    actual_state = matched_status.get("state") if isinstance(matched_status, dict) else None
    if actual_state != "verified":
        raise WikiError(
            f"写入收据后 implementation_status 校验未达到 verified（当前为 {actual_state!r}）"
        )

    return {
        "method_id": method_id,
        "implementation": impl_id,
        "state": "verified",
        "receipt": f"methods/{method_id}/{receipt_rel}",
        "scope": scope,
        "driver_sha256": driver_sha256_before,
        "checks": checks,
        "environment": environment,
        "files": file_hashes,
        "output_sha256": output_hashes,
    }
