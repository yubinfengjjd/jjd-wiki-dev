import json
import re

import pytest

from conftest import DEV_ROOT, SKILL_ROOT

VAULT_ROOT = DEV_ROOT.parent
PR_SECTIONS = ("关联 Issue", "改动摘要", "测试结果（CI）", "本地专属验证", "受保护字节核验", "未完成项")
ISSUE_SECTIONS = ("目标", "验收标准", "本地证据", "验收结论")


def check_repo_files(root):
    template = (root / ".github/pull_request_template.md").read_text(encoding="utf-8")
    assert re.findall(r"^## (.+)$", template, re.M) == list(PR_SECTIONS)
    issue = (root / ".github/ISSUE_TEMPLATE/task.md").read_text(encoding="utf-8")
    assert "<!-- rwiki-task:" in issue
    assert re.findall(r"^## (.+)$", issue, re.M) == list(ISSUE_SECTIONS)
    pytest_lines = [line for line in (root / ".github/workflows/ci.yml").read_text(encoding="utf-8").splitlines()
                    if "-m pytest" in line]
    assert pytest_lines and all("not local" in line for line in pytest_lines)
    assert "* -text" in (root / ".gitattributes").read_text(encoding="utf-8").splitlines()


def test_dev_repo_files():
    check_repo_files(DEV_ROOT)
    ci = (DEV_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "not r and not compose and not local" in ci
    assert "gh guard --range origin/${{ github.base_ref }}..HEAD" in ci
    config = json.loads((DEV_ROOT / "ci/config.ci.json").read_text(encoding="utf-8"))
    assert "push_guard" not in config
    example = json.loads((SKILL_ROOT / "config.example.json").read_text(encoding="utf-8"))
    assert set(config) <= set(example)


@pytest.mark.local
def test_vault_repo_files():
    check_repo_files(VAULT_ROOT)
    ci = (VAULT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for needle in ("secrets.DEV_DEPLOY_KEY", "lint --ci", "gh protect-baseline --check", "tools/tests"):
        assert needle in ci
