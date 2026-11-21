"""Compare the pilot SRT with its voice takes and render every cue on neutral gray."""

import json
import subprocess
import sys
import tempfile
from itertools import pairwise
from pathlib import Path

from PIL import Image

EPISODE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(EPISODE / "edit/motion"), str(EPISODE.parents[1] / "tools")]
from film import FPS, H, W, write_caption_track
from scene_evidence import caption_cues


def check_takes(cues):
    lines = [
        row.split(" · ", 1)[1]
        for row in (EPISODE / "script/script.md").read_text().splitlines()
        if row.startswith("- `")
    ]
    takes = json.loads((EPISODE / "edit/timings.json").read_text())
    # SRT timestamps have millisecond precision, while take lengths use sample time.
    spans = [(round(s * 1000), round(e * 1000), text) for s, e, text in cues]
    if not spans or (spans[0][0], spans[-1][1]) != (
        round(takes[0][0] * 1000),
        round(takes[-1][1] * 1000),
    ):
        raise ValueError("자막과 녹음의 전체 길이가 다릅니다.")
    if any(left[1] != right[0] for left, right in pairwise(spans)):
        raise ValueError("자막 시간에 틈 또는 겹침이 있습니다.")
    for (start, end), line in zip(takes, lines, strict=True):
        low, high = round(start * 1000), round(end * 1000)
        group = [c for c in spans if low <= c[0] < c[1] <= high]
        if not group or group[0][0] != low or group[-1][1] != high:
            raise ValueError(f"녹음과 자막 경계 불일치: {line}")
        if " ".join(c[2] for c in group) != line:
            raise ValueError(f"원고와 자막 문구 불일치: {line}")
    return len(takes)


def check_pixels(cues):
    # Keep the actual presentation timestamps through the select filter for libass.
    select = "+".join(f"eq(n\\,{round((s + e) * FPS / 2)})" for s, e, _ in cues)
    with tempfile.TemporaryDirectory() as temp:
        write_caption_track(Path(temp) / "captions.ass")
        frames = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c=gray:s={W}x{H}:r={FPS}:d={cues[-1][1] + 1}",
                "-vf",
                f"select='{select}',ass=captions.ass",
                "-fps_mode",
                "passthrough",
                "-pix_fmt",
                "gray",
                "-threads",
                "1",
                "-f",
                "rawvideo",
                "-",
            ],
            cwd=temp,
        )
    stride = W * H
    if len(frames) != stride * len(cues):
        raise ValueError("자막마다 한 프레임을 렌더해야 합니다.")
    margins = []
    for index, (_, _, text) in enumerate(cues):
        im = Image.frombytes("L", (W, H), frames[index * stride : (index + 1) * stride])
        band = im.point(lambda v: 255 if v < 90 else 0).getbbox()
        letters = im.point(lambda v: 255 if v > 195 else 0).getbbox()
        if band != (256, 616, 1024, 672) or letters is None:
            raise ValueError(f"자막 띠 또는 글자가 없습니다: {text}")
        left, top, right, bottom = letters
        x = min(left - band[0], band[2] - right)
        y = min(top - band[1], band[3] - bottom)
        if x < 0 or y < 0:
            raise ValueError(f"띠 밖으로 나간 자막: {text}")
        margins.append((x, y))
    return min(x for x, _ in margins), min(y for _, y in margins)


if __name__ == "__main__":
    captions = caption_cues(EPISODE / "edit/captions.srt")
    takes = check_takes(captions)
    horizontal, vertical = check_pixels(captions)
    print(
        f"{takes} takes, {len(captions)} cues, minimum margins {horizontal}px × {vertical}px"
    )
