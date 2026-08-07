"""정적 대시보드 생성 — 데이터 임베드 단일 HTML (docs/index.html)."""

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
  --s:#7c3aed; --a:#2563eb; --b:#059669; --c:#d97706; --d:#9ca3af;
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#12151c; --card:#1a1f29; --ink:#e8ebf1; --sub:#98a1b3; --line:#2a3140;
          --accent:#5b8def; --accent-soft:#1e2a44; --warn:#f59e0b; --warn-soft:#3a2c14; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.55 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard",sans-serif; }
.wrap { max-width:1240px; margin:0 auto; padding:20px 16px 60px; }
h1 { font-size:20px; margin:0 0 2px; }
.meta { color:var(--sub); font-size:12px; margin-bottom:14px; }
.tabs { display:flex; gap:8px; margin:14px 0; }
.tab { flex:0 0 auto; padding:8px 22px; border-radius:10px; border:1px solid var(--line);
  background:var(--card); cursor:pointer; font-weight:600; font-size:14px; color:var(--sub); }
.tab.on { background:var(--accent); border-color:var(--accent); color:#fff; }
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
.badge { display:inline-block; min-width:26px; text-align:center; padding:3px 8px;
  border-radius:8px; color:#fff; font-weight:700; font-size:13px; }
.badge.S{background:var(--s);} .badge.A{background:var(--a);}
.badge.B{background:var(--b);} .badge.C{background:var(--c);} .badge.D{background:var(--d);}
.tag { display:inline-block; padding:1px 7px; border-radius:6px; font-size:11px; font-weight:600;
  margin-left:4px; vertical-align:1px; }
.tag.lease { background:var(--warn-soft); color:var(--warn); }
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
.facts { display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:6px 18px;
  margin:10px 0; padding:10px 12px; background:var(--card); border:1px solid var(--line); border-radius:10px; }
.fact { font-size:12px; }
.fact b { display:block; font-size:13px; }
.fact .k { color:var(--sub); }
.fact.warn b { color:var(--warn); }
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
  <div class="meta">생성: __GENERATED__ · 데이터: 네이버 부동산 (동일매물 묶음) · 평점: 가격가치 중심 가중 __WEIGHTS__ · 교통=업무지구 70%+역세권 30%</div>
  <div class="tabs">
    <button class="tab on" data-trade="B2" onclick="setTrade('B2')">월세 <span id="cntB2"></span></button>
    <button class="tab" data-trade="A1" onclick="setTrade('A1')">매매 <span id="cntA1"></span></button>
  </div>
  <div class="filters">
    <div class="f"><label>지역(시군구) — 다중 선택</label>
      <button class="msbtn" id="msBtn" onclick="toggleMs(event)">전체</button>
      <div class="mspanel" id="msPanel"></div>
    </div>
    <div class="f" id="fRentBox"><label>월세 최대(만원)</label><input type="number" id="fRent" placeholder="100"></div>
    <div class="f" id="fWarBox"><label>보증금 최대(억)</label><input type="number" id="fWar" step="0.5" placeholder="3"></div>
    <div class="f" id="fDealMinBox" style="display:none"><label>매매가 최소(억)</label><input type="number" id="fDealMin" step="0.5" placeholder="7"></div>
    <div class="f" id="fDealBox" style="display:none"><label>매매가 최대(억)</label><input type="number" id="fDeal" step="0.5" placeholder="12"></div>
    <div class="f"><label>전용면적 최소(㎡)</label><input type="number" id="fArea" placeholder="59"></div>
    <div class="f"><label>세대수 최소</label><input type="number" id="fHh" placeholder="300"></div>
    <div class="f"><label>역도보 최대(분)</label><input type="number" id="fWalk" placeholder="∞"></div>
    <div class="f"><label>용적률 최대(%)</label><input type="number" id="fFar" step="10" placeholder="∞"></div>
    <div class="f"><label>평점 최소</label><input type="number" id="fScore" step="0.5" placeholder="0"></div>
    <div class="f"><label>경사(언덕)</label>
      <select id="fSlope">
        <option value="">전체</option>
        <option value="1.5">평지만 (&lt;1.5%)</option>
        <option value="3">완만까지 (&lt;3%)</option>
        <option value="5">약한 언덕까지 (&lt;5%)</option>
        <option value="8">언덕까지 (&lt;8%)</option>
      </select>
    </div>
    <div class="f chk"><input type="checkbox" id="fNoLease"><label for="fNoLease" style="font-size:13px;color:var(--ink)">임대혼합 제외</label></div>
    <div class="f chk" id="fNoGapBox" style="display:none"><input type="checkbox" id="fNoGap"><label for="fNoGap" style="font-size:13px;color:var(--ink)">세안고 제외</label></div>
  </div>
  <div class="count" id="count"></div>
  <table>
    <thead><tr>
      <th data-k="score_total">평점 <span class="arrow"></span></th>
      <th data-k="complex_name">단지 <span class="arrow"></span></th>
      <th data-k="_price">가격 <span class="arrow"></span></th>
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
const SCORE_LABELS = {value:"가격가치", transit:"교통", school:"학군", infra:"인프라", scale_age:"규모·연식", slope:"언덕"};
const PY = 3.3058, RATE = 0.055;
let trade = "B2", sortKey = "score_total", sortAsc = false, openRow = null;
let selectedSigu = new Set();

DATA.forEach(a => {
  a._price = a.trade_type === "A1" ? a.deal_price : a.warranty_price;
  const eff = a.trade_type === "A1" ? a.deal_price : a.warranty_price + a.rent_price*12/RATE;
  a._ppp = a.exclusive_m2 ? eff / (a.exclusive_m2/PY) : 0;
});

function won(v){ if(!v) return "-";
  const eok = Math.floor(v/1e8), man = Math.round(v%1e8/1e4);
  if (eok && man) return eok + "억 " + man.toLocaleString();
  if (eok) return eok + "억";
  return man.toLocaleString(); }
function priceText(a){
  return a.trade_type === "A1" ? won(a.deal_price)
    : won(a.warranty_price) + " / " + Math.round(a.rent_price/1e4) + "만"; }
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
function msLabel(){
  const b = document.getElementById("msBtn");
  b.textContent = selectedSigu.size === 0 ? "전체"
    : (selectedSigu.size <= 2 ? [...selectedSigu].join(", ") : selectedSigu.size + "개 지역"); }

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
  const slopeMax = parseFloat(document.getElementById("fSlope").value);
  const noLease = document.getElementById("fNoLease").checked;
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
    if (!isNaN(scMin) && a.score_total < scMin) return false;
    if (!isNaN(slopeMax) && !(a.grade_pct != null && a.grade_pct < slopeMax)) return false;
    if (noLease && (a.lease_ratio||0) >= 10) return false;
    if (noGap && a.gap_sale) return false;
    return true;
  });
}

