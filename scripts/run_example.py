"""Smoke test: run the Phase 1 pipeline on the HapticGen paper.

Usage:
    python scripts/run_example.py
"""
from __future__ import annotations

from src.pipeline import app

# HapticGen: Generative Text-to-Vibration Model (CHI 2025)
# arXiv: 2412.13476
HAPTICGEN_ARXIV_ID = "2412.13476"

if __name__ == "__main__":
    app(["run", HAPTICGEN_ARXIV_ID, "--paper-slug", "hapticgen-chi2025", "--venue", "CHI 2025"])
