# home-watch — 아파트 매물 대시보드

네이버 부동산에서 조건에 맞는 아파트 월세/매매 매물을 수집해
평점(가격가치·교통·학군·인프라·규모연식·언덕)을 매기고
정적 HTML 대시보드([docs/index.html](docs/index.html))로 보여준다.

## 조건 (config.json)

| | 월세 | 매매 |
|---|---|---|
| 세대수 | 300+ | 500+ |
| 전용면적 | 59㎡+ | 59㎡+ |
| 가격 | 보증금 1억~4억, 월세 ≤150만 | 8억~14억 |
| 기타 | 쉐어하우스/방한칸/단기 제외 | 재건축(JGC) 포함 |

지역: 서울 전체 + 성남 분당구·수정구·중원구·용인 수지구(신분당선)·의왕·과천·안양 동안구·하남.

## 실행

```bash
./run.sh                 # 수집 → 평점 → 대시보드 → 브라우저 오픈
./run.sh --skip-articles # 재수집 없이 평점/대시보드만 재생성
```

전체 수집은 30분 안팎(537개 동 × 월세/매매). 매물·단지 메타는 20시간
캐시되므로 같은 날 재실행은 몇 분이면 끝난다.

## 데이터 경로와 제약

- **매물·단지 메타**: `fin.land.naver.com` front-api 단일 채널
  (`article/legalDivisionArticleList` + `complex/legalDivisionComplexList`,
  법정동 단위, 가격·면적·세대수 서버측 필터). curl/requests는 403이고
  `navigator.webdriver` 감지 시 404로 튕기므로, **로컬 Google Chrome**을
  Playwright(`channel="chrome"` + `--disable-blink-features=AutomationControlled`)로
  구동해 페이지 컨텍스트 안에서 호출한다. Chrome 필수. 상세는 `finland.py` docstring.
- **법정동 코드**: `m.land.naver.com/map/getRegionList` — 대량 요청 시 m.land가
  IP를 소프트 차단하지만(302), 지역 트리는 캐시 폴백으로 흡수된다.
  m.land `cluster/complexList` 대량 크롤은 차단을 부르므로 하지 말 것
  (첫 구축 때 537개 동 크롤 중 차단당해 fin.land 채널로 전환한 이력).
- **경사도**: opentopodata SRTM 30m 공개 API (단지당 5지점, 영구 캐시).
- 요청 간격을 지키자(fin.land 0.6s). 줄이면 차단 위험.
- `m.land cluster/clusterList`·`cluster/ajax/articleList` 는 2026-08 현재
  서버가 null 을 반환한다 — 다시 시도하지 말 것.

## 평점

가격 가치 중심 가중치 (config `score_weights`, 합 100):
value 35 / transit 20 / scale_age 15 / school 10 / infra 10 / slope 10.

- **가격가치**: 같은 (시군구·거래유형·면적밴드) 중위 평당가 대비 할인율.
  월세는 `보증금 + 월세×12/5.5%` 로 환산해 비교.
- **교통**: 판교·강남·여의도·시청 4대 업무지구 직선거리 평균 (3km 만점, 25km 0점).
- **학군/인프라**: `score.py`의 정적 테이블(시군구 단위 편집 점수) — 표만 고치면 반영.
- **언덕**: 단지 주변 120m 최대 구배. <1.5% 평지 10점, 8%+ 급경사 1점.

## 설치

```bash
pip3 install --user -r requirements.txt
```

Playwright는 별도 브라우저 다운로드 없이 설치된 Google Chrome을 그대로 쓴다.
