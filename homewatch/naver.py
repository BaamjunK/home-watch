"""네이버 부동산 m.land 무키 API — 지역 트리 / 단지 목록(세대수) / 단지 좌표.

검증된 엔드포인트 (2026-08, auction-watch에서 이어받음):
    GET m.land.naver.com/map/getRegionList?cortarNo={코드}
        → 하위 지역 목록 (CortarNo/CortarNm/MapXCrdn/MapYCrdn)
    GET m.land.naver.com/cluster/ajax/complexList?cortarNo={법정동}&rletTpCd=APT|JGC&page=N
        → 단지 목록 (hscpNo, totHsehCnt, useAprvYmd, dealCnt/rentCnt, 호가범위)
    GET m.land.naver.com/complex/ajax/complexListByCortarNo?cortarNo={법정동}
        → 단지 좌표 (hscpNo, lat, lng)

주의: cluster/clusterList·cluster/ajax/articleList 는 서버가 null 을 반환하도록
차단됨(2026-08 확인). 매물 목록은 articles.py 의 Playwright 경로를 쓴다.
new.land.naver.com /api/* 는 토큰 없이는 사용 불가.
"""

import json
import re
import time
from pathlib import Path

import requests

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
REGION_URL = "https://m.land.naver.com/map/getRegionList"
COMPLEX_LIST_URL = "https://m.land.naver.com/cluster/ajax/complexList"
COMPLEX_COORD_URL = "https://m.land.naver.com/complex/ajax/complexListByCortarNo"
ROOT_CORTAR = "0000000000"

PAGE_SIZE = 20
MAX_PAGES = 30


def _parse_price(s):
    """'15<em ...>억</em> 5,000' / '9억 8,000' / '25,000' → 원 단위 int."""
    if not s:
        return None
    text = re.sub(r"<[^>]+>", "", str(s)).replace(",", "").strip()
    m = re.match(r"(?:(\d+)억)?\s*(\d+)?", text)
    if not m or (not m.group(1) and not m.group(2)):
        return None
    won = int(m.group(1) or 0) * 100_000_000 + int(m.group(2) or 0) * 10_000
    return won or None


def _parse_use_date(s):
    """'1988.10.24.' → '1988-10-24'. 미상이면 None."""
    if not s:
        return None
    m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", str(s))
    if not m:
        return None
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class MetaCache:
    """단지 메타(목록/좌표/지역)는 자주 안 바뀌므로 일 단위 TTL 캐시."""

    def __init__(self, path: Path, ttl_days: float = 7):
        self.path = path
        self.ttl = ttl_days * 86400
        self.data = {}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def get(self, key, allow_stale=False):
        ent = self.data.get(key)
        if ent and (allow_stale or time.time() - ent.get("t", 0) < self.ttl):
            return ent["v"]
        return None

    def put(self, key, value):
        self.data[key] = {"t": time.time(), "v": value}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")


