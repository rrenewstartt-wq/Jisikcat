#!/usr/bin/env python3
"""Prepare or run one Codex team assignment for an initialized episode."""
import argparse
from pathlib import Path
import sqlite3
import subprocess
import sys

import studio
import story_formulas


def assignment(episode, stage):
    directory = (studio.ROOT / "episodes" / episode).resolve()
    if directory.parent != (studio.ROOT / "episodes").resolve() or not (directory / "studio.db").is_file():
        raise ValueError("init으로 생성한 회차 ID를 입력하세요.")
    with sqlite3.connect(directory / "studio.db") as db:
        db.execute("begin")
        valid, _ = studio.accepted(db, directory)
        rework = studio.pending_rework(db, stage)
        topic = db.execute("select topic from episode").fetchone()[0]
    name, deps, questions, outputs = studio.STAGES[stage]
    missing = [key for key in deps if key not in valid]
    if missing:
        raise ValueError("선행 제출 필요: " + ", ".join(missing))
    instructions = (studio.ROOT / ".agents" / "skills" / stage / "SKILL.md").read_text(encoding="utf-8")
    return directory / stage, "\n".join([
        f"{name} 팀으로 이 회차의 산출물을 작성한다.",
        f"회차 주제: {topic}",
        f"저장소: {studio.ROOT}",
        f"작업 디렉터리: {directory / stage}",
        "입력: " + ", ".join(str(directory / dep) for dep in deps),
        "검토할 선행 제출 번호: " + str({dep: valid[dep][0] for dep in deps}),
        "비교 기준 폴더: " + str(directory / "evidence"),
        "작성할 파일: " + ", ".join([*outputs, "handoff.json"]),
        "인계 항목: " + ", ".join(questions),
        "저장소의 benchmark와 docs를 근거로 사용한다. 검증할 수 없는 내용은 미확인으로 남긴다.",
        "현재 팀 디렉터리에만 산출물을 작성한다. submit, 외부 게시, 원격 저장소 변경은 담당자에게 맡긴다.",
        "실제 음원·확인된 권리 등 선행 재료가 부족하면 누락 사항을 보고한다.",
        story_formulas.brief(directory, stage),
        *([rework] if rework else []),
        instructions,
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode")
    parser.add_argument("team", choices=list(studio.STAGES))
    parser.add_argument("--run", action="store_true", help="설치된 Codex CLI로 작업 실행")
    args = parser.parse_args()
    workdir, prompt = assignment(args.episode, args.team)
    if args.run:
        result = subprocess.run(["codex", "exec", "--cd", str(workdir), "--sandbox",
                                 "workspace-write", "-"], input=prompt, text=True)
        return result.returncode
    print(prompt)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, sqlite3.Error) as error:
        sys.exit(f"오류: {error}")
