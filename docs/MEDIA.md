# 레퍼런스 영상 계측

분석팀이 회차별 출처와 비교 조건을 남기고 편집팀이 독립적으로 재현하는 절차다. Python 3, FFmpeg, ffprobe를 사용한다. 온라인 목록 조회에는 yt-dlp 실행 파일이 필요하다. [FFmpeg](https://github.com/FFmpeg/FFmpeg) · [yt-dlp](https://github.com/yt-dlp/yt-dlp)

## 표본 목록 만들기

```sh
python3 tools/media.py sample --format videos --limit 12 > reference-videos.json
python3 tools/media.py sample --format shorts --limit 12 > reference-shorts.json
```

기본값은 요청한 채널 ID다. 목록은 채널 탭의 반환 순서를 따른다. 조회수와 길이가 제공되지 않으면 JSON에서 null로 남긴다. 두 형식의 표본을 분리하고 수집일을 기록한다. 연속 업로드 표본과 성과 상위 사례를 구분한다. 상위 사례만으로 채널 전체의 공식을 정하면 이례적인 히트작을 일상적인 편집 관행으로 오인할 수 있다.

## 로컬 원본 측정

영상, 썸네일, 자막을 제공받거나 사용할 수 있는 출처에서 확보한 뒤 다음처럼 검사한다. source에는 해당 영상의 실제 URL을 넣는다. 썸네일과 자막은 선택 사항이다.

```sh
python3 tools/media.py inspect reference.mp4 --source "$VIDEO_URL" \
  --thumbnail thumbnail.jpg --captions captions.vtt > observations.json
```

|출력|판독과 후속 검수|
|---|---|
|candidate_cut_seconds|가로 320픽셀로 축소한 프레임 간 FFmpeg scene 값이 기본 0.30을 넘는 시점이다. 번쩍임도 후보가 되므로 컷 앞뒤를 대조한다. 줌이나 천천히 바뀌는 화면은 빠질 수 있다.|
|median_candidate_shot_s|영상 시작과 끝을 포함해 인접 후보 사이의 중앙값을 낸다. 도입과 본문의 편집 속도가 다르면 구간별 타임코드를 별도 기록한다.|
|dark_fraction_lt64, bright_fraction_ge192|썸네일을 160×90 회색조로 축소해 측정한 어두운 픽셀과 밝은 픽셀 비율이다. 색상, 글자와 배경의 실제 대비, 소재 배치는 원본을 따로 읽는다. 세로·가로 프레임을 같은 그룹에 섞지 않는다.|
|cue_count, median_duration_s, median_lines, median_chars_per_cue|외부 SRT 또는 WebVTT의 표시 구간과 줄을 집계한다. 자동 생성 자막은 누적 표시가 겹칠 수 있다. 외부 파일에서 폰트나 화면 내 번인 자막 타이밍을 추정하지 않는다.|

## 수작업 프레임 대조

첫 훅, 첫 설명 컷, 중간 전환, 결론 직전에서 각각 정확한 시각을 정한다. 16초 지점을 예로 들면 아래처럼 PNG 한 장을 얻는다.

```sh
ffmpeg -ss 16 -i reference.mp4 -frames:v 1 frame-16s.png
```

프레임마다 자막 상단·하단의 y 좌표를 세로 해상도로 나누고, 줄 수·강조색·배경 상자·외곽선·단어 강조 전환을 적는다. 서체 이름은 공식 크레디트가 있을 때만 확정한다. 자료의 원출처를 추적할 때는 영상 설명과 화면 내 크레디트를 먼저 대조하고 원본 게시물의 날짜·작성자·라이선스를 별도로 기록한다. 한 화면이 특정 라이브러리와 닮았다는 사실만으로 그 라이브러리를 실제 출처로 적을 수 없다.

## 오프라인 검사 결과

검정 1초와 흰색 1초를 이은 320×180 합성 영상, 같은 크기의 검정 PNG, 1초씩 두 문장이 담긴 WebVTT로 검사했다. 장면 후보는 1.0초, 후보 간 중앙값은 1.0초였다. 어두운 픽셀 비율은 1.0, 자막 수는 2, 자막 노출 중앙값은 1.0초였다. 이 수치는 도구 검증용 합성 입력의 결과다.
