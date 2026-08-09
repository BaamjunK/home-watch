"""정적 대시보드 생성 — 데이터 임베드 단일 HTML (docs/index.html).

평점 가중치는 기본값만 서버(config)에서 넣고, 대시보드에서 사용자가 조정하면
클라이언트에서 즉시 재계산·재정렬한다(localStorage 유지). 항목별 점수(0~10)는
매물마다 임베드돼 있으므로 재수집 없이 가중치만 바꿔볼 수 있다.
"""

import json
from pathlib import Path

TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --bg:#f6f7f9; --card:#fff; --ink:#1c2330; --sub:#68707f; --line:#e4e7ec;
  --accent:#2563eb; --accent-soft:#eff4ff; --warn:#d97706; --warn-soft:#fef3e2;
  --good:#059669;
  --s:#7c3aed; --a:#2563eb; --b:#059669; --c:#d97706; --d:#9ca3af;
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#12151c; --card:#1a1f29; --ink:#e8ebf1; --sub:#98a1b3; --line:#2a3140;
          --accent:#5b8def; --accent-soft:#1e2a44; --warn:#f59e0b; --warn-soft:#3a2c14;
          --good:#34d399; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.55 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard",sans-serif; }
.wrap { max-width:1240px; margin:0 auto; padding:20px 16px 60px; }
h1 { font-size:20px; margin:0 0 2px; }
.meta { color:var(--sub); font-size:12px; margin-bottom:14px; }
.tabs { display:flex; gap:8px; margin:14px 0; align-items:center; }
.tab { flex:0 0 auto; padding:8px 22px; border-radius:10px; border:1px solid var(--line);
  background:var(--card); cursor:pointer; font-weight:600; font-size:14px; color:var(--sub); }
