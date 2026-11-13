from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .errors import WikiError
from .pages import visual_path
from .templates import ready_page

FONT_PATH = Path("C:/Windows/Fonts/msyh.ttc")


def contact_sheet(config: Config, entry_ids: list[str], out: Path) -> Path:
    if not 1 <= len(entry_ids) <= 3:
        raise WikiError("候选拼图需要 1–3 个模板 id")
    pages = [ready_page(config, entry_id)[0] for entry_id in entry_ids]
    if not FONT_PATH.is_file():
        raise WikiError(f"中文字体不存在: {FONT_PATH}")
    number_font = ImageFont.truetype(str(FONT_PATH), 52)
    title_font = ImageFont.truetype(str(FONT_PATH), 32)
    previews = []
    for entry_id in entry_ids:
        path = visual_path(config.wiki_root, entry_id).with_suffix("") / "preview.png"
        if not path.is_file():
            raise WikiError(f"缺少 preview.png: {entry_id}")
        with Image.open(path) as source:
            previews.append(source.convert("RGBA").resize(
                (900, round(source.height * 900 / source.width)), Image.Resampling.LANCZOS))
    sheet = Image.new("RGB", (len(pages) * 900 + (len(pages) - 1) * 40,
                              110 + max(image.height for image in previews)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (meta, preview) in enumerate(zip(pages, previews)):
        x = index * 940
        title = meta["title"]
        if draw.textlength(title, font=title_font) > 795:
            while draw.textlength(title + "…", font=title_font) > 795:
                title = title[:-1]
            title += "…"
        draw.text((x + 20, 10), str(index + 1), fill="black", font=number_font)
        draw.text((x + 85, 28), title, fill="black", font=title_font)
        sheet.paste(preview, (x, 110), preview)
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, format="PNG")
    return out
