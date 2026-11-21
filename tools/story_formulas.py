"""회차가 채택한 서사 설계를 팀 작업으로 변환한다."""
import json

# 사례별 핵심 질문과 필요한 검증 단서. 제목 기반 전용과 실제 관찰을 구분한다.
CASES = {
    "average": ("한국인 평균", "통념을 어떤 분모로 계산했는가", "집단·기간·평균/중앙값·반례"),
    "field": ("몽골", "익숙한 현상을 현지 조건으로 다시 설명할 수 있는가", "장소·시점·관찰·일반화 한계"),
    "aftermath": ("러시아", "사건 뒤 누가 어떤 대가를 치렀는가", "사건 전후·부담 주체·시차·대체 설명"),
    "flow": ("석유복지", "재원은 어떤 경로와 조건으로 수혜자에게 가는가", "재원·중간 기관·자격·실수혜자"),
    "chain": ("리먼", "복잡한 위기가 어떤 경로로 전파됐는가", "발단·전달 기제·결과·끊길 수 있는 고리"),
}

# 각 행의 첫 항목은 산출물 작업, 두 번째는 후속 팀이 재현할 확인 동작.
DESKS = {
    "format": ("선정한 기준작의 도입·중반·결말과 썸네일을 profile.json에 고정한다.", "각 시각을 열어 서사·컷·자막·소리의 관찰을 재현한다."),
    "visualproof": ("대본의 각 주장에 이번 버전의 화면 증거를 대응시킨다.", "분위기 컷, 실사례와 모형의 혼동, 반복 자산이 보태는 정보를 점검한다."),
    "analysis": ("다섯 질문을 이번 소재에 대입하고 채택 근거를 observations.md에 적는다.",
                 "관찰한 원문·영상 위치와 새 회차에 적용할 가설을 구분한다."),
    "evidence": ("선택한 질문에서 확인할 원본 컷·발화·제목과 시간 위치를 reference.json의 선정 근거에 남긴다.",
                 "원본에서 확인한 표현과 자체 구성안을 서로 다른 문장으로 적는다."),
    "planning": ("질문 제시 → 판단에 필요한 증거 → 답 순서로 brief.md에 세 구간을 설계한다.",
                 "끝 구간이 도입 질문에 답하는지, 예외가 빠지지 않았는지 짚는다."),
    "script": ("script.md에 질문, 증거, 결론 문장을 쓰고 주장별 키로 facts.md에 연결한다.",
               "검증 단서 각각에 원문과 조건을 달고 반례를 읽어도 결론이 성립하는지 확인한다."),
    "assets": ("검증 단서를 보여줄 수치표·지도·연표·흐름도 중 적합한 자료를 골라 sources.json에 기록한다.",
               "화면에 쓰는 항목별 원자료·시점·사용권을 대조한다."),
    "thumbnail": ("선택한 질문을 한 장면에서 알아볼 수 있게 주체와 비교 대상을 배치한다.",
                   "작게 봐도 주체가 보이고 그래픽이 본문보다 강한 결론을 암시하지 않는지 확인한다."),
    "audio": ("질문·증거·결론의 경계를 읽는 속도와 쉼으로 나누고 검증 단서의 핵심어를 또렷이 읽는다.",
              "실제 녹음에서 수치 단위, 장소, 시간, 주체를 대본과 대조한다."),
    "edit": ("증거가 나오는 발화에 대응하는 자료 컷을 붙이고 검증 단서를 자막에 남긴다.",
             "각 컷의 단서가 음성과 같은 대상을 가리키는지 편집본 시각으로 확인한다."),
    "marketing": ("metadata.md에 선택한 유형에 맞는 제목과 답의 범위를 설명하는 소개문을 작성한다.",
                  "본문에서 회수하는 질문인지, 제목과 썸네일의 조합이 과장하는지 확인한다."),
    "comparison": ("원본과 제작본에서 질문 제시·증거·회수에 해당하는 위치를 찾아 비교 기록을 만든다.",
                   "구조상 대응이 없는 장면은 차이로 기록하고 원본 프레임 없이 일치를 추정하지 않는다."),
    "qa": ("질문에서 결론까지 검증 단서가 유지되는지 원자료·대본·자막·썸네일을 함께 대조한다.",
           "누락된 조건이나 대안 설명이 결론을 뒤집는다면 해당 시각과 근거를 적고 반송한다."),
    "release": ("delivery.md에 선택한 공식과 승인된 원고·자막·썸네일·제목의 버전을 함께 적는다.",
                "최종 패키지에서도 질문과 답, 출처와 조건 표기가 검수본과 같은지 확인한다."),
    "learning": ("retrospective.md에 다음 회차에서 바꿔볼 한 요소와 관측 구간을 정한다.",
                 "도입·증거·결말의 실제 조회 가능 지표와 미제공 지표를 구분하고 인과 추정을 보류한다."),
}


def selected(episode):
    path = episode / "analysis" / "handoff.json"
    if not path.is_file():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("analysis/handoff.json은 객체여야 합니다.")
    key = data.get("story_formula", "")
    if not isinstance(key, str) or (key and key not in CASES and key != "custom"):
        raise ValueError("story_formula는 " + ", ".join([*CASES, "custom"]) + " 중 하나입니다.")
    return key


def brief(episode, stage):
    key = selected(episode)
    lines = ["서사 공식 근거: benchmark/top5-stories.md",
             "아래 공식은 새 회차의 설계 후보입니다. 원작 전개의 실측 결과는 근거 문서의 확인 범위를 따르세요."]
    if not key:
        lines.append("미선택: 적합한 한 가지를 골라 분석 인계의 story_formula에 기록할 수 있습니다. 기타 구성은 custom입니다.")
    elif key == "custom":
        lines.append("선택: custom. 분석팀 observations.md에 적은 자체 질문·검증 단서를 적용하세요.")
    else:
        lines.append("선택: " + key)
    for code, (label, question, cues) in CASES.items():
        if key and code != key:
            continue
        lines.append(f"  {code} ({label}) | {question} | 검증 단서: {cues}")
    task, check = DESKS[stage]
    lines.extend(["팀 작업: " + task, "인계 전 확인: " + check])
    return "\n".join(lines)
