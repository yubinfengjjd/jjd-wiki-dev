import json
import os
import shutil
import subprocess
import sys

from conftest import SKILL_ROOT, commit_file, git_run, run_wiki, write_config
from rwiki.ghflow import DEPLOYED_ENV, hook_entry, install_hook

SKIP = shutil.ignore_patterns("__pycache__", "*.pyc")


def skill_copy(target, config_path=None, broken=False):
    """wiki.py + rwiki/ 的副本；broken 时把 push_guard.pre_push 改成直接放行（模拟检出被改坏）。"""
    target.mkdir(parents=True)
    shutil.copyfile(SKILL_ROOT / "wiki.py", target / "wiki.py")
    shutil.copytree(SKILL_ROOT / "rwiki", target / "rwiki", ignore=SKIP)
    if config_path:
        shutil.copyfile(config_path, target / "config.json")
    if broken:
        guard = target / "rwiki/push_guard.py"
        text = guard.read_text(encoding="utf-8")
        head = "def pre_push(repo: Path, remote: str, stdin: str, rules: Rules) -> int:\n"
        assert head in text
        guard.write_text(text.replace(head, head + "    return 0\n"), encoding="utf-8", newline="\n")
    return target


def run_copy(copy, cwd, *args, deployed):
    env = {**os.environ, DEPLOYED_ENV: str(deployed)}
    return subprocess.run([sys.executable, "-X", "utf8", str(copy / "wiki.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env)


def push(work, branch):
    return subprocess.run(["git", "-C", str(work), "push", "origin", branch],
                          capture_output=True, text=True, encoding="utf-8")


def test_install_hook_cli_is_idempotent_and_blocks_legacy(git_pair, tmp_path):
    """新克隆 / 新机器：gh install-hook 不需要 gh；重复安装结果不变；安装后 legacy/* 推送被拒。"""
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    result = run_wiki(work, "--config", str(config_path), "gh", "install-hook")
    assert result.returncode == 0, result.stderr
    hook = work / ".git" / "hooks" / "pre-push"
    text = hook.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n") and 'gh guard --pre-push "$1" "$2"' in text
    assert config_path.as_posix() in text and "# 来源：checkout" in text
    again = run_wiki(work, "--config", str(config_path), "gh", "install-hook")
    assert again.returncode == 0 and hook.read_text(encoding="utf-8") == text
    git_run(work, "branch", "legacy/master")
    pushed = push(work, "legacy/master")
    assert pushed.returncode != 0 and "legacy" in pushed.stderr
    assert git_run(work, "ls-remote", "origin", "refs/heads/legacy/master") == ""


def test_install_hook_by_repo_key_and_refuses_foreign_hook(git_pair, tmp_path):
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki", github={"dev_root": str(work)})
    hook = work / ".git" / "hooks" / "pre-push"
    hook.write_text("#!/bin/sh\necho 自定义\n", encoding="utf-8", newline="\n")
    refused = run_wiki(tmp_path, "--config", str(config_path), "gh", "install-hook", "--repo", "dev")
    assert refused.returncode != 0 and hook.read_text(encoding="utf-8") == "#!/bin/sh\necho 自定义\n"
    hook.unlink()
    result = run_wiki(tmp_path, "--config", str(config_path), "gh", "install-hook", "--repo", "dev")
    assert result.returncode == 0, result.stderr
    assert "gh guard --pre-push" in hook.read_text(encoding="utf-8")


def test_hook_runs_deployed_guard_even_if_checkout_is_broken(git_pair, tmp_path):
    """已部署副本存在：hook 调用副本的 wiki.py 与 config.json，检出里的 guard 改坏也照样拦下违规推送。"""
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    deployed = skill_copy(tmp_path / "deployed", config_path)
    checkout = skill_copy(tmp_path / "checkout", broken=True)
    result = run_copy(checkout, work, "--config", str(config_path), "gh", "install-hook", deployed=deployed)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["source"] == "deployed" and report["wiki_py"] == str(deployed / "wiki.py")
    assert report["config"] == str(deployed / "config.json") and "deploy.py" not in result.stderr
    text = (work / ".git/hooks/pre-push").read_text(encoding="utf-8")
    assert "# 来源：deployed" in text and (deployed / "wiki.py").as_posix() in text
    assert (checkout / "wiki.py").as_posix() not in text and (deployed / "config.json").as_posix() in text
    git_run(work, "checkout", "-q", "-b", "task/x-P1-y")
    commit_file(work, "课题/wiki-use/_project/raw.csv", "a,b\n")
    pushed = push(work, "task/x-P1-y")
    assert pushed.returncode != 0 and "project-data" in pushed.stderr
    assert git_run(work, "ls-remote", "origin", "refs/heads/task/x-P1-y") == ""


def test_hook_falls_back_to_checkout_with_warning(git_pair, tmp_path):
    """部署副本缺失或不完整：退回当前检出（现行行为），stderr 中文警告建议先运行 tools/deploy.py。"""
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "wiki.py").write_text("", encoding="utf-8")
    checkout = skill_copy(tmp_path / "checkout", broken=True)
    for deployed in (tmp_path / "missing", partial):
        result = run_copy(checkout, work, "--config", str(config_path), "gh", "install-hook", deployed=deployed)
        assert result.returncode == 0, result.stderr
        assert "tools/deploy.py" in result.stderr and "警告" in result.stderr
        report = json.loads(result.stdout)
        assert report["source"] == "checkout" and report["wiki_py"] == str(checkout / "wiki.py")
        assert report["config"] == str(config_path.resolve())
        text = (work / ".git/hooks/pre-push").read_text(encoding="utf-8")
        assert "# 来源：checkout" in text and (checkout / "wiki.py").as_posix() in text
    # 对照：退回的是被改坏的检出，违规推送不再被拦——这正是优先用部署副本的原因。
    git_run(work, "checkout", "-q", "-b", "task/x-P1-y")
    commit_file(work, "课题/wiki-use/_project/raw.csv", "a,b\n")
    assert push(work, "task/x-P1-y").returncode == 0


def test_hook_entry_parameter_overrides_default(git_pair, tmp_path, capsys):
    """进程内调用：deployed 参数可注入；install_hook 接受预先算好的 entry。"""
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    deployed = skill_copy(tmp_path / "deployed", config_path)
    entry = hook_entry(config_path, deployed)
    assert entry == {"source": "deployed", "wiki_py": str(deployed / "wiki.py"),
                     "config": str(deployed / "config.json")}
    hook = install_hook(git_pair.work, config_path, entry)
    assert (deployed / "wiki.py").as_posix() in hook.read_text(encoding="utf-8")
    assert hook_entry(config_path, tmp_path / "missing")["source"] == "checkout"
    assert "tools/deploy.py" in capsys.readouterr().err
