"""Common TTS interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, speaker: str, out_path: Path) -> Path:
        """Synthesize `text` as `speaker` voice, write to `out_path`. Return the path."""
        raise NotImplementedError
