#!/bin/bash
# launchd 자동 갱신용 — 수집 → 커밋 → push (Pages 반영)까지 무인 수행.
# 사용자가 자동 push 를 명시 승인한 리포 (2026-08-07). 수동 커밋용은 deploy.sh.
set -e
cd "$(dirname "$0")"

/usr/bin/python3 -m homewatch.pipeline

# first_seen.json 은 되돌릴 수 없는 관측 기록이라 함께 남긴다
git add data/listings.json docs/index.html data/first_seen.json
if git diff --cached --quiet; then
    echo "$(date '+%F %T') 변경 없음 — 커밋 생략"
    exit 0
fi
git commit -m "자동 갱신 $(date '+%Y-%m-%d %H:%M')"
git push origin main
echo "$(date '+%F %T') Pages 반영 완료"
