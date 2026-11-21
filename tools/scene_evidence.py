"""Validate reference observations and the evidence visible for each scripted claim."""

import json
import re
import subprocess

from editorial_review import SEGMENTS, duration, observed, timestamp

PROOF_KINDS = ("document", "measurement", "demonstration", "model")
PROFILE_FIELDS = ("narrative_function", "shot_and_cut", "caption_style", "sound")
PACKAGING_FIELDS = ("subject_and_crop", "text_hierarchy", "title_promise")
CLAIM_ID = re.compile(r"(?<![A-Za-z0-9_])C\d+(?![A-Za-z0-9_])")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def specific(value):
    return observed(value) and value.strip().casefold() not in {
        "확인",
        "미확인",
        "보류",
        "미정",
        "확인 불가",
        "pending",
        "todo",
        "n/a",
        "-",
    }


def format_brief(episode, stage):
    profile = read(episode / "format/profile.json")
    lines = [f"승인된 포맷 기준 {profile['video_id']} · format/profile.json"]
    if stage in ("planning", "thumbnail", "marketing", "comparison", "qa"):
        lines.append(
            "표지·제목 | "
            + " / ".join(profile["packaging"][k] for k in PACKAGING_FIELDS)
        )
    fields = {
        "script": ("narrative_function",),
        "audio": ("sound",),
        "assets": ("shot_and_cut",),
        "edit": ("shot_and_cut", "caption_style", "sound"),
    }
    if stage not in ("thumbnail", "marketing"):
        for key in SEGMENTS:
            row = profile["anchors"][key]
            lines.append(
                f"{key} {row['at']} | "
                + " / ".join(row[k] for k in fields.get(stage, PROFILE_FIELDS))
            )
    return "\n".join(lines)


def profile_template():
    return {
        "video_id": "",
        "packaging": dict.fromkeys(PACKAGING_FIELDS, ""),
        "anchors": {
            key: dict.fromkeys(("at", *PROFILE_FIELDS), "") for key in SEGMENTS
        },
    }


def validate_profile(episode):
    profile = read(episode / "format/profile.json")
    original = read(episode / "evidence/reference.json")
    if not isinstance(profile, dict) or profile.get("video_id") != original["video_id"]:
        raise ValueError("profile.json의 영상 ID가 기준물과 다릅니다.")
    packaging = profile.get("packaging")
    if not isinstance(packaging, dict) or not all(
        specific(packaging.get(k)) for k in PACKAGING_FIELDS
    ):
        raise ValueError("기준 썸네일 구도·문구 위계·제목의 약속을 기록하세요.")
    length = duration(episode / "evidence/reference.mp4")
    anchors = profile.get("anchors")
    for index, key in enumerate(SEGMENTS):
        row = anchors.get(key) if isinstance(anchors, dict) else None
        if not isinstance(row, dict) or not all(
            specific(row.get(k)) for k in PROFILE_FIELDS
        ):
            raise ValueError(f"{key}: 서사·컷·자막·음향의 원본 관찰이 필요합니다.")
        if (
            not length * index / 3
            <= timestamp(row.get("at"))
            < length * (index + 1) / 3
        ):
            raise ValueError(f"{key}: 기준 원본의 해당 구간에서 시각을 선택하세요.")


def claims(episode):
    folder = episode / "script"
    plan = read(folder / "claims.json")
    if not isinstance(plan, dict) or not plan:
        raise ValueError("claims.json에 핵심 주장과 필요한 증거 유형을 기록하세요.")
    for key, kind in plan.items():
        if not CLAIM_ID.fullmatch(key) or kind not in PROOF_KINDS:
            raise ValueError(f"{key}: 주장 ID 또는 증거 유형 오류")
    for file in ("script.md", "facts.md"):
        ids = set(CLAIM_ID.findall((folder / file).read_text(encoding="utf-8")))
        if ids != set(plan):
            raise ValueError(
                f"{file}의 주장 ID와 claims.json이 다릅니다: {sorted(ids ^ set(plan))}"
            )
    return plan


def caption_cues(path):
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        lines = block.splitlines()
        if len(lines) < 3 or " --> " not in lines[1]:
            raise ValueError("자막 블록의 시각 또는 발화가 누락됐습니다.")
        start, end = lines[1].replace(",", ".").split(" --> ")
        cues.append(
            (timestamp(start), timestamp(end), " ".join(" ".join(lines[2:]).split()))
        )
    return cues


