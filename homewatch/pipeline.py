"""수집 → 필터 → 평점 → 대시보드 생성 파이프라인.

실행:  python3 -m homewatch.pipeline [--skip-articles]
  --skip-articles: 매물 재수집 없이 캐시(data/listings.json)로 평점/대시보드만 재생성

수집은 fin.land front-api 단일 채널(finland.py, 브라우저 1세션):
법정동별 매물 목록(서버측 필터) + 단지 목록(세대수·연식) + 단지 상세(임대세대 등).
법정동 코드는 m.land 지역 트리(naver.py)에서 얻되 차단 시 캐시로 폴백.
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

from . import naver, score, webgen
from .finland import FinLandClient
from .elevation import ElevationClient

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 매매 매물의 "전세끼고 매매(세안고)" 신호 — 설명 키워드
GAP_KEYWORDS = ["세안고", "전세안고", "전세끼", "전세낀", "세끼고", "월세안고", "월세끼",
                "갭투자", "갭 투자", "세입자", "임차인", "전세만기", "월세만기", "보증금안고",
                "전세승계", "월세승계", "임대차승계"]


def load_config():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def is_sharehouse(desc, keywords):
    """설명에 쉐어/룸임대/단기 신호가 있으면 True. 공백 제거본에도 매칭."""
    d = (desc or "").lower()
    compact = d.replace(" ", "").replace(".", "").replace(",", "")
    return any(k.lower() in d or k.lower() in compact for k in keywords)


def is_gap_sale(desc):
    d = (desc or "").replace(" ", "")
    return any(k.replace(" ", "") in d for k in GAP_KEYWORDS)


def collect(cfg):
    crawler = cfg["crawler"]
    rent_cfg, deal_cfg = cfg["rent"], cfg["deal"]

    print("1) 법정동 목록 해석 …", flush=True)
    meta = naver.NaverMeta(DATA / "cache" / "naver_meta.json",
                           interval_sec=crawler["mland_interval_sec"],
                           ttl_days=crawler["meta_cache_days"])
    dongs = meta.resolve_dongs(cfg["regions"])
    print(f"   {len(dongs)}개 동", flush=True)

    rent_filter = {
        "warrantyPrice": {"min": 0, "max": rent_cfg["max_warranty_won"]},
        "rentPrice": {"min": 0, "max": rent_cfg["max_rent_won"]},
        "space": {"min": rent_cfg["min_exclusive_m2"]},
        "filtersExclusiveSpace": True,
        "householdNumber": {"min": rent_cfg["min_households"]},
    }
    deal_filter = {
        "dealPrice": {"min": deal_cfg["min_price_won"], "max": deal_cfg["max_price_won"]},
        "space": {"min": deal_cfg["min_exclusive_m2"]},
        "filtersExclusiveSpace": True,
        "householdNumber": {"min": deal_cfg["min_households"]},
    }

    print("2) 법정동별 매물 + 단지 메타 수집 (fin.land) …", flush=True)
    rows, cplx_meta = [], {}
    t0 = time.time()
    with FinLandClient(DATA / "cache" / "finland.json",
                       interval_sec=crawler["finland_interval_sec"],
                       ttl_hours=crawler["article_cache_hours"],
                       max_pages=crawler["max_article_pages"]) as fin:
        for i, d in enumerate(dongs, 1):
            dong_rows = []
            try:
                dong_rows += fin.articles(d["code"], "B2", rent_filter)
                dong_rows += fin.articles(d["code"], "A1", deal_filter)
            except Exception as e:
                print(f"   ! {d['sigu']} {d['dong']}: {e}", file=sys.stderr, flush=True)
                continue
            if dong_rows:
                try:
                    cplx_meta.update(fin.complexes(
                        d["code"], min_households=rent_cfg["min_households"]))
                except Exception as e:
                    print(f"   ! 단지메타 {d['sigu']} {d['dong']}: {e}", file=sys.stderr, flush=True)
                for a in dong_rows:
                    a.update({"sido": d["sido"], "sigu": d["sigu"], "dong": d["dong"]})
                    rows.append(a)
            if i % 25 == 0:
                el = time.time() - t0
                print(f"   … {i}/{len(dongs)} 동, 매물 {len(rows)}건"
                      f" (경과 {el/60:.0f}분, 남은 예상 {el/i*(len(dongs)-i)/60:.0f}분)", flush=True)
                fin.cache.save()
        print(f"   원시 매물 {len(rows)}건, 단지 메타 {len(cplx_meta)}곳", flush=True)

        # 단지 메타 결합 + 로컬 필터 (서버 필터 재확인 + 쉐어하우스 제외)
        out = []
        for a in rows:
            c = cplx_meta.get(a["complex_no"], {})
            a["households"] = c.get("households") or 0
            a["use_date"] = c.get("use_date") or (
                f"{a['approval_date_raw'][:4]}-{a['approval_date_raw'][4:6]}-{a['approval_date_raw'][6:8]}"
                if a.get("approval_date_raw") and len(a["approval_date_raw"]) == 8 else None)
            a["is_jgc"] = (a.get("real_estate_type") == "A04") or (c.get("type") == "A04")
            a["complex_deal_min"] = c.get("deal_min") or 0
            a["gap_sale"] = a["trade_type"] == "A1" and is_gap_sale(a["description"])
            if not a.get("lat"):
                a["lat"], a["lng"] = c.get("lat"), c.get("lng")

            m2 = a.get("exclusive_m2")
            if a["trade_type"] == "B2":
                if (not m2 or m2 < rent_cfg["min_exclusive_m2"]
                        or a["warranty_price"] > rent_cfg["max_warranty_won"]
                        or a["rent_price"] > rent_cfg["max_rent_won"] or a["rent_price"] <= 0
                        or (a["households"] and a["households"] < rent_cfg["min_households"])
                        or is_sharehouse(a["description"], rent_cfg["exclude_keywords"])):
                    continue
            else:
                if (not m2 or m2 < deal_cfg["min_exclusive_m2"]
                        or not (deal_cfg["min_price_won"] <= a["deal_price"] <= deal_cfg["max_price_won"])
                        or (a["households"] and a["households"] < deal_cfg["min_households"])):
                    continue
            out.append(a)

        dedup = group_same_units(out)
        dedup = drop_partial_rentals(dedup, rent_cfg.get("min_value_ratio", 0.25))
        print(f"   필터 통과 {len(out)}건 → 동일매물 그룹 {len(dedup)}건 (부분임대 제거 포함)", flush=True)

        # 3) 단지 상세 (임대세대·주차·용적률 — 최종 매물 단지만)
        uniq = sorted({a["complex_no"] for a in dedup if a["complex_no"]})
        print(f"3) 단지 상세 조회 ({len(uniq)}곳) …", flush=True)
        details = {}
        for j, cno in enumerate(uniq, 1):
            try:
                details[cno] = fin.complex_detail(cno)
            except Exception as e:
                print(f"   ! 상세 {cno}: {e}", file=sys.stderr, flush=True)
            if j % 100 == 0:
                print(f"   … {j}/{len(uniq)}", flush=True)
                fin.detail_cache.save()
        for a in dedup:
            det = details.get(a["complex_no"], {})
            a["lease_households"] = det.get("lease_households") or 0
            a["lease_ratio"] = (round(a["lease_households"] / a["households"] * 100)
                                if a["households"] and a["lease_households"] else 0)
            a["parking_per_hh"] = det.get("parking_per_hh")
            a["floor_area_ratio"] = det.get("floor_area_ratio")
            a["coverage_ratio"] = det.get("coverage_ratio")
            a["construction_company"] = det.get("construction_company")
            a["highest_floor"] = det.get("highest_floor")
            a["jgc_transfer_restricted"] = det.get("jgc_transfer_restricted", False)

    return dedup


def group_same_units(rows):
    """동일 매물로 보이는 것 묶기 — 같은 단지·유형·면적·가격(층 무관)은
    한 세대를 여러 중개사가 올린 것일 가능성이 높다. 대표 1건 + variants.

    대표 선정: 집주인 확인매물 > 확인일 최신 순.
    """
    def unit_key(a):
        return (a["complex_no"], a["trade_type"], round(a["exclusive_m2"] or 0),
                a["deal_price"], a["warranty_price"], a["rent_price"])

    groups = {}
    for a in rows:
        groups.setdefault(unit_key(a), []).append(a)

    out = []
    for _k, g in groups.items():
        g.sort(key=lambda a: (a.get("verification") != "OWNER",
                              a.get("confirm_date") or ""), reverse=False)
        # OWNER 우선, 그다음 확인일 최신
        g.sort(key=lambda a: ((0 if a.get("verification") == "OWNER" else 1),
                              -(int((a.get("confirm_date") or "0").replace("-", "") or 0))))
        rep = g[0]
        rep["dup_count"] = len(g) - 1
        rep["variants"] = [{
            "article_no": v["article_no"], "floor_info": v["floor_info"],
            "realtor": v["realtor"], "confirm_date": v["confirm_date"],
            "description": (v["description"] or "")[:80],
            "complex_no": v["complex_no"],
        } for v in g[1:]]
        out.append(rep)
    return out


def drop_partial_rentals(rows, min_ratio):
    """가격 정합성 가드 — 설명에 힌트가 없는 부분임대(세대분리형 원룸) 제거.

    84㎡ 아파트를 원룸 부분만 임대하는 매물은 설명이 없으면 키워드로 못 잡는다.
    1차: 월세 환산가(보증금+월세×12/전환율)가 같은 단지 매매 최저 호가의
         20% 미만이면 전체 세대 임대로 불가능한 가격 → 제외.
         단, 재건축(A04)·30년+ 구축은 개발기대로 전세가율 10~20%가 정상이라 면제.
    2차(단지 호가 없을 때): 같은 시군구 매매 중위 평당가 대비 min_ratio 미만 제외.
    (정상 월세의 환산가는 통상 매매가의 40~70% 수준)
    """
    import datetime
    from statistics import median
    from .score import effective_price, PYEONG
    this_year = datetime.date.today().year
    deal_ppp = {}
    for a in rows:
        if a["trade_type"] == "A1" and a.get("exclusive_m2"):
            deal_ppp.setdefault(a["sigu"], []).append(
                a["deal_price"] / (a["exclusive_m2"] / PYEONG))
    med = {k: median(v) for k, v in deal_ppp.items() if len(v) >= 10}

    def is_old_or_jgc(a):
        if a.get("is_jgc"):
            return True
        y = (a.get("use_date") or "")[:4]
        return y.isdigit() and this_year - int(y) >= 30

    kept = []
    for a in rows:
        if a["trade_type"] == "B2" and a.get("exclusive_m2"):
            eff = effective_price(a)
            if a.get("complex_deal_min") and not is_old_or_jgc(a):
                ratio = eff / a["complex_deal_min"]
                if ratio < 0.20:
                    print(f"   부분임대 의심 제외(단지최저가의 {ratio:.0%}): {a['sigu']}"
                          f" {a['complex_name']} {a['exclusive_m2']}㎡"
                          f" {a['warranty_price']/1e8:.1f}억/{a['rent_price']/1e4:.0f}만", flush=True)
                    continue
            elif a["sigu"] in med:
                ratio = (eff / (a["exclusive_m2"] / PYEONG)) / med[a["sigu"]]
                if ratio < min_ratio and not is_old_or_jgc(a):
                    print(f"   부분임대 의심 제외(시군구 중위의 {ratio:.0%}): {a['sigu']}"
                          f" {a['complex_name']} {a['exclusive_m2']}㎡"
                          f" {a['warranty_price']/1e8:.1f}억/{a['rent_price']/1e4:.0f}만", flush=True)
                    continue
        kept.append(a)
    return kept


def attach_stations(rows):
    """최기 지하철역 — data/subway_stations.json(OSM) 기준 직선거리 → 도보시간.

    도보시간 = 직선거리 × 1.35(경로 보정) ÷ 67m/분.
    """
    path = DATA / "subway_stations.json"
    if not path.exists():
        print("   ! subway_stations.json 없음 — 역세권 표기 생략", flush=True)
        return rows
    stations = json.loads(path.read_text(encoding="utf-8"))
    cache = {}
    for a in rows:
        if not (a.get("lat") and a.get("lng")):
            a["station_name"] = None
            continue
        key = a["complex_no"]
        if key not in cache:
            lat, lng = a["lat"], a["lng"]
            best, bd = None, 1e18
            coslat = math.cos(math.radians(lat))
            for s in stations:
                # 근사 평면거리(빠름) — 최근접 선별에는 충분
                dy = (s["lat"] - lat) * 111_320
                dx = (s["lon"] - lng) * 111_320 * coslat
                d2 = dx * dx + dy * dy
                if d2 < bd:
                    bd, best = d2, s
            dist = math.sqrt(bd)
            cache[key] = (best["name"], round(dist), round(dist * 1.35 / 67))
        a["station_name"], a["station_m"], a["station_walk_min"] = cache[key]
    return rows


def enrich_and_score(cfg, rows):
    print("4) 최기역 계산 …", flush=True)
    attach_stations(rows)

    print("5) 경사도(언덕) 계산 …", flush=True)
    elev = ElevationClient(DATA / "cache" / "elevation.json")
    cplx_coords = {a["complex_no"]: (a["lat"], a["lng"])
                   for a in rows if a.get("lat") and a.get("lng")}
    slopes = elev.slopes(cplx_coords)
    for a in rows:
        info = slopes.get(a["complex_no"])
        a["grade_pct"] = info["grade_pct"] if info else None
        a["slope_label"] = score.slope_label(a["grade_pct"])

    print("6) 평점 계산 …", flush=True)
    score.score_articles(rows, cfg["score_weights"], cfg["transit_hubs"])
    rows.sort(key=lambda a: -a["score_total"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-articles", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    listings_path = DATA / "listings.json"

    if args.skip_articles and listings_path.exists():
        rows = json.loads(listings_path.read_text(encoding="utf-8"))["listings"]
    else:
        rows = collect(cfg)

    rows = enrich_and_score(cfg, rows)

    listings_path.parent.mkdir(parents=True, exist_ok=True)
    listings_path.write_text(json.dumps(
        {"generated_at": time.strftime("%Y-%m-%d %H:%M"), "listings": rows},
        ensure_ascii=False), encoding="utf-8")

    print("7) 대시보드 생성 …", flush=True)
    out = ROOT / cfg["web"]["output_html"]
    webgen.render(rows, cfg, out)
    n_rent = sum(1 for a in rows if a["trade_type"] == "B2")
    print(f"완료: 월세 {n_rent}건 / 매매 {len(rows)-n_rent}건 → {out}")


if __name__ == "__main__":
    main()
