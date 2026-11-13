import random

from conftest import git_init, git_run
from rwiki.push_guard import USER_BLOCK, check_baseline, write_baseline

SEED = 20261029
ITERATIONS = 100
TEXT = "ab cd\n\r\n中文x\t"
REPLACEMENTS = b"az \r\n\xe4"


def random_text(rng, limit=12):
    return "".join(rng.choice(TEXT) for _ in range(rng.randint(0, limit)))


def random_page(rng) -> bytes:
    parts = [random_text(rng)]
    for _ in range(rng.randint(0, 3)):
        parts.append(f"<!-- user:start -->{random_text(rng)}<!-- user:end -->")
        parts.append(random_text(rng))
    return "".join(parts).encode("utf-8")


def inside_block(data: bytes, position: int) -> bool:
    return any(match.start() <= position < match.end() for match in USER_BLOCK.finditer(data))


def test_baseline_detects_exactly_author_block_changes(tmp_path):
    """Feature: github-structured-workflow, Property 5: 作者块基准只锁作者内容"""
    root = git_init(tmp_path / "wiki")
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        pages = {f"p{index}.md": random_page(rng) for index in range(rng.randint(1, 3))}
        pages["p0.md"] += b"<!-- user:start -->\r\nauthor\n<!-- user:end -->\n"
        for stale in root.glob("p*.md"):
            stale.unlink()
        for name, data in pages.items():
            (root / name).write_bytes(data)
        git_run(root, "add", "-A")
        write_baseline(root)
        assert check_baseline(root) == [], f"seed={SEED} iteration={iteration}"
        name = rng.choice(sorted(pages))
        data = pages[name]
        newlines = [index for index, byte in enumerate(data) if byte == 0x0A]
        if newlines and rng.random() < 0.35:
            # 行尾变化：在某个 \n 前插入或删去 \r。
            index = rng.choice(newlines)
            changed = (data[:index - 1] + data[index:] if index and data[index - 1] == 0x0D
                       else data[:index] + b"\r" + data[index:])
            expected = inside_block(data, index)
        else:
            index = rng.randrange(len(data))
            byte = rng.choice([b for b in REPLACEMENTS if b != data[index]])
            changed = data[:index] + bytes([byte]) + data[index + 1:]
            expected = inside_block(data, index)
        (root / name).write_bytes(changed)
        problems = check_baseline(root)
        assert bool(problems) == expected, f"seed={SEED} iteration={iteration} page={name} index={index}"
        (root / name).write_bytes(data)
