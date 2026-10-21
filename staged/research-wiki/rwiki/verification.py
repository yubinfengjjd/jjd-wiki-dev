import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def record_preview(target: Path, mean: float | None = None) -> None:
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "exit_code": 0}
    if mean is not None:
        record["mean_absolute_difference"] = mean
    (target / "verify/verify.json").write_text(json.dumps(record, indent=2) + "\n",
                                             encoding="utf-8", newline="\n")
    shutil.copyfile(target / "verify/figure.png", target / "preview.png")


def compare_images(original: Path, output: Path) -> tuple[float, Path]:
    with Image.open(original) as source, Image.open(output) as rendered:
        left, right = source.convert("RGB"), rendered.convert("RGB")
    height = min(left.height, right.height)
    left = left.resize((round(left.width * height / left.height), height), Image.Resampling.LANCZOS)
    right = right.resize((round(right.width * height / right.height), height), Image.Resampling.LANCZOS)
    compare = Image.new("RGB", (left.width + 24 + right.width, height), "white")
    compare.paste(left, (0, 0))
    compare.paste(right, (left.width + 24, 0))
    path = output.parent / "compare.png"
    compare.save(path)
    difference = ImageChops.difference(left, right.resize(left.size, Image.Resampling.LANCZOS))
    return sum(ImageStat.Stat(difference).mean) / 3, path
