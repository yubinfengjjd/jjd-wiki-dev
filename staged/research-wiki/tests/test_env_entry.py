"""运行入口：config.env 合并进进程环境，stdout/stderr 统一 UTF-8。"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rwiki.config import load_config, prepare_env
from rwiki.errors import WikiError

SKILL_ROOT = Path(__file__).resolve().parents[1]


def _config(tmp_path, **extra):
    values = {key: str(tmp_path) for key in ("wiki_root", "gallery_root", "taxonomy")}
    values.update(python_exe=sys.executable, rscript_exe="Rscript", port=8765, **extra)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
    return path


def test_env_defaults_to_empty(tmp_path):
    assert load_config(_config(tmp_path)).env == {}


@pytest.mark.parametrize("env", [[], {"vars": {"A": 1}}, {"vars": []}, {"path_prepend": "x"},
                                 {"path_prepend": [1]}, {"other": {}}])
def test_bad_env_is_error(tmp_path, env):
    with pytest.raises(WikiError, match="env"):
        load_config(_config(tmp_path, env=env))


# 下列测试用独立的 environ 字典，不写进程环境，避免泄漏到同进程后面的测试。
def test_existing_env_beats_config_beats_default(tmp_path):
    environ = {"HTTPS_PROXY": "http://already:1"}
    config = load_config(_config(tmp_path, env={"vars": {
        "HTTPS_PROXY": "http://config:2", "RWIKI_TEST_FROM_CONFIG": "yes"}}))
    prepare_env(config, environ)
    assert environ["HTTPS_PROXY"] == "http://already:1"
    assert environ["RWIKI_TEST_FROM_CONFIG"] == "yes"
    assert environ["GH_PROMPT_DISABLED"] == "1"  # 缺省只在未设置时补


def test_config_overrides_default_and_existing_overrides_default(tmp_path):
    environ = {}
    prepare_env(load_config(_config(tmp_path, env={"vars": {"GH_PROMPT_DISABLED": "0"}})), environ)
    assert environ["GH_PROMPT_DISABLED"] == "0"
    environ = {"GH_PROMPT_DISABLED": "keep"}
    prepare_env(load_config(_config(tmp_path)), environ)
    assert environ["GH_PROMPT_DISABLED"] == "keep"


def test_git_identity_not_injected_by_default(tmp_path):
    environ = {}
    prepare_env(load_config(_config(tmp_path)), environ)
    assert not any(key.startswith(("GIT_AUTHOR", "GIT_COMMITTER")) for key in environ)
    prepare_env(load_config(_config(tmp_path, env={"vars": {"GIT_AUTHOR_NAME": "显式"}})), environ)
    assert environ["GIT_AUTHOR_NAME"] == "显式"


@pytest.mark.parametrize("name", ["RWIKI_AGENT", "RWIKI_WIKI_ROOT", "RWIKI_BOOTSTRAP", "GIT_DIR",
                                  "git_work_tree", "GIT_INDEX_FILE", "PATH", "Path"])
def test_dangerous_env_names_rejected(tmp_path, name):
    with pytest.raises(WikiError, match=name):
        load_config(_config(tmp_path, env={"vars": {name: "x"}}))


def test_path_prepend_dedup_and_skip_missing(tmp_path):
    present, other = tmp_path / "gh", tmp_path / "已在"
    present.mkdir()
    other.mkdir()
    environ = {"PATH": os.pathsep.join([str(other), "base"])}
    config = load_config(_config(tmp_path, env={"path_prepend": [
        str(present), str(tmp_path / "不存在"), str(other), str(present)]}))
    prepare_env(config, environ)
    prepare_env(config, environ)  # 重复调用也不重复添加
    assert environ["PATH"].split(os.pathsep) == [str(present), str(other), "base"]


def test_chinese_error_is_utf8_on_stderr(tmp_path):
    """不依赖 -X utf8 / PYTHONIOENCODING，入口自己把 stderr 设成 UTF-8。"""
    values = {key: str(tmp_path) for key in ("wiki_root", "gallery_root", "taxonomy")}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    env = {key: value for key, value in os.environ.items()
           if key not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    result = subprocess.run([sys.executable, str(SKILL_ROOT / "wiki.py"), "--config", str(path), "lint"],
                            capture_output=True, env=env, cwd=SKILL_ROOT, timeout=120)
    assert result.returncode == 1
    assert "配置缺少" in result.stderr.decode("utf-8")
