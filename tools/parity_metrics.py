"""Compare a local reference package to a cut before editorial review.

Each threshold in LIMITS is (absolute floor, fraction of reference value).
The larger allowance applies, in the units named by the metric. These are
proposed production tolerances. Whole-program averages do not measure font,
wording, semantic shot choice or mix balance; review those against frames.
"""
import json
import math
import re
import subprocess
from pathlib import Path

if __package__:
    from . import media
else:
    import media


LIMITS = {
    "video_aspect_ratio": (0, 0.01),
    "duration_s": (1.0, 0.15),
    "median_candidate_shot_s": (0.35, 0.25),
    "candidate_cuts_per_min": (1.0, 0.25),
    "integrated_lufs": (2.0, 0),
    "caption_cues_per_min": (1.0, 0.20),
    "caption_median_duration_s": (0.25, 0.20),
    "caption_median_lines": (0.5, 0),
    "caption_median_chars": (2, 0.20),
    "thumbnail_aspect_ratio": (0, 0.01),
    "thumbnail_mean_gray": (18, 0),
    "thumbnail_gray_stddev": (15, 0),
    "thumbnail_dark_fraction": (0.12, 0),
    "thumbnail_bright_fraction": (0.12, 0),
}


MINIMUMS = ("video_width", "video_height", "thumbnail_width", "thumbnail_height")


def integrated_lufs(video):
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", str(video),
               "-map", "0:a:0", "-vn", "-af", "loudnorm=print_format=json",
               "-f", "null", "-"]
    result = subprocess.run(command, text=True, capture_output=True)
    match = re.search(r'\{\s*"input_i"[^{}]*\}', result.stderr)
    if result.returncode or not match:
        raise ValueError(f"오디오 스트림을 측정할 수 없습니다: {video}")
    value = float(json.loads(match.group())["input_i"])
    if not math.isfinite(value):
        raise ValueError(f"유효한 통합 음량을 측정할 수 없습니다: {video}")
    return value


def measure(video, captions, thumbnail):
    scene = media.scene_metrics(video, 0.30)
    length = scene["duration_s"]
    if not math.isfinite(length) or length <= 0:
        raise ValueError(f"유효한 영상 길이가 필요합니다: {video}")
    text = media.caption_metrics(captions)
    if not text["median_chars_per_cue"]:
        raise ValueError(f"자막 내용이 비어 있습니다: {captions}")
    thumb = media.thumbnail_metrics(thumbnail)
    return {
        "video_width": scene["width"],
        "video_height": scene["height"],
        "thumbnail_width": thumb["width"],
        "thumbnail_height": thumb["height"],
        "video_aspect_ratio": scene["width"] / scene["height"],
        "duration_s": length,
        "median_candidate_shot_s": scene["median_candidate_shot_s"],
        "candidate_cuts_per_min": 60 * len(scene["candidate_cut_seconds"]) / length,
        "integrated_lufs": integrated_lufs(video),
        "caption_cues_per_min": 60 * text["cue_count"] / length,
        "caption_median_duration_s": text["median_duration_s"],
        "caption_median_lines": text["median_lines"],
        "caption_median_chars": text["median_chars_per_cue"],
        "thumbnail_aspect_ratio": thumb["width"] / thumb["height"],
        "thumbnail_mean_gray": thumb["mean_gray_0_255"],
        "thumbnail_gray_stddev": thumb["gray_stddev"],
        "thumbnail_dark_fraction": thumb["dark_fraction_lt64"],
        "thumbnail_bright_fraction": thumb["bright_fraction_ge192"],
    }


def compare(episode: Path):
    """Return measured reference/candidate pairs, raising ValueError on failure."""
    inputs = [
        ("evidence/reference.mp4", "evidence/reference.srt", "evidence/reference.jpg"),
        ("edit/master.mp4", "edit/captions.srt", "thumbnail/thumbnail.jpg"),
    ]
    paths = [[episode / name for name in group] for group in inputs]
    for group in paths:
        for path in group:
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f"측정 파일이 없거나 비어 있습니다: {path}")
    try:
        reference, candidate = [measure(*group) for group in paths]
    except (OSError, KeyError, IndexError, ArithmeticError) as error:
        raise ValueError(f"미디어 계측 실패: {error}") from error

    pairs = {}
    errors = []
    for metric, (floor, fraction) in LIMITS.items():
        ref, actual = reference[metric], candidate[metric]
        allowance = max(floor, abs(ref) * fraction)
        pairs[metric] = {"reference": ref, "candidate": actual, "tolerance": allowance}
        if not math.isfinite(actual) or abs(actual - ref) > allowance + 1e-9:
            errors.append(f"{metric}: 기준 {ref:.3f}, 결과 {actual:.3f}, 허용차 {allowance:.3f}")
    for metric in MINIMUMS:
        ref, actual = reference[metric], candidate[metric]
        pairs[metric] = {"reference": ref, "candidate": actual, "minimum": ref}
        if actual < ref:
            errors.append(f"{metric}: 기준 해상도 {ref}, 제작본 {actual}")
    if errors:
        raise ValueError("실측 기준 초과\n" + "\n".join(errors))
    return pairs
