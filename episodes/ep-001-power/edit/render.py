"""Render the episode from the approved-for-edit voice take, cue sheet and hourly prices."""

import argparse
import io
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

EP = Path(__file__).resolve().parents[1]


def frame(path, second):
    output = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            str(second),
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=1280:720",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-threads",
            "1",
            "-",
        ]
    )
    return Image.open(io.BytesIO(output)).convert("RGB")


def thumbnail(sources):
    # Source coordinates measured on the 640 x 360 preview at exactly 00:53.
    washer = frame(sources / "laundry.webm", 53)
    mask = Image.new("L", washer.size)
    outline = [
        (86, 52),
        (92, 43),
        (110, 37),
        (244, 8),
        (288, 2),
        (346, 0),
        (370, 8),
        (382, 25),
        (391, 69),
        (401, 107),
        (407, 159),
        (410, 217),
        (406, 282),
        (396, 320),
        (375, 360),
        (108, 360),
        (96, 313),
        (90, 249),
        (85, 160),
        (83, 96),
    ]
    ImageDraw.Draw(mask).polygon([(2 * x, 2 * y) for x, y in outline], fill=255)
    # Keep the lower crop below the fade and leave the chimney visible at left.
    washer = washer.crop((150, 0, 834, 720)).resize(
        (500, 526), Image.Resampling.LANCZOS
    )
    mask = mask.crop((150, 0, 834, 720)).resize(washer.size, Image.Resampling.LANCZOS)
    scene = frame(sources / "grid.webm", 8).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    scene = Image.blend(scene, Image.new("RGB", scene.size, "#0B1722"), 0.30)
    edge = mask.filter(ImageFilter.MaxFilter(11))
    scene.paste("#FBF8EC", (567, 18, 1067, 544), edge)
    scene.paste(washer, (567, 18), mask)
    fade = Image.new("L", (1, 720))
    fade.putdata([round(255 * min(1, max(0, (y - 290) / 245))) for y in range(720)])
    scene.paste("#070B10", (0, 0, 1280, 720), fade.resize(scene.size))
    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    previews = Image.new("RGB", (684, 340), "#20272C")
    labels = ImageDraw.Draw(previews)
    for column, (file, second_line) in enumerate(
        (
            ("thumbnail.jpg", "−135.45유로"),
            ("thumbnail-alt.jpg", "마이너스였다"),
        )
    ):
        image = scene.copy()
        draw = ImageDraw.Draw(image)
        for xy, text, size, color in (
            ((55, 400), "도매 전력 1 MWh", 101, "#FFFCF3"),
            ((48, 528), second_line, 145, "#FFE565"),
        ):
            draw.text(
                xy,
                text,
                font=ImageFont.truetype(font_path, size, index=1),
                anchor="lt",
                fill=color,
                stroke_width=2,
                stroke_fill="#111419",
            )
        image.save(EP / "thumbnail" / file, quality=94, subsampling=0)
        x = 14 + 336 * column
        labels.text(
            (x, 7),
            f"{'B' if column else 'A'}  /  320 px · 160 px",
            font=ImageFont.truetype(font_path, 16),
            fill="white",
        )
        for width, top in ((320, 42), (160, 237)):
            small = image.resize((width, width * 9 // 16), Image.Resampling.LANCZOS)
            d = ImageDraw.Draw(small)
            right, bottom = small.width - 3, small.height - 3
            d.rounded_rectangle(
                (right - 34, bottom - 14, right, bottom), radius=2, fill="#131313"
            )
            d.text(
                (right - 2, bottom - 2),
                "2:18",
                font=ImageFont.truetype(font_path, 11),
                anchor="rb",
                fill="white",
            )
            previews.paste(small, (x, top))
    previews.save(EP / "thumbnail/mobile-review.jpg", quality=94)


def main():
    from motion import film, prepare

    parser = argparse.ArgumentParser(description="EP-001 실사·모션 마스터 재생성")
    parser.add_argument("--sources", type=Path, help="직접 보관한 원본 촬영본 폴더")
    args = parser.parse_args()
    sources = args.sources
    if sources is None:
        prepare.main()
        sources = prepare.WORK / "footage"
    thumbnail(sources.resolve())
    film.build(
        sources.resolve(),
        EP / "edit/master.mp4",
        film.ROOT / "renders/day-ahead.mp4",
        film.ROOT / "renders/tariff.mp4",
    )


if __name__ == "__main__":
    main()
