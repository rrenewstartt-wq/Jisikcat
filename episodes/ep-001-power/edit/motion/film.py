"""Cut licensed location footage against the EP-001 narration and animate its evidence."""

import argparse
import csv
import json
import math
import os
import subprocess as sp
import tempfile
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
EP = ROOT.parents[1]
W, H, FPS = 1280, 720, 24
INK = (10, 18, 29)
WHITE = "#FCF9EF"
GOLD = "#FFE565"
CYAN = "#77F0D6"
MUTED = "#BCCBD3"
SHOTS = list(csv.DictReader((ROOT / "shots.csv").open()))
LENGTH = math.ceil(json.loads((EP / "edit/timings.json").read_text())[-1][1] * FPS)
FILES = {
    "laundry": "laundry.webm",
    "drum": "drum.mp4",
    "grid": "grid.webm",
    "power": "power.webm",
}
CREDITS = {
    "laundry": "자료화면  ·  SGMaheshwari",
    "drum": "자료화면  ·  Mixkit",
    "grid": "함부르크 무어부르크 발전소  ·  Cvoelker  /  자료화면",
    "power": "발전소 야경  ·  klimets  /  자료화면",
}


def clamp(value, lo=0, hi=1):
    return min(hi, max(lo, value))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


@lru_cache(None)
def font(size, bold):
    weight = "Bold" if bold else "Regular"
    return ImageFont.truetype(
        f"/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc", size, index=1
    )


@lru_cache(600)
def lettering(s, size, color, bold):
    face = font(size, bold)
    left, top, right, bottom = face.getbbox(s, anchor="lt")
    sprite = Image.new("RGBA", (max(1, right - left + 4), max(1, bottom - top + 5)))
    ImageDraw.Draw(sprite).text(
        (2 - left, 2 - top), s, font=face, fill=color, anchor="lt", stroke_width=0
    )
    return sprite


def write(im, x, y, s, size, color=WHITE, bold=True):
    layer = lettering(s, size, color, bold)
    im.paste(layer, (round(x), round(y)), layer)


@lru_cache(12)
def shade(strength):
    gradient = Image.new("L", (128, 72))
    gradient.putdata(
        [
            int(
                255
                * clamp(
                    strength + 0.33 * (1 - x / 127) + 0.16 * max(0, (y - 45) / 26),
                    0,
                    0.92,
                )
            )
            for y in range(72)
            for x in range(128)
        ]
    )
    return gradient.resize((W, H), Image.Resampling.BILINEAR)


def transit(im, t, mode):
    d = ImageDraw.Draw(im)
    write(im, 74, 157, "판매자", 57)
    write(im, 987, 157, "구매자", 57)
    for row, (name, color) in enumerate(
        [("전력 인도", CYAN), ("음수 가격 정산금", GOLD)]
    ):
        if row and mode == "delivery":
            continue
        y = 304 + row * 118
        write(im, 76, y - 34, name, 27, color)
        d.line((275, y, 1120, y), fill="#8D9DA7", width=3)
        for j in range(5):
            x = 279 + ((t * 152 + j * 163) % 815)
            d.polygon([(x, y - 10), (x + 18, y), (x, y + 10)], fill=color)
    write(im, 77, 526, "하루 전 시장에서 해당 가격으로 거래한 경우", 22, MUTED)


def blocks(im, t):
    p = ease((t - 50.29) / 4.7)
    d = ImageDraw.Draw(im)
    write(im, 75, 147, "1 MWh", 75)
    write(im, 78, 256, "= 1,000 kWh", 62, CYAN)
    write(im, 80, 370, "한 층 100 kWh × 10층", 28)
    for z in range(10):
        cx = 904 + int(28 * math.sin(0.55 * t))
        cy = 445 - z * (11 + 8 * p)
        step = 12
        dy = 4.1
        d.polygon(
            [(cx, cy - 10 * dy), (cx + 120, cy), (cx, cy + 10 * dy), (cx - 120, cy)],
            fill="#7DE7CB",
        )
        d.polygon(
            [
                (cx - 120, cy),
                (cx, cy + 10 * dy),
                (cx, cy + 10 * dy + 9),
                (cx - 120, cy + 9),
            ],
            fill="#237D76",
        )
        d.polygon(
            [
                (cx + 120, cy),
                (cx, cy + 10 * dy),
                (cx, cy + 10 * dy + 9),
                (cx + 120, cy + 9),
            ],
            fill="#2CA591",
        )
        for n in range(11):
            d.line(
                [
                    (cx + n * step, cy - 10 * dy + n * dy),
                    (cx - 120 + n * step, cy + n * dy),
                ],
                fill="#307D78",
                width=1,
            )
            d.line(
                [
                    (cx - n * step, cy - 10 * dy + n * dy),
                    (cx + 120 - n * step, cy + n * dy),
                ],
                fill="#307D78",
                width=1,
            )


def title(im, small, main, t, color=GOLD):
    x = 74 + 30 * (1 - ease(t / 0.5))
    write(im, x, 181, small, 26, CYAN)
    write(im, x - 2, 241, main, 67, color)