.tab.on { background:var(--accent); border-color:var(--accent); color:#fff; }
.wbtn { margin-left:auto; padding:8px 14px; border-radius:10px; border:1px solid var(--line);
  background:var(--card); cursor:pointer; font-size:13px; color:var(--ink); }
.wpanel { display:none; padding:12px; background:var(--card); border:1px solid var(--line);
  border-radius:12px; margin-bottom:12px; }
.wpanel.open { display:block; }
.wgrid { display:flex; flex-wrap:wrap; gap:10px 18px; align-items:flex-end; }
.wf { display:flex; flex-direction:column; gap:3px; }
.wf label { font-size:11px; color:var(--sub); }
.wf input { width:70px; padding:6px 8px; border:1px solid var(--line); border-radius:8px;
  background:var(--bg); color:var(--ink); font-size:13px; }
.wnote { font-size:12px; color:var(--sub); margin-top:8px; }
.wreset { padding:6px 12px; border-radius:8px; border:1px solid var(--accent);
  background:transparent; color:var(--accent); cursor:pointer; font-size:12px; font-weight:600; }
.filters { display:flex; flex-wrap:wrap; gap:10px; padding:12px; background:var(--card);
  border:1px solid var(--line); border-radius:12px; margin-bottom:12px; align-items:flex-end; }
.f { display:flex; flex-direction:column; gap:3px; position:relative; }
.f label { font-size:11px; color:var(--sub); }
.f input, .f select, .f .msbtn { padding:6px 8px; border:1px solid var(--line); border-radius:8px;
  background:var(--bg); color:var(--ink); font-size:13px; min-width:90px; text-align:left; cursor:pointer; }
.f input[type=number] { width:100px; }
.chk { flex-direction:row; align-items:center; gap:6px; padding-bottom:6px; }
.mspanel { display:none; position:absolute; top:100%; left:0; z-index:30; margin-top:4px;
  background:var(--card); border:1px solid var(--line); border-radius:10px; padding:8px 10px;
  max-height:280px; overflow:auto; box-shadow:0 8px 24px rgba(0,0,0,.15); min-width:180px; }
.mspanel.open { display:block; }
.mspanel label { display:flex; gap:6px; align-items:center; font-size:13px; color:var(--ink);
  padding:3px 0; cursor:pointer; white-space:nowrap; }
.msall { border-bottom:1px solid var(--line); margin-bottom:4px; padding-bottom:6px !important; }
.count { margin:10px 2px; color:var(--sub); font-size:13px; }
table { width:100%; border-collapse:collapse; background:var(--card);
  border:1px solid var(--line); border-radius:12px; overflow:hidden; }
thead th { text-align:left; font-size:11px; color:var(--sub); font-weight:600;
  padding:10px 8px; border-bottom:1px solid var(--line); white-space:nowrap;
  cursor:pointer; user-select:none; position:sticky; top:0; background:var(--card); z-index:5; }
thead th .arrow { opacity:.6; font-size:10px; }
tbody td { padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:middle; }
tbody tr.row { cursor:pointer; }
tbody tr.row:hover { background:var(--accent-soft); }
.cname { font-weight:600; }
.sub { color:var(--sub); font-size:12px; }
.price { font-weight:700; white-space:nowrap; }
.rp { font-size:11px; font-weight:400; color:var(--sub); white-space:nowrap; }
.rp .down { color:var(--good); font-weight:600; }
.rp .up { color:var(--warn); font-weight:600; }
.badge { display:inline-block; min-width:26px; text-align:center; padding:3px 8px;
  border-radius:8px; color:#fff; font-weight:700; font-size:13px; }
.badge.S{background:var(--s);} .badge.A{background:var(--a);}
.badge.B{background:var(--b);} .badge.C{background:var(--c);} .badge.D{background:var(--d);}
.tag { display:inline-block; padding:1px 7px; border-radius:6px; font-size:11px; font-weight:600;
  margin-left:4px; vertical-align:1px; }
.tag.lease { background:var(--warn-soft); color:var(--warn); }
.tag.good { background:rgba(5,150,105,.12); color:var(--good); }
.tag.gap { background:var(--accent-soft); color:var(--accent); }
.tag.jgc { background:var(--line); color:var(--sub); }
.tag.dup { background:var(--line); color:var(--sub); }
.slope-flat{color:var(--b);} .slope-hill{color:var(--c);} .slope-steep{color:#dc2626;}
tr.detail td { background:var(--bg); padding:14px 16px; }
.bars { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:8px 20px; margin:6px 0 12px; }
.bar { font-size:12px; }
.bar .t { display:flex; justify-content:space-between; color:var(--sub); }
.bar .g { height:6px; background:var(--line); border-radius:3px; overflow:hidden; margin-top:3px; }
.bar .g i { display:block; height:100%; background:var(--accent); border-radius:3px; }
.hbtn { border:1px solid var(--line); background:var(--card); color:var(--sub); cursor:pointer;
  width:15px; height:15px; line-height:1; border-radius:50%; font-size:10px; padding:0;
  vertical-align:1px; font-weight:700; }
.hbtn:hover { border-color:var(--accent); color:var(--accent); }
.help { display:none; margin-top:6px; padding:8px 10px; background:var(--card);
  border:1px solid var(--line); border-radius:8px; font-size:11.5px; line-height:1.6; color:var(--sub); }
.help.open { display:block; }
.help b { color:var(--ink); }
.help .hw { color:var(--warn); }
.facts { display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:6px 18px;
  margin:10px 0; padding:10px 12px; background:var(--card); border:1px solid var(--line); border-radius:10px; }
.fact { font-size:12px; }
.fact b { display:block; font-size:13px; }
.fact .k { color:var(--sub); }
.fact.warn b { color:var(--warn); }
.fact.good b { color:var(--good); }
.desc { font-size:13px; margin:8px 0; }
.links a { display:inline-block; margin:6px 8px 0 0; padding:7px 14px; border-radius:8px;
  background:var(--accent); color:#fff; text-decoration:none; font-size:13px; font-weight:600; }
.links a.ghost { background:transparent; border:1px solid var(--accent); color:var(--accent); }
.vars { margin-top:10px; border-top:1px dashed var(--line); padding-top:8px; }
.vars .v { font-size:12px; color:var(--sub); padding:3px 0; }
.vars .v a { color:var(--accent); }
.empty { text-align:center; padding:50px 0; color:var(--sub); }
@media (max-width:760px){ .hide-m{display:none;} .wrap{padding:12px 8px 40px;} }
</style>
</head>
<body>
<div class="wrap">
  <h1>__TITLE__</h1>
  <div class="meta">생성: __GENERATED__ · 데이터: 네이버 부동산 (동일매물 묶음·실거래 포함) · 교통=업무지구 70%+역세권 30%</div>
  <div class="tabs">
    <button class="tab on" data-trade="B2" onclick="setTrade('B2')">월세 <span id="cntB2"></span></button>
    <button class="tab" data-trade="A1" onclick="setTrade('A1')">매매 <span id="cntA1"></span></button>
    <button class="wbtn" onclick="document.getElementById('wpanel').classList.toggle('open')">⚖️ 가중치 조정 <span id="wsum"></span></button>
    <button class="wbtn" style="margin-left:8px" onclick="document.getElementById('mpanel').classList.toggle('open')">📐 산정 방식</button>
  </div>
  <div class="wpanel" id="mpanel">
    <div style="font-size:13px; line-height:1.7">
      <b>평점 = Σ(항목점수 0~10 × 가중치) ÷ Σ가중치</b> · 미상 항목은 제외 후 정규화 · 등급 S≥8.5 / A≥7.5 / B≥6.5 / C≥5.5 / D<br><br>
      <b>가격가치</b> — 같은 (시군구·거래유형·면적밴드 59~85/85㎡+) 매물들의 <b>중위 평당가 대비 할인율</b>.
        월세는 보증금+월세×12÷5.5%(전월세전환율)로 환산. 중위가보다 30% 싸면 10점, 같으면 5점, 30% 비싸면 0점. 표본 5건 미만이면 시·도 전체로 폴백.<br>
      <b>교통</b> — ① 업무지구 70%: 판교·강남·여의도·시청 직선거리, 각 3km 이내 10점→25km 0점 선형, 4곳 평균
        ② 역세권 30%: 최기역 도보 5분 이하 10점→25분 0점. 역 좌표는 OSM 수도권 508개 역, 도보시간=직선거리×1.35÷67m/분.
        <span style="color:var(--warn)">실제 대중교통 소요시간이 아닌 거리 근사.</span><br>
      <b>학군</b> — <b>단지 좌표 반경 실측</b>: 학원 밀집 35%(1km 내 학원 수, 500m 학원가 가점) + 배정 중학교 과밀도 25%(학급당 학생수÷시 평균 — 학군 선호 지역은 전입 수요로 과밀) + 초품아 25%(초등학교 거리, 200m 이내 만점) + 명문·특목고 근접 15%(2km 내 외고·과학고·국제고·주요 자사고).
        <span style="color:var(--warn)">특목고 진학률 원본(학교알리미)은 대량 수집이 불가능해, 진학 성과와 상관이 높은 학원 밀집도·중학교 과밀도로 대체한 추정치입니다.</span><br>
      <b>인프라</b> — <b>단지 좌표 반경 실측</b>(각 20%): 백화점 거리 · 대형마트 1km 개수/거리 · 병원 1km 개수 · 생활편의(편의점 500m + 약국 1km) · 공원 거리(OSM). POI 수집 실패 단지만 시군구 폴백 점수.<br>
      <b>규모·연식</b> — 세대수 60%(300세대 5점~3,000세대+ 10점) + 연식 40%(≤5년 10점→35년+ 3점, 재건축 +1 보정).<br>
      <b>언덕</b> — 단지 중심 5×5 그리드(240m) 고도 평면 피팅 구배%. 위성 DEM 2종(SRTM 2000 / Copernicus 2011~15)의 최솟값 — 옛 지형·건물반영 과대오류 상쇄. &lt;1.5% 평지 10점 ~ 8%+ 급경사 1점.<br><br>
      <b>기타 표기</b> — 실거래: 네이버 공개 실거래(신고 기준, 반영 지연 있음), 같은 평형(전용면적 최근접 매칭) 최근 3건.
      실거래 대비(동일층): 호가를 <b>같은 층 구분</b>(저층 1~3층 / 일반층 4층~)의 최근 실거래 평균과 비교 — 직전 1건은 그 거래가 저층·급매면 왜곡되므로 쓰지 않음. 전세가율·갭: 단지 전세 호가 범위 기준(실거래 아님). 저층 할인율: 1~3층 매물의 호가를 같은 평형 <b>일반층(4층~) 실거래 평균</b>과 비교 — 저층은 채광·소음 탓에 통상 10% 이상 싸므로 그에 못 미치면 '할인부족'으로 표시. 세안고: 매물 설명 키워드 감지. 임대세대: 단지 등록 정보.
      부분임대(세대분리 원룸) 매물은 키워드+가격 정합성 검사로 자동 제외.
    </div>
  </div>
  <div class="wpanel" id="wpanel">
    <div class="wgrid" id="wgrid"></div>
    <div class="wnote">항목별 점수(0~10)에 가중치를 곱해 평점을 냅니다. 비율만 의미 있으므로 합이 100이 아니어도 됩니다.
      변경 즉시 재계산·재정렬되고 이 브라우저에 저장됩니다. <button class="wreset" onclick="resetWeights()">기본값 복원</button></div>
  </div>
  <div class="filters">
    <div class="f"><label>지역(시군구) — 다중 선택</label>
      <button class="msbtn" id="msBtn" onclick="toggleMs(event)">전체</button>
      <div class="mspanel" id="msPanel"></div>
    </div>
    <div class="f" id="fRentBox"><label>월세 최대(만원)</label><input type="number" id="fRent" placeholder="100"></div>
    <div class="f" id="fWarBox"><label>보증금 최대(억)</label><input type="number" id="fWar" step="0.5" placeholder="3"></div>
    <div class="f" id="fDealMinBox" style="display:none"><label>매매가 최소(억)</label><input type="number" id="fDealMin" step="0.5" placeholder="8"></div>
    <div class="f" id="fDealBox" style="display:none"><label>매매가 최대(억)</label><input type="number" id="fDeal" step="0.5" placeholder="13"></div>
    <div class="f"><label>전용면적 최소(㎡)</label><input type="number" id="fArea" placeholder="59"></div>
    <div class="f"><label>세대수 최소</label><input type="number" id="fHh" placeholder="300"></div>
    <div class="f"><label>역도보 최대(분)</label><input type="number" id="fWalk" value="15" placeholder="∞"></div>
    <div class="f"><label>용적률 최대(%)</label><input type="number" id="fFar" step="10" value="350" placeholder="∞"></div>
    <div class="f"><label>재건축</label>
      <select id="fJgc">
        <option value="">전체</option>
        <option value="only">재건축만</option>
        <option value="excl">재건축 제외</option>
      </select>
    </div>
    <div class="f"><label>경사(언덕)</label>
      <select id="fSlope">
        <option value="">전체</option>
        <option value="1.5">평지만 (&lt;1.5%)</option>
        <option value="3">완만까지 (&lt;3%)</option>
        <option value="5">약한 언덕까지 (&lt;5%)</option>
        <option value="8">언덕까지 (&lt;8%)</option>
      </select>
    </div>
    <div class="f"><label>21년 월거래 최소</label><input type="number" id="fVol" step="0.1" value="1" placeholder="0"></div>
    <div class="f"><label>평점 최소</label><input type="number" id="fScore" step="0.5" placeholder="0"></div>
    <div class="f chk"><input type="checkbox" id="fNoLease"><label for="fNoLease" style="font-size:13px;color:var(--ink)">임대혼합 제외</label></div>
    <div class="f chk"><input type="checkbox" id="fLowOk"><label for="fLowOk" style="font-size:13px;color:var(--ink)">저층 할인부족 제외</label></div>
    <div class="f chk" id="fNoGapBox" style="display:none"><input type="checkbox" id="fNoGap"><label for="fNoGap" style="font-size:13px;color:var(--ink)">세안고 제외</label></div>
  </div>
  <div class="count" id="count"></div>
  <div class="count" id="defnote" style="margin-top:-6px">기본 필터 적용 중: 용적률 ≤350% · 21년 월거래 ≥1건 · 역도보 ≤15분
    <button class="wreset" style="margin-left:8px" onclick="clearDefaults()">기본 필터 해제</button></div>
  <table>
    <thead><tr>
      <th data-k="score_total">평점 <span class="arrow"></span></th>
      <th data-k="complex_name">단지 <span class="arrow"></span></th>
      <th data-k="_price">호가 <span class="arrow"></span></th>
      <th data-k="real_gap_pct" class="hide-m">실거래 대비(동일층) <span class="arrow"></span></th>
      <th data-k="_vol21" class="hide-m">21년 거래 <span class="arrow"></span></th>
      <th data-k="exclusive_m2">전용 <span class="arrow"></span></th>
      <th data-k="_ppp" class="hide-m">평당(환산) <span class="arrow"></span></th>
      <th data-k="households" class="hide-m">세대 <span class="arrow"></span></th>
      <th data-k="use_date" class="hide-m">연식 <span class="arrow"></span></th>
      <th data-k="station_walk_min">역 <span class="arrow"></span></th>
      <th data-k="grade_pct">경사 <span class="arrow"></span></th>
    </tr></thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="empty" id="empty" style="display:none">조건에 맞는 매물이 없습니다.</div>
</div>
<script>
const DATA = __DATA__;
const DEFAULT_WEIGHTS = __WEIGHTS_JSON__;
const SCORE_LABELS = {value:"가격가치", transit:"교통", school:"학군", infra:"인프라", scale_age:"규모·연식", slope:"언덕"};
// 항목별 산정 방식 — 점수 바의 ? 아이콘에 붙는다
const SCORE_HELP = {
  value: "같은 시군구·거래유형·면적밴드(59~85 / 85㎡+) 매물들의 <b>중위 평당가 대비 할인율</b>. 월세는 보증금+월세×12÷5.5%(전월세전환율)로 환산해 비교합니다. 중위가보다 30% 싸면 10점, 같으면 5점, 30% 비싸면 0점. 표본 5건 미만이면 시·도 전체로 폴백.",
  transit: "<b>업무지구 70%</b>: 판교·강남·여의도·시청까지 직선거리, 각 3km 이내 10점 → 25km 0점 선형, 4곳 평균.<br><b>역세권 30%</b>: 최기역 도보 5분 이하 10점 → 25분 0점. 역 좌표는 OSM 수도권 508개 역, 도보시간 = 직선거리×1.35(경로 보정) ÷ 67m/분.<br><span class='hw'>실제 대중교통 소요시간(환승·배차)이 아닌 거리 근사입니다.</span>",
  school: "<b>단지 반경 실측</b> — 학원 밀집 35%(1km 내 학원 수, 500m 학원가 가점) + 배정 중학교 과밀도 25%(학급당 학생수÷시 평균, 학군 선호지는 전입 수요로 과밀) + 초품아 25%(초등학교 거리, 200m 이내 만점) + 명문·특목고 근접 15%(2km 내 외고·과학고·국제고·주요 자사고).<br><span class='hw'>특목고 진학률 원본(학교알리미)은 대량 수집이 불가능해, 진학 성과와 상관이 높은 지표로 대체한 추정치입니다.</span>",
  infra: "<b>단지 반경 실측</b>(각 20%) — 백화점 거리 · 대형마트 1km 개수/거리 · 병원 1km 개수 · 생활편의(편의점 500m + 약국 1km) · 공원 거리(OSM 수도권 5,591곳).<br>POI 수집에 실패한 단지만 시군구 평균 점수로 폴백합니다.",
  scale_age: "세대수 60%(300세대 5점 → 3,000세대 이상 10점 구간별) + 연식 40%(5년 이하 10점 → 35년 이상 3점). 재건축 단지는 개발 잠재가치로 +1 보정.",
  slope: "단지 중심 5×5 그리드(240m 범위) 고도에 최소제곱 평면을 피팅한 구배%. 위성 DEM 2종(SRTM 2000년 / Copernicus 2011~15년)에서 각각 구한 뒤 <b>최솟값</b>을 씁니다 — 각각 옛 지형·건물 높이 반영이라는 과대측정 오류가 있어 min이 실지형에 가깝습니다.<br>1.5% 미만 평지 10점 · 3% 완만 8점 · 5% 약한 언덕 6점 · 8% 언덕 3점 · 그 이상 급경사 1점.",
};
const PY = 3.3058, RATE = 0.055;
let WEIGHTS = loadWeights();
let trade = "B2", sortKey = "score_total", sortAsc = false, openRow = null;
let selectedSigu = new Set();

DATA.forEach(a => {
  a._price = a.trade_type === "A1" ? a.deal_price : a.warranty_price;
  const eff = a.trade_type === "A1" ? a.deal_price : a.warranty_price + a.rent_price*12/RATE;
  a._ppp = a.exclusive_m2 ? eff / (a.exclusive_m2/PY) : 0;
  a._vol21 = a.vol_2021 ? a.vol_2021.per_month : null;
});

function loadWeights(){
  try {
    const s = JSON.parse(localStorage.getItem("hw_weights"));
    if (s && Object.keys(SCORE_LABELS).every(k => typeof s[k] === "number")) return s;
  } catch(e){}
  return {...DEFAULT_WEIGHTS};
}
function saveWeights(){ localStorage.setItem("hw_weights", JSON.stringify(WEIGHTS)); }
function resetWeights(){
  WEIGHTS = {...DEFAULT_WEIGHTS}; saveWeights(); buildWeightPanel(); recompute(); render(); }
function gradeOf(t){ return t>=8.5?"S":t>=7.5?"A":t>=6.5?"B":t>=5.5?"C":"D"; }
function recompute(){
  DATA.forEach(a => {
    let tot=0, eff=0;
    for (const k in WEIGHTS){
      const v = a.scores[k];
      if (v==null) continue;              // 경사 미상 등은 가중치 제외 후 정규화
      tot += v * WEIGHTS[k]; eff += WEIGHTS[k];
    }
    a.score_total = eff ? Math.round(tot/eff*100)/100 : 0;
    a.grade = gradeOf(a.score_total);
  });
  const sum = Object.values(WEIGHTS).reduce((x,y)=>x+y,0);
  document.getElementById("wsum").textContent = "(" +
    Object.keys(SCORE_LABELS).map(k=>WEIGHTS[k]).join("/") + ")";
}
function buildWeightPanel(){
  const g = document.getElementById("wgrid");
  g.innerHTML = "";
  for (const k in SCORE_LABELS){
    const d = document.createElement("div"); d.className = "wf";
    d.innerHTML = '<label>'+SCORE_LABELS[k]+'</label>';
    const inp = document.createElement("input");
    inp.type = "number"; inp.min = 0; inp.max = 100; inp.step = 5; inp.value = WEIGHTS[k];
    inp.addEventListener("input", () => {
      const v = parseFloat(inp.value);
      if (!isNaN(v) && v >= 0) { WEIGHTS[k] = v; saveWeights(); recompute(); render(); }
    });
    d.appendChild(inp); g.appendChild(d);
  }
}

function won(v){ if(!v) return "-";
  const eok = Math.floor(v/1e8), man = Math.round(v%1e8/1e4);
  if (eok && man) return eok + "억 " + man.toLocaleString();
  if (eok) return eok + "억";
  return man.toLocaleString(); }
function wonShort(v){ if(!v) return "-";
  return (v/1e8).toFixed(1).replace(/\.0$/,"") + "억"; }
function priceText(a){
  return a.trade_type === "A1" ? won(a.deal_price)
    : won(a.warranty_price) + " / " + Math.round(a.rent_price/1e4) + "만"; }
function rpText(a){
  const rs = a.real_summary;
  if (!rs || !rs.all) return "";
  const p = a.trade_type === "A1" ? wonShort(rs.all.avg)
    : wonShort(rs.all.avg) + (rs.all.rent_avg ? "/"+Math.round(rs.all.rent_avg/1e4)+"만" : "");
  return '<div class="rp">실거래 평균 '+p+' <span style="opacity:.7">('+rs.months+'개월 '+rs.total+'건)</span></div>'; }
function volCell(a){
  const v = a.vol_2021;
  if (!v) return "-";
  const cls = v.per_month >= 1 ? "down" : (v.count === 0 ? "up" : "");
  return '<span class="rp"><span class="'+cls+'">월 '+v.per_month+'</span>건</span>'; }

function gapCell(a){
  if (a.real_gap_pct == null) return "-";
  const g = a.real_gap_pct;
  const cls = g <= 0 ? "down" : "up";
  return '<span class="rp"><span class="'+cls+'">'+(g>0?"+":"")+g+'%</span></span>'; }
function slopeCls(g){ if(g==null) return ""; if(g<3) return "slope-flat";
  return g<8 ? "slope-hill" : "slope-steep"; }
function ageText(d){ if(!d) return "-"; const y = new Date().getFullYear() - parseInt(d.slice(0,4));
  return d.slice(0,4) + "년(" + y + "y)"; }
function stationText(a){ if(!a.station_name) return "-";
  return a.station_name + " <span class='sub'>" + a.station_walk_min + "분</span>"; }

function setTrade(t){ trade = t; openRow = null;
  document.querySelectorAll(".tab").forEach(el => el.classList.toggle("on", el.dataset.trade===t));
  document.getElementById("fRentBox").style.display = t==="B2" ? "" : "none";
  document.getElementById("fWarBox").style.display = t==="B2" ? "" : "none";
  document.getElementById("fDealBox").style.display = t==="A1" ? "" : "none";
  document.getElementById("fDealMinBox").style.display = t==="A1" ? "" : "none";
  document.getElementById("fNoGapBox").style.display = t==="A1" ? "" : "none";
  render(); }

function toggleMs(e){ e.stopPropagation();
  document.getElementById("msPanel").classList.toggle("open"); }
document.addEventListener("click", e => {
  if (!e.target.closest(".mspanel") && !e.target.closest("#msBtn"))
    document.getElementById("msPanel").classList.remove("open"); });
let ALL_SIGUS = [];
function msLabel(){
  const b = document.getElementById("msBtn");
  const n = selectedSigu.size;
  b.textContent = (n === 0 || n === ALL_SIGUS.length) ? "전체"
    : (n <= 2 ? [...selectedSigu].join(", ") : n + "개 지역"); }

function filtered(){
  const rentMax = parseFloat(document.getElementById("fRent").value) * 1e4;
  const warMax = parseFloat(document.getElementById("fWar").value) * 1e8;
  const dealMax = parseFloat(document.getElementById("fDeal").value) * 1e8;
  const dealMin = parseFloat(document.getElementById("fDealMin").value) * 1e8;
  const areaMin = parseFloat(document.getElementById("fArea").value);
  const hhMin = parseFloat(document.getElementById("fHh").value);
  const walkMax = parseFloat(document.getElementById("fWalk").value);
  const farMax = parseFloat(document.getElementById("fFar").value);
  const scMin = parseFloat(document.getElementById("fScore").value);
  const volMin = parseFloat(document.getElementById("fVol").value);
  const slopeMax = parseFloat(document.getElementById("fSlope").value);
  const jgc = document.getElementById("fJgc").value;
  const noLease = document.getElementById("fNoLease").checked;
  const lowOk = document.getElementById("fLowOk").checked;
  const noGap = document.getElementById("fNoGap").checked;
  return DATA.filter(a => {
    if (a.trade_type !== trade) return false;
    if (selectedSigu.size && !selectedSigu.has(a.sigu)) return false;
    if (trade==="B2" && !isNaN(rentMax) && a.rent_price > rentMax) return false;
    if (trade==="B2" && !isNaN(warMax) && a.warranty_price > warMax) return false;
    if (trade==="A1" && !isNaN(dealMax) && a.deal_price > dealMax) return false;
    if (trade==="A1" && !isNaN(dealMin) && a.deal_price < dealMin) return false;
    if (!isNaN(areaMin) && (a.exclusive_m2||0) < areaMin) return false;
    if (!isNaN(hhMin) && (a.households||0) < hhMin) return false;
    if (!isNaN(walkMax) && (a.station_walk_min==null || a.station_walk_min > walkMax)) return false;
    if (!isNaN(farMax) && (a.floor_area_ratio==null || a.floor_area_ratio > farMax)) return false;
    if (!isNaN(slopeMax) && !(a.grade_pct != null && a.grade_pct < slopeMax)) return false;
    if (jgc === "only" && !a.is_jgc) return false;
    if (jgc === "excl" && a.is_jgc) return false;
    if (!isNaN(scMin) && a.score_total < scMin) return false;
    if (!isNaN(volMin) && !(a.vol_2021 && a.vol_2021.per_month >= volMin)) return false;
    if (noLease && (a.lease_ratio||0) >= 10) return false;
    if (lowOk && a.low_floor && !a.low_floor.fair) return false;
    if (noGap && a.gap_sale) return false;
    return true;
  });
}

function clearDefaults(){
  ["fWalk","fFar","fVol"].forEach(id => document.getElementById(id).value = "");
  document.getElementById("defnote").style.display = "none";
  render();
}

function tags(a){
  let t = "";
  if (a.is_jgc) t += '<span class="tag jgc">재건축</span>';
  if ((a.lease_ratio||0) >= 10) t += '<span class="tag lease">임대 '+a.lease_ratio+'%</span>';
  if (a.gap_sale) t += '<span class="tag gap">세안고</span>';
  if (a.dup_count) t += '<span class="tag dup">동일 +'+a.dup_count+'</span>';
  if (a.low_floor) t += a.low_floor.fair
    ? '<span class="tag good">저층 -'+a.low_floor.discount_pct+'%</span>'
    : '<span class="tag lease">저층 할인부족 '+(a.low_floor.discount_pct>0?"-":"+")+Math.abs(a.low_floor.discount_pct)+'%</span>';
  return t;
}

function render(){
  const rows = filtered();
  rows.sort((x,y) => {
    let a = x[sortKey], b = y[sortKey];
    if (a==null) a = sortAsc ? Infinity : -Infinity;
    if (b==null) b = sortAsc ? Infinity : -Infinity;
    if (typeof a === "string") return sortAsc ? a.localeCompare(b) : b.localeCompare(a);
    return sortAsc ? a-b : b-a;
  });
  document.getElementById("count").textContent = rows.length.toLocaleString() + "건";
  document.querySelectorAll("thead th").forEach(th => {
    th.querySelector(".arrow").textContent = th.dataset.k===sortKey ? (sortAsc?"▲":"▼") : ""; });
  const tb = document.getElementById("tbody");
  tb.innerHTML = "";
  document.getElementById("empty").style.display = rows.length ? "none" : "";
  const frag = document.createDocumentFragment();
  rows.slice(0, 500).forEach(a => {
    const tr = document.createElement("tr");
    tr.className = "row";
    tr.innerHTML =
      '<td><span class="badge '+a.grade+'">'+a.grade+'</span> <b>'+a.score_total.toFixed(1)+'</b></td>' +
      '<td><div class="cname">'+a.complex_name+tags(a)+'</div>' +
        '<div class="sub">'+a.sigu+' '+a.dong+(a.bld_dong?' · '+a.bld_dong+'동':'')+(a.floor_info?' · '+a.floor_info+'층':'')+'</div></td>' +
      '<td class="price">'+priceText(a)+rpText(a)+'</td>' +
      '<td class="hide-m">'+gapCell(a)+'</td>' +
      '<td class="hide-m">'+volCell(a)+'</td>' +
      '<td>'+(a.exclusive_m2||"-")+'㎡</td>' +
      '<td class="hide-m">'+(a._ppp? Math.round(a._ppp/1e4).toLocaleString()+"만":"-")+'</td>' +
      '<td class="hide-m">'+(a.households||"-")+'</td>' +
      '<td class="hide-m">'+ageText(a.use_date)+'</td>' +
      '<td>'+stationText(a)+'</td>' +
      '<td class="'+slopeCls(a.grade_pct)+'">'+(a.slope_label||"미상")+'</td>';
    tr.onclick = () => toggleDetail(tr, a);
    frag.appendChild(tr);
  });
  tb.appendChild(frag);
  if (rows.length > 500) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="11" class="sub" style="text-align:center">상위 500건만 표시 — 필터를 좁혀보세요</td>';
    tb.appendChild(tr);
  }
}

function toggleHelp(e, k){
  e.stopPropagation();          // 행 클릭(상세 접기)으로 번지지 않게
  const el = document.getElementById("help-"+k);
  if (el) el.classList.toggle("open");
}

function fact(k, v, cls){
  if (v === null || v === undefined || v === "") return "";
  return '<div class="fact'+(cls?' '+cls:'')+'"><span class="k">'+k+'</span><b>'+v+'</b></div>';
}

function toggleDetail(tr, a){
  if (openRow) { openRow.remove(); if (openRow._for === tr) { openRow = null; return; } }
  const d = document.createElement("tr");
  d.className = "detail"; d._for = tr;
  let bars = "";
  for (const k in SCORE_LABELS) {
    const v = a.scores[k];
    bars += '<div class="bar"><div class="t"><span>'+SCORE_LABELS[k] +
            ' <button class="hbtn" onclick="toggleHelp(event,\''+k+'\')" title="산정 방식">?</button>' +
            ' <span style="opacity:.6">×'+(WEIGHTS[k]||0)+'</span></span><b>'+(v==null?"-":v.toFixed(1))+'</b></div>' +
            '<div class="g"><i style="width:'+(v==null?0:v*10)+'%"></i></div>' +
            '<div class="help" id="help-'+k+'">'+SCORE_HELP[k]+'</div></div>';
  }
  // 실거래 요약 — 저층(1~3층) / 일반층 평균
  const rs = a.real_summary;
  const money = g => a.trade_type==="A1" ? wonShort(g.avg)
      : wonShort(g.avg) + (g.rent_avg ? "/"+Math.round(g.rent_avg/1e4)+"만" : "");
  let rpAll = "이력 없음", rpLow = null, rpHigh = null;
  if (rs) {
    rpAll = money(rs.all) + " <span class='sub'>(" + rs.months + "개월 " + rs.total + "건)</span>";
    if (rs.low)  rpLow  = money(rs.low)  + " <span class='sub'>(" + rs.low.count + "건)</span>";
    if (rs.high) rpHigh = money(rs.high) + " <span class='sub'>(" + rs.high.count + "건)</span>";
  }
  // 전세가율/갭 (매매)
  let jeonseFacts = "";
  if (a.trade_type === "A1" && a.jeonse_max) {
    const ratio = Math.round(a.jeonse_max / a.deal_price * 100);
    const gap = a.deal_price - a.jeonse_max;
    jeonseFacts =
      fact("단지 전세 호가", wonShort(a.jeonse_min)+" ~ "+wonShort(a.jeonse_max)+" (전세가율 "+ratio+"%)") +
      fact("갭(호가-전세최고)", wonShort(gap), gap <= 300000000 ? "good" : "");
  }
  const vol = a.vol_2021;
  const facts =
    fact("실거래 평균", rpAll) +
    fact("저층 1~3층", rpLow) +
    fact("일반층 4층~", rpHigh) +
    (vol ? fact("2021년 거래량", vol.count + "건 · 월 " + vol.per_month + "건",
                vol.per_month >= 1 ? "good" : (vol.count === 0 ? "warn" : "")) : "") +
    (a.low_floor ? fact("저층 할인율",
        (a.low_floor.discount_pct >= 0 ? "-" : "+") + Math.abs(a.low_floor.discount_pct) + "% (일반층 실거래 평균 대비)"
        + (a.low_floor.fair ? " · 적정" : " · 10% 미만"),
        a.low_floor.fair ? "good" : "warn") : "") +
    (a.real_gap_pct != null
      ? fact("실거래 대비 호가", (a.real_gap_pct>0?"+":"")+a.real_gap_pct+"%"
             + (a.real_gap_basis ? " (" + a.real_gap_basis + ")" : ""),
             a.real_gap_pct <= 0 ? "good" : (a.real_gap_pct >= 10 ? "warn" : "")) : "") +
    jeonseFacts +
    fact("평형", (a.pyeong_name||"") + (a.pyeong_households ? " · "+a.pyeong_households+"세대" : "")) +
    (a.poi ? fact("학원가", (a.poi.academy_1km||0)+"곳/1km" + (a.poi.academy_500m ? " ("+a.poi.academy_500m+"곳/500m)" : ""),
                  (a.poi.academy_1km||0) >= 50 ? "good" : ((a.poi.academy_1km||0) < 5 ? "warn" : "")) : "") +
    (a.poi && a.poi.middle_crowding != null
      ? fact("배정중 과밀도", a.poi.middle_crowding+"배 (시평균=1)",
             a.poi.middle_crowding >= 1.2 ? "good" : "") : "") +
    (a.poi && (a.poi.elite_high||[]).length ? fact("명문·특목고", a.poi.elite_high.join(", "), "good") : "") +
    (a.poi && a.poi.elem_near_m != null ? fact("초등학교", a.poi.elem_near_m+"m",
             a.poi.elem_near_m <= 300 ? "good" : (a.poi.elem_near_m > 800 ? "warn" : "")) : "") +
    (a.poi ? fact("생활 인프라",
        [(a.poi.dept_near_m != null ? "백화점 "+a.poi.dept_near_m+"m" : null),
         (a.poi.mart_1km ? "마트 "+a.poi.mart_1km+"곳" : (a.poi.mart_near_m != null ? "마트 "+a.poi.mart_near_m+"m" : null)),
         (a.poi.hospital_1km ? "병원 "+a.poi.hospital_1km : null),
         (a.poi.conv_500m ? "편의점 "+a.poi.conv_500m : null)].filter(Boolean).join(" · ") || "정보 없음") : "") +
    (a.poi ? fact("공원", a.poi.park_near_m != null ? "최근접 "+a.poi.park_near_m+"m" : "1km 내 없음",
             a.poi.park_near_m != null && a.poi.park_near_m <= 300 ? "good" : "") : "") +
    fact("임대세대", a.lease_households ? a.lease_households+"세대 ("+a.lease_ratio+"%)" : "없음", (a.lease_ratio||0)>=10?"warn":"") +
    fact("세대당 주차", a.parking_per_hh != null ? a.parking_per_hh+"대" : null, a.parking_per_hh != null && a.parking_per_hh < 1 ? "warn":"") +
    fact("용적률/건폐율", a.floor_area_ratio ? a.floor_area_ratio+"% / "+(a.coverage_ratio||"-")+"%" : null) +
    fact("최기역", a.station_name ? a.station_name+"역 도보 "+a.station_walk_min+"분 ("+a.station_m+"m)" : null, a.station_walk_min > 15?"warn":"") +
    fact("경사", a.slope_label + (a.grade_pct!=null ? " ("+a.grade_pct+"%)" : ""), a.grade_pct >= 5?"warn":"") +
    fact("관리비", a.mgmt_fee ? Math.round(a.mgmt_fee/1e4)+"만원" : null) +
    fact("건설사", a.construction_company) +
    fact("최고층", a.highest_floor ? a.highest_floor+"층" : null) +
    fact("세대수", (a.households||"-") + "세대 · " + ageText(a.use_date)) +
    (a.trade_type==="A1" ? fact("세안고(전세끼고)", a.gap_sale ? "설명에 언급 있음" : "언급 없음", a.gap_sale?"warn":"") : "") +
    (a.is_jgc ? fact("조합원 지위양도", a.jgc_transfer_restricted ? "제한 있음 ⚠" : "확인 필요", a.jgc_transfer_restricted?"warn":"") : "") +
    fact("확인매물", (a.verification==="OWNER"?"집주인 확인 · ":"") + (a.confirm_date||""));
  const newland = "https://new.land.naver.com/complexes/"+a.complex_no+"?articleNo="+a.article_no;
  const finland = "https://fin.land.naver.com/articles/"+a.article_no;
  let vars = "";
  if (a.variants && a.variants.length) {
    vars = '<div class="vars"><div class="sub" style="margin-bottom:4px">같은 매물로 보이는 등록 '+a.variants.length+'건 (중개사만 다름)</div>' +
      a.variants.map(v =>
        '<div class="v">'+(v.floor_info?v.floor_info+"층 · ":"")+(v.realtor||"")+
        (v.confirm_date?" · 확인 "+v.confirm_date:"")+
        ' · <a href="https://new.land.naver.com/complexes/'+v.complex_no+'?articleNo='+v.article_no+'" target="_blank" rel="noopener">보기</a>'+
        (v.description?'<div class="sub">'+v.description+'</div>':'')+'</div>').join("") + '</div>';
  }
  d.innerHTML = '<td colspan="11">' +
    '<div class="bars">'+bars+'</div>' +
    '<div class="facts">'+facts+'</div>' +
    (a.description ? '<div class="desc">📝 '+a.description+'</div>' : '') +
    '<div class="sub">'+[a.direction?("향: "+a.direction):null, a.realtor].filter(Boolean).join(" · ")+'</div>' +
    '<div class="links"><a href="'+newland+'" target="_blank" rel="noopener">네이버 부동산에서 보기</a>' +
    '<a class="ghost" href="'+finland+'" target="_blank" rel="noopener">모바일 매물 페이지</a></div>' +
    vars + '</td>';
  tr.after(d); openRow = d;
}

(function init(){
  const sigus = [...new Set(DATA.map(a=>a.sigu))].sort();
  const panel = document.getElementById("msPanel");
  const all = document.createElement("label");
  all.className = "msall";
  all.innerHTML = '<input type="checkbox" id="msAll" checked> 전체';
  panel.appendChild(all);
  ALL_SIGUS = sigus;
  sigus.forEach(s => {
    const l = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.value = s; cb.className = "msItem"; cb.checked = true;
    selectedSigu.add(s);
    l.appendChild(cb); l.appendChild(document.createTextNode(" " + s));
    panel.appendChild(l);
  });
  msLabel();
  panel.addEventListener("change", e => {
    const items = document.querySelectorAll(".msItem");
    if (e.target.id === "msAll") {
      // 전체를 켜면 하위 지역이 모두 켜지고, 거기서 원하는 것만 끄면 된다
      const on = e.target.checked;
      selectedSigu.clear();
      items.forEach(c => { c.checked = on; if (on) selectedSigu.add(c.value); });
    } else {
      if (e.target.checked) selectedSigu.add(e.target.value);
      else selectedSigu.delete(e.target.value);
      document.getElementById("msAll").checked = selectedSigu.size === items.length;
    }
    msLabel(); render();
  });
  document.getElementById("cntB2").textContent = "("+DATA.filter(a=>a.trade_type==="B2").length+")";
  document.getElementById("cntA1").textContent = "("+DATA.filter(a=>a.trade_type==="A1").length+")";
  document.querySelectorAll(".filters input, .filters select").forEach(el => el.addEventListener("input", render));
  document.querySelectorAll("thead th").forEach(th => th.addEventListener("click", () => {
    const k = th.dataset.k;
    if (sortKey === k) sortAsc = !sortAsc;
    else { sortKey = k; sortAsc = (k==="complex_name"||k==="_price"||k==="_ppp"||k==="grade_pct"||k==="station_walk_min"||k==="real_gap_pct"); }
    render();
  }));
  buildWeightPanel();
  recompute();
  render();
})();
</script>
</body>
</html>
"""


def render(rows, cfg, out_path: Path):
    import time
    slim = []
    for a in rows:
        slim.append({k: a.get(k) for k in (
            "article_no", "complex_no", "complex_name", "bld_dong", "trade_type",
            "deal_price", "warranty_price", "rent_price", "mgmt_fee",
            "exclusive_m2", "supply_m2", "floor_info", "direction", "description",
            "confirm_date", "verification", "realtor",
            "sido", "sigu", "dong", "households", "use_date", "is_jgc",
            "grade_pct", "slope_label", "scores", "score_total", "grade",
            "lease_households", "lease_ratio", "parking_per_hh", "floor_area_ratio",
            "coverage_ratio", "construction_company", "highest_floor",
            "jgc_transfer_restricted", "gap_sale", "dup_count", "variants",
            "station_name", "station_m", "station_walk_min",
            "real_prices", "real_summary", "vol_2021", "low_floor", "real_gap_pct", "real_gap_basis", "jeonse_min", "jeonse_max",
            "pyeong_name", "pyeong_households", "poi")})
    html = (TEMPLATE
            .replace("__TITLE__", cfg["web"]["title"])
            .replace("__GENERATED__", time.strftime("%Y-%m-%d %H:%M"))
            .replace("__WEIGHTS_JSON__", json.dumps(cfg["score_weights"]))
            .replace("__DATA__", json.dumps(slim, ensure_ascii=False)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
