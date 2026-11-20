---
name: evidence
description: "표본 영상·자막·썸네일의 출처와 시점을 고정해 회차별 비교 기준물을 준비할 때 사용한다."
---

# 기준물 확보팀

분석팀의 표본 선정 근거를 읽고 같은 형식·러닝타임·서사적 역할을 가진 대표 영상 한 편을 선택한다. 회차 폴더는 `python3 tools/studio.py brief EPISODE evidence`로 확인한다.

1. 레퍼런스 채널과 영상의 공개 페이지를 확인한다. 채널 ID, 영상 ID, 선정 이유, 파일을 얻은 경로와 확인일을 `reference.json`의 `channel_id`, `video_id`, `selection_reason`, `origin_note`에 적는다.
2. 이 표본에 대한 확보 권한이 있는 영상·자막·썸네일을 각각 `reference.mp4`, `reference.srt`, `reference.jpg`로 준비한다. 링크, 확장자만 고친 텍스트, 다른 채널 영상은 대조 기준물이 될 수 없다. 접근이 막히면 누락 파일과 필요한 제공자를 적고 해당 제출을 보류한다.
3. 셋이 같은 영상·버전인지 확인한다. 첫 대사와 중간 대사를 재생해 자막 시간축을 맞춘다. 자막이 수기 전사·자동 전사인 경우 확보 방식을 기록한다. 번인 자막의 위치·타입·스타일 판단은 실제 영상 프레임을 확인한다.
4. `handoff.json` 질문에 답하고 `python3 tools/studio.py submit EPISODE evidence --by NAME`으로 기획팀에 넘긴다. 개인이 확보한 기준물은 회차 폴더에 보관하고 공개 배포물에서는 제외한다.

[공통 검수 지침](../../../docs/QUALITY.md)
