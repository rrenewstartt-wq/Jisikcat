"""Validate the independent editor's decision against the reviewed cut."""
import json
import re
import subprocess

DIMENSIONS = ("hook", "structure", "accuracy", "visuals", "captions", "audio", "packaging")
SEGMENTS = ("opening", "middle", "ending")


def template():
    return {
        "comparison_submission": None,
        "decision": "pending",
        "open_blockers": [],
        "dimensions": {
            key: {"grade": "pending", "reference_observation": "", "candidate_observation": ""}
            for key in DIMENSIONS
        },
        "playback": {
            key: {"reference_at": "", "candidate_at": "", "finding": ""}
            for key in SEGMENTS
        },
    }


def duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=False, capture_output=True, text=True,
    )
    if result.returncode:
        raise ValueError(f"검수 영상의 재생시간을 읽을 수 없습니다: {path.name}")
    return float(result.stdout)


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:[0-5]\d:[0-5]\d(?:\.\d{1,3})?", value):
        raise ValueError("검수 시각은 HH:MM:SS 또는 HH:MM:SS.sss 형식이어야 합니다.")
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def observed(value):
    return isinstance(value, str) and bool(value.strip())


def validate(episode, comparison_id):
    decision = json.loads((episode / "qa/decision.json").read_text(encoding="utf-8"))
    current = decision.get("comparison_submission") if isinstance(decision, dict) else None
    if type(current) is not int or current != comparison_id:
        raise ValueError("decision.json에 현재 대조 심사 제출 번호를 기록하세요.")
    if decision.get("decision") != "approve" or decision.get("open_blockers") != []:
        raise ValueError("미승인 또는 미해결 차단 결함이 있어 출고할 수 없습니다.")
    note = (episode / "qa/review.md").read_text(encoding="utf-8")
    if re.search(r"^\s*(?:보류|반송|차단)\s*[:：]", note, re.MULTILINE):
        raise ValueError("검수 메모의 미해결 표식(보류·반송·차단)을 먼저 처리하세요.")
    dimensions = decision.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("독립 편집 판정이 필요합니다.")
    for key in DIMENSIONS:
        row = dimensions.get(key)
        if (not isinstance(row, dict) or row.get("grade") not in ("equivalent", "better")
                or not all(observed(row.get(k)) for k in ("reference_observation", "candidate_observation"))):
            raise ValueError(f"{key}: 양쪽 관찰과 동급 이상 판정이 필요합니다.")
    samples = decision.get("playback")
    if not isinstance(samples, dict):
        raise ValueError("도입·중반·결말 재생 기록이 필요합니다.")
    lengths = {"reference_at": duration(episode / "evidence/reference.mp4"),
               "candidate_at": duration(episode / "edit/master.mp4")}
    for third, name in enumerate(SEGMENTS):
        sample = samples.get(name)
        if not isinstance(sample, dict) or not observed(sample.get("finding")):
            raise ValueError(f"{name}: 양쪽 영상을 재생한 관찰을 기록하세요.")
        for field, length in lengths.items():
            point = timestamp(sample.get(field))
            if not length * third / 3 <= point < length * (third + 1) / 3:
                raise ValueError(f"{name}: {field}가 해당 재생 구간 밖에 있습니다.")