def plant_cost(im, t):
    elapsed = t - 65.17
    draw = ImageDraw.Draw(im)
    write(im, 75, 104, "가상 발전기   /   1시간에 1 MWh", 29, CYAN)
    write(im, 72, 158, "한 시간의 선택", 62)
    # Each bar uses the same zero and euros-per-pixel scale.
    for y, label, amount, color, delay in (
        (295, "계속 가동", 155.45, CYAN, 0),
        (391, "정지 후 재가동", 200, GOLD, 1),
    ):
        write(im, 75, y, label, 31)
        x = 367
        draw.line((x, y + 23, x + 410, y + 23), fill="#405056", width=12)
        width = round(amount * 2.05 * ease((elapsed - delay) / 1.1))
        if width:
            draw.line((x, y + 23, x + width, y + 23), fill=color, width=12)
        write(im, 811, y - 4, f"{amount:g} 유로", 41, color)
    if elapsed < 4.8:
        write(im, 76, 500, "가동 손실 = 정산금 135.45 + 가정한 변동비 20유로", 30)
    else:
        write(im, 76, 499, "계속 가동하면 44.55유로 절감", 44, CYAN)


def retail_clause(im, t, extras):
    # Re-typeset the two relevant rows of the public 2025 tariff.
    x = 74 + round(18 * (1 - ease((t - 91.92) / 0.55)))
    d = ImageDraw.Draw(im)
    paper = "#F5EFDC"
    ink = "#172B2D"
    d.rectangle((x, 101, x + 1102, 553), fill=paper)
    write(im, x + 35, 125, "Stadtwerke Haltern am See   /   Dynamischer Tarif", 29, ink)
    write(im, x + 35, 181, "독일 할테른   ·   2025.01.01 시행", 36, ink)
    d.line((x + 36, 251, x + 1064, 251), fill="#6B7876", width=2)
    y = 363 if extras else 263
    progress = ease((t - (95.67 if extras else 91.92)) / 0.65)
    d.rectangle((x + 30, y, x + 30 + round(1030 * progress), y + 78), fill="#C0E9CF")
    write(im, x + 44, 282, "시간별 EPEX 가격 × 같은 시간 사용량", 42, ink)
    write(im, x + 44, 385, "추가 단가   16.40 유로센트/kWh  (세전)", 39, ink)
    foot = (
        "추가 단가에 망 이용료·전력세 포함   /   연 기본료 별도"
        if extras
        else "공식 요금표 1쪽   ·   Börsenpreisformel / Basispreis"
    )
    write(im, x + 36, 484, foot, 25, ink, False)


def opening_receipts(im, elapsed):
    draw = ImageDraw.Draw(im)
    for start, x, heading, detail, color in (
        (0, 78, "도매 정산", "1 MWh  ·  −135.45유로", "#95EDDA"),
        (0.65, 654, "우리 집 요금", "1 kWh  ·  얼마일까?", "#FFE565"),
    ):
        if elapsed < start:
            continue
        y = round(176 + 120 * (1 - ease((elapsed - start) / 0.55)))
        draw.rectangle((x, y, x + 540, y + 234), fill="#FCF7E9")
        for dx in range(0, 540, 20):
            draw.polygon(
                [(x + dx, y + 234), (x + dx + 10, y + 244), (x + dx + 20, y + 234)],
                fill="#FCF7E9",
            )
        draw.rectangle((x, y, x + 540, y + 17), fill=color)
        write(im, x + 28, y + 40, heading, 51, "#10242E")
        draw.line((x + 28, y + 132, x + 512, y + 132), fill="#768382", width=2)
        write(im, x + 28, y + 163, detail, 39, "#21383D")


def decorate(im, t, shot):
    mode = shot["mode"]
    local = t - float(shot["start"])
    asset = shot["asset"]
    heavy = mode in ("chart", "delivery", "settle", "units", "convert", "cost", "math")
    im = Image.composite(
        Image.new("RGB", im.size, INK), im, shade(0.57 if heavy else 0.08)
    )
    if mode == "question":
        opening_receipts(im, local)
    elif mode == "cost":
        plant_cost(im, t)
    elif mode in ("indexed", "extras"):
        retail_clause(im, t, mode == "extras")
    elif mode in ("delivery", "settle"):
        transit(im, t, mode)
    elif mode == "units":
        blocks(im, t)
    else:
        headings = {
            "zero": ("09시 도매가격  /  €/MWh", "−2.80"),
            "low": ("13시 도매가격  /  €/MWh", "−135.45"),
            "fee18": ("가상 계약  /  추가 단가", "+18 유로센트/kWh"),
            "total18": ("1 kWh 추가 사용  /  가상 계약", "약 +4.46 유로센트"),
            "total8": ("1 kWh 추가 사용  /  가상 계약", "약 −5.55 유로센트"),
            "opening": ("도매 전력  /  1 MWh", "−135.45 유로"),
            "market": ("2024년 5월 12일", "하루 전 전력시장"),
            "convert": ("1 kWh로 환산하면", "−13.545 유로센트"),
            "retail": ("두 번째 영수증", "우리 집의 계약"),
            "fixed": ("고정 단가 계약", "약정 단가 적용"),
            "month": ("월 청구액", "시간별 요금의 합 + 기본료"),
            "return": ("도매 정산", "판매자 → 구매자"),
            "answer": ("가정의 실제 요금", "같은 시간의 단가와 사용량"),
        }
        if mode in headings:
            title(im, *headings[mode], local)
    write(im, 75, 38, CREDITS[asset], 19, WHITE)
    return im


