# 다른 논문 영상 재현하기

논문별 자료는 `recipes/<paper>/recipe.json`, 제작기는 `scripts/build_paper_short.py`로 분리했습니다. 기존 HaptiCraft 전용 명령도 계속 사용할 수 있습니다.

## Generative Agents 예제

Python 3.10+, FFmpeg/ffprobe를 설치한 뒤 저장소 루트에서 실행합니다. 설치 방법은 [HaptiCraft 실행 문서](hapticraft.md)를 참고하세요. Windows는 `.venv\Scripts\python.exe`, macOS/Linux는 `.venv/bin/python`을 사용합니다.

```bash
python -m venv .venv
# 가상환경 활성화 후
python -m pip install -r requirements.txt
python scripts/build_paper_short.py --recipe recipes/generative-agents/recipe.json --pdf /path/to/3586183.3606763.pdf --work-dir data/build-generative-agents --output data/videos/generative-agents-shorts-1.2x.mp4
```

원본 22쪽 PDF는 직접 제공해야 합니다. 음성, 단어 타이밍, 도입부 데모는 저장소에 포함되어 API 키나 웹사이트 접속 없이 재현됩니다. 1080×1920, 30fps, Puck 연속 나레이션 1.2배속, 원래 제목·댓글 안내·자막 형식입니다. 실행해도 YouTube에 업로드하지 않습니다. FFmpeg 버전에 따라 인코딩 바이트는 달라질 수 있습니다.

## 새 논문 추가

1. 예제 폴더를 `recipes/<새 논문>/`으로 복사하고 `slug`, `title_hook`, `paper`, `script`를 바꿉니다. 원문을 확인해서 대본을 작성하세요. 영어·숫자는 원래 표기를 사용합니다.
2. 한 번에 녹음/생성한 음성을 1.2배속으로 만든 `reference/narration-1.2x.wav`와, 그 최종 음성에 맞춘 `reference/words.json`을 준비합니다. words는 대본을 공백으로 나눈 각 토큰의 `{text, line, start, end}` 배열입니다. `line`은 0부터, 시간은 초입니다. 기존 음성에 새 대본을 끼워 넣으면 안 됩니다.
3. `figures`에 PDF의 1부터 시작하는 `page`, 0부터 시작하는 `image_index`를 기록합니다. image_index는 PyMuPDF `page.get_image_info(xrefs=True)` 순서입니다. `shots`는 `{line, cue, figure, rect?}`입니다. `cue: null`은 문장 시작, 문자열은 해당 단어 시작에 맞춥니다. rect는 원본 이미지에 대한 `[left, top, right, bottom]` 비율(0~1)입니다. 원본에 글씨를 덧그리지 않습니다.
4. 선택적으로 `intro_demo`에 로컬 클립 경로·원출처·끝나는 문장 `end_line`을 기록합니다. 데모가 없으면 필드 전체를 제거하세요. 데모 음성은 사용하지 않습니다.
5. 아래 명령으로 체크섬을 갱신한 뒤 공통 제작기로 렌더하고, 크롭·자막·싱크를 눈으로 확인합니다. 대본 생성·새 음성 합성·논문 해석은 이 재현 명령의 기능에 포함되지 않습니다.

```bash
python scripts/seal_paper_recipe.py --recipe recipes/<새 논문>/recipe.json --pdf /path/to/paper.pdf
python scripts/build_paper_short.py --recipe recipes/<새 논문>/recipe.json --pdf /path/to/paper.pdf
```

`layout.figure_box`는 기존 1080×1920 캔버스 안의 figure 배치 영역입니다. 화면 합성기는 이 캔버스를 88%로 축소합니다. `caption_y`, `caption_font_size`도 레시피에 저장합니다. 도입부 데모는 기존 형식의 중앙 영역에 배치됩니다.

## 출처

Generative Agents: Joon Sung Park 외, UIST 2023, [DOI](https://doi.org/10.1145/3586183.3606763). 도입부는 [연구팀 공식 공개 웹 데모](https://reverie.herokuapp.com/arXiv_Demo/)의 리플레이 화면을 녹화했습니다. NPC 이동 장면이며 실제 파티 영상이라고 표시하지 않습니다. 파티 장면과 이후 설명에는 제공한 PDF의 원본 figure를 사용합니다. 게임 에셋 작가는 [연구팀 저장소의 acknowledgements](https://github.com/joonspk-research/generative_agents#acknowledgements)를 참고하세요.
