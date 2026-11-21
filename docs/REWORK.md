# 회차 반송과 재검수

담당자가 `status`에서 확인한 **접수 번호**에 대해 반송을 기록한다. 사유에는 문제 위치, 수정 내용, 재검수 통과 기준을 함께 적는다. 다음은 편집 제출 번호가 12인 회차의 예다.

```sh
python3 tools/studio.py status ep-001
python3 tools/studio.py reject ep-001 edit --submission 12 --by '독립 검수 서현' --owner '편집 유진' --reason '00:43 그래프의 단위가 원자료와 다름. 축을 원/가구로 고치고 자막 단위와 대조할 것.'
python3 tools/studio.py brief ep-001 edit
python3 tools/studio.py history ep-001
```

반송 시 편집팀의 기존 접수와 이를 사용한 대조 심사·독립 검수·출고 접수는 효력을 잃는다. 썸네일처럼 해당 산출물에 의존하지 않는 팀은 유효한 접수를 유지한다. 여러 팀이 서로 다른 결함을 수정해야 하면 해당 팀별로 현재 유효한 제출을 반송한다. 상위 제출의 반송으로 이미 무효화된 하위 팀은 상위 수정본 접수 후 재검토한다.

수정 담당자는 `brief`에 나온 반송 사유에 맞게 필수 산출물을 고치고, 검수자가 다시 볼 위치와 변경점을 handoff.json에 적는다. 실제 필수 산출물이 그대로면 제출자나 인계 문구만 바꿔도 CLI가 재접수를 차단한다. 현재 회차의 다음 제출 번호는 원장이 자동으로 배정한다.

```sh
python3 tools/studio.py submit ep-001 edit --by '편집 유진'
python3 tools/studio.py status ep-001
python3 tools/studio.py brief ep-001 comparison
```

비교 심사자는 새 접수 번호로 편집본을 다시 대조하고 독립 검수자는 새 심사 버전과 재생 위치를 확인한다. 출고 팀은 새 QA가 통과한 뒤 인계한다. 수정한 파일의 기술적 검사를 통과해도 결함이 남아 있다면 검수자는 새 제출 번호를 반송할 수 있다. `history`는 최초 접수·반송 사유·수정 담당·연결된 수정 접수 번호를 남긴다. 이미 완료된 외부 게시를 되돌리는 명령은 아니다.

기존 회차는 반송 원장을 처음 쓸 때 자동 생성한다. 새로운 QA 양식이 필요한 회차는 `python3 tools/studio.py upgrade ep-001`로 누락된 양식을 추가한다. `reject`와 `submit`은 같은 SQLite 쓰기 잠금을 사용한다. 동일 판정 재시도에는 새 반송 이력이 생기지 않고, 지난 제출 번호로 도착한 판정이 새 버전을 반송할 수 없다. CLI 실행 중에는 검사 대상 파일을 편집하지 않는다.
