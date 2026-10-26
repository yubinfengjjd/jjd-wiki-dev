import subprocess

from conftest import git_run, run_wiki, write_config


def test_install_hook_cli_is_idempotent_and_blocks_legacy(git_pair, tmp_path):
    """新克隆 / 新机器：gh install-hook 不需要 gh；重复安装结果不变；安装后 legacy/* 推送被拒。"""
    work = git_pair.work
    config_path = write_config(tmp_path / "c.json", tmp_path / "no-wiki")
    result = run_wiki(work, "--config", str(config_path), "gh", "install-hook")
    assert result.returncode == 0, result.stderr
    hook = work / ".git" / "hooks" / "pre-push"
    text = hook.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n") and 'gh guard --pre-push "$1" "$2"' in text
    assert config_path.as_posix() in text
    again = run_wiki(work, "--config", str(config_path), "gh", "install-hook")
    assert again.returncode == 0 and hook.read_text(encoding="utf-8") == text
    git_run(work, "branch", "legacy/master")
    pushed = subprocess.run(["git", "-C", str(work), "push", "origin", "legacy/master"], capture_output=True,
                            text=True, encoding="utf-8")
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
