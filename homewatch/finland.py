"""fin.land front-api — 법정동 단위 매물/단지 조회 (Playwright + 로컬 Chrome).

curl/requests 는 front-api 가 TOO_MANY_REQUESTS/403 을 반환하고, 헤드리스도
navigator.webdriver 감지 시 404 로 튕긴다. 동작 조건(2026-08 검증):
  - channel="chrome" + --disable-blink-features=AutomationControlled
  - fin.land 페이지 1회 로드 후 같은 컨텍스트에서 same-origin fetch

엔드포인트 (모두 POST, size 상한 30, lastInfo+seed 페이지네이션):
  /front-api/v1/article/legalDivisionArticleList  — 법정동 매물 목록
  /front-api/v1/complex/legalDivisionComplexList  — 법정동 단지 목록(세대수·좌표·연식)

서버측 필터(filter 객체, 가격은 원 단위):
  tradeTypes ["A1"|"B2"], realEstateTypes ["A01" 아파트, "A04" 재건축],
  dealPrice/warrantyPrice/rentPrice {min,max}, space {min,max}(+filtersExclusiveSpace
  true 면 전용면적 기준), householdNumber {min,max}
잘못된 필드명은 조용히 무시되므로(400 아님) 필드명 오타 주의.
"""

import json
import random
import time
from pathlib import Path

ARTICLE_URL = "/front-api/v1/article/legalDivisionArticleList"
COMPLEX_URL = "/front-api/v1/complex/legalDivisionComplexList"
DETAIL_URL = "/front-api/v1/complex"   # GET ?complexNumber= — 임대세대·주차·용적률 등
HOME_URL = "https://fin.land.naver.com/home"
PAGE_SIZE = 30
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

FETCH_JS = """async (payload) => {
    const opt = payload.body
        ? {method: 'POST',
           headers: {'Content-Type': 'application/json',
                     'Accept': 'application/json, text/plain, */*'},
           body: JSON.stringify(payload.body)}
        : {headers: {'Accept': 'application/json, text/plain, */*'}};
    const res = await fetch(payload.url, opt);
    return {status: res.status, text: await res.text()};
}"""


def base_filter(dong_code, trade_types, real_estate_types=("A01", "A04")):
    return {
        "tradeTypes": list(trade_types),
        "realEstateTypes": list(real_estate_types),
        "roomCount": [], "bathRoomCount": [], "optionTypes": [],
        "oneRoomShapeTypes": [], "moveInTypes": [], "filtersExclusiveSpace": False,
        "floorTypes": [], "directionTypes": [], "hasArticlePhoto": False,
        "isAuthorizedByOwner": False, "parkingTypes": [], "entranceTypes": [],
        "hasArticle": False,
        "legalDivisionNumbers": [dong_code], "legalDivisionType": "EUP",
    }


def _parse_article(item):
    a = item.get("representativeArticleInfo") or {}
    space = a.get("spaceInfo") or {}
    detail = a.get("articleDetail") or {}
    price = a.get("priceInfo") or {}
    verify = a.get("verificationInfo") or {}
    broker = a.get("brokerInfo") or {}
    addr = a.get("address") or {}
    coord = addr.get("coordinates") or {}
    bld = a.get("buildingInfo") or {}
    return {
        "article_no": a.get("articleNumber"),
        "complex_no": str(a.get("complexNumber") or ""),
        "complex_name": a.get("complexName"),
        "bld_dong": a.get("dongName"),
        "trade_type": a.get("tradeType"),          # A1 매매 / B2 월세
        "real_estate_type": a.get("realEstateType"),
        "deal_price": price.get("dealPrice") or 0,           # 원
        "warranty_price": price.get("warrantyPrice") or 0,   # 보증금, 원
        "rent_price": price.get("rentPrice") or 0,           # 월세, 원
        "mgmt_fee": price.get("managementFeeAmount") or 0,
        "exclusive_m2": space.get("exclusiveSpace"),
        "supply_m2": space.get("supplySpace"),
        "floor_info": detail.get("floorInfo"),
        "direction": detail.get("direction"),
        "description": detail.get("articleFeatureDescription") or "",
        "confirm_date": verify.get("articleConfirmDate"),
        "verification": verify.get("verificationType"),
        "realtor": broker.get("brokerageName"),
        "lat": coord.get("yCoordinate"),
        "lng": coord.get("xCoordinate"),
        "approval_date_raw": bld.get("buildingConjunctionDate"),
    }


