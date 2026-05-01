#!/bin/bash
# 12 deep learning classics, one shorts each, scheduled 3/day over 4 days.
set -e
PY=c:/git/youtube-paper/.venv/Scripts/python.exe

run() {
    local arxiv="$1"; local when="$2"; local url="$3"
    $PY -m src.pipeline shorts-only "$arxiv" --official-url "$url" 2>&1 | tail -2
    $PY -m src.pipeline upload "${arxiv}-shorts" --shorts --privacy public --publish-at "$when" 2>&1 | tail -2
    echo "---"
}

run 1301.3781 "2026-04-23T09:00:00+09:00" "https://arxiv.org/abs/1301.3781"
run 1312.6114 "2026-04-23T18:00:00+09:00" "https://arxiv.org/abs/1312.6114"
run 1409.3215 "2026-04-23T21:00:00+09:00" "https://arxiv.org/abs/1409.3215"
run 1409.0473 "2026-04-24T09:00:00+09:00" "https://arxiv.org/abs/1409.0473"
run 1409.1556 "2026-04-24T18:00:00+09:00" "https://arxiv.org/abs/1409.1556"
run 1409.4842 "2026-04-24T21:00:00+09:00" "https://arxiv.org/abs/1409.4842"
run 1508.06576 "2026-04-25T09:00:00+09:00" "https://arxiv.org/abs/1508.06576"
run 1506.02640 "2026-04-25T18:00:00+09:00" "https://arxiv.org/abs/1506.02640"
run 1810.04805 "2026-04-25T21:00:00+09:00" "https://arxiv.org/abs/1810.04805"
run 2005.14165 "2026-04-26T09:00:00+09:00" "https://arxiv.org/abs/2005.14165"
run 2103.00020 "2026-04-26T18:00:00+09:00" "https://arxiv.org/abs/2103.00020"
run 2106.09685 "2026-04-26T21:00:00+09:00" "https://arxiv.org/abs/2106.09685"
