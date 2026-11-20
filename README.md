# Jisikcat 제작 스튜디오

지식한입의 공개 영상에서 확인한 편성·질문 설계·설명 구조를 독립 지식 채널의 제작 공정으로 옮긴 저장소다. 회차별 산출물, 팀 의존 관계, 검수자와 출고 이력을 관리한다.

## 바로 실행

저장소 루트에서 Python 3.9 이상으로 실행한다. 실제 미디어 제출에는 FFprobe가 필요하다.

```bash
python3 tools/studio.py teams
python3 tools/studio.py init ep-001 --topic "전기를 쓰면 돈을 주는 시간은 왜 생길까?"
python3 tools/studio.py status ep-001
python3 tools/studio.py brief ep-001 analysis
```

회차 폴더에 결과물을 채운 뒤 `python3 tools/studio.py submit ep-001 analysis --by analyst`로 인계한다. 분석 결과가 바뀌면 기존 결과에 의존한 제출물의 유효성이 다시 계산된다. GitHub Actions의 **Studio harness → Run workflow**에서도 회차 ID와 주제를 입력해 시작용 작업 폴더를 ZIP으로 받을 수 있다. GitHub 이슈의 **제작 회차** 양식은 담당자·산출물 링크를 공유하는 용도다. 회차 SQLite 원장은 단일 작업공간에서 관리한다.

## 팀 구성

```text
분석 → 기획 ┬→ 대본·팩트체크 ┬→ 자료·권리 ─┐
            │                ├→ 내레이션 ──┴→ 편집·자막 ──┐
            │                └──────────────────┐        │
            └→ 썸네일 ─────────────────────────┴→ 마케팅 ┴→ 독립 검수 → 출고 → 성과 회고
```

각 역할의 실행 지침은 [.agents/skills](.agents/skills)에 있다. 사람이 역할을 맡거나 에이전트에게 역할을 지정해 사용한다. CLI는 결과물·승인 의존 관계를 검사한다. 실제 자료 수집, 원고 작성, 녹음, 편집과 외부 게시에는 해당 팀의 작업이 필요하다.

|먼저 볼 문서|내용|
|---|---|
|[콘텐츠 분석](benchmark/content.md)|최근 10편 편성·제목 표본, 장편 길이, 별도 1편의 타임코드별 대본 분석|
|[시각 분석](benchmark/visual.md)|썸네일·영상에 대해 확인한 자료와 측정 범위|
|[롱폼 편성 예시](examples/negative-power/brief.md)|장편의 질문·산업 분류·반론 전개를 새 주제와 시각 자료에 적용한 15분 기획|
|[제작 핸드북](docs/PLAYBOOK.md) · [인계 명령](docs/WORKFLOW.md)|팀별 업무·산출물·재검수 방법|
|[자료 조달표](docs/SOURCES.md)|장면별 자료 공급 경로, 권리·사실 확인, 편집 인계 항목|
|[미디어 계측](docs/MEDIA.md)|yt-dlp로 표본 수집, FFmpeg로 후보 컷·명도·자막 노출 측정|
|[22초 제작 예시](examples/gray-square/README.md)|자체 생성 썸네일, 무음 검토 영상, 자막, 대본과 재생성 코드|

## 사용 도구

[yt-dlp](https://github.com/yt-dlp/yt-dlp)는 채널 표본 수집에, [FFmpeg](https://github.com/FFmpeg/FFmpeg)는 장면·음성 스트림 검사 및 예제 렌더링에 사용한다. GitHub Actions는 회차 작업공간을 구성하고 내려받을 수 있게 한다. 참고 영상의 촬영 원본, 사용 폰트, 내부 성과 지표처럼 공개 증거가 부족한 값은 실측 전까지 보류한다.

## 에이전트에 작업 배정

`python3 tools/dispatch.py ep-001 analysis`는 유효한 선행 제출을 확인해 팀 지시서와 산출물 목록을 출력한다. 인증된 [Codex CLI](https://github.com/openai/codex)가 설치된 환경에서는 끝에 `--run`을 붙여 팀 작업을 실행한다. 담당자는 파일을 확인한 뒤 submit한다. 기획 접수 후 썸네일과 대본처럼 선행 조건이 충족된 서로 다른 팀은 각자 별도 프로세스로 작업할 수 있다. 같은 회차·팀 폴더에는 한 번에 한 작업자만 배정한다.
