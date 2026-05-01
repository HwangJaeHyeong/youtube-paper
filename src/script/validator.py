"""Pydantic schema for generated scripts."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Section = Literal["intro", "background", "method", "results", "backstory", "limitations", "rating", "outro"]
Emotion = Literal["neutral", "skeptical", "excited", "dry", "amused"]


class Line(BaseModel):
    section: Section
    speaker: str
    text: str
    emotion: Emotion = "neutral"
    pause_after_ms: int = Field(default=200, ge=0, le=5000)
    visual_ref: str | None = None  # e.g. "Figure 1", "Table 2", or null


from pydantic import ConfigDict


class Rating(BaseModel):
    model_config = ConfigDict(extra="allow")
    verdict: str


class Metadata(BaseModel):
    estimated_duration_sec: int = 600
    target_length: Literal["longform", "shorts"] = "longform"
    generated_at: str = ""
    official_url: str | None = None


class Script(BaseModel):
    paper_id: str
    paper_title: str
    authors: list[str] = []
    venue: str = ""
    metadata: Metadata = Metadata()
    script: list[Line]
    rating: Rating


def validate_script(data: dict) -> Script:
    return Script.model_validate(data)
