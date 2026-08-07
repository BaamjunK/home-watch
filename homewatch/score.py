"""매물 평점 — 가격 가치 중심 가중치.

항목(기본 가중치, config.score_weights 로 조정):
  value    35  같은 (시군구, 거래유형, 면적밴드) 안에서 평(3.3㎡)당 가격이 싼 정도
  transit  20  판교·강남·여의도·시청 4대 업무지구 종합 접근성(직선거리 근사)
  school   10  시군구/동 단위 학군 평판 (정적 테이블)
  infra    10  상업·생활 인프라 (정적 테이블)
  scale_age 15 단지 세대수 + 연식(신축/재건축 잠재 반영)
  slope    10  단지 주변 경사도 (SRTM 고도 기반, 평지일수록 높음)

학군/인프라는 공개 지표를 단순화한 편집 점수다(0~10).
근거: 학군 — 특목·자사고 진학률과 학원가(대치·목동·중계·평촌·분당) 통념,
인프라 — 백화점/대형몰/종합병원 밀집도. 필요하면 표만 고치면 된다.
"""

import math
import re
from statistics import median

PYEONG = 3.3058
RENT_CONVERT_RATE = 0.055  # 전월세 전환율 — 월세→보증금 환산에 사용

# ── 정적 테이블 (시군구 이름 부분일치, 위가 우선) ────────────────────
SCHOOL_BY_SIGU = [
    ("강남구", 10), ("서초구", 9.5), ("양천구", 9.5), ("성남시 분당구", 9.5),
    ("송파구", 8.5), ("노원구", 8.5), ("안양시 동안구", 8.5), ("과천시", 8.5),
    ("광진구", 7.5), ("강동구", 7), ("마포구", 7), ("동작구", 7), ("영등포구", 6.5),
    ("용산구", 6.5), ("성동구", 6.5), ("서대문구", 6), ("동대문구", 6), ("성북구", 6),
    ("하남시", 6), ("의왕시", 6), ("강서구", 6), ("은평구", 5.5), ("중구", 5.5),
    ("종로구", 5.5), ("구로구", 5), ("관악구", 5), ("광명시", 5), ("도봉구", 5),
    ("강북구", 4.5), ("중랑구", 4.5), ("금천구", 4.5), ("안양시 만안구", 5.5),
]
# 동 단위 가점 (대표 학원가/학군지)
SCHOOL_DONG_BONUS = {
    "대치동": 0.5, "목동": 0.5, "중계동": 1.0, "잠실동": 0.5, "반포동": 0.5,
    "평촌동": 1.0, "수내동": 0.5, "서현동": 0.5, "정자동": 0.5,
}
INFRA_BY_SIGU = [
    ("강남구", 10), ("서초구", 9), ("송파구", 9), ("영등포구", 8.5), ("중구", 8.5),
    ("용산구", 8), ("성동구", 8), ("마포구", 8), ("성남시 분당구", 8.5), ("종로구", 8),
    ("광진구", 7.5), ("양천구", 7.5), ("동작구", 7), ("강동구", 7), ("하남시", 7.5),
    ("과천시", 7), ("안양시 동안구", 7.5), ("서대문구", 6.5), ("동대문구", 6.5),
    ("강서구", 6.5), ("노원구", 6.5), ("성북구", 6), ("구로구", 6), ("관악구", 6),
    ("은평구", 5.5), ("중랑구", 5), ("도봉구", 5), ("강북구", 5), ("금천구", 5.5),
    ("안양시 만안구", 6), ("의왕시", 5.5), ("광명시", 6),
]


def _table_lookup(table, sigu, default=5.5):
    for name, score in table:
        if name in sigu or sigu in name:
            return score
    return default


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def transit_score(lat, lon, hubs, station_walk_min=None):
    """업무지구 접근성 70% + 역세권 30%.

    업무지구: 4대 허브 평균, 3km 이내 10점 → 25km 0점 선형 감쇠.
    역세권: 최기역 도보 5분 이하 10점 → 25분 0점 선형 감쇠.
    """
    if not lat or not lon:
        return 5.0
    scores = []
    for _name, (hlat, hlon) in hubs.items():
        d = haversine_km(lat, lon, hlat, hlon)
        scores.append(max(0.0, min(10.0, 10.0 * (25.0 - d) / 22.0)))
    hub = sum(scores) / len(scores)
    if station_walk_min is None:
        return round(hub, 1)
    st = max(0.0, min(10.0, 10.0 * (25.0 - station_walk_min) / 20.0))
    return round(hub * 0.7 + st * 0.3, 1)


def school_score(sigu, dong):
    base = _table_lookup(SCHOOL_BY_SIGU, sigu or "")
    return round(min(10.0, base + SCHOOL_DONG_BONUS.get(dong or "", 0)), 1)


def infra_score(sigu):
    return _table_lookup(INFRA_BY_SIGU, sigu or "")


