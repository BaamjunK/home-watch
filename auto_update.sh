#!/bin/bash
# launchd 자동 갱신용 — 수집 → 커밋 → push (Pages 반영)까지 무인 수행.
# 사용자가 자동 push 를 명시 승인한 리포 (2026-08-07). 수동 커밋용은 deploy.sh.
set -e
cd "$(dirname "$0")"

# 다음 회차 2분 전 자동 기상 예약 — 맥이 잠들어도 배치가 이어지도록 체인을 만든다.
# (sudoers 에 pmset NOPASSWD 가 등록된 경우에만 동작, 없으면 조용히 건너뜀.
#  매일 08:58 안전망 기상은 `pmset repeat` 로 별도 등록 — 체인이 끊겨도 아침에 재시동)
schedule_next_wake() {
    local now next="" d day hm ts
    now=$(date +%s)
    for d in 0 1; do
        day=$(date -v+"${d}"d +%m/%d/%y)
        for hm in 08:58 11:58 14:58 17:28 20:58; do
            ts=$(date -j -f "%m/%d/%y %H:%M" "$day $hm" +%s 2>/dev/null) || continue
            if [ "$ts" -gt "$now" ]; then next="$day $hm:00"; break 2; fi
        done
    done
    if [ -n "$next" ]; then
        sudo -n /usr/bin/pmset schedule wakeorpoweron "$next" 2>/dev/null \
            && echo "$(date '+%F %T') 다음 기상 예약: $next" || true
    fi
}
schedule_next_wake

# caffeinate: 수집(30분 안팎) 중 유휴/시스템 잠자기로 끊기지 않게 잡아둔다 (-s 는 전원 연결 시)
/usr/bin/caffeinate -is /usr/bin/python3 -m homewatch.pipeline

# first_seen.json 은 되돌릴 수 없는 관측 기록이라 함께 남긴다
git add data/listings.json docs/index.html data/first_seen.json
if git diff --cached --quiet; then
    echo "$(date '+%F %T') 변경 없음 — 커밋 생략"
    exit 0
fi
git commit -m "자동 갱신 $(date '+%Y-%m-%d %H:%M')"
git push origin main
echo "$(date '+%F %T') Pages 반영 완료"
