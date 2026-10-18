# HaptiCraft 최종본 재현

공개한 버전: https://www.youtube.com/shorts/vcRK_zeecjE

기존 상단 제목·팝업 자막·하단 안내, Puck 단일 음성, 1.2배속, 단어별 화면 전환을 저장했습니다.
Figure에는 원문에 없는 글씨·가림판·범례를 추가하지 않습니다.

## 다른 컴퓨터에서 실행

Python 3.10 이상과 FFmpeg/FFprobe가 필요합니다. FFmpeg는 `subtitles` 필터(libass)가 포함된 빌드여야 합니다.
macOS는 `brew install ffmpeg`, Ubuntu는 `sudo apt install ffmpeg`로 설치할 수 있습니다.
Windows는 FFmpeg를 설치하고 `ffmpeg`, `ffprobe`가 PATH에서 실행되도록 설정하세요.
이 재현 스크립트에는 Poppler, Claude/Codex 로그인, Gemini API 키가 필요하지 않습니다.

```bash
git clone https://github.com/HwangJaeHyeong/youtube-paper.git
cd youtube-paper
python -m venv .venv
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/rebuild_hapticraft.py --pdf "/path/to/HaptiCraft.pdf"
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\rebuild_hapticraft.py --pdf "C:\papers\HaptiCraft.pdf"
```

입력은 14페이지 원문 PDF입니다. [출판사 원문](https://doi.org/10.1109/TVCG.2026.3683951)에서 받아 지정하세요.
논문 PDF와 계정 자격 증명은 GitHub에 포함하지 않았습니다.

출력:

```text
data/videos/hapticraft-standard-shorts-figures-only-1.2x.mp4
```

완전히 빈 작업 폴더로도 실행할 수 있습니다:

```bash
.venv/bin/python scripts/rebuild_hapticraft.py --pdf "/path/to/HaptiCraft.pdf" \
  --work-dir "/tmp/hapticraft-data" --output-dir "/tmp/hapticraft-output"
```

## 저장한 입력

- `recipes/hapticraft/recipe.json`: 최종 대본, 숫자·영문 표기, PDF Figure/크롭 좌표, 음성·레이아웃 설정, 화면 전환 기준 단어.
- `recipes/hapticraft/reference/narration-1.2x.wav`: 공개본의 음성을 그대로 재사용합니다. 새 TTS 호출에 따른 목소리 변화를 막습니다.
- `recipes/hapticraft/reference/words.json`: 공개본의 실제 발화 시점.
- `assets/fonts/Pretendard-Black.otf`: 제목·자막 폰트. 함께 둔 OFL 라이선스로 배포합니다.

폰트를 따로 설치할 필요가 없습니다. 자막 엔진에 번들 폰트 폴더를 직접 전달합니다.
대본과 음성은 연결된 스냅샷입니다. 대본만 수정하면 잘못된 싱크로 렌더링하지 않고 오류를 냅니다.
다른 논문의 음성 생성은 별도 제작 단계이며, 이 스크립트는 공개본을 재현하는 용도입니다.
FFmpeg/운영체제 버전에 따라 MP4 바이트는 달라질 수 있지만 음성과 편집 기준은 동일합니다.

## 업로드

재현 스크립트는 YouTube에 업로드하지 않습니다.
업로드를 별도로 실행하려면 자신의 `credentials/youtube_oauth_client.json`과 YouTube 로그인이 필요합니다:

```bash
.venv/bin/python scripts/upload_hapticraft.py
```

이 업로드 스크립트는 **공개** 업로드입니다. `data/raw/hapticraft-public-upload.json` 기록이 있으면 중복 실행을 막습니다.