def _parse_complex(item):
    cwrap = item.get("complex") or {}
    c = cwrap.get("complexInfo") or {}
    price = cwrap.get("articlePriceInfoDto") or {}
    coord = (c.get("address") or {}).get("coordinates") or {}
    use = c.get("useApprovalDate")  # '19880513'
    use_fmt = f"{use[:4]}-{use[4:6]}-{use[6:8]}" if use and len(use) == 8 else None
    return {
        "complex_no": str(c.get("complexNumber") or ""),
        "name": c.get("name"),
        "type": c.get("type"),                     # A01 아파트 / A04 재건축
        "households": c.get("totalHouseholdNumber") or 0,
        "building_count": c.get("buildingCount") or 0,
        "use_date": use_fmt,
        "lat": coord.get("yCoordinate"),
        "lng": coord.get("xCoordinate"),
        "deal_min": price.get("dealMinPrice") or 0,   # 단지 매매 호가 최저 (원)
        "deal_max": price.get("dealMaxPrice") or 0,
    }


class TTLCache:
    def __init__(self, path: Path, ttl_hours: float):
        self.path = path
        self.ttl = ttl_hours * 3600
        self.data = {}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def get(self, key):
        ent = self.data.get(key)
        if ent and time.time() - ent.get("t", 0) < self.ttl:
            return ent["v"]
        return None

    def put(self, key, value):
        self.data[key] = {"t": time.time(), "v": value}

    def save(self):
        now = time.time()
        self.data = {k: v for k, v in self.data.items() if now - v.get("t", 0) < self.ttl}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")


