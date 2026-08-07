"""단지 경사도(언덕 여부) — 위성 DEM 2종 교차 검증.

단지 중심 5×5 그리드(60m 간격)의 고도에 최소제곱 평면을 피팅해 구배(%)를
계산하되, 서로 다른 시기·방식의 DEM 두 개에서 각각 구한 뒤 **최솟값**을 쓴다:

  - SRTM 30m (opentopodata): 2000년 2월 측정 — 이후 조성된 단지는 공사 전
    구릉이 찍혀 있어 과대 (인덕원센트럴푸르지오 7.2% vs 실제 평탄 사례).
  - Copernicus GLO-90 (open-meteo): 2011~2015 측정 TanDEM-X 기반 DSM —
    고층 건물 높이가 강하게 반영돼 과대 (은마 3.6% vs SRTM 1.7% 사례).

두 소스의 오류가 모두 "과대" 방향이므로 min 이 실지형에 가장 가깝고,
진짜 언덕은 양쪽 다 높게 나와 그대로 잡힌다(정릉풍림아이원 8.5/15.5%).
지형은 불변이므로 캐시는 영구.

API 제한: opentopodata 100지점/요청·1rps·일1000회, open-meteo 100지점/요청.
"""

import json
import math
import time
from pathlib import Path

import requests

SRTM_API = "https://api.opentopodata.org/v1/srtm30m"
GLO_API = "https://api.open-meteo.com/v1/elevation"
GRID_N = 5           # 5×5 그리드
STEP_M = 60.0        # 그리드 간격
POINTS_PER_CPLX = GRID_N * GRID_N
BATCH = 100          # 요청당 최대 지점 수 (양쪽 공통)
CACHE_VER = "v3"     # min(SRTM, GLO-90) 방식 — 구버전 캐시 무효화


def _grid(lat, lon):
    dlat = STEP_M / 111_320.0
    dlon = STEP_M / (111_320.0 * math.cos(math.radians(lat)))
    half = GRID_N // 2
    return [(lat + i * dlat, lon + j * dlon)
            for i in range(-half, half + 1) for j in range(-half, half + 1)]


