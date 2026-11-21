#!/usr/bin/env python3
"""회차별 제작 인계. Python 3.9+, 미디어 제출에는 ffprobe가 필요하다."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

import editorial_review
import media
import parity_metrics
import story_formulas

ROOT = Path(__file__).resolve().parents[1]
# key: (담당 팀, 선행 단계, 제출 시 답할 항목, 필수 산출물)
STAGES = {
    "analysis": ("레퍼런스 분석", [], ["표본 선정 근거", "관찰과 타임코드", "반복 공식과 예외", "미확인 사항"], ["observations.md"]),
    "evidence": ("비교 기준·원본 확보", ["analysis"], ["비교 형식과 길이", "원본 영상과 자막의 대응", "채널·영상 ID 확인 근거"], ["reference.json", "reference.mp4", "reference.srt", "reference.jpg"]),
    "planning": ("편성·기획", ["evidence"], ["타깃 시청자", "한 문장 약속", "차별화 소재", "구간별 구성"], ["brief.md"]),
    "script": ("대본·팩트체크", ["planning"], ["오프닝", "핵심 주장의 근거", "결말 회수"], ["script.md", "facts.md"]),
    "assets": ("자료 조사·권리", ["script"], ["필요 컷", "이용 조건 확인"], ["sources.json"]),
    "thumbnail": ("썸네일 디자인", ["planning"], ["작은 화면 가독성", "시선 순서", "제목과의 역할 분담"], ["thumbnail.jpg"]),
    "audio": ("내레이션·음향", ["script"], ["발음과 속도", "음량 검수"], ["narration.wav"]),
    "edit": ("편집·자막", ["assets", "audio"], ["컷 전환 기준", "자막 안전 영역", "음성 싱크"], ["master.mp4", "captions.srt"]),
    "marketing": ("패키징·마케팅", ["script", "thumbnail"], ["최종 제목", "설명과 출처 표기", "노출 후 측정 계획"], ["metadata.md"]),
    "comparison": ("레퍼런스 대조 심사", ["edit", "marketing", "evidence"], ["전편 대조 결과", "반송 및 수정 이력"], ["scorecard.json"]),
    "qa": ("독립 검수", ["comparison"], ["사실·출처 대조", "미디어 재생·자막·오디오", "썸네일·제목·영상 일치", "권리 증빙 대조"], ["review.md", "decision.json"]),
    "release": ("출고", ["qa"], ["배포 파일 식별", "공개 범위와 일정", "승인자"], ["delivery.md"]),
    "learning": ("성과 분석", ["release"], ["관측 시점과 지표", "비교 기준", "다음 실험"], ["retrospective.md"]),
}
MEDIA = {"thumbnail.jpg": {"video": "mjpeg"}, "narration.wav": {"audio": None},
         "master.mp4": {"video": None, "audio": None}}
MEDIA["reference.mp4"] = MEDIA["master.mp4"]
MEDIA["reference.jpg"] = MEDIA["thumbnail.jpg"]
DIMENSIONS = ("hook", "structure", "accuracy", "visuals", "captions", "audio", "packaging")
ASSET_KEYS = ["asset", "source", "license", "evidence", "credit"]


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def quality_templates(dest):
    files = {
        "qa/decision.json": editorial_review.template(),
        "evidence/reference.json": dict.fromkeys(("channel_id", "video_id", "selection_reason", "origin_note"), ""),
        "comparison/scorecard.json": {key: {"reference_at": "", "candidate_at": "", "finding": "", "verdict": "pending"}
                                     for key in DIMENSIONS},
    }
    for stage in ("evidence", "comparison"):
        (dest / stage).mkdir(exist_ok=True)
        files[f"{stage}/handoff.json"] = dict.fromkeys(STAGES[stage][2], "")
    for name, data in files.items():
        path = dest / name
        if not path.exists():
            path.write_text(json_text(data), encoding="utf-8")


def validate_comparison(folder, inputs):
    report = json.loads((folder / "scorecard.json").read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("reviewed_inputs") != inputs:
        raise ValueError("심사 버전 불일치. brief에 표시된 reviewed_inputs를 대조표에 기록하세요.")
    for key in DIMENSIONS:
        row = report.get(key)
        if not isinstance(row, dict) or row.get("verdict") != "pass" or not nonempty(row.get("finding")):
            raise ValueError(f"{key}: 비교 근거와 통과 판정이 필요합니다.")
        for field in ("reference_at", "candidate_at"):
            if not re.fullmatch(r"\d{2}:[0-5]\d:[0-5]\d", str(row.get(field))):
                raise ValueError(f"{key}: {field} 시각 오류")
    result = parity_metrics.compare(folder.parent)
    for key in DIMENSIONS:
        for field, side in (("reference_at", "reference"), ("candidate_at", "candidate")):
            hours, minutes, seconds = map(int, report[key][field].split(":"))
            if hours * 3600 + minutes * 60 + seconds >= result["duration_s"][side]:
                raise ValueError(f"{key}: {field}가 영상 범위를 벗어났습니다.")
    return result


def init(root, episode, topic):
    root.mkdir(parents=True, exist_ok=True)
    dest = root / episode
    if dest.exists():
        raise ValueError("이미 있는 회차입니다.")
    tmp = Path(tempfile.mkdtemp(prefix=".init-", dir=root))
    try:
        for stage, (_, _, questions, files) in STAGES.items():
            folder = tmp / stage
            folder.mkdir()
            (folder / "handoff.json").write_text(json_text(dict.fromkeys(questions, "")), encoding="utf-8")
            if "sources.json" in files:
                (folder / "sources.json").write_text(json_text([dict.fromkeys(ASSET_KEYS, "")]), encoding="utf-8")
        quality_templates(tmp)
        with sqlite3.connect(tmp / "studio.db") as db:
            db.execute("create table episode(topic text not null)")
            db.execute("insert into episode values (?)", (topic,))
            db.execute("""create table submissions(id integer primary key, stage text, author text,
                       fingerprint text, parents text, time text default current_timestamp)""")
        tmp.rename(dest)
        print(dest)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def digest(folder, files, *, include_handoff=True):
    h = hashlib.sha256()
    if include_handoff and folder.name == "comparison":
        h.update(b"comparison-policy:2\0")
    for name in (["handoff.json", *files] if include_handoff else files):
        path = folder / name
        if not path.is_file() or path.stat().st_size == 0:
            return None
        h.update(name.encode() + b"\0")
        file_hash = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                file_hash.update(block)
        h.update(file_hash.digest())
    return h.hexdigest()


def has_rework(db):
    return db.execute("select 1 from sqlite_master where type='table' and name='rejections'").fetchone()


def pending_rework(db, stage):
    """Return a correction brief using the caller's current transaction, including legacy DBs."""
    if not has_rework(db):
        return ""
    row = db.execute("""select submission_id, reviewer, owner, reason from rejections
                        where stage=? and corrected_by is null""", (stage,)).fetchone()
    if not row:
        return ""
    submission, reviewer, owner, reason = row
    return f"반송 #{submission} | 판정자 {reviewer} | 수정 담당 {owner} | 사유 {reason}"


