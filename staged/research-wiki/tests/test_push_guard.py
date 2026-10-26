import random

import pytest

from rwiki.errors import WikiError
from rwiki.push_guard import GPL_MARKERS, Rules, classify, find_abs_paths, parse_allow

SEED = 20261027
ITERATIONS = 400
MAX_BYTES = 1000
GPL_DIRS = ("知识库/methods/gplm/code/", "知识库/methods/gplm/source/")
DIRS = ("画廊/2026-x/figures", "知识库/methods/gplm/code", "知识库/methods/gplm/source",
        "知识库/methods/okm/code", "vendor/SCP-local/R", "课题/wiki-use/_project", "docs", "",
        "知识库/methods/gplm", "a/wiki-use/_project/deep")
NAMES = ("a.py", "b.R", "LICENSE", "license.md", "notes.md", "img.png", "link.lnk", "data.json", "x.sh")
LINES = ("plain text", r"path E:\data\x.csv", "/Users/bob/project", "https://example.org/a", "C:/tmp/y",
         "ratio 3:/4", "json \"E:\\\\research\"")
# 标记由 GPL_MARKERS 拼出，本文件头不含完整标记，自身不会被 gpl-header 拦截。
HEADS = (b"", f"# {GPL_MARKERS[0]} v3".encode(), f"# {GPL_MARKERS[1]}-3.0-or-later".encode(),
         f"{GPL_MARKERS[3]}-2.1".encode(), b"\0\x89PNG binary", b"MIT License")
# 每条豁免与参考模型中的谓词一一对应。
ALLOW = {("abs-path", "docs/**"): lambda segs: segs[0] == "docs",
         ("size", "**/*.png"): lambda segs: segs[-1].endswith(".png"),
         ("abs-path", "**/*.lnk"): lambda segs: segs[-1].endswith(".lnk"),
         ("size", "画廊/**"): lambda segs: segs[0] == "画廊",
         ("abs-path", "知识库/**"): lambda segs: segs[0] == "知识库"}
ABSOLUTE = (r"E:\data", "/Users/bob/", "C:/tmp", "E:\\\\research")


def reference(path, size, added, head, allow):
    """独立实现的参考模型：返回命中规则集合。"""
    segs = path.split("/")
    name = segs[-1]
    hits = set()
    if segs[0] == "画廊":
        hits.add("gallery")
    if any(segs[i] == "wiki-use" and segs[i + 1] == "_project" for i in range(len(segs) - 2)):
        hits.add("project-data")
    if path.startswith(GPL_DIRS) or "SCP-local" in segs[:-1]:
        hits.add("gpl-path")
    code = name.rsplit(".", 1)[-1].lower() in ("py", "r", "sh") if "." in name else False
    if (code or name.upper().startswith("LICENSE")) and any(m.encode() in head for m in GPL_MARKERS):
        hits.add("gpl-header")
    if size > MAX_BYTES:
        hits.add("size")
    if name.endswith(".lnk") or (b"\0" not in head and any(a in line for line in added for a in ABSOLUTE)):
        hits.add("abs-path")
    for (rule, _), predicate in ALLOW.items():
        if (rule, _) in allow and rule in hits and predicate(segs):
            hits.discard(rule)
    return hits


def test_classify_matches_reference_model():
    """Feature: github-structured-workflow, Property 2: 规则分类与参考模型一致"""
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        directory = rng.choice(DIRS)
        path = f"{directory}/{rng.choice(NAMES)}" if directory else rng.choice(NAMES)
        size = rng.randint(0, 2 * MAX_BYTES)
        added = rng.sample(LINES, rng.randint(0, 3))
        head = rng.choice(HEADS)
        allow = tuple(rng.sample(sorted(ALLOW), rng.randint(0, len(ALLOW))))
        rules = Rules(MAX_BYTES, ("**/SCP-local/**",), GPL_MARKERS, GPL_DIRS, allow)
        got = {rule for rule, _ in classify(path, size, added, head, rules)}
        assert got == reference(path, size, added, head, allow), \
            f"seed={SEED} iteration={iteration} path={path} size={size} added={added} head={head} allow={allow}"
        # 豁免永远去不掉画廊、GPL、课题数据。
        everything = Rules(MAX_BYTES, ("**/SCP-local/**",), GPL_MARKERS, GPL_DIRS,
                           (("abs-path", "**"), ("size", "**")))
        kept = {rule for rule, _ in classify(path, size, added, head, everything)}
        protected = reference(path, size, added, head, ()) & {"gallery", "gpl-path", "gpl-header", "project-data"}
        assert kept == protected and protected <= got, f"seed={SEED} iteration={iteration} path={path}"


def test_allow_rejects_protected_rules_and_missing_reasons():
    """Feature: github-structured-workflow, Property 2: 规则分类与参考模型一致（豁免文件解析）"""
    rng = random.Random(SEED + 1)
    for iteration in range(ITERATIONS):
        rule = rng.choice(("gallery", "gpl-path", "gpl-header", "project-data", "secret", "abs-path", "size"))
        reason = rng.choice(("  # 本地复核回执", "", "  #   "))
        text = f"# 注释行\n\n{rule} 知识库/**/verification/**{reason}\n"
        if rule in ("abs-path", "size") and reason.strip("# "):
            assert parse_allow(text) == ((rule, "知识库/**/verification/**"),), f"seed={SEED + 1} iteration={iteration}"
        else:
            with pytest.raises(WikiError):
                parse_allow(text)


def test_find_abs_paths_examples():
    assert find_abs_paths(r"见 E:\research-wiki\x 与 C:/Users/me") == ["E:\\", "C:/"]
    assert find_abs_paths('{"p": "E:\\\\research"}') == ["E:\\"]
    assert find_abs_paths("/Users/alice/a and /home/bob/b") == ["/Users/alice/", "/home/bob/"]
    assert find_abs_paths("https://github.com/x and ratio 3:/4 and data:/x") == []
