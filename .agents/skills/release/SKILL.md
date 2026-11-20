---
name: release
description: "출고 담당. 납품 패키지와 게시 결과를 관리할 때 사용한다."
---

# 출고

먼저 해당 회차의 status를 확인하고 작업 지시를 연다.

```sh
python3 tools/studio.py brief EPISODE release
```

1. 검수 승인 버전과 실제 파일의 해시를 비교한다.
2. 최종 영상, 썸네일, 자막, 설명문, 라이선스 기록을 함께 묶는다.
3. 승인받은 채널·공개 범위·예약 시간을 기록하고 게시한 경우 실제 URL을 확인한다.

작업 결과와 남은 의문을 회차 산출물에 적고 CLI의 submit으로 인계한다.
