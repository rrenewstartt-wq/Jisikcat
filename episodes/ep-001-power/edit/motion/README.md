# EP-001 실사·모션 재편집

`shots.csv`에는 마스터 시간축의 컷 지점과 원본 파일 시작 시각이 초 단위로 들어 있다. `chart`와 `math` 구간에는 각각 Remotion과 HyperFrames 렌더가 들어가며 이 구간의 바탕 영상은 읽지 않는다. `film.py`가 24 fps 프레임 경계로 컷을 맞추고 축자 자막과 원래의 한국어 내레이션을 합친다. 실사 파일은 [출처·이용 조건·해시](footage.json)에서 확인할 수 있다.

## 같은 편집본 재생성

Python 3.11+, Pillow, FFmpeg(libass·libx264), Noto Sans CJK KR, Node.js와 Chromium을 준비하고 이 폴더에서 실행한다. `prepare.py`는 공개 소스에서 확인한 파일만 내려받고 해시를 검증한다. 두 장면의 완성된 렌더는 `renders/`에 포함했다.

```sh
npm ci
python3 prepare.py
python3 film.py work/footage ../../edit/master.mp4
```

가격 그래프나 영수증을 수정했다면 아래 명령으로 해당 렌더를 먼저 갱신한다. 설치된 Chromium 경로는 환경에 맞춰 지정한다. `npm run studio`에서 그래프를 스크러빙할 수 있다.

```sh
npx remotion render src.jsx DayAhead renders/day-ahead.mp4 --browser-executable=/usr/bin/chromium
npx hyperframes lint tariff
HYPERFRAMES_BROWSER_PATH=/usr/bin/chromium npx hyperframes render tariff --fps 24 --workers 1 --output renders/tariff.mp4
```

실사 구간에서는 현장 소스의 움직임을 사용한다. 발전소와 구매자 사이에 표시한 흐름은 음수 가격에서의 에너지 거래를 설명하는 자체 도해다. 한 화면의 발전소가 그 거래를 수행했다는 의미는 없다.
