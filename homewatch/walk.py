"""역까지 도보 시간 — 직선거리가 아니라 장애물 우회를 반영한다.

직선거리에 고정 보정(×1.35)만 곱하면, 사이에 고속도로·철도·하천이 있어도
그대로 짧게 나온다. 실제 사례: 용인 벽산타운1단지 → 동천역은 직선 225m라
5분으로 계산됐지만, 경부고속도로가 가로막아 네이버 도보는 10분이 넘는다.

계산 순서:
  1. 단지→역 직선이 지상 장애물(고속·간선도로 / 지상철도 / 하천)과 교차하는지
     본다. 터널 구간은 지상 보행을 막지 않으므로 장애물에서 제외한다.
  2. 교차하지 않으면 기존대로 직선 × 1.35.
  3. 교차하면 그 주변 보행로가 장애물을 가로지르는 지점(육교·지하도·건널목)을
     찾아 단지→횡단지점→역 경로 길이를 쓰고, 횡단 1회당 진입·계단·신호 대기로
     BARRIER_PENALTY_MIN 을 더한다.

장애물(data/barriers.json)과 횡단 지점(data/crossings.json) 모두 권역 단위로
1회만 수집한다. 단지마다 Overpass 를 부르면 수백 회에서 차단당하므로
(실측: 두 번째 호출부터 504) 조회는 전부 로컬 기하 계산으로 끝낸다.
"""

import json
import math
from pathlib import Path

WALK_M_PER_MIN = 67.0        # 성인 보통 걸음
ROUTE_FACTOR = 1.35          # 직선 → 실제 길 굴곡 보정
BARRIER_PENALTY_MIN = 3.0    # 횡단 1회당 육교·지하도 진입, 계단, 신호 대기
MAX_DETOUR_RATIO = 2.2       # 우회가 직선의 이 배를 넘으면 횡단 데이터가 빈 것으로 본다
STATION_RAIL_M = 250         # 역은 선로 위에 있다 — 역 근처 철도 교차는 장애물이 아니다

BARRIER_HW = {"motorway", "trunk", "primary", "motorway_link", "trunk_link"}
WALK_HW = {"footway", "path", "pedestrian", "steps", "residential", "service",
           "secondary", "tertiary", "unclassified", "living_street", "cycleway", "track"}


def meters(a, b):
    dy = (b[0] - a[0]) * 111_320.0
    dx = (b[1] - a[1]) * 111_320.0 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def _side(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_cross(p1, p2, p3, p4):
    d1, d2 = _side(p3, p4, p1), _side(p3, p4, p2)
    d3, d4 = _side(p1, p2, p3), _side(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def intersection(p1, p2, p3, p4):
    x1, y1, x2, y2 = p1[1], p1[0], p2[1], p2[0]
    x3, y3, x4, y4 = p3[1], p3[0], p4[1], p4[0]
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-14:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (y1 + t * (y2 - y1), x1 + t * (x2 - x1))
    return None


class WalkRouter:
    """단지→역 도보 시간. 조회 없이 로컬 기하 계산만 한다."""

    def __init__(self, barriers_path: Path, crossings_path: Path):
        self.barriers = self._load(barriers_path, tagged=True)
        self.crossings = self._load(crossings_path)
        # 횡단 지점은 점 단위로 펼쳐 격자에 담아 근접 검색을 빠르게 한다
        self.grid = {}
        for g in self.crossings:
            for p in g:
                self.grid.setdefault((round(p[0], 2), round(p[1], 2)), []).append(p)

    @staticmethod
    def _load(path: Path, tagged=False):
        """tagged=True 면 [종류, 좌표열] 형식으로 읽는다."""
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if tagged:
            return [(row[0], [tuple(p) for p in row[1]]) for row in raw
                    if isinstance(row, list) and len(row) == 2 and len(row[1]) >= 2]
        return [[tuple(p) for p in g] for g in raw]

    # ── 1단계: 장애물 교차 여부 ────────────────────────────────
    def _blocking(self, a, b):
        """직선을 가로막는 장애물 — 교차점을 모아 60m 이내는 한 도로로 합친다.

        고속도로는 상·하행이 별개 way 로 그려져 있어 way 수를 세면 한 도로가
        둘로 잡힌다. 페널티가 두 배가 되므로 교차점 기준으로 묶는다.
        """
        lo_lat, hi_lat = min(a[0], b[0]), max(a[0], b[0])
        lo_lon, hi_lon = min(a[1], b[1]), max(a[1], b[1])
        pad = 0.002
        pts = []
        for kind, g in self.barriers:
            if all(p[0] < lo_lat - pad or p[0] > hi_lat + pad or
                   p[1] < lo_lon - pad or p[1] > hi_lon + pad for p in g):
                continue
            for i in range(len(g) - 1):
                if segments_cross(a, b, g[i], g[i + 1]):
                    p = intersection(a, b, g[i], g[i + 1])
                    if p and not (kind == "rail" and meters(p, b) < STATION_RAIL_M):
                        pts.append(p)      # 역 앞 선로는 건너는 게 아니라 역에 닿는 것
                    break
        groups = []
        for p in sorted(pts, key=lambda q: meters(a, q)):
            if not groups or meters(groups[-1], p) > 60:
                groups.append(p)
        return len(groups), groups

    # ── 3단계: 횡단 지점 탐색 (로컬 격자) ──────────────────────
    def _nearest_crossing(self, a, b, bar_pts):
        """장애물 교차 지점 근처(200m)의 보행 교량·터널 중 우회가 가장 짧은 곳."""
        best, best_len = None, None
        for cell in {(round(p[0], 2) + dy, round(p[1], 2) + dx)
                     for p in bar_pts for dy in (-0.01, 0, 0.01) for dx in (-0.01, 0, 0.01)}:
            for p in self.grid.get((round(cell[0], 2), round(cell[1], 2)), ()):
                if min(meters(p, bp) for bp in bar_pts) > 200:
                    continue          # 그 장애물을 건너는 지점이 아니다
                total = meters(a, p) + meters(p, b)
                if best_len is None or total < best_len:
                    best, best_len = p, total
        return best, best_len

    # ── 공개 API ─────────────────────────────────────────────
    def walk(self, a, b):
        """(도보 분, 경로 m, 우회 여부) — a=단지, b=역."""
        straight = meters(a, b)
        if not self.barriers:
            return round(straight * ROUTE_FACTOR / WALK_M_PER_MIN), round(straight), False
        n_bar, bar_pts = self._blocking(a, b)
        if not n_bar:
            return round(straight * ROUTE_FACTOR / WALK_M_PER_MIN), round(straight), False

        cross, routed = self._nearest_crossing(a, b, bar_pts)
        # 횡단 지점이 없거나, 있어도 우회가 비현실적으로 길면(주변 육교·지하도가
        # OSM 에 안 그려진 경우) 직선 기준으로 되돌리고 페널티만 적용한다.
        if cross is None or routed > straight * MAX_DETOUR_RATIO:
            routed = straight
        minutes = routed * ROUTE_FACTOR / WALK_M_PER_MIN + BARRIER_PENALTY_MIN * n_bar
        return round(minutes), round(routed), True