def reject(db, dest, args, valid, latest):
    if not all(nonempty(v) for v in (args.by, args.owner, args.reason)):
        raise ValueError("반송자, 수정 담당자, 구체적 반송 사유를 입력하세요.")
    row = latest.get(args.stage)
    if not row or row[0] != args.submission:
        raise ValueError("현재 제출 번호와 다릅니다. status를 확인하세요.")
    decision = (args.by.strip(), args.owner.strip(), args.reason.strip())
    if args.stage not in valid:
        if has_rework(db):
            existing = db.execute("""select reviewer, owner, reason from rejections
                                     where submission_id=? and corrected_by is null""",
                                  (args.submission,)).fetchone()
            if existing == decision:
                print(pending_rework(db, args.stage))
                return
        raise ValueError("현 버전에 유효하게 접수된 제출만 반송할 수 있습니다.")
    folder = dest / args.stage
    files = STAGES[args.stage][3]
    outputs = digest(folder, files, include_handoff=False)
    if outputs is None or digest(folder, files) != row[3]:
        raise ValueError("반송 중 산출물이 변경됐습니다. status를 확인하세요.")
    db.execute("""create table if not exists rejections(
                  seq integer primary key, submission_id integer not null unique references submissions(id), stage text not null,
                  reviewer text not null, owner text not null, reason text not null,
                  outputs text not null, after_id integer not null, time text default current_timestamp,
                  corrected_by integer references submissions(id))""")
    db.execute("""insert into rejections(submission_id, stage, reviewer, owner, reason, outputs, after_id)
                  values (?,?,?,?,?,?,(select max(id) from submissions))""",
               (args.submission, args.stage, *decision, outputs))
    print(pending_rework(db, args.stage))


def show_history(db):
    rejections = {}
    if has_rework(db):
        for event in db.execute("""select after_id, time, stage, submission_id, reviewer, owner, reason,
                                   corrected_by from rejections order by after_id, seq"""):
            rejections.setdefault(event[0], []).append(event[1:])
    for row in db.execute("select id, time, stage, author from submissions order by id"):
        print(*row, sep=" | ")
        for when, stage, rejected, reviewer, owner, why, fixed in rejections.get(row[0], []):
            result = f"수정 접수 #{fixed}" if fixed else "수정 대기"
            print(f"반송 #{rejected}", when, stage, reviewer, owner, why, result, sep=" | ")


