"""Regenerates icons/icon{16,32,48,128}.png. Run: python tools/make_icons.py"""
from pathlib import Path

from PIL import Image, ImageDraw

S = 1024
BLUE = (15, 108, 189, 255)
PAPER = (248, 245, 236, 255)
FOLD = (196, 214, 232, 255)
LINE = (150, 182, 214, 255)
GREEN = (30, 123, 52, 255)
WHITE = (255, 255, 255, 255)


def draw() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=230, fill=BLUE)

    # index-card page with a folded corner
    l, t, r, b, fold = 250, 170, 730, 830, 150
    d.polygon([(l, t), (r - fold, t), (r, t + fold), (r, b), (l, b)], fill=PAPER)
    d.polygon([(r - fold, t), (r - fold, t + fold), (r, t + fold)], fill=FOLD)
    for i, y in enumerate((400, 500, 600)):
        d.rounded_rectangle((l + 80, y, r - (80 if i < 2 else 230), y + 44), radius=22, fill=LINE)

    # "last update" clock badge
    cx, cy, rad = 720, 760, 210
    d.ellipse((cx - rad - 40, cy - rad - 40, cx + rad + 40, cy + rad + 40), fill=BLUE)
    d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=GREEN)
    w = 52
    d.line((cx, cy, cx, cy - 130), fill=WHITE, width=w)
    d.line((cx, cy, cx + 100, cy + 60), fill=WHITE, width=w)
    d.ellipse((cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2), fill=WHITE)
    for x, y in ((cx, cy - 130), (cx + 100, cy + 60)):
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=WHITE)
    return img


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "icons"
    out.mkdir(exist_ok=True)
    big = draw()
    for size in (16, 32, 48, 128):
        big.resize((size, size), Image.LANCZOS).save(out / f"icon{size}.png")
    print("wrote", sorted(p.name for p in out.glob("icon*.png")))


if __name__ == "__main__":
    main()
