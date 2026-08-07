"""단지 주변 실측 POI — 학군(학원·학교)과 인프라(백화점·마트·병원·공원).

시군구 단위 편집 점수 대신 **단지 좌표 반경** 안에 실제로 무엇이 있는지 센다.

출처:
  - fin.land `education/map/educationClusters` (categories: ES/MS/HS/AC)
    학원(AC)·초/중/고 위치. 단지 반경 1km bbox 1회 요청.
  - fin.land `data-service/map/facilityClusters`
    (DEPARTMENT/MART/HOSPITAL/PHARMACY/CONVENIENCE). 같은 bbox 1회 요청.
  - fin.land `education/school?schoolCode=` 배정 중학교 상세
    (학급당 학생수 + 시/구 평균 → 과밀도 = 학군 선호 신호)
  - OSM Overpass `leisure=park` (네이버에 공원 카테고리가 없어 별도 수집, data/parks.json)

특목고 진학률 원본(학교알리미)은 SPA·세션 구조라 대량 수집이 불가능해,
학원 밀집도 + 배정 중학교 과밀도 + 명문고 근접으로 대체한다.
"""

import json
import math
from pathlib import Path

EDU_URL = "/front-api/v1/education/map/educationClusters"
FACILITY_URL = "/front-api/v1/data-service/map/facilityClusters"
SCHOOL_URL = "/front-api/v1/education/school"

EDU_CATS = ["ES", "MS", "HS", "AC"]
FAC_CATS = ["DEPARTMENT", "MART", "HOSPITAL", "PHARMACY", "CONVENIENCE"]
RADIUS_M = 1000.0

# 이름으로 판별되는 특목고 + 서울·경기 주요 자사고(이름에 유형이 안 드러남)
ELITE_PATTERNS = ("외국어고", "과학고", "국제고", "영재")
ELITE_NAMES = (
    "휘문", "중동", "현대", "세화", "배재", "이대부", "중앙대학교사범대학부속",
    "선덕", "양정", "한대부", "경희", "대광", "보인", "장훈", "신일", "하나",
    "안산동산", "용인한국외국어대학교부설",
)


def _bbox(lat, lon, radius_m=RADIUS_M):
    dlat = radius_m / 111_320.0
    dlon = radius_m / (111_320.0 * math.cos(math.radians(lat)))
    return {"left": lon - dlon, "right": lon + dlon,
            "top": lat + dlat, "bottom": lat - dlat}


def _dist_m(lat1, lon1, lat2, lon2):
    dy = (lat2 - lat1) * 111_320.0
    dx = (lon2 - lon1) * 111_320.0 * math.cos(math.radians(lat1))
    return math.hypot(dx, dy)


def _flatten(clusters):
    for c in clusters or []:
        for it in c.get("items") or []:
            coord = it.get("coordinates") or {}
            if coord.get("yCoordinate") and coord.get("xCoordinate"):
                yield {"name": it.get("name"), "cat": it.get("category"),
                       "code": it.get("id"),
                       "lat": coord["yCoordinate"], "lon": coord["xCoordinate"]}


def is_elite_high(name):
    n = (name or "").replace(" ", "")
    return (any(p in n for p in ELITE_PATTERNS)
            or any(n.startswith(e) for e in ELITE_NAMES))


def load_parks(path: Path):
    """OSM 공원 [(lat, lon, area_m2)] — 없으면 빈 목록."""
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


