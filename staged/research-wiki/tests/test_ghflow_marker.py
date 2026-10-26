import random

from rwiki.ghflow import add_migrated_marker

SEED = 20261103
ITERATIONS = 300
PIECES = (b"\xef\xbb\xbf", b"# \xe4\xbb\xbb\xe5\x8a\xa1\xe4\xb9\xa6", b"\r\n", b"\n", b"text", b"\x00\xff", b" ")


def test_migrated_marker_is_idempotent_and_keeps_bytes():
    """Feature: github-structured-workflow, Property 15: 迁移标记幂等且保留原字节"""
    rng = random.Random(SEED)
    for iteration in range(ITERATIONS):
        data = b"".join(rng.choice(PIECES) for _ in range(rng.randint(0, 12)))
        url = f"https://github.com/tester/research-wiki-dev/issues/{rng.randint(1, 999)}"
        header = add_migrated_marker(b"", url)
        result = data
        for _ in range(rng.randint(1, 4)):
            result = add_migrated_marker(result, url)
        assert result.count(b"<!-- rwiki-migrated:") == 1, f"seed={SEED} iteration={iteration}"
        assert result == header + data, f"seed={SEED} iteration={iteration}"
        assert result[len(header):] == data
        assert f"已迁移，停止维护：{url}".encode() in header
