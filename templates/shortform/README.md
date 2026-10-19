# 숏폼템플릿 (templates/shortform)

기존 `recipes/`, `src/pipeline.py`와 분리된 숏폼 템플릿입니다.
자막 형식(단어 단위 타이밍)과 피규어 핀트(`shots`의 `cue`/`rect`)는 기존과 같고,
**대본 컨셉 · 목소리 · 디자인**만 이 폴더에서 정합니다.

```
templates/shortform/
├── prompt.md      대본 작성 프롬프트 (말투, 구성, 금지어, 예시)  ★ 주로 고칠 곳
├── critic.md      채점 기준 (초안을 채점하고 고칠 점 지적)
├── polish.md      마지막 다듬기 기준 (Opus)
├── voice.json     목소리 설정 (참고 음성 경로, 받아쓰기, 속도)
├── voice/         참고 음성 파일 (mp3/wav는 gitignore — 레포에 안 올라감)
├── design.json    디자인 값 (자막 방식·위치, 제목, 피규어 영역)
├── background.png 배경 이미지
├── font.ttf       제목·자막 폰트 (Dancing Peoples, OFL)
└── papers/        논문별 결과물: papers/<slug>/recipe.json (+ reference/)
```

## 채울 것
1. `prompt.md`, `critic.md`, `polish.md`의 ★ 부분 (맨 아래 [출력] 형식은 그대로)
2. `voice/`에 참고 음성을 넣고 `voice.json`의 `ref_text`에 그 음성의 정확한 받아쓰기
3. `design.json` 값 (지금은 기존 영상과 같은 기본값)
