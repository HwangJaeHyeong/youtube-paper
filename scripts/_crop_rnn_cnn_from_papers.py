"""Download canonical RNN/CNN papers and crop their architecture figures.

- CNN: VGG (Simonyan & Zisserman, arXiv 1409.1556) — Table 1 / Figure 1
- RNN: Sutskever seq2seq (arXiv 1409.3215) — Figure 1 (unrolled RNN encoder-decoder)

Saves to data/audio/attention-mental-shorts/crops/{CNN,RNN}.png
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AUDIO_DIR, PAPERS_DIR
from src.ingest import arxiv_fetcher
from src.video import figure_cropper, figure_indexer

OUT_DIR = AUDIO_DIR / "attention-mental-shorts" / "crops"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (arxiv_id, slug, pref_refs_in_order, dest_filename)
SOURCES = [
    ("1409.3215", "rnn-seq2seq",     ["Figure 1"],                                 "RNN.png"),
    # GoogLeNet — Figure 3 is the full-width CNN architecture (Inception v1).
    ("1409.4842", "cnn-googlenet",   ["Figure 3", "Figure 2"],                     "CNN.png"),
]

for arxiv_id, slug, pref_refs, fname in SOURCES:
    print(f"\n=== {arxiv_id} ({slug}) → {fname} ===", flush=True)
    pdf = arxiv_fetcher.fetch_by_id(arxiv_id, dest_dir=PAPERS_DIR, slug=slug)
    print(f"  pdf: {pdf}")
    idx = figure_indexer.build_index(pdf)
    print(f"  figure_index: {idx}")
    chosen_ref = next((r for r in pref_refs if r in idx), None)
    if not chosen_ref:
        print(f"  FAIL: none of {pref_refs} indexed")
        continue
    page_idx = idx[chosen_ref]
    tmp_png = pdf.parent / f"{slug}__{chosen_ref.replace(' ', '_')}.png"
    figure_cropper.crop_visual(pdf, page_idx, chosen_ref, tmp_png)
    final = OUT_DIR / fname
    shutil.copy(tmp_png, final)
    print(f"  OK: cropped {chosen_ref} (page {page_idx}) → {final} ({final.stat().st_size} bytes)")
    time.sleep(1)
