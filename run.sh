#!/bin/bash
# 매물 수집 + 대시보드 갱신. 완료 후 docs/index.html 을 브라우저로 연다.
set -e
cd "$(dirname "$0")"
python3 -m homewatch.pipeline "$@"
open docs/index.html