class PoiCollector:
    """FinLandClient 의 브라우저 세션을 빌려 단지별 POI 를 센다.

    결과는 단지 단위이므로 30일 캐시(detail_cache 재사용).
    """

    def __init__(self, fin, parks_path: Path):
        self.fin = fin
        self.parks = load_parks(parks_path)

    def _post(self, url, body):
        from .finland import FETCH_JS
        self.fin._throttle()
        r = self.fin._page.evaluate(FETCH_JS, {"url": url, "body": body})
        if r["status"] != 200:
            raise RuntimeError(f"{url.split('/')[-1]} {r['status']}")
        d = json.loads(r["text"])
        if not d.get("isSuccess"):
            raise RuntimeError(f"{url.split('/')[-1]} 실패")
        return d.get("result") or []

    def _middle_school_crowding(self, code):
        """배정 중학교 과밀도 = 학급당 학생수 ÷ 시 평균. 없으면 None."""
        key = f"school:{code}"
        hit = self.fin.detail_cache.get(key)
        if hit is not None:
            return hit
        try:
            res = self._post_get(f"{SCHOOL_URL}?schoolCode={code}")
        except Exception:
            return None
        st = (res or {}).get("student") or {}
        city = (res or {}).get("cityStudent") or {}
        val = None
        if st.get("countPerClassroom") and city.get("countPerClassroom"):
            val = round(st["countPerClassroom"] / city["countPerClassroom"], 2)
        self.fin.detail_cache.put(key, val)
        return val

    def _post_get(self, url):
        from .finland import FETCH_JS
        self.fin._throttle()
        r = self.fin._page.evaluate(FETCH_JS, {"url": url, "body": None})
        if r["status"] != 200:
            raise RuntimeError(f"GET {r['status']}")
        return json.loads(r["text"]).get("result")

    def collect(self, complex_no, lat, lon):
        """단지 1곳의 학군·인프라 원자료. 30일 캐시."""
        key = f"poi2:{complex_no}"
        hit = self.fin.detail_cache.get(key)
        if hit is not None:
            return hit

        bbox = _bbox(lat, lon)
        edu = list(_flatten(self._post(EDU_URL, {"boundingBox": bbox, "categories": EDU_CATS})))
        fac = list(_flatten(self._post(FACILITY_URL, {"boundingBox": bbox, "categories": FAC_CATS})))

        def within(items, cat, r):
            return [it for it in items
                    if it["cat"] == cat and _dist_m(lat, lon, it["lat"], it["lon"]) <= r]

        academies = within(edu, "AC", 1000)
        academies_500 = within(edu, "AC", 500)
        elems = within(edu, "ES", 1000)
        middles = within(edu, "MS", 1500)
        highs = within(edu, "HS", 2000)
        elite = [h for h in highs if is_elite_high(h["name"])]

        # 가장 가까운 중학교의 과밀도 (배정 중학교 근사)
        crowding = None
        if middles:
            near = min(middles, key=lambda m: _dist_m(lat, lon, m["lat"], m["lon"]))
            if near.get("code"):
                crowding = self._middle_school_crowding(near["code"])

        def nearest_m(items):
            return round(min((_dist_m(lat, lon, i["lat"], i["lon"]) for i in items), default=99999))

        # 공원: 반경 1km 안 면적 합(㎡)과 최근접 거리
        park_area, park_near = 0, 99999
        for pk in self.parks:
            d = _dist_m(lat, lon, pk[0], pk[1])
            if d <= 1000:
                park_area += pk[2]
                park_near = min(park_near, round(d))

        out = {
            "academy_1km": len(academies),
            "academy_500m": len(academies_500),
            "elem_near_m": nearest_m(elems) if elems else None,
            "middle_crowding": crowding,
            "elite_high": [h["name"] for h in elite][:3],
            "dept_near_m": nearest_m(within(fac, "DEPARTMENT", 3000)) if within(fac, "DEPARTMENT", 3000) else None,
            "mart_1km": len(within(fac, "MART", 1000)),
            "mart_near_m": nearest_m(within(fac, "MART", 3000)) if within(fac, "MART", 3000) else None,
            "hospital_1km": len(within(fac, "HOSPITAL", 1000)),
            "pharmacy_1km": len(within(fac, "PHARMACY", 1000)),
            "conv_500m": len(within(fac, "CONVENIENCE", 500)),
            "park_area_ha": round(park_area / 10000, 1),
            "park_near_m": park_near if park_near < 99999 else None,
        }
        self.fin.detail_cache.put(key, out)
        return out