class NaverMeta:
    def __init__(self, cache_path: Path, interval_sec: float = 1.0, ttl_days: float = 7):
        self.cache = MetaCache(cache_path, ttl_days)
        self.interval = interval_sec
        self._last = 0.0
        self.sess = requests.Session()
        self.sess.headers.update({
            "User-Agent": UA,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://m.land.naver.com/",
            "X-Requested-With": "XMLHttpRequest",
        })

    def _throttle(self):
        wait = self.interval - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def _get_json(self, url, params):
        self._throttle()
        r = self.sess.get(url, params=params, timeout=20)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError as e:
            raise requests.RequestException(f"비JSON 응답 (차단 가능성): {r.text[:80]!r}") from e

    # ── 지역 트리 ────────────────────────────────────────────────────

    def region_children(self, code: str):
        key = f"region:{code}"
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        try:
            rows = ((self._get_json(REGION_URL, {"cortarNo": code}).get("result") or {})
                    .get("list")) or []
        except requests.RequestException:
            # m.land 차단 중이면 만료된 캐시라도 사용 (지역 트리는 사실상 불변)
            stale = self.cache.get(key, allow_stale=True)
            if stale is not None:
                return stale
            raise
        out = [{"name": c.get("CortarNm"), "code": c.get("CortarNo"),
                "lat": _to_float(c.get("MapYCrdn")), "lon": _to_float(c.get("MapXCrdn"))}
               for c in rows]
        if out:
            self.cache.put(key, out)
        return out

    def resolve_dongs(self, regions_cfg: dict):
        """config regions → [{sido, sigu, dong, code, lat, lon}] 법정동 목록.

        값이 ["*"] 이면 해당 시도의 전체 시군구를 순회한다.
        시군구 이름은 접두 일치(예: '안양시' → 만안구+동안구).
        """
        sido_map = {re.sub(r"(특별자치|특별|광역)?(시|도)$", "", (s["name"] or "").replace(" ", "")): s
                    for s in self.region_children(ROOT_CORTAR)}
        dongs = []
        for sido_name, sigu_wants in regions_cfg.items():
            sido_key = re.sub(r"(특별자치|특별|광역)?(시|도)$", "", sido_name.replace(" ", ""))
            sido = sido_map.get(sido_key)
            if not sido:
                raise ValueError(f"시도 해석 실패: {sido_name}")
            for sigu in self.region_children(sido["code"]):
                sname = (sigu["name"] or "").replace(" ", "")
                if "*" not in sigu_wants and not any(
                        sname.startswith(w.replace(" ", "")) or w.replace(" ", "") in sname
                        for w in sigu_wants):
                    continue
                for dong in self.region_children(sigu["code"]):
                    dongs.append({
                        "sido": sido["name"], "sigu": sigu["name"], "dong": dong["name"],
                        "code": dong["code"], "lat": dong["lat"], "lon": dong["lon"],
                    })
        return dongs

    # ── 단지 목록 (세대수·연식·매물수·호가) ─────────────────────────

    def list_complexes(self, bjd_code: str):
        key = f"cplx:{bjd_code}"
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        out, seen = [], set()
        for tp in ("APT", "JGC"):
            for page in range(1, MAX_PAGES + 1):
                rows = self._get_json(COMPLEX_LIST_URL, {
                    "cortarNo": bjd_code, "rletTpCd": tp, "page": page,
                }).get("result") or []
                for c in rows:
                    no = str(c.get("hscpNo") or "")
                    if not no or no in seen:
                        continue
                    seen.add(no)
                    out.append({
                        "complex_no": no,
                        "name": c.get("hscpNm"),
                        "type": c.get("hscpTypeNm"),
                        "is_jgc": tp == "JGC",
                        "households": c.get("totHsehCnt") or 0,
                        "dong_count": c.get("totDongCnt") or 0,
                        "use_date": _parse_use_date(c.get("useAprvYmd")),
                        "deal_cnt": c.get("dealCnt") or 0,
                        "rent_cnt": c.get("rentCnt") or 0,
                        "deal_min": _parse_price(c.get("dealPrcMin")),
                        "deal_max": _parse_price(c.get("dealPrcMax")),
                        "area_min": _to_float(c.get("minSpc")),
                        "area_max": _to_float(c.get("maxSpc")),
                    })
                if len(rows) < PAGE_SIZE:
                    break
        self.cache.put(key, out)  # 단지 없는 동도 정상 — 빈 목록 캐시
        return out

    # ── 단지 좌표 ────────────────────────────────────────────────────

    def complex_coords(self, bjd_code: str):
        """{hscpNo: (lat, lng)} — 동 단위 1회 요청."""
        key = f"coord:{bjd_code}"
        hit = self.cache.get(key)
        if hit is not None:
            return {k: tuple(v) for k, v in hit.items()}
        rows = self._get_json(COMPLEX_COORD_URL, {"cortarNo": bjd_code}).get("result") or []
        out = {}
        for c in rows:
            lat, lng = _to_float(c.get("lat")), _to_float(c.get("lng"))
            if c.get("hscpNo") and lat and lng:
                out[str(c["hscpNo"])] = (lat, lng)
        self.cache.put(key, out)
        return out