def run(args, **kwargs):
    return sp.run(args, check=True, **kwargs)


def cut(source, asset, start, n):
    zoom = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720"
    return sp.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-threads",
            "2",
            "-ss",
            str(start),
            "-i",
            str(source / FILES[asset]),
            "-an",
            "-vf",
            "fps=24," + zoom,
            "-frames:v",
            str(n),
            "-threads",
            "2",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        stdout=sp.PIPE,
    )


def write_caption_track(path):
    # Let FFmpeg parse SRT timing and text, including commas inside a cue.
    raw = run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(EP / "edit/captions.srt"),
            "-f",
            "ass",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stdout
    _, events = raw.split("[Events]\n", 1)
    header = (
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\n"
        "\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
    )
    # One centered 768 x 56 band, 48 px above the lower edge at 720p.
    style = "Style: Default,Noto Sans CJK KR,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1"
    band = (
        r"{\an7\pos(256,616)\p1\bord0\shad0\1c&H1D1812&\1a&H27&}"
        "m 12 0 l 756 0 b 763 0 768 5 768 12 l 768 44 b 768 51 763 56 756 56 "
        "l 12 56 b 5 56 0 51 0 44 l 0 12 b 0 5 5 0 12 0"
    )
    format_line, *lines = events.splitlines()
    output = [header + style, "", "[Events]", format_line]
    for line in lines:
        if line.startswith("Dialogue:"):
            *fields, text = line.split(",", 9)
            output.append(",".join([*fields, band]))
            fields[0] = "Dialogue: 1"
            output.append(",".join([*fields, r"{\an5\pos(640,644)\q2}" + text]))
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def build(source, output, chart, tariff):
    boundaries = [round(float(s["start"]) * FPS) for s in SHOTS] + [LENGTH]
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        silent = Path(temp) / "picture.mp4"
        encoder = sp.Popen(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                "1280x720",
                "-framerate",
                "24",
                "-i",
                "pipe:0",
                "-an",
                "-c:v",
                "libx264",
                "-threads",
                "3",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                "-pix_fmt",
                "yuv420p",
                str(silent),
            ],
            stdin=sp.PIPE,
        )
        try:
            for i, s in enumerate(SHOTS):
                n = boundaries[i + 1] - boundaries[i]
                mode = s["mode"]
                special = (
                    chart if mode == "chart" else tariff if mode == "math" else None
                )
                if special:
                    first = next(
                        j for j, row in enumerate(SHOTS) if row["mode"] == mode
                    )
                    src = sp.Popen(
                        [
                            "ffmpeg",
                            "-v",
                            "error",
                            "-threads",
                            "2",
                            "-ss",
                            str((boundaries[i] - boundaries[first]) / FPS),
                            "-i",
                            str(special),
                            "-frames:v",
                            str(n),
                            "-threads",
                            "2",
                            "-pix_fmt",
                            "rgb24",
                            "-f",
                            "rawvideo",
                            "pipe:1",
                        ],
                        stdout=sp.PIPE,
                    )
                else:
                    src = cut(source, s["asset"], s["inpoint"], n)
                try:
                    for f in range(n):
                        pixels = src.stdout.read(W * H * 3)
                        if len(pixels) != W * H * 3:
                            raise ValueError(f"Short source at shot {i}, frame {f}")
                        if not special:
                            pixels = decorate(
                                Image.frombytes("RGB", (W, H), pixels),
                                (boundaries[i] + f) / FPS,
                                s,
                            ).tobytes()
                        encoder.stdin.write(pixels)
                finally:
                    src.stdout.close()
                    src.wait()
                print(f"{i + 1}/{len(SHOTS)} {mode}", flush=True)
        finally:
            encoder.stdin.close()
            status = encoder.wait()
        if status:
            raise RuntimeError("Picture encode failed")
        write_caption_track(Path(temp) / "captions.ass")
        ready = Path(temp) / "finished.mp4"
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(silent),
                "-i",
                str(EP / "audio/narration.wav"),
                "-vf",
                "ass=captions.ass",
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=9",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-b:a",
                "144k",
                "-c:v",
                "libx264",
                "-threads",
                "3",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                "-movflags",
                "+faststart",
                str(ready),
            ],
            cwd=temp,
        )
        os.replace(ready, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--chart", type=Path, default=ROOT / "renders/day-ahead.mp4")
    parser.add_argument("--tariff", type=Path, default=ROOT / "renders/tariff.mp4")
    args = parser.parse_args()
    build(args.sources.resolve(), args.output.resolve(), args.chart, args.tariff)