class FinLandClient:
    """법정동 단위 매물·단지 조회. with 문으로 사용 (브라우저 1세션)."""

    def __init__(self, cache_path: Path, interval_sec: float = 0.6,
                 ttl_hours: float = 20, max_pages: int = 40, headless: bool = True):
        self.cache = TTLCache(cache_path, ttl_hours)
        # 단지 상세(임대세대·주차·용적률)는 거의 안 바뀌므로 30일 캐시
        self.detail_cache = TTLCache(cache_path.parent / "finland_detail.json", 24 * 30)
        self.interval = interval_sec
        self.max_pages = max_pages
        self.headless = headless
        self._pw = self._browser = self._page = None
        self._last = 0.0

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._open_browser()
        return self

    def __exit__(self, *exc):
        self.cache.save()
        self.detail_cache.save()
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    def _open_browser(self):
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
        self._browser = self._pw.chromium.launch(
            channel="chrome", headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"])
        ctx = self._browser.new_context(
            user_agent=UA, viewport={"width": 390, "height": 844},
            is_mobile=True, locale="ko-KR")
        self._page = ctx.new_page()
        self._page.goto(HOME_URL, wait_until="domcontentloaded", timeout=45000)
        self._page.wait_for_timeout(2000)
        if "fin.land" not in self._page.url:
            raise RuntimeError(f"fin.land 홈 로드 실패(봇 감지 가능성): {self._page.url}")

    def _throttle(self):
        wait = self.interval + random.uniform(0, 0.3) - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def _call(self, url, body, _retried=False):
        self._throttle()
        try:
            r = self._page.evaluate(FETCH_JS, {"url": url, "body": body})
        except Exception:
            if _retried:
                raise
            self._open_browser()
            return self._call(url, body, _retried=True)
        if r["status"] != 200:
            if not _retried:
                time.sleep(5)
                self._open_browser()
                return self._call(url, body, _retried=True)
            raise RuntimeError(f"front-api {r['status']}: {r['text'][:120]}")
        d = json.loads(r["text"])
        if not d.get("isSuccess"):
            raise RuntimeError(f"front-api 실패: {r['text'][:120]}")
        return d["result"]

    def _paged(self, url, body, paging_key, parse, cache_key):
        hit = self.cache.get(cache_key)
        if hit is not None:
            return hit
        out, seen = [], set()
        truncated = False
        for page_no in range(self.max_pages):
            res = self._call(url, body)
            for item in res.get("list") or []:
                row = parse(item)
                key = row.get("article_no") or row.get("complex_no")
                if key and key not in seen:
                    seen.add(key)
                    out.append(row)
            if not res.get("hasNextPage"):
                break
            body[paging_key]["lastInfo"] = res.get("lastInfo") or []
            if res.get("seed"):
                body[paging_key]["seed"] = res["seed"]
        else:
            truncated = True
        self.cache.put(cache_key, out)
        if truncated:
            print(f"   ! {cache_key}: {self.max_pages}페이지 상한 도달 — 일부 누락 가능", flush=True)
        return out

    def articles(self, dong_code: str, trade_type: str, extra_filter: dict):
        """법정동 매물 목록 (서버측 필터 적용)."""
        f = base_filter(dong_code, [trade_type])
        f.update(extra_filter)
        body = {"filter": f,
                "articlePagingRequest": {"size": PAGE_SIZE, "userChannelType": "MOBILE",
                                         "articleSortType": "RANKING_DESC", "lastInfo": []}}
        return self._paged(ARTICLE_URL, body, "articlePagingRequest",
                           _parse_article, f"art:{dong_code}:{trade_type}")

    def complexes(self, dong_code: str, min_households: int = 0):
        """법정동 단지 목록 (세대수·좌표·연식) — 매물 있는 단지만."""
        f = base_filter(dong_code, ["A1", "B2"])
        f["hasArticle"] = True
        if min_households:
            f["householdNumber"] = {"min": min_households}
        body = {"filter": f,
                "complexPagingRequest": {"size": PAGE_SIZE, "userChannelType": "MOBILE",
                                         "complexSortType": "POPULARITY_DESC", "lastInfo": []}}
        rows = self._paged(COMPLEX_URL, body, "complexPagingRequest",
                           _parse_complex, f"cplx2:{dong_code}")
        return {c["complex_no"]: c for c in rows}

    def complex_detail(self, complex_no: str):
        """단지 기본정보 — 임대세대수·세대당주차·용적률·건설사·지위양도제한."""
        key = f"detail:{complex_no}"
        hit = self.detail_cache.get(key)
        if hit is not None:
            return hit
        self._throttle()
        r = self._page.evaluate(FETCH_JS, {"url": f"{DETAIL_URL}?complexNumber={complex_no}",
                                           "body": None})
        if r["status"] != 200:
            raise RuntimeError(f"complex detail {r['status']}")
        d = json.loads(r["text"])
        if not d.get("isSuccess"):
            raise RuntimeError(f"complex detail 실패: {r['text'][:100]}")
        res = d["result"]
        ratio = res.get("buildingRatioInfo") or {}
        parking = res.get("parkingInfo") or {}
        out = {
            "lease_households": res.get("leaseHouseholdNumber") or 0,
            "parking_per_hh": parking.get("parkingCountPerHousehold"),
            "floor_area_ratio": ratio.get("floorAreaRatio"),
            "coverage_ratio": ratio.get("buildingCoverageRatio"),
            "construction_company": res.get("constructionCompany"),
            "highest_floor": res.get("highestDongFloor"),
            "jgc_transfer_restricted":
                bool(res.get("isRestrictedTransferOfReconstructionAssociationMembership")),
        }
        self.detail_cache.put(key, out)
        return out
