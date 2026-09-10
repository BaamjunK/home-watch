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

# 수집 + 워치독: 잠자기로 얼어붙은 실행이 밤을 새우며 다음 회차를 막는 일을 끊는다.
# launchd 는 이전 인스턴스가 살아있으면 새 회차를 띄우지 않으므로, 총 실행이
# 상한(2시간 30분 — 회차 간격 3시간보다 짧게)을 넘으면 이번 회차를 버리고 끝낸다.
# 잠자기 중엔 감시 루프도 함께 얼지만, 깨어나는 즉시 벽시계 경과를 보고 발동한다.
MAX_RUN_SEC=$((150 * 60))
/usr/bin/python3 -m homewatch.pipeline &
PIPE_PID=$!
/usr/bin/caffeinate -is -w "$PIPE_PID" &   # 파이프라인이 살아있는 동안만 잠자기 억제
START=$(date +%s)
while kill -0 "$PIPE_PID" 2>/dev/null; do
    if [ $(( $(date +%s) - START )) -ge "$MAX_RUN_SEC" ]; then
        echo "$(date '+%F %T') 워치독: 실행 $((MAX_RUN_SEC/60))분 초과 — 이번 회차 중단, 다음 회차가 이어받는다"
        kill "$PIPE_PID" 2>/dev/null || true
        sleep 10
        kill -9 "$PIPE_PID" 2>/dev/null || true
        exit 1
    fi
    sleep 30
done
wait "$PIPE_PID"   # 파이프라인이 실패로 끝났으면 set -e 로 여기서 중단

# first_seen.json 은 되돌릴 수 없는 관측 기록이라 함께 남긴다
git add data/listings.json docs/index.html data/first_seen.json
if git diff --cached --quiet; then
    echo "$(date '+%F %T') 변경 없음 — 커밋 생략"
    exit 0
fi
git commit -m "자동 갱신 $(date '+%Y-%m-%d %H:%M')"
git push origin main
echo "$(date '+%F %T') Pages 반영 완료"
