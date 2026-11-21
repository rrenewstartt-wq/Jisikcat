# 회차 인계

1. 저장소 루트에서 `python3 tools/studio.py init ep-001 --topic "이번 주제"`를 실행한다.
2. `python3 tools/studio.py status ep-001`로 현재 작업 가능한 팀을 찾는다.
3. `python3 tools/studio.py brief ep-001 analysis`로 필수 파일과 인계 질문을 확인한다. 팀별 작업 폴더는 episodes/ep-001/팀이름이다.
4. 질문에 답한 handoff.json과 실제 산출물을 해당 폴더에 둔다. 자료팀은 sources.json에 asset, source, license, evidence, credit을 기록한다.
5. `python3 tools/studio.py submit ep-001 analysis --by analyst`를 실행한다. 다음 팀은 선행 산출물이 접수된 후 제출할 수 있다.
6. 제작 참여자와 다른 검수자가 qa를 제출한다. `python3 tools/studio.py history ep-001`에서 인계 이력을 확인한다.

선행 파일의 내용이 달라지면 기존 제출은 재검토 대상으로 바뀐다. 인계된 파일을 고친 경우 해당 팀과 그 결과에 의존하는 팀이 차례대로 다시 제출한다. 미디어 검증에는 ffprobe가 필요하다. 해시와 제출 원장은 파일 버전을 추적하며 내용 판단은 해당 팀과 검수자가 수행한다.

원본 확보팀(evidence)과 포맷 분석팀(format)을 통과해야 기획을 제출할 수 있다. 화면 근거 검수팀(visualproof)은 완성본의 주장별 증거를 확인하고 대조 심사팀에 넘긴다. [제출 규격](SCENE-EVIDENCE.md) 대조 심사팀(comparison)은 brief에서 현재 reviewed_inputs를 읽고 scorecard.json에 그 객체를 추가한다. 계측표와 판정은 같은 회차의 동일 버전에 묶인다. 통과한 비교표는 `python3 tools/studio.py metrics 회차ID`로 확인한다. 기존 회차는 upgrade 명령으로 신규 양식을 추가한다.