def scale_age_score(households, use_date, is_jgc):
    """세대수 60% + 연식 40%. 재건축(JGC)은 노후 감점 대신 잠재 가점."""
    if households >= 3000:
        h = 10
    elif households >= 1500:
        h = 9
    elif households >= 1000:
        h = 8
    elif households >= 700:
        h = 7
    elif households >= 500:
        h = 6
    else:
        h = 5
    year = None
    m = re.match(r"(\d{4})", use_date or "")
    if m:
        year = int(m.group(1))
    if year is None:
        a = 5
    else:
        import datetime
        age = datetime.date.today().year - year
        if age <= 5:
            a = 10
        elif age <= 10:
            a = 9
        elif age <= 15:
            a = 8
        elif age <= 25:
            a = 6
        elif age <= 35:
            a = 4
        else:
            a = 5 if is_jgc else 3   # 재건축 추진 노후 단지는 잠재가치 반영
    if is_jgc:
        a = min(10, a + 1)
    return round(h * 0.6 + a * 0.4, 1)


def slope_score(grade_pct):
    """구배% → 점수. 2% 미만 평지, 5% 이상이면 체감되는 언덕."""
    if grade_pct is None:
        return None
    if grade_pct < 1.5:
        return 10.0
    if grade_pct < 3.0:
        return 8.0
    if grade_pct < 5.0:
        return 6.0
    if grade_pct < 8.0:
        return 3.0
    return 1.0


def slope_label(grade_pct):
    if grade_pct is None:
        return "미상"
    if grade_pct < 1.5:
        return "평지"
    if grade_pct < 3.0:
        return "완만"
    if grade_pct < 5.0:
        return "약한 언덕"
    if grade_pct < 8.0:
        return "언덕"
    return "급경사"


def effective_price(article):
    """가치 비교용 환산가(원). 매매=매매가, 월세=보증금+월세 환산."""
    if article["trade_type"] == "A1":
        return article["deal_price"]
    return article["warranty_price"] + article["rent_price"] * 12 / RENT_CONVERT_RATE


def _area_band(m2):
    return "s" if m2 < 85 else "l"


def value_scores(articles):
    """{article_no: 0~10} — 같은 (시군구, 거래유형, 면적밴드) 중위 평당가 대비.

    중위가보다 30% 싸면 10점, 30% 비싸면 0점 선형. 표본 5건 미만이면
    시도 전체 그룹으로 폴백.
    """
    def ppp(a):  # 평당 환산가
        return effective_price(a) / (a["exclusive_m2"] / PYEONG)

    groups, fallback = {}, {}
    for a in articles:
        if not a.get("exclusive_m2"):
            continue
        groups.setdefault((a["sigu"], a["trade_type"], _area_band(a["exclusive_m2"])), []).append(ppp(a))
        fallback.setdefault((a["sido"], a["trade_type"], _area_band(a["exclusive_m2"])), []).append(ppp(a))

    out = {}
    for a in articles:
        if not a.get("exclusive_m2"):
            out[a["article_no"]] = 5.0
            continue
        g = groups.get((a["sigu"], a["trade_type"], _area_band(a["exclusive_m2"])), [])
        if len(g) < 5:
            g = fallback.get((a["sido"], a["trade_type"], _area_band(a["exclusive_m2"])), g)
        med = median(g) if g else None
        if not med:
            out[a["article_no"]] = 5.0
            continue
        ratio = ppp(a) / med          # 1.0 = 중위가
        score = 5.0 + (1.0 - ratio) / 0.30 * 5.0
        out[a["article_no"]] = round(max(0.0, min(10.0, score)), 1)
    return out


def grade_label(total):
    if total >= 8.5:
        return "S"
    if total >= 7.5:
        return "A"
    if total >= 6.5:
        return "B"
    if total >= 5.5:
        return "C"
    return "D"


def score_articles(articles, weights, hubs):
    """각 매물에 scores{}, score_total, grade 를 채운다 (in-place)."""
    wsum = sum(weights.values())
    vals = value_scores(articles)
    for a in articles:
        s = {
            "value": vals.get(a["article_no"], 5.0),
            "transit": transit_score(a.get("lat"), a.get("lng"), hubs,
                                     a.get("station_walk_min")),
            "school": school_score(a.get("sigu"), a.get("dong")),
            "infra": infra_score(a.get("sigu")),
            "scale_age": scale_age_score(a.get("households") or 0, a.get("use_date"), a.get("is_jgc")),
            "slope": slope_score(a.get("grade_pct")),
        }
        total = 0.0
        for k, w in weights.items():
            v = s.get(k)
            if v is None:          # 경사도 미상이면 해당 가중치 제외하고 정규화
                continue
            total += v * w
        eff_w = sum(w for k, w in weights.items() if s.get(k) is not None)
        a["scores"] = s
        a["score_total"] = round(total / eff_w, 2) if eff_w else 0.0
        a["grade"] = grade_label(a["score_total"])
    return articles
