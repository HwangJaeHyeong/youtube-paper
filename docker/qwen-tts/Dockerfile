# Qwen3-TTS GPU server. RTX 50 series (Blackwell) needs CUDA 12.8 builds.
FROM pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime

RUN apt-get update && apt-get install -y --no-install-recommends sox libsox-fmt-all && rm -rf /var/lib/apt/lists/*
# Pin torchaudio to the image's torch so pip doesn't swap torch out.
RUN pip install --no-cache-dir torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128 \
 && pip install --no-cache-dir qwen-tts==0.1.1

WORKDIR /app
COPY server.py .
EXPOSE 8880
CMD ["python", "server.py"]
