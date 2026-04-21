"""Smoke test for the Phase 1 pipeline.

HapticGen is not on arXiv (ACM DL only), so we can't fetch it by ID.
For the first-run smoke test we use a well-known arXiv paper instead.
To test on HapticGen: drop the PDF into `data/papers/hapticgen-chi2025.pdf`
and call `src.pipeline.run` from a Python shell with a local path.

Usage:
    python scripts/run_example.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import app

# Attention Is All You Need (Vaswani et al., 2017) — short, famous, arXiv-hosted.
DEMO_ARXIV_ID = "1706.03762"

if __name__ == "__main__":
    app(["run", DEMO_ARXIV_ID, "--paper-slug", "attention-is-all-you-need", "--venue", "NeurIPS 2017"])
