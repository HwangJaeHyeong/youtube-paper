# PaperCast pipeline (script -> TTS via qwen-tts service -> FFmpeg video).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg poppler-utils fonts-noto-cjk nodejs npm curl \
 && rm -rf /var/lib/apt/lists/*
# Claude Code CLI for claude-agent-sdk (auth: CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY in .env)
RUN npm install -g @anthropic-ai/claude-code
# Pretendard (OFL) — subtitle/header font the project uses; Malgun is Windows-only.
RUN mkdir -p /usr/share/fonts/pretendard && for w in Black Bold Regular; do \
      curl -fsSL -o /usr/share/fonts/pretendard/Pretendard-$w.otf \
      https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/packages/pretendard/dist/public/static/Pretendard-$w.otf; \
    done && fc-cache -f
ENV FONT_BOLD=/usr/share/fonts/pretendard/Pretendard-Bold.otf \
    FONT_REG=/usr/share/fonts/pretendard/Pretendard-Regular.otf \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Source is bind-mounted at /app by docker-compose (edits apply without rebuild).
CMD ["python", "-m", "src.pipeline", "inbox"]