def accepted(db, dest):
    latest = {row[1]: row for row in db.execute(
        "select id, stage, author, fingerprint, parents from submissions order by id")}
    rejected = set()
    if has_rework(db):
        rejected = {r[0] for r in db.execute("select submission_id from rejections where corrected_by is null")}
    valid = {}
    for stage, (_, deps, _, files) in STAGES.items():
        row = latest.get(stage)
        if row and row[0] not in rejected and all(p in valid for p in deps):
            if (json.loads(row[4]) == [valid[p][0] for p in deps]
                    and row[3] == digest(dest / stage, files)):
                valid[stage] = row
    return valid, latest


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(folder, stage):
    _, _, questions, files = STAGES[stage]
    if stage == "analysis":
        story_formulas.selected(folder.parent)
    answers = json.loads((folder / "handoff.json").read_text(encoding="utf-8"))
    if not isinstance(answers, dict) or not all(nonempty(answers.get(q)) for q in questions):
        raise ValueError("handoff.json의 모든 질문에 답하세요.")
    for name in files:
        path = folder / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"필수 파일 누락: {path}")
        if name.endswith(".md") and not nonempty(path.read_text(encoding="utf-8")):
            raise ValueError(f"빈 문서: {path}")
        if name == "reference.json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(data, dict) or data.get("channel_id") != media.CHANNEL
                    or not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(data.get("video_id", "")))
                    or not all(nonempty(data.get(key)) for key in ("selection_reason", "origin_note"))):
                raise ValueError("비교할 레퍼런스의 채널·영상 ID, 선정 근거, 출처 기록이 필요합니다.")
        if name == "sources.json":
            rows = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(rows, list) or not rows or not all(
                    isinstance(row, dict) and all(nonempty(row.get(k)) for k in ASSET_KEYS) for row in rows):
                raise ValueError("자료별 asset/source/license/evidence/credit을 기록하세요.")
        if name in MEDIA:
            result = subprocess.run(["ffprobe", "-v", "error", "-of", "json", "-show_streams",
                                     str(path)], capture_output=True, text=True)
            if result.returncode:
                raise ValueError(f"미디어를 읽을 수 없습니다: {name}")
            streams = json.loads(result.stdout)["streams"]
            for kind, codec in MEDIA[name].items():
                if not any(s.get("codec_type") == kind and (not codec or s.get("codec_name") == codec)
                           for s in streams):
                    raise ValueError(f"{name}에 필요한 스트림이 없습니다: {kind}")
        if name.endswith(".srt"):
            stamp = r"(\d{2}):([0-5]\d):([0-5]\d),(\d{3})"
            prev = 0
            for idx, cue in enumerate(re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()), 1):
                lines = cue.splitlines()
                m = re.fullmatch(stamp + " --> " + stamp, lines[1]) if len(lines) >= 3 else None
                if not m or lines[0].strip() != str(idx) or not "".join(lines[2:]).strip():
                    raise ValueError(f"자막 {idx}번 형식 오류")
                times = [sum(int(n) * w for n, w in zip(m.groups()[i:i+4], [3600000, 60000, 1000, 1]))
                         for i in (0, 4)]
                if not prev <= times[0] < times[1]:
                    raise ValueError(f"자막 {idx}번 시간 순서 오류")
                prev = times[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "episodes", help="회차 작업 디렉터리")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("teams")
    for cmd in ("init", "upgrade", "metrics", "status", "brief", "submit", "history", "reject"):
        p = sub.add_parser(cmd)
        p.add_argument("episode")
        if cmd == "init":
            p.add_argument("--topic", required=True)
        if cmd in ("brief", "submit", "reject"):
            p.add_argument("stage", choices=STAGES)
        if cmd == "reject":
            p.add_argument("--submission", required=True, type=int, help="검토한 제출 번호")
            p.add_argument("--owner", required=True, help="수정 담당자")
            p.add_argument("--reason", required=True, help="문제 위치, 수정 요청, 재검수 기준")
        if cmd in ("submit", "reject"):
            p.add_argument("--by", required=True)
    args = parser.parse_args()
    if args.cmd == "teams":
        for key, (name, deps, _, files) in STAGES.items():
            print(key, name, "선행", ", ".join(deps) or "없음", "제출", ", ".join(files), sep=" | ")
        return
    if not re.fullmatch(r"[A-Za-z0-9가-힣][A-Za-z0-9가-힣_-]{0,79}", args.episode):
        raise ValueError("회차 ID에는 글자, 숫자, 하이픈, 밑줄을 사용하세요.")
    dest = args.root / args.episode
    if args.cmd == "init":
        if not nonempty(args.topic):
            raise ValueError("주제를 입력하세요.")
        return init(args.root, args.episode, args.topic)
    if not (dest / "studio.db").is_file():
        raise ValueError("회차가 없습니다. init으로 생성하세요.")
    if args.cmd == "upgrade":
        quality_templates(dest)
        return
    with sqlite3.connect(dest / "studio.db", timeout=30) as db:
        db.execute("begin immediate" if args.cmd in ("submit", "reject") else "begin")
        if args.cmd == "history":
            show_history(db)
            return
        valid, latest = accepted(db, dest)
        if args.cmd == "reject":
            return reject(db, dest, args, valid, latest)
        if args.cmd == "metrics":
            if "comparison" not in valid:
                raise ValueError("현재 버전에 대한 통과 계측표가 없습니다.")
            row = db.execute("select measurements from comparisons where submission_id = ?",
                             (valid["comparison"][0],)).fetchone()
            print(row[0])
            return
        if args.cmd == "status":
            print(db.execute("select topic from episode").fetchone()[0])
            for stage, (_, deps, _, _) in STAGES.items():
                missing = [d for d in deps if d not in valid]
                state = "대기 (" + ", ".join(missing) + ")" if missing else "작업 가능"
                if stage in valid:
                    state = f"접수 #{valid[stage][0]} ({valid[stage][2]})"
                elif stage in latest:
                    state = "재제출 필요 / " + state
                correction = pending_rework(db, stage)
                if correction:
                    state = f"{correction} / {state}"
                print(f"{stage:10} {state}")
            return
        stage = args.stage
        name, deps, questions, files = STAGES[stage]
        if args.cmd == "brief":
            print(name, db.execute("select topic from episode").fetchone()[0], sep=" | ")
            for dep in deps:
                print("입력", dest / dep, "접수" if dep in valid else "대기")
            if stage == "comparison" and all(dep in valid for dep in deps):
                print("reviewed_inputs", json_text({dep: valid[dep][0] for dep in deps}))
            if stage == "qa" and "comparison" in valid:
                print("현재 comparison 제출 번호", valid["comparison"][0])
            correction = pending_rework(db, stage)
            if correction:
                print(correction)
            print(story_formulas.brief(dest, stage))
            print("작성 위치", dest / stage)
            print("인계 질문", *questions, sep="\n  ")
            print("필수 파일", *files, "handoff.json", sep="\n  ")
            return
        if not nonempty(args.by):
            raise ValueError("제출자를 입력하세요.")
        author = args.by.strip()
        if any(dep not in valid for dep in deps):
            raise ValueError("선행 팀의 유효한 제출이 필요합니다.")
        exempt = {stage, "qa", "release", "learning"}
        if stage in ("comparison", "qa") and any(author.casefold() == row[2].casefold()
                for key, row in valid.items() if key not in exempt):
            raise ValueError("제작에 참여하지 않은 별도 검수자를 지정하세요.")
        before = digest(dest / stage, files)
        validate(dest / stage, stage)
        if stage == "qa":
            editorial_review.validate(dest, valid["comparison"][0])
        if stage == "comparison":
            measurements = validate_comparison(dest / stage, {dep: valid[dep][0] for dep in deps})
        fingerprint = digest(dest / stage, files)
        if fingerprint is None or fingerprint != before:
            raise ValueError("제출 중 파일 변경. 다시 제출하세요.")
        rejected = None
        if has_rework(db):
            rejected = db.execute("""select submission_id, outputs from rejections
                                     where stage=? and corrected_by is null""", (stage,)).fetchone()
        if rejected and rejected[1] == digest(dest / stage, files, include_handoff=False):
            raise ValueError("반송된 산출물과 동일합니다. 산출물을 수정한 뒤 제출하세요.")
        parents = json.dumps([valid[p][0] for p in deps])
        if stage in valid and valid[stage][2] == author:
            print("이미 접수된 동일 제출입니다.")
            return
        cur = db.execute("insert into submissions(stage,author,fingerprint,parents) values (?,?,?,?)",
                         (stage, author, fingerprint, parents))
        if rejected:
            db.execute("update rejections set corrected_by=? where submission_id=?",
                       (cur.lastrowid, rejected[0]))
        if stage == "comparison":
            db.execute("create table if not exists comparisons(submission_id integer primary key, measurements text not null)")
            db.execute("insert into comparisons values (?,?)", (cur.lastrowid, json_text(measurements)))
        print(f"{name} 접수 #{cur.lastrowid}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, sqlite3.Error) as err:
        sys.exit(f"오류: {err}")