function tags(a){
  let t = "";
  if (a.is_jgc) t += '<span class="tag jgc">재건축</span>';
  if ((a.lease_ratio||0) >= 10) t += '<span class="tag lease">임대 '+a.lease_ratio+'%</span>';
  if (a.gap_sale) t += '<span class="tag gap">세안고</span>';
  if (a.dup_count) t += '<span class="tag dup">동일 +'+a.dup_count+'</span>';
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
      '<td class="price">'+priceText(a)+'</td>' +
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
    tr.innerHTML = '<td colspan="9" class="sub" style="text-align:center">상위 500건만 표시 — 필터를 좁혀보세요</td>';
    tb.appendChild(tr);
  }
}

function fact(k, v, warn){
  if (v === null || v === undefined || v === "" ) return "";
  return '<div class="fact'+(warn?' warn':'')+'"><span class="k">'+k+'</span><b>'+v+'</b></div>';
}

function toggleDetail(tr, a){
  if (openRow) { openRow.remove(); if (openRow._for === tr) { openRow = null; return; } }
  const d = document.createElement("tr");
  d.className = "detail"; d._for = tr;
  let bars = "";
  for (const k in SCORE_LABELS) {
    const v = a.scores[k];
    bars += '<div class="bar"><div class="t"><span>'+SCORE_LABELS[k]+'</span><b>'+(v==null?"-":v.toFixed(1))+'</b></div>' +
            '<div class="g"><i style="width:'+(v==null?0:v*10)+'%"></i></div></div>';
  }
  const facts =
    fact("임대세대", a.lease_households ? a.lease_households+"세대 ("+a.lease_ratio+"%)" : "없음", (a.lease_ratio||0)>=10) +
    fact("세대당 주차", a.parking_per_hh != null ? a.parking_per_hh+"대" : null, a.parking_per_hh != null && a.parking_per_hh < 1) +
    fact("용적률/건폐율", a.floor_area_ratio ? a.floor_area_ratio+"% / "+(a.coverage_ratio||"-")+"%" : null) +
    fact("최기역", a.station_name ? a.station_name+"역 도보 "+a.station_walk_min+"분 ("+a.station_m+"m)" : null, a.station_walk_min > 15) +
    fact("경사", a.slope_label + (a.grade_pct!=null ? " ("+a.grade_pct+"%)" : ""), a.grade_pct >= 5) +
    fact("관리비", a.mgmt_fee ? Math.round(a.mgmt_fee/1e4)+"만원" : null) +
    fact("건설사", a.construction_company) +
    fact("최고층", a.highest_floor ? a.highest_floor+"층" : null) +
    fact("세대수", (a.households||"-") + "세대 · " + ageText(a.use_date)) +
    (a.trade_type==="A1" ? fact("세안고(전세끼고)", a.gap_sale ? "설명에 언급 있음" : "언급 없음", a.gap_sale) : "") +
    (a.is_jgc ? fact("조합원 지위양도", a.jgc_transfer_restricted ? "제한 있음 ⚠" : "확인 필요", a.jgc_transfer_restricted) : "") +
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
  d.innerHTML = '<td colspan="9">' +
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
  sigus.forEach(s => {
    const l = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.value = s; cb.className = "msItem";
    l.appendChild(cb); l.appendChild(document.createTextNode(" " + s));
    panel.appendChild(l);
  });
  panel.addEventListener("change", e => {
    if (e.target.id === "msAll") {
      selectedSigu.clear();
      document.querySelectorAll(".msItem").forEach(c => c.checked = false);
    } else {
      if (e.target.checked) selectedSigu.add(e.target.value);
      else selectedSigu.delete(e.target.value);
      document.getElementById("msAll").checked = selectedSigu.size === 0;
    }
    msLabel(); render();
  });
  document.getElementById("cntB2").textContent = "("+DATA.filter(a=>a.trade_type==="B2").length+")";
  document.getElementById("cntA1").textContent = "("+DATA.filter(a=>a.trade_type==="A1").length+")";
  document.querySelectorAll(".filters input, .filters select").forEach(el => el.addEventListener("input", render));
  document.querySelectorAll("thead th").forEach(th => th.addEventListener("click", () => {
    const k = th.dataset.k;
    if (sortKey === k) sortAsc = !sortAsc;
    else { sortKey = k; sortAsc = (k==="complex_name"||k==="_price"||k==="_ppp"||k==="grade_pct"||k==="station_walk_min"); }
    render();
  }));
  render();
})();
</script>
</body>
</html>
"""


def render(rows, cfg, out_path: Path):
    import time
    weights = cfg["score_weights"]
    wtext = " / ".join(f"{k} {v}%" for k, v in weights.items())
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
            "station_name", "station_m", "station_walk_min")})
    html = (TEMPLATE
            .replace("__TITLE__", cfg["web"]["title"])
            .replace("__GENERATED__", time.strftime("%Y-%m-%d %H:%M"))
            .replace("__WEIGHTS__", wtext)
            .replace("__DATA__", json.dumps(slim, ensure_ascii=False)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
