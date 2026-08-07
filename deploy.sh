#!/bin/bash
# 수집 결과를 Pages 에 반영하기 위한 커밋 스크립트.
# 컨벤션: 커밋까지만 수행하고 push 는 직접 실행한다.
set -e
cd "$(dirname "$0")"
git add data/listings.json docs/index.html
if git diff --cached --quiet; then
    echo "변경 없음 — 커밋 생략"
    exit 0
fi
git commit -m "매물 데이터 갱신 $(date +%Y-%m-%d)"
echo "커밋 완료 — 반영하려면: git push"