def _plane_slope(elevs):
    """5×5 고도 → 최소제곱 평면 z = a·x + b·y + c 의 구배 % 와 중심 고도."""
    half = GRID_N // 2
    sxz = syz = sxx = 0.0
    for idx, z in enumerate(elevs):
        i, j = divmod(idx, GRID_N)
        y = (i - half) * STEP_M
        x = (j - half) * STEP_M
        sxz += x * z
        syz += y * z
        sxx += x * x   # Σx² == Σy² (대칭 그리드)
    a, b = sxz / sxx, syz / sxx
    grade = math.hypot(a, b) * 100.0
    center = elevs[len(elevs) // 2]
    return round(grade, 1), center


class ElevationClient:
    def __init__(self, cache_path: Path, interval_sec: float = 1.1):
        self.path = cache_path
        self.interval = interval_sec
        self._last = 0.0
        self._glo_last = 0.0
        self._glo_interval = 10.0   # 분당 지점 쿼터 회피 (100지점 × 6회/분)
        self._glo_fail_streak = 0
        self.cache = {}
        if cache_path.exists():
            try:
                self.cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    def _throttle(self):
        wait = self.interval - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def _query_srtm(self, points):
        self._throttle()
        locs = "|".join(f"{la:.6f},{lo:.6f}" for la, lo in points)
        try:
            r = requests.get(SRTM_API, params={"locations": locs}, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data.get("status") != "OK":
                return [None] * len(points)
            return [row.get("elevation") for row in data["results"]]
        except requests.RequestException:
            return [None] * len(points)

    def _query_glo(self, points):
        """open-meteo 는 지점 수 기준 분당 쿼터가 있어 배치 간 10초 간격 + 429 시
        1회만 재시도한다. 연속 실패가 쌓이면 이번 실행에서는 포기(서킷브레이커)
        — 누락분은 다음 실행의 재시도 pass 가 채운다."""
        if self._glo_fail_streak >= 5:
            return [None] * len(points)
        las = ",".join(f"{la:.6f}" for la, _lo in points)
        los = ",".join(f"{lo:.6f}" for _la, lo in points)
        for backoff in (0, 10):
            if backoff:
                time.sleep(backoff)
            wait = self._glo_interval - (time.time() - self._glo_last)
            if wait > 0:
                time.sleep(wait)
            self._glo_last = time.time()
            try:
                r = requests.get(GLO_API, params={"latitude": las, "longitude": los},
                                 timeout=30)
                r.raise_for_status()
                elev = r.json().get("elevation")
                if elev:
                    self._glo_fail_streak = 0
                    return elev
            except requests.RequestException:
                continue
        self._glo_fail_streak += 1
        if self._glo_fail_streak == 5:
            print("   ! GLO-90 연속 실패 — 이번 실행에서는 SRTM 단독으로 진행"
                  " (누락분은 다음 실행에서 자동 보충)", flush=True)
        return [None] * len(points)

    def slopes(self, complexes):
        """{complex_no: (lat, lng)} → {complex_no: {"grade_pct", "elevation", ...}}.

        소스별 구배를 따로 캐시하고, 한쪽 소스가 실패했던 단지는 다음 호출에서
        그 소스만 다시 채운다. grade_pct = min(성공한 소스들).
        """
        def ck(no):
            return f"{CACHE_VER}:{no}"

        def run_batch(chunk, need_srtm, need_glo):
            points = []
            for _no, (lat, lon) in chunk:
                points.extend(_grid(lat, lon))
            srtm = self._query_srtm(points) if need_srtm else [None] * len(points)
            glo = self._query_glo(points) if need_glo else [None] * len(points)
            for j, (no, _ll) in enumerate(chunk):
                ent = self.cache.get(ck(no), {})
                s = srtm[j * POINTS_PER_CPLX:(j + 1) * POINTS_PER_CPLX]
                g = glo[j * POINTS_PER_CPLX:(j + 1) * POINTS_PER_CPLX]
                if need_srtm and not any(v is None for v in s):
                    ent["grade_srtm"], ent["elevation"] = _plane_slope(s)
                if need_glo and not any(v is None for v in g):
                    gr, c2 = _plane_slope(g)
                    ent["grade_glo"] = gr
                    ent.setdefault("elevation", c2)
                grades = [ent[k] for k in ("grade_srtm", "grade_glo") if ent.get(k) is not None]
                if not grades:
                    continue  # 전부 실패 — 캐시하지 않고 다음 실행에서 재시도
                ent["grade_pct"] = min(grades)
                ent["sources"] = len(grades)
                self.cache[ck(no)] = ent
            self._save()

        per_batch = BATCH // POINTS_PER_CPLX  # 4단지씩
        # 1) SRTM 미확보 단지 — SRTM 먼저 (빠르고 안정적)
        todo = [(no, ll) for no, ll in complexes.items()
                if self.cache.get(ck(no), {}).get("grade_srtm") is None]
        for i in range(0, len(todo), per_batch):
            run_batch(todo[i:i + per_batch], need_srtm=True, need_glo=False)
        # 2) GLO-90 은 SRTM 이 평지가 아니라고 한 단지만 — min 이 평지 판정을
        #    더 낮춰봐야 라벨이 안 바뀌므로, 교차검증이 의미 있는 곳만 조회
        need_glo = [(no, ll) for no, ll in complexes.items()
                    if (ent := self.cache.get(ck(no))) is not None
                    and ent.get("grade_glo") is None
                    and (ent.get("grade_srtm") or 0) >= 1.5]
        if need_glo:
            print(f"   GLO-90 교차검증 대상: {len(need_glo)}곳", flush=True)
        for i in range(0, len(need_glo), per_batch):
            run_batch(need_glo[i:i + per_batch], need_srtm=False, need_glo=True)
        return {no: self.cache[ck(no)] for no in complexes if ck(no) in self.cache}
