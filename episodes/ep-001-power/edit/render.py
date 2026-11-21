"""Render the episode from the approved-for-edit voice take, cue sheet and hourly prices."""

import argparse
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EP = Path(__file__).resolve().parents[1]
INK, PAPER, LIME, TEAL, DIM = "#122C31", "#F5F1DF", "#DCFA67", "#00756D", "#53716F"


@lru_cache(None)
def font(size, bold=True):
    name = "Bold" if bold else "Regular"
    return ImageFont.truetype(
        f"/usr/share/fonts/opentype/noto/NotoSansCJK-{name}.ttc", size, index=1
    )


def label(draw, xy, text, size, color=INK, bold=True, anchor="la"):
    draw.text(xy, text, font=font(size, bold), fill=color, anchor=anchor)


def washer(draw, x, y, size):
    w = size
    draw.rounded_rectangle(
        (x, y, x + w, y + w), radius=22, fill=PAPER, outline=INK, width=6
    )
    draw.line((x + 3, y + w * 0.23, x + w - 3, y + w * 0.23), fill=INK, width=5)
    draw.rounded_rectangle(
        (x + w * 0.09, y + w * 0.08, x + w * 0.35, y + w * 0.15), 4, fill=TEAL
    )
    for frac in (0.72, 0.85):
        cx = x + w * frac
        cy = y + w * 0.12
        draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=INK)
    cx, cy, r = x + w * 0.5, y + w * 0.60, w * 0.305
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=TEAL, outline=INK, width=6)
    draw.chord(
        (cx - r * 0.80, cy - r * 0.80, cx + r * 0.80, cy + r * 0.80), 10, 166, fill=LIME
    )
    draw.arc(
        (cx - r * 0.72, cy - r * 0.72, cx + r * 0.72, cy + r * 0.72),
        195,
        268,
        fill=PAPER,
        width=6,
    )


def thumbnail():
    im = Image.new("RGB", (1280, 720), LIME)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((-138, 455, 680, 920), 120, fill="#BED947")
    d.line((70, 106, 745, 106), fill=INK, width=3)
    label(d, (73, 51), "독일 전력시장   /   실제 가격표", 31, INK)
    label(d, (62, 151), "전기값이", 108)
    label(d, (60, 288), "마이너스?", 124)
    washer(d, 846, 166, 338)
    d.rounded_rectangle((76, 538, 724, 623), 14, fill=INK)
    label(d, (103, 544), "−135.45 유로 / MWh", 48, LIME)
    im.save(EP / "thumbnail/thumbnail.jpg", quality=93)


def main():
    from motion import film, prepare

    parser = argparse.ArgumentParser(description="EP-001 실사·모션 마스터 재생성")
    parser.add_argument("--sources", type=Path, help="직접 보관한 원본 촬영본 폴더")
    args = parser.parse_args()
    sources = args.sources
    if sources is None:
        prepare.main()
        sources = prepare.WORK / "footage"
    thumbnail()
    film.build(
        sources.resolve(),
        EP / "edit/master.mp4",
        film.ROOT / "renders/day-ahead.mp4",
        film.ROOT / "renders/tariff.mp4",
    )


if __name__ == "__main__":
    main()
