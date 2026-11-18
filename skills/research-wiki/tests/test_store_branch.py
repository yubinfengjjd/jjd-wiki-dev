from conftest import git_run
from rwiki.store import save, save_policy

BRANCHES = ("main", "feat/template-studio-v3", "project/glaucoma", "task/no-lock-needed")


def test_save_policy_is_plain():
    assert all(save_policy(b) == "plain" for b in BRANCHES)
    assert save_policy("") == "plain"


def test_save_commits_on_any_branch_scoped_to_wiki_subtree(wiki_repo):
    config, _, vault = wiki_repo
    wiki = config.wiki_root
    for idx, branch in enumerate(BRANCHES):
        exists = git_run(vault, "branch", "--list", branch).strip()
        git_run(vault, "checkout", "-q", *(() if exists else ("-b",)), branch)
        (wiki / "附件").mkdir(exist_ok=True)
        (wiki / f"附件/{idx}.txt").write_text(f"item {idx}\n", encoding="utf-8")
        (vault / f"文档/外部 {idx}.md").write_text("不属于知识库\n", encoding="utf-8")
        head = git_run(vault, "rev-parse", "HEAD").strip()
        save(config, f"save {idx}")
        new_head = git_run(vault, "rev-parse", "HEAD").strip()
        assert new_head != head
        changed = git_run(vault, "-c", "core.quotePath=false", "diff-tree", "--no-commit-id",
                          "--name-only", "-r", "-z", head, new_head).split("\0")
        assert all(path.startswith("知识库/") for path in changed if path)
        assert git_run(vault, "status", "--porcelain", "--", "知识库").strip() == ""
        assert git_run(vault, "status", "--porcelain", "--", "文档").strip()