def validate_proof(episode, inputs):
    plan = claims(episode)
    report = read(episode / "visualproof/proof.json")
    if not isinstance(report, dict):
        raise ValueError("화면 검증 버전 불일치. brief의 reviewed_inputs를 사용하세요.")
    versions = report.get("reviewed_inputs")
    if inputs is not None and (
        versions != inputs or any(type(n) is not int for n in versions.values())
    ):
        raise ValueError("화면 검증 버전 불일치. brief의 reviewed_inputs를 사용하세요.")
    rows = report.get("claims")
    if not isinstance(rows, dict) or set(rows) != set(plan):
        raise ValueError("대본의 모든 핵심 주장에 화면 검증이 필요합니다.")
    sources = {r["asset"] for r in read(episode / "assets/sources.json")}
    length = duration(episode / "edit/master.mp4")
    captions = caption_cues(episode / "edit/captions.srt")
    script_lines = (
        (episode / "script/script.md").read_text(encoding="utf-8").splitlines()
    )
    seen = set()
    issues = []
    for key, expected in plan.items():
        row = rows[key]
        if not isinstance(row, dict):
            raise ValueError(f"{key}: 화면 검증 객체가 필요합니다.")
        try:
            point = timestamp(row.get("at"))
            excerpt = row.get("spoken")
            if not observed(excerpt):
                raise ValueError("주장에 대응하는 자막 발췌가 필요합니다.")
            excerpt = " ".join(excerpt.split())
            if not any(
                start <= point < end and excerpt in text
                for start, end, text in captions
            ):
                raise ValueError("지정 시각에 해당 발췌 자막이 없습니다.")
            if not any(
                key in CLAIM_ID.findall(line) and excerpt in " ".join(line.split())
                for line in script_lines
            ):
                raise ValueError("발췌 자막이 대본의 해당 주장 행과 연결되지 않습니다.")
            if point >= length:
                raise ValueError("완성본의 재생 범위를 벗어났습니다.")
        except ValueError as err:
            issues.append(f"{key}: {err}")
        asset = row.get("asset")
        if not observed(asset) or asset not in sources:
            issues.append(f"{key}: 자료팀 sources.json에 등록한 asset이 필요합니다.")
        elif asset in seen and not specific(row.get("reuse_reason")):
            issues.append(f"{key}: 반복 자산이 새롭게 보여 주는 정보를 기록하세요.")
        elif observed(asset):
            seen.add(asset)
        if row.get("kind") != expected:
            issues.append(f"{key}: 대본이 요구한 화면 근거는 {expected}입니다.")
        if row.get("anchor") not in SEGMENTS or not specific(row.get("visible")):
            issues.append(f"{key}: 기준 장면과 무음으로 확인한 화면 관찰이 필요합니다.")
        if row.get("verdict") != "pass":
            issues.append(
                f"{key}: 미해결 화면 근거. {row.get('reason') or '수정 후 재검수하세요.'}"
            )
    if issues:
        raise ValueError("\n".join(issues))


def frame_pair(episode, key, output):
    """Export the two recorded positions for editorial replay, without changing approvals."""
    if output.suffix.lower() != ".png":
        raise ValueError("비교 프레임 출력 경로는 .png여야 합니다.")
    original = episode / "evidence/reference.mp4"
    candidate = episode / "edit/master.mp4"
    if not original.is_file() or not candidate.is_file():
        raise ValueError("기준 원본과 완성본 두 영상이 모두 필요합니다.")
    validate_profile(episode)
    profile = read(episode / "format/profile.json")
    rows = read(episode / "visualproof/proof.json").get("claims", {})
    row = rows.get(key)
    if not isinstance(row, dict) or row.get("anchor") not in SEGMENTS:
        raise ValueError(f"{key}: 검토할 주장과 기준 장면을 먼저 지정하세요.")
    ref_at = profile["anchors"][row["anchor"]]["at"]
    candidate_at = row["at"]
    args = ["ffmpeg", "-hide_banner", "-v", "error", "-nostdin"]
    for video, stamp in ((original, ref_at), (candidate, candidate_at)):
        if timestamp(stamp) >= duration(video):
            raise ValueError(f"{video.name}: 프레임 시각이 범위를 벗어났습니다.")
        args.extend(["-ss", stamp, "-i", str(video)])
    fit = "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1"
    result = subprocess.run(
        args
        + [
            "-filter_complex_threads",
            "1",
            "-filter_complex",
            f"[0:v]{fit}[a];[1:v]{fit}[b];[a][b]hstack=inputs=2[v]",
            "-map",
            "[v]",
            "-frames:v",
            "1",
            "-c:v",
            "png",
            "-f",
            "image2pipe",
            "pipe:1",
        ],
        capture_output=True,
    )
    if result.returncode or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("선택한 시각에서 비교 프레임을 읽지 못했습니다.")
    with output.open("xb") as stream:
        stream.write(result.stdout)
    print(f"{output} | 왼쪽 기준작 {ref_at} · 오른쪽 제작본 {candidate_at}")
