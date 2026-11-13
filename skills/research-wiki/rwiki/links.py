import re
from pathlib import Path


def extract_links(body: str) -> list[str]:
    visible = []
    fence = 0
    for line in body.splitlines(keepends=True):
        marker = re.match(r"\s*(`{3,})(.*)$", line)
        if marker:
            length = len(marker[1])
            if not fence:
                fence = length
            elif length >= fence and not marker[2].strip():
                fence = 0
        elif not fence:
            visible.append(line)
    text = re.sub(r"(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)", "", "".join(visible))
    return [match.split("|", 1)[0].split("#", 1)[0].strip()
            for match in re.findall(r"!?\[\[([^\]\n]+)\]\]", text)]


def resolve(wiki_root: Path, target: str) -> Path:
    path = Path(target)
    if not path.suffix:
        path = path.with_suffix(".md")
    return wiki_root / path
