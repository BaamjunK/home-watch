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
<meta http-equiv="Cache-Control" content="no-cache, must-revalidate">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<title>__TITLE__</title>
<style>
/* Hallmark · genre: editorial · macrostructure: Catalogue · theme: Almanac (oat paper / terracotta)
 * nav: N6 newspaper masthead · footer: Ft4 dense colophon · enrichment: none
 * tone: 인쇄된 매물 카탈로그 · anchor hue: 75 (warm oat) · accent: terracotta 45
 * pre-emit critique: P5 H5 E5 S5 R5 V4
 * contrast: pass (40-41, light+dark 30/30) · mobile: pass (34, 49-57 @320/375/414/768)
 * tokens: pass (48) · icons: pass (30) · chrome: pass (47) · honest: pass (46)
 */
:root {
  /* 종이 — 매물 전단의 웜 오트. 순백/순흑 없음 */
  --color-paper:    oklch(97%   0.008 75);
  --color-paper-2:  oklch(94.5% 0.010 72);
  --color-paper-3:  oklch(91.5% 0.012 70);
  --color-rule:     oklch(86%   0.012 68);
  --color-rule-2:   oklch(70%   0.014 62);
  --color-neutral:  oklch(57%   0.012 62);
  --color-muted:    oklch(44%   0.012 58);
  --color-ink:      oklch(23%   0.014 55);
  /* 액센트는 벽돌색 하나 — 화면의 3% 이하 */
  --color-accent:   oklch(51%   0.135 45);
  --color-accent-2: oklch(93%   0.030 45);
  --color-focus:    oklch(51%   0.160 45);
  /* 데이터 신호 (기능용, 저채도) */
  --color-good:     oklch(45%   0.095 152);
  --color-warn:     oklch(50%   0.115 68);
  --color-alert:    oklch(48%   0.150 28);
  --color-star:     oklch(63%   0.130 78);
  --color-shadow:   oklch(23%   0.014 55 / .14);

  --font-display: "Nanum Myeongjo", ui-serif, Georgia, serif;
  --font-body: "Pretendard", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
  --font-num: "JetBrains Mono", ui-monospace, SFMono-Regular, monospace;

  --space-4xs:.125rem; --space-3xs:.25rem; --space-2xs:.5rem; --space-xs:.75rem; --space-sm:1rem;
  --space-md:1.5rem; --space-lg:2rem; --space-xl:3rem; --space-2xl:4.5rem;

  --text-xs:.75rem;    --text-sm:.8125rem;  --text-base:.9375rem;
  --text-md:1.0625rem; --text-lg:1.3125rem; --text-xl:1.625rem;
  --text-display: clamp(1.75rem, 3.4vw + .75rem, 2.75rem);

  --ease-out: cubic-bezier(.16,1,.3,1);
  --dur-short: 160ms;
  --radius-sm: 2px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-paper:    oklch(16%   0.012 68);
    --color-paper-2:  oklch(19.5% 0.013 68);
    --color-paper-3:  oklch(23%   0.014 68);
    --color-rule:     oklch(32%   0.014 66);
    --color-rule-2:   oklch(45%   0.016 64);
    --color-neutral:  oklch(62%   0.012 68);
    --color-muted:    oklch(74%   0.010 70);
    --color-ink:      oklch(93%   0.008 78);
    --color-accent:   oklch(70%   0.115 48);
    --color-accent-2: oklch(28%   0.045 45);
    --color-focus:    oklch(72%   0.140 48);
    --color-good:     oklch(70%   0.100 152);
    --color-warn:     oklch(75%   0.105 70);
    --color-alert:    oklch(68%   0.135 28);
    --color-star:     oklch(76%   0.120 80);
    --color-shadow:   oklch(4%    0.010 60 / .5);
  }
}

* { box-sizing:border-box; }
html, body { overflow-x:clip; }
body { margin:0; background:var(--color-paper); color:var(--color-ink);
  font-family:var(--font-body); font-size:var(--text-base); line-height:1.55;
  -webkit-font-smoothing:antialiased; font-variant-numeric:tabular-nums; }
.wrap { max-width:1360px; margin:0 auto; padding:0 var(--space-md) var(--space-2xl); }
:focus-visible { outline:2px solid var(--color-focus); outline-offset:2px; }

/* ── N6 마스트헤드 ─────────────────────────────── */
.masthead { padding:var(--space-lg) 0 var(--space-xs); text-align:center;
  border-bottom:1px solid var(--color-rule-2); position:relative; }
.masthead::after { content:""; position:absolute; left:0; right:0; bottom:-4px;
  border-bottom:1px solid var(--color-rule); }
.masthead h1 { font-family:var(--font-display); font-weight:700; font-style:normal;
  font-size:var(--text-display); line-height:1.12; letter-spacing:-.015em;
  margin:0 0 var(--space-2xs); overflow-wrap:anywhere; min-width:0; }
.masthead .issue { margin:0; color:var(--color-muted); font-size:var(--text-xs);
  letter-spacing:.02em; }
.masthead .issue b { font-weight:600; color:var(--color-ink); }

/* ── 판 선택 + 도구 ─────────────────────────────── */
.tabs { display:flex; gap:var(--space-md); align-items:baseline; flex-wrap:wrap;
  padding:var(--space-md) 0 var(--space-xs); }
.tab { flex:0 0 auto; padding:0 0 var(--space-3xs); border:0; background:none; cursor:pointer;
  font-family:var(--font-body); font-size:var(--text-md); font-weight:500;
  color:var(--color-muted); border-bottom:2px solid transparent; white-space:nowrap;
  transition:color var(--dur-short) var(--ease-out); }
.tab:hover { color:var(--color-ink); }
.tab.on { color:var(--color-ink); font-weight:700; border-bottom-color:var(--color-accent); }
.tab:active { color:var(--color-accent); }
.tab:disabled, .wbtn:disabled, .wreset:disabled, .hbtn:disabled, .fav:disabled {
  opacity:.55; cursor:not-allowed; }
.tab span { font-family:var(--font-num); font-size:var(--text-sm); color:var(--color-muted);
  font-weight:400; }
.wbtn { padding:var(--space-3xs) var(--space-2xs); border:0; border-bottom:1px solid var(--color-neutral);
  background:none; cursor:pointer; font-family:var(--font-body); font-size:var(--text-sm);
  color:var(--color-muted); white-space:nowrap;
  transition:color var(--dur-short) var(--ease-out), border-color var(--dur-short) var(--ease-out); }
.wbtn:hover { color:var(--color-ink); border-bottom-color:var(--color-accent); }
.wbtn:active { color:var(--color-accent); }
.wbtn.on { color:var(--color-accent); border-bottom-color:var(--color-accent); }
#favBtn { margin-left:auto; }

/* ── 패널 (가중치) ─────────────────────────────── */
.wpanel { display:none; padding:var(--space-sm) 0 var(--space-md);
  border-bottom:1px solid var(--color-rule); }
.wpanel.open { display:block; }
.wgrid { display:flex; flex-wrap:wrap; gap:var(--space-sm) var(--space-md); align-items:flex-end; }
.wf { display:flex; flex-direction:column; gap:var(--space-3xs); }
.wf label { font-size:var(--text-xs); color:var(--color-muted); letter-spacing:.04em; }
.wf input { width:4.5rem; padding:var(--space-3xs) 0; border:0;
  border-bottom:1px solid var(--color-neutral); background:none; color:var(--color-ink);
  font-family:var(--font-num); font-size:var(--text-sm); }
.wf input:focus-visible { border-bottom-color:var(--color-accent); }
.wnote { font-size:var(--text-xs); color:var(--color-muted); margin-top:var(--space-xs);
  max-width:70ch; line-height:1.65; }
.wreset { padding:var(--space-3xs) var(--space-2xs); border:1px solid var(--color-accent);
  border-radius:var(--radius-sm); background:none; color:var(--color-accent); cursor:pointer;
  font-family:var(--font-body); font-size:var(--text-xs); font-weight:600; white-space:nowrap;
  transition:background-color var(--dur-short) var(--ease-out), color var(--dur-short) var(--ease-out); }
.wreset:hover { background:var(--color-accent); color:var(--color-paper); }
.wreset:active { transform:translateY(1px); }
.wreset.ghost { border-color:var(--color-neutral); color:var(--color-muted); }
.wreset.ghost:hover { background:none; border-color:var(--color-ink); color:var(--color-ink); }

/* ── 필터 밴드 ─────────────────────────────────── */
.filters { display:flex; flex-wrap:wrap; gap:var(--space-sm) var(--space-md);
  padding:var(--space-sm) 0 var(--space-md); align-items:flex-end;
  border-bottom:1px solid var(--color-rule); }
.f { display:flex; flex-direction:column; gap:var(--space-3xs); position:relative; }
.f label { font-size:var(--text-xs); color:var(--color-muted); letter-spacing:.04em; }
.f input, .f select, .f .msbtn { padding:var(--space-3xs) 0; border:0;
  border-bottom:1px solid var(--color-neutral); background:none; color:var(--color-ink);
  font-family:var(--font-body); font-size:var(--text-sm); min-width:6.5rem;
  text-align:left; cursor:pointer; border-radius:0; }
.f input { font-family:var(--font-num); }
.f select { cursor:pointer; }
.f input:focus-visible, .f select:focus-visible, .f .msbtn:focus-visible {
  border-bottom-color:var(--color-accent); }
.f input[type=number] { width:6rem; }
.chk { flex-direction:row; align-items:center; gap:var(--space-2xs); padding-bottom:var(--space-3xs); }
.chk label { font-size:var(--text-sm); color:var(--color-ink); letter-spacing:0; cursor:pointer; }
.chk input[type=checkbox] { accent-color:var(--color-accent); width:1rem; height:1rem; cursor:pointer; }
.mspanel { display:none; position:absolute; top:100%; left:0; z-index:30; margin-top:var(--space-3xs);
  background:var(--color-paper); border:1px solid var(--color-rule-2); padding:var(--space-2xs) var(--space-xs);
  max-height:17rem; overflow:auto; box-shadow:0 6px 18px var(--color-shadow); min-width:11rem; }
.mspanel.open { display:block; }
.mspanel label { display:flex; gap:var(--space-2xs); align-items:center; font-size:var(--text-sm);
  color:var(--color-ink); padding:var(--space-3xs) 0; cursor:pointer; white-space:nowrap; }
.mspanel input[type=checkbox] { accent-color:var(--color-accent); }
.msall { border-bottom:1px solid var(--color-rule); margin-bottom:var(--space-3xs);
  padding-bottom:var(--space-2xs) !important; }

/* ── 재고 헤더 ─────────────────────────────────── */
.count { margin:var(--space-md) 0 var(--space-3xs); color:var(--color-ink);
  font-size:var(--text-sm); }
.count b, #count { font-weight:600; }
#defnote { margin:0 0 var(--space-xs); color:var(--color-muted); font-size:var(--text-xs); }
.fresh { margin:var(--space-sm) 0; padding:var(--space-2xs) var(--space-xs);
  font-size:var(--text-sm); color:var(--color-warn);
  border-left:2px solid var(--color-warn); background:none; }

/* ── 카탈로그 표: 카드가 아니라 괘선 ──────────────── */
table { width:100%; border-collapse:collapse; background:none; border:0; }
thead th { text-align:left; font-size:var(--text-xs); color:var(--color-muted); font-weight:600;
  letter-spacing:.08em; padding:var(--space-2xs) var(--space-2xs); white-space:nowrap;
  cursor:pointer; user-select:none; position:sticky; top:0; z-index:5;
  background:var(--color-paper); border-bottom:1px solid var(--color-rule-2); }
thead th:first-child { padding-left:0; }
thead th .arrow { color:var(--color-accent); font-size:var(--text-xs); }
tbody td { padding:var(--space-xs) var(--space-2xs); border-bottom:1px solid var(--color-rule);
  vertical-align:middle; }
/* 보조 지표(실거래대비·21년거래·평당·세대·연식)는 한 단계 작게 — 단지·호가에 자리를 내준다 */
tbody td.hide-m { font-size:var(--text-xs); color:var(--color-muted); white-space:nowrap; }
tbody td:nth-child(6) { white-space:nowrap; font-size:var(--text-xs); color:var(--color-muted); }
tbody td:nth-child(10) { font-size:var(--text-xs); }
tbody td:nth-child(11) { font-size:var(--text-xs); white-space:nowrap; }
tbody td:first-child { padding-left:0; }
tbody tr.row { cursor:pointer; transition:background-color var(--dur-short) var(--ease-out); }
tbody tr.row:hover { background:var(--color-paper-2); }
tbody tr.grp.open { background:var(--color-accent-2); }
tbody tr.grp .caret { color:var(--color-accent); font-size:var(--text-xs); }
tbody tr.sub-row { background:var(--color-paper-2); }
tbody tr.sub-row td { border-bottom:1px solid var(--color-rule); }
tbody tr.sub-row td:first-child { padding-left:var(--space-md); }
.cname { font-family:var(--font-display); font-weight:700; font-size:var(--text-md);
  line-height:1.25; letter-spacing:-.01em; }
.sub { color:var(--color-muted); font-size:var(--text-xs); }
.price { font-family:var(--font-num); font-weight:600; font-size:var(--text-md);
  white-space:nowrap; letter-spacing:-.01em; }
/* .rp 는 호가 아래 보조줄과 표 안 인라인 수치에 함께 쓰인다 — 기본은 인라인 */
.rp { font-family:var(--font-body); font-size:var(--text-xs); font-weight:400;
  color:var(--color-muted); white-space:nowrap; }
.price .rp { display:block; margin-top:var(--space-4xs); }
.rp .down { color:var(--color-good); font-weight:600; }
.rp .up { color:var(--color-warn); font-weight:600; }

/* 등급 — 무지개 배지 대신 한 색의 농도 */
.badge { display:inline-block; min-width:1.5em; text-align:center;
  font-family:var(--font-num); font-size:var(--text-xs); font-weight:700; letter-spacing:.02em;
  padding:.15em .3em; border:1px solid currentColor; border-radius:var(--radius-sm); }
.badge.S { color:var(--color-paper); background:var(--color-accent); border-color:var(--color-accent); }
.badge.A { color:var(--color-accent); }
.badge.B { color:var(--color-ink); }
.badge.C { color:var(--color-muted); }
.badge.D { color:var(--color-muted); border-color:var(--color-neutral); }
tbody td:first-child b { font-family:var(--font-num); font-size:var(--text-md); font-weight:600; }

/* 태그 — 칠하지 않고 괘선으로 */
.tag { display:inline-block; padding:0 .35em; margin-left:var(--space-3xs);
  font-size:var(--text-xs); font-weight:500; letter-spacing:.01em; vertical-align:1px;
  border:1px solid var(--color-rule-2); border-radius:var(--radius-sm); color:var(--color-muted); }
.tag.lease { color:var(--color-warn); border-color:var(--color-warn); }
.tag.good { color:var(--color-good); border-color:var(--color-good); }
.tag.gap { color:var(--color-accent); border-color:var(--color-accent); }
.tag.jgc, .tag.dup { color:var(--color-muted); border-color:var(--color-rule-2); }

.fav { border:0; background:none; cursor:pointer; font-size:var(--text-md); padding:0 var(--space-3xs);
  color:var(--color-rule-2); line-height:1; vertical-align:-1px;
  transition:color var(--dur-short) var(--ease-out); }
.fav:hover { color:var(--color-star); }
.fav.on { color:var(--color-star); }
.fav:active { transform:scale(.92); }

.slope-flat { color:var(--color-good); }
.slope-hill { color:var(--color-warn); }
.slope-steep { color:var(--color-alert); }

/* ── 상세: 중첩 카드 없이 괘선으로만 ────────────── */
tr.detail td { background:var(--color-paper-2); padding:var(--space-md) var(--space-sm);
  border-bottom:2px solid var(--color-rule-2); }
.bars { display:grid; grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));
  gap:var(--space-xs) var(--space-md); margin-bottom:var(--space-md); }
.bar { font-size:var(--text-xs); }
.bar .t { display:flex; justify-content:space-between; align-items:baseline;
  color:var(--color-muted); gap:var(--space-2xs); }
.bar .t b { font-family:var(--font-num); color:var(--color-ink); font-size:var(--text-sm); }
.bar .g { height:3px; background:var(--color-rule); overflow:hidden; margin-top:var(--space-3xs); }
.bar .g i { display:block; height:100%; background:var(--color-accent); }
.hbtn { border:1px solid var(--color-neutral); background:none; color:var(--color-muted);
  cursor:pointer; width:1.05rem; height:1.05rem; line-height:1; border-radius:50%;
  font-size:var(--text-xs); padding:0; vertical-align:1px; font-weight:700;
  transition:color var(--dur-short) var(--ease-out), border-color var(--dur-short) var(--ease-out); }
.hbtn:hover { border-color:var(--color-accent); color:var(--color-accent); }
.hbtn:active { background:var(--color-accent-2); }
.help { display:none; margin-top:var(--space-2xs); padding:var(--space-2xs) 0 var(--space-2xs) var(--space-xs);
  border-left:2px solid var(--color-rule-2); font-size:var(--text-xs); line-height:1.7;
  color:var(--color-muted); }
.help.open { display:block; }
.help b { color:var(--color-ink); }
.help .hw { color:var(--color-warn); }
.facts { display:grid; grid-template-columns:repeat(auto-fill,minmax(11rem,1fr));
  gap:var(--space-xs) var(--space-md); margin:0 0 var(--space-md);
  padding:var(--space-sm) 0; border-top:1px solid var(--color-rule);
  border-bottom:1px solid var(--color-rule); }
.fact { font-size:var(--text-xs); }
.fact b { display:block; font-size:var(--text-sm); font-weight:600; margin-top:var(--space-4xs); }
.fact .k { color:var(--color-muted); letter-spacing:.03em; }
.fact.warn b { color:var(--color-warn); }
.fact.good b { color:var(--color-good); }
.desc { font-size:var(--text-sm); margin:var(--space-2xs) 0; padding-left:var(--space-xs);
  border-left:2px solid var(--color-rule-2); color:var(--color-ink); max-width:72ch; }
.links { margin-top:var(--space-sm); display:flex; flex-wrap:wrap; gap:var(--space-2xs); }
.links a { display:inline-block; padding:var(--space-3xs) var(--space-xs);
  border:1px solid var(--color-accent); border-radius:var(--radius-sm);
  background:var(--color-accent); color:var(--color-paper); text-decoration:none;
  font-size:var(--text-sm); font-weight:600; white-space:nowrap;
  transition:background-color var(--dur-short) var(--ease-out), color var(--dur-short) var(--ease-out); }
.links a:hover { background:none; color:var(--color-accent); }
.links a.ghost { background:none; color:var(--color-accent); }
.links a.ghost:hover { background:var(--color-accent); color:var(--color-paper); }
.links a:active { transform:translateY(1px); }
.f input:disabled, .f select:disabled, .wf input:disabled {
  opacity:.55; cursor:not-allowed; border-bottom-style:dashed; }
.vars { margin-top:var(--space-sm); border-top:1px solid var(--color-rule); padding-top:var(--space-2xs); }
.vars .v { font-size:var(--text-xs); color:var(--color-muted); padding:var(--space-3xs) 0; }
.vars .v a { color:var(--color-accent); }
.empty { text-align:center; padding:var(--space-2xl) 0; color:var(--color-muted); }

/* ── Ft4 콜로폰 ────────────────────────────────── */
.colophon { margin-top:var(--space-2xl); padding-top:var(--space-md);
  border-top:1px solid var(--color-rule-2); font-size:var(--text-xs); line-height:1.75;
  color:var(--color-muted); }
.colophon h2 { font-family:var(--font-display); font-size:var(--text-md); font-weight:700;
  color:var(--color-ink); margin:0 0 var(--space-2xs); }
.colophon__grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));
  gap:var(--space-sm) var(--space-lg); }
.colophon b { color:var(--color-ink); font-weight:600; }
.colophon .hw { color:var(--color-warn); }
.colophon p { margin:0 0 var(--space-2xs); max-width:62ch; }

/* ── 모바일 ────────────────────────────────────── */
.mobar { display:none; gap:var(--space-2xs); margin:var(--space-sm) 0 var(--space-3xs); }
.msort { flex:1; min-width:0; padding:var(--space-2xs) 0; border:0;
  border-bottom:1px solid var(--color-neutral); background:none; color:var(--color-ink);
  font-family:var(--font-body); font-size:var(--text-sm); border-radius:0; }
@media (max-width:900px){
  .wrap { padding:0 var(--space-sm) var(--space-xl); }
  .masthead { padding-top:var(--space-md); text-align:left; }
  .tabs { gap:var(--space-sm); padding-top:var(--space-sm); }
  .wbtn { margin-left:0 !important; }
  #grpBtn, #favBtn { margin-left:0 !important; }
  .mobar { display:flex; align-items:flex-end; }
  .mbtn { flex:0 0 auto; }
  .filters { display:none; }
  .filters.open { display:flex; }
  .f { flex:1 1 44%; min-width:0; }
  .f input, .f select, .f .msbtn { min-width:0; width:100%; }
  .f.chk { flex:1 1 100%; }
  /* 표 → 카탈로그 슬립: 괘선으로 구분된 항목 */
  thead { display:none; }
  tbody, tbody tr, tbody td { display:block; }
  tbody tr.row { padding:var(--space-xs) 0; border-bottom:1px solid var(--color-rule);
    position:relative; }
  tbody tr.row td { border:0; padding:0; }
  tbody tr.row td:nth-child(1) { position:absolute; right:0; top:var(--space-xs); }
  tbody tr.row td:nth-child(2) { padding-right:5.5rem; }
  tbody tr.row td:nth-child(3) { margin-top:var(--space-3xs); }
  tbody tr.row td:nth-child(6) { display:inline-block; margin:var(--space-3xs) var(--space-2xs) 0 0;
    font-size:var(--text-xs); color:var(--color-muted); }
  tbody tr.row td:nth-child(10),
  tbody tr.row td:nth-child(11) { display:inline-block; font-size:var(--text-xs);
    margin:var(--space-3xs) var(--space-2xs) 0 0; }
  /* 라벨과 값은 한 단위 — 사이에서 줄이 갈리면 표가 아니라 파편으로 읽힌다 */
  .hide-m { display:inline-block !important; font-size:var(--text-xs); color:var(--color-muted);
    white-space:nowrap; margin:var(--space-3xs) var(--space-2xs) 0 0; }
  .hide-m::before { content:attr(data-l) " "; color:var(--color-muted); opacity:.72; }
  .hide-m:empty { display:none !important; }
  tbody tr.sub-row { padding-left:var(--space-sm); }
  tbody tr.sub-row td:first-child { padding-left:0; }
  tr.detail { display:block; }
  tr.detail td { display:block; padding:var(--space-sm) 0; }
  .bars { grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:var(--space-2xs) var(--space-sm); }
  .facts { grid-template-columns:minmax(0,1fr) minmax(0,1fr); }
  .links a { flex:1 1 auto; text-align:center; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition-duration:.01ms !important; animation-duration:.01ms !important; }
}
</style>
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <h1>__TITLE__</h1>
    <p class="issue"><b>__GENERATED__</b> 기준 · 네이버 부동산 · 동일매물 묶음 · 실거래 포함</p>
  </header>
  <div class="tabs">
    <button class="tab" data-trade="B2" onclick="setTrade('B2')">월세 <span id="cntB2"></span></button>
    <button class="tab on" data-trade="A1" onclick="setTrade('A1')">매매 <span id="cntA1"></span></button>
    <button class="wbtn" id="favBtn" onclick="toggleFavView()">☆ 관심 <span id="favCnt"></span></button>
    <button class="wbtn" id="grpBtn" onclick="toggleGroup()">단지별 묶기</button>
    <button class="wbtn" onclick="document.getElementById('wpanel').classList.toggle('open')">가중치 <span id="wsum"></span></button>
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
    <div class="f" id="fRentBox" style="display:none"><label>월세 최대(만원)</label><input type="number" id="fRent" placeholder="100"></div>
    <div class="f" id="fWarBox" style="display:none"><label>보증금 최대(억)</label><input type="number" id="fWar" step="0.5" placeholder="3"></div>
    <div class="f" id="fDealMinBox"><label>매매가 최소(억)</label><input type="number" id="fDealMin" step="0.5" placeholder="8"></div>
    <div class="f" id="fDealBox"><label>매매가 최대(억)</label><input type="number" id="fDeal" step="0.5" placeholder="14"></div>
    <div class="f"><label>전용면적 최소(㎡)</label><input type="number" id="fArea" placeholder="59"></div>
    <div class="f"><label>세대수 최소</label><input type="number" id="fHh" placeholder="300"></div>
    <div class="f"><label>역도보 최대(분)</label><input type="number" id="fWalk" placeholder="∞"></div>
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
    <div class="f"><label>등록 N일 이내</label><input type="number" id="fListed" placeholder="∞"></div>
    <div class="f"><label>21년 월거래 최소</label><input type="number" id="fVol" step="0.1" value="1" placeholder="0"></div>
    <div class="f"><label>평점 최소</label><input type="number" id="fScore" step="0.5" placeholder="0"></div>
    <div class="f chk"><input type="checkbox" id="fNoLease"><label for="fNoLease">임대혼합 제외</label></div>
    <div class="f chk"><input type="checkbox" id="fLowOk"><label for="fLowOk">저층 할인부족 제외</label></div>
    <div class="f chk" id="fNoGapBox"><input type="checkbox" id="fNoGap"><label for="fNoGap">세안고 제외</label></div>
    <div class="f"><label>저장한 필터</label>
      <select id="fPreset" onchange="loadPreset(this.value)"><option value="">선택…</option></select>
    </div>
    <div class="f chk">
      <button class="wreset" onclick="savePreset()">＋ 현재 필터 저장</button>
      <button class="wreset ghost" onclick="deletePreset()">삭제</button>
    </div>
  </div>
  <div id="freshness" class="fresh" style="display:none"></div>
  <div class="mobar">
    <button class="wbtn mbtn" onclick="document.querySelector('.filters').classList.toggle('open')">필터</button>
    <select id="mSort" class="msort" onchange="applyMobileSort(this.value)"></select>
  </div>
  <div class="count" id="count"></div>
  <div class="count" id="defnote" style="margin-top:-6px">기본 필터 적용 중: 용적률 ≤350% · 21년 월거래 ≥1건(2020년 이후 준공 신축은 면제)
    <button class="wreset" onclick="clearDefaults()">기본 필터 해제</button></div>
  <table>
    <thead><tr>
      <th data-k="score_total">평점 <span class="arrow"></span></th>
      <th data-k="complex_name">단지 <span class="arrow"></span></th>
      <th data-k="_price">호가 <span class="arrow"></span></th>
      <th data-k="real_gap_pct" class="hide-m">실거래 대비(동일층) <span class="arrow"></span></th>
      <th data-k="_vol21" class="hide-m">21년 거래(단지) <span class="arrow"></span></th>
      <th data-k="listed_days" class="hide-m">등록일 <span class="arrow"></span></th>
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
  <footer class="colophon" id="mpanel">
    <h2>산정 방식</h2>
    <div class="colophon__grid"><div>
      <b>평점 = Σ(항목점수 0~10 × 가중치) ÷ Σ가중치</b> · 미상 항목은 제외 후 정규화 · 등급 S≥8.5 / A≥7.5 / B≥6.5 / C≥5.5 / D<br><br>
      <b>가격가치</b> — 같은 (시군구·거래유형·면적밴드 59~85/85㎡+) 매물들의 <b>중위 평당가 대비 할인율</b>.
        월세는 보증금+월세×12÷5.5%(전월세전환율)로 환산. 중위가보다 30% 싸면 10점, 같으면 5점, 30% 비싸면 0점. 표본 5건 미만이면 시·도 전체로 폴백.<br>
    </div><div>
      <b>교통</b> — ① 업무지구 70%: 판교·강남·여의도·시청 직선거리, 각 3km 이내 10점→25km 0점 선형, 4곳 평균
        ② 역세권 30%: 최기역 도보 5분 이하 10점→25분 0점. 역 좌표는 OSM 수도권 508개 역. 고속·간선도로·지상철도·하천이 가로막으면 육교·지하도 경유 거리로 계산하고 횡단 1회당 2분 가산.
        <span class="hw">실제 대중교통 소요시간이 아닌 거리 근사.</span><br>
      <b>학군</b> — <b>단지 좌표 반경 실측</b>: 학원 밀집 35%(1km 내 학원 수, 500m 학원가 가점) + 배정 중학교 과밀도 25%(학급당 학생수÷시 평균 — 학군 선호 지역은 전입 수요로 과밀) + 초품아 25%(초등학교 거리, 200m 이내 만점) + 명문·특목고 근접 15%(2km 내 외고·과학고·국제고·주요 자사고).
        <span class="hw">특목고 진학률 원본(학교알리미)은 대량 수집이 불가능해, 진학 성과와 상관이 높은 학원 밀집도·중학교 과밀도로 대체한 추정치입니다.</span><br>
      <b>인프라</b> — <b>단지 좌표 반경 실측</b>(각 20%): 백화점 거리 · 대형마트 1km 개수/거리 · 병원 1km 개수 · 생활편의(편의점 500m + 약국 1km) · 공원 거리(OSM). POI 수집 실패 단지만 시군구 폴백 점수.<br>
      <b>규모·연식</b> — 세대수 60%(300세대 5점~3,000세대+ 10점) + 연식 40%(≤5년 10점→35년+ 3점, 재건축 +1 보정).<br>
      <b>언덕</b> — 단지 중심 5×5 그리드(240m) 고도 평면 피팅 구배%. 위성 DEM 2종(SRTM 2000 / Copernicus 2011~15)의 최솟값 — 옛 지형·건물반영 과대오류 상쇄. &lt;1.5% 평지 10점 ~ 8%+ 급경사 1점.<br><br>
    </div><div>
      <b>등록</b> — 네이버 노출 시작일 기준 경과일. 값이 없으면 이 대시보드가 그 매물을 처음 본 날로 대신하고, 상세의 ‘처음 확인’에 수집 시각(하루 5회)까지 남깁니다. 3일 이내면 ‘신규’.<br><b>기타 표기</b> — 실거래: 네이버 공개 실거래(신고 기준, 반영 지연 있음), 같은 평형(전용면적 최근접 매칭) 최근 3건.
      실거래 대비(동일층): 호가를 <b>같은 층 구분</b>(저층 1~3층 / 일반층 4층~)의 최근 실거래 평균과 비교 — 직전 1건은 그 거래가 저층·급매면 왜곡되므로 쓰지 않음. 전세가율·갭: 단지 전세 호가 범위 기준(실거래 아님). 저층 할인율: 1~3층 매물의 호가를 같은 평형 <b>일반층(4층~) 실거래 평균</b>과 비교 — 저층은 채광·소음 탓에 통상 10% 이상 싸므로 그에 못 미치면 '할인부족'으로 표시. 세안고: 매물 설명 키워드 감지. 임대세대: 단지 등록 정보.
      부분임대(세대분리 원룸) 매물은 키워드+가격 정합성 검사로 자동 제외.
    </div></div>
  </footer>
</div>
<script>
const DATA = __DATA__;
const GENERATED_AT = "__GENERATED__";
function hardReload(){ location.href = location.pathname + "?t=" + Date.now(); }
(function checkFreshness(){
  // 정적 페이지라 브라우저가 옛 HTML 을 캐시하면 사라진 매물이 계속 보인다.
  // 갱신은 3시간마다 도므로 6시간 넘게 오래된 화면이면 캐시를 의심하고 알린다.
  const gen = new Date(GENERATED_AT.replace(/-/g, "/"));
  const hrs = (Date.now() - gen.getTime()) / 3600000;
  if (!(hrs > 6)) return;
  const el = document.getElementById("freshness");
  el.style.display = "";
  el.innerHTML = "이 화면은 " + Math.floor(hrs) + "시간 전 데이터입니다. 브라우저에 캐시된 옛 페이지일 수 있어요. " +
    '<button class="wreset" onclick="hardReload()">최신으로 새로고침</button>';
})();
const DEFAULT_WEIGHTS = __WEIGHTS_JSON__;
const SCORE_LABELS = {value:"가격가치", transit:"교통", school:"학군", infra:"인프라", scale_age:"규모·연식", slope:"언덕"};
// 항목별 산정 방식 — 점수 바의 ? 아이콘에 붙는다
const SCORE_HELP = {
  value: "같은 시군구·거래유형·면적밴드(59~85 / 85㎡+) 매물들의 <b>중위 평당가 대비 할인율</b>. 월세는 보증금+월세×12÷5.5%(전월세전환율)로 환산해 비교합니다. 중위가보다 30% 싸면 10점, 같으면 5점, 30% 비싸면 0점. 표본 5건 미만이면 시·도 전체로 폴백.",
  transit: "<b>업무지구 70%</b>: 판교·강남·여의도·시청까지 직선거리, 각 3km 이내 10점 → 25km 0점 선형, 4곳 평균.<br><b>역세권 30%</b>: 최기역 도보 5분 이하 10점 → 25분 0점. 역 좌표는 OSM 수도권 508개 역. 도보시간 = 경로거리×1.35 ÷ 67m/분이며, 단지와 역 사이를 <b>고속·간선도로 / 지상철도 / 하천이 가로막으면</b> 가장 가까운 육교·지하도를 경유하는 거리로 바꾸고 횡단 1회당 2분을 더합니다(터널 구간은 장애물로 보지 않음).<br><span class='hw'>실제 대중교통 소요시간(환승·배차)이 아닌 거리 근사입니다.</span>",
  school: "<b>단지 반경 실측</b> — 학원 밀집 35%(1km 내 학원 수, 500m 학원가 가점) + 배정 중학교 과밀도 25%(학급당 학생수÷시 평균, 학군 선호지는 전입 수요로 과밀) + 초품아 25%(초등학교 거리, 200m 이내 만점) + 명문·특목고 근접 15%(2km 내 외고·과학고·국제고·주요 자사고).<br><span class='hw'>특목고 진학률 원본(학교알리미)은 대량 수집이 불가능해, 진학 성과와 상관이 높은 지표로 대체한 추정치입니다.</span>",
  infra: "<b>단지 반경 실측</b>(각 20%) — 백화점 거리 · 대형마트 1km 개수/거리 · 병원 1km 개수 · 생활편의(편의점 500m + 약국 1km) · 공원 거리(OSM 수도권 5,591곳).<br>POI 수집에 실패한 단지만 시군구 평균 점수로 폴백합니다.",
  scale_age: "세대수 60%(300세대 5점 → 3,000세대 이상 10점 구간별) + 연식 40%(5년 이하 10점 → 35년 이상 3점). 재건축 단지는 개발 잠재가치로 +1 보정.",
  slope: "단지 중심 5×5 그리드(240m 범위) 고도에 최소제곱 평면을 피팅한 구배%. 위성 DEM 2종(SRTM 2000년 / Copernicus 2011~15년)에서 각각 구한 뒤 <b>최솟값</b>을 씁니다 — 각각 옛 지형·건물 높이 반영이라는 과대측정 오류가 있어 min이 실지형에 가깝습니다.<br>1.5% 미만 평지 10점 · 3% 완만 8점 · 5% 약한 언덕 6점 · 8% 언덕 3점 · 그 이상 급경사 1점.",
};
const PY = 3.3058, RATE = 0.055;
const NEW_DAYS = 3;   // 이 안에 올라온 매물은 신규로 본다
let WEIGHTS = loadWeights();
let trade = "A1", sortKey = "score_total", sortAsc = false, openRow = null;
let byComplex = true, expandedKey = null;
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
function relDays(d){ return d === 0 ? "오늘" : (d === 1 ? "어제" : d + "일 전"); }

function listedCell(a){
  const d = a.listed_days;
  if (d == null) return "-";
  // 날짜를 그대로 보여주고(정렬 기준과 눈으로 맞춰지도록) 경과일은 툴팁에 둔다
  const ymd = a.listed_date ? a.listed_date.slice(5) : relDays(d);
  return '<span class="rp" title="' + (a.listed_date || "") + ' · ' + relDays(d) + '">'
    + '<span class="'+(d <= NEW_DAYS ? "down" : "")+'">' + ymd + '</span></span>'; }

function volCell(a){
  const v = a.vol_2021;
  if (isNewBuild(a) && (!v || !v.count)) return '<span class="rp">신축</span>';
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
  return a.station_name + " <span class='sub'>" + a.station_walk_min + "분"
    + (a.station_detour ? " 우회" : "") + "</span>"; }

function setTrade(t){ trade = t; openRow = null; expandedKey = null;
  document.querySelectorAll(".tab").forEach(el => el.classList.toggle("on", el.dataset.trade===t));
  document.getElementById("fRentBox").style.display = t==="B2" ? "" : "none";
  document.getElementById("fWarBox").style.display = t==="B2" ? "" : "none";
  document.getElementById("fDealBox").style.display = t==="A1" ? "" : "none";
  document.getElementById("fDealMinBox").style.display = t==="A1" ? "" : "none";
  document.getElementById("fNoGapBox").style.display = t==="A1" ? "" : "none";
  render(); }

const SORT_OPTS = [["score_total","평점 높은순",false],["_price","가격 낮은순",true],
  ["_price","가격 높은순",false],["_ppp","평당가 낮은순",true],["real_gap_pct","저평가순",true],
  ["_vol21","거래 활발순",false],["listed_days","최근 등록순",true],["station_walk_min","역 가까운순",true],
  ["grade_pct","평지순",true],["exclusive_m2","면적 넓은순",false],["use_date","신축순",false],
  ["households","대단지순",false]];
function buildMobileSort(){
  const sel = document.getElementById("mSort");
  sel.innerHTML = SORT_OPTS.map((o,i) => '<option value="'+i+'">'+o[1]+'</option>').join("");
}
function applyMobileSort(i){
  const o = SORT_OPTS[i]; sortKey = o[0]; sortAsc = o[2]; expandedKey = null; render();
}

function toggleGroup(){
  byComplex = !byComplex; expandedKey = null; openRow = null;
  document.getElementById("grpBtn").textContent = byComplex ? "단지별 묶기" : "매물별 보기";
  render();
}

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
  const listedMax = parseFloat(document.getElementById("fListed").value);
  const slopeMax = parseFloat(document.getElementById("fSlope").value);
  const jgc = document.getElementById("fJgc").value;
  const noLease = document.getElementById("fNoLease").checked;
  const lowOk = document.getElementById("fLowOk").checked;
  const noGap = document.getElementById("fNoGap").checked;
  return DATA.filter(a => {
    if (favView) { if (!favs.has(a.article_no)) return false; }
    else if (a.trade_type !== trade) return false;
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
    // 2020년 이후 준공은 2021년에 거래가 없거나 희박한 게 정상 — 거래량 필터 면제
    if (!isNaN(volMin) && !isNewBuild(a) && !(a.vol_2021 && a.vol_2021.per_month >= volMin)) return false;
    if (!isNaN(listedMax) && !(a.listed_days != null && a.listed_days <= listedMax)) return false;
    if (noLease && (a.lease_ratio||0) >= 10) return false;
    if (lowOk && a.low_floor && !a.low_floor.fair) return false;
    if (noGap && a.gap_sale) return false;
    return true;
  });
}

function clearDefaults(){
  ["fFar","fVol"].forEach(id => document.getElementById(id).value = "");
  document.getElementById("defnote").style.display = "none";
  render();
}

const FILTER_IDS = ["fRent","fWar","fDealMin","fDeal","fArea","fHh","fWalk","fFar","fVol","fScore"];
const SELECT_IDS = ["fSlope","fJgc"];
const CHECK_IDS = ["fNoLease","fLowOk","fNoGap"];
let favs = new Set(JSON.parse(localStorage.getItem("hw_favs") || "[]"));
let favView = false;

function saveFavs(){ localStorage.setItem("hw_favs", JSON.stringify([...favs])); updateFavBtn(); }
function updateFavBtn(){
  const n = favs.size;
  // textContent 로 갈아끼우면 내부 span 이 사라져 다음 갱신이 죽는다 — innerHTML 로 통째 재구성
  document.getElementById("favBtn").innerHTML =
    (favView ? "★ 관심" : "☆ 관심") + ' <span id="favCnt">' + (n ? "("+n+")" : "") + '</span>';
}
function toggleFav(e, no){
  e.stopPropagation();
  if (favs.has(no)) favs.delete(no); else favs.add(no);
  saveFavs(); render();
}
function toggleFavView(){
  favView = !favView; expandedKey = null; openRow = null;
  document.getElementById("favBtn").classList.toggle("on", favView);
  updateFavBtn(); render();
}
function favBtnHtml(a){
  const on = favs.has(a.article_no);
  return '<button class="fav'+(on?" on":"")+'" title="관심 매물" aria-label="관심 매물" onclick="toggleFav(event,\''+a.article_no+'\')">'+(on?"★":"☆")+'</button>';
}

function getPresets(){ try { return JSON.parse(localStorage.getItem("hw_presets")||"[]"); } catch(e){ return []; } }
function renderPresets(sel){
  const list = getPresets();
  const el = document.getElementById("fPreset");
  el.innerHTML = '<option value="">선택…</option>' +
    list.map((p,i) => '<option value="'+i+'"'+(sel==i?" selected":"")+'>'+p.name+'</option>').join("");
}
function savePreset(){
  const name = prompt("필터 이름을 입력하세요", "내 조건 " + (getPresets().length+1));
  if (!name) return;
  const st = {name: name, trade: trade, sigus: [...selectedSigu], vals: {}, sels: {}, chks: {}};
  FILTER_IDS.forEach(id => st.vals[id] = document.getElementById(id).value);
  SELECT_IDS.forEach(id => st.sels[id] = document.getElementById(id).value);
  CHECK_IDS.forEach(id => st.chks[id] = document.getElementById(id).checked);
  const list = getPresets(); list.push(st);
  localStorage.setItem("hw_presets", JSON.stringify(list));
  renderPresets(list.length-1);
}
function loadPreset(i){
  if (i === "") return;
  const st = getPresets()[i];
  if (!st) return;
  FILTER_IDS.forEach(id => document.getElementById(id).value = st.vals[id] ?? "");
  SELECT_IDS.forEach(id => document.getElementById(id).value = st.sels[id] ?? "");
  CHECK_IDS.forEach(id => document.getElementById(id).checked = !!st.chks[id]);
  selectedSigu = new Set(st.sigus || []);
  document.querySelectorAll(".msItem").forEach(c => c.checked = selectedSigu.has(c.value));
  document.getElementById("msAll").checked = selectedSigu.size === ALL_SIGUS.length;
  msLabel();
  if (st.trade && st.trade !== trade) setTrade(st.trade); else render();
}
function deletePreset(){
  const el = document.getElementById("fPreset");
  const i = el.value;
  if (i === "") { alert("삭제할 필터를 먼저 선택하세요"); return; }
  const list = getPresets();
  if (!confirm('"'+list[i].name+'" 필터를 삭제할까요?')) return;
  list.splice(i,1);
  localStorage.setItem("hw_presets", JSON.stringify(list));
  renderPresets();
}

function isNewBuild(a){
  const y = parseInt((a.use_date||"").slice(0,4));
  return !isNaN(y) && y >= 2020;
}

function tags(a){
  let t = "";
  if (a.is_jgc) t += '<span class="tag jgc">재건축</span>';
  if ((a.lease_ratio||0) >= 10) t += '<span class="tag lease">임대 '+a.lease_ratio+'%</span>';
  if (a.gap_sale) t += '<span class="tag gap">세안고</span>';
  if (a.dup_count) t += '<span class="tag dup">동일 +'+a.dup_count+'</span>';
  if (a.listed_days != null && a.listed_days <= NEW_DAYS) t += '<span class="tag good">신규</span>';
  if (a.low_floor) t += a.low_floor.fair
    ? '<span class="tag good">저층 -'+a.low_floor.discount_pct+'%</span>'
    : '<span class="tag lease">저층 할인부족 '+(a.low_floor.discount_pct>0?"-":"+")+Math.abs(a.low_floor.discount_pct)+'%</span>';
  return t;
}

function sortVals(x, y){
  let a = x[sortKey], b = y[sortKey];
  if (a==null) a = sortAsc ? Infinity : -Infinity;
  if (b==null) b = sortAsc ? Infinity : -Infinity;
  if (typeof a === "string") return sortAsc ? a.localeCompare(b) : b.localeCompare(a);
  return sortAsc ? a-b : b-a;
}

function articleRow(a, indent){
  const tr = document.createElement("tr");
  tr.className = "row" + (indent ? " sub-row" : "");
  tr.innerHTML =
    '<td><span class="badge '+a.grade+'">'+a.grade+'</span> <b>'+a.score_total.toFixed(1)+'</b>'+favBtnHtml(a)+'</td>' +
    '<td>' + (indent
        ? '<div class="cname">'+(a.bld_dong?a.bld_dong+'동 ':'')+(a.floor_info?a.floor_info+'층':'')+tags(a)+'</div>'
          + '<div class="sub">'+(a.pyeong_name?a.pyeong_name+'타입 · ':'')+(a.realtor||'')+'</div>'
        : '<div class="cname">'+a.complex_name+tags(a)+'</div>'
          + '<div class="sub">'+a.sigu+' '+a.dong+(a.bld_dong?' · '+a.bld_dong+'동':'')+(a.floor_info?' · '+a.floor_info+'층':'')+'</div>')
      + '</td>' +
    '<td class="price">'+priceText(a)+rpText(a)+'</td>' +
    '<td class="hide-m" data-l="실거래대비">'+gapCell(a)+'</td>' +
    '<td class="hide-m" data-l="21년 단지">'+volCell(a)+'</td>' +
    '<td class="hide-m" data-l="등록일">'+listedCell(a)+'</td>' +
    '<td data-l="전용">'+(a.exclusive_m2||"-")+'㎡</td>' +
    '<td class="hide-m" data-l="평당">'+(a._ppp? Math.round(a._ppp/1e4).toLocaleString()+"만":"-")+'</td>' +
    '<td class="hide-m" data-l="세대">'+(indent ? "" : (a.households||"-"))+'</td>' +
    '<td class="hide-m" data-l="연식">'+(indent ? "" : ageText(a.use_date))+'</td>' +
    '<td data-l="역">'+(indent ? "" : stationText(a))+'</td>' +
    '<td class="'+slopeCls(a.grade_pct)+'">'+(indent ? "" : (a.slope_label||"미상"))+'</td>';
  tr.onclick = (e) => { e.stopPropagation(); toggleDetail(tr, a); };
  return tr;
}

function groupByComplex(rows){
  const map = new Map();
  rows.forEach(a => {
    const k = a.complex_no + ":" + a.trade_type;
    if (!map.has(k)) map.set(k, {key: k, items: [], head: a});
    const g = map.get(k);
    g.items.push(a);
    if (a.score_total > g.head.score_total) g.head = a;   // 최고 점수 매물이 대표
  });
  const groups = [...map.values()];
  groups.forEach(g => {
    g.items.sort((x,y) => y.score_total - x.score_total);
    const prices = g.items.map(a => a._price);
    const areas = g.items.map(a => a.exclusive_m2 || 0);
    const ppps = g.items.map(a => a._ppp).filter(Boolean);
    g.count = g.items.length;
    g.minPrice = Math.min(...prices); g.maxPrice = Math.max(...prices);
    g.minArea = Math.min(...areas); g.maxArea = Math.max(...areas);
    g.minPpp = ppps.length ? Math.min(...ppps) : 0;
    // 정렬 키는 대표 매물 기준(가격류는 최저가 기준)
    g.score_total = g.head.score_total; g.grade = g.head.grade;
    g.complex_name = g.head.complex_name;
    g._price = g.minPrice; g._ppp = g.minPpp;
    // 면적은 정렬 방향에 맞춰(오름차순=최소, 내림차순=최대) 대표값을 잡아야 직관적
    g.exclusive_m2 = sortAsc ? g.minArea : g.maxArea;
    g.households = g.head.households;
    g.use_date = g.head.use_date; g.station_walk_min = g.head.station_walk_min;
    g.grade_pct = g.head.grade_pct;
    // 실거래 대비는 단지 내 가장 저평가된 매물 기준(21년 거래량은 평형별이라 최대)
    const gaps = g.items.map(a => a.real_gap_pct).filter(v => v != null);
    g.real_gap_pct = gaps.length ? Math.min(...gaps) : null;
    const newest = g.items.filter(a => a.listed_days != null)
                          .sort((x, y) => x.listed_days - y.listed_days)[0];
    g.listed_days = newest ? newest.listed_days : null;
    g.listed_date = newest ? newest.listed_date : null;
    const vols = g.items.map(a => a._vol21).filter(v => v != null);
    g._vol21 = vols.length ? Math.max(...vols) : null;
  });
  return groups;
}

function groupRow(g){
  const a = g.head;
  const tr = document.createElement("tr");
  tr.className = "row grp" + (expandedKey === g.key ? " open" : "");
  tr.dataset.key = g.key;
  const priceRange = g.minPrice === g.maxPrice ? priceText(a)
    : won(g.minPrice) + " ~ " + won(g.maxPrice);
  const areaRange = g.minArea === g.maxArea ? g.minArea + "㎡"
    : g.minArea + "~" + g.maxArea + "㎡";
  tr.innerHTML =
    '<td><span class="badge '+g.grade+'">'+g.grade+'</span> <b>'+g.score_total.toFixed(1)+'</b></td>' +
    '<td><div class="cname"><span class="caret">'+(expandedKey===g.key?"▾":"▸")+'</span> '+a.complex_name+
       ' <span class="tag dup">'+g.count+'건</span>'+tags(a).replace(/<span class="tag dup">[^<]*<\/span>/,"")+'</div>' +
      '<div class="sub">'+a.sigu+' '+a.dong+'</div></td>' +
    '<td class="price">'+priceRange+rpText(a)+'</td>' +
    '<td class="hide-m" data-l="실거래대비">'+gapCell({real_gap_pct: g.real_gap_pct, trade_type: a.trade_type})+'</td>' +
    '<td class="hide-m" data-l="21년 단지">'+volCell({vol_2021: g._vol21 == null ? null : {per_month: g._vol21, count: Math.round(g._vol21*12)}})+'</td>' +
    '<td class="hide-m" data-l="등록일">'+listedCell({listed_days: g.listed_days, listed_date: g.listed_date})+'</td>' +
    '<td data-l="전용">'+areaRange+'</td>' +
    '<td class="hide-m" data-l="평당">'+(g.minPpp? Math.round(g.minPpp/1e4).toLocaleString()+"만~":"-")+'</td>' +
    '<td class="hide-m" data-l="세대">'+(a.households||"-")+'</td>' +
    '<td class="hide-m" data-l="연식">'+ageText(a.use_date)+'</td>' +
    '<td data-l="역">'+stationText(a)+'</td>' +
    '<td class="'+slopeCls(a.grade_pct)+'">'+(a.slope_label||"미상")+'</td>';
  tr.onclick = () => {
    // 재렌더하면 위쪽(다른 단지의 펼침·상세)이 접히며 높이가 줄어 클릭한 행이
    // 화면 밖으로 밀려난다. 클릭 전 화면 위치를 기억했다가 그대로 되돌린다.
    const before = tr.getBoundingClientRect().top;
    expandedKey = (expandedKey === g.key) ? null : g.key;
    openRow = null;
    render();
    const el = document.querySelector('tr.grp[data-key="' + g.key + '"]');
    if (el) {
      const after = el.getBoundingClientRect().top;
      if (Math.abs(after - before) > 1) window.scrollBy(0, after - before);
    }
  };
  return tr;
}

function render(){
  const rows = filtered();
  const tb = document.getElementById("tbody");
  tb.innerHTML = "";
  document.querySelectorAll("thead th").forEach(th => {
    th.querySelector(".arrow").textContent = th.dataset.k===sortKey ? (sortAsc?"▲":"▼") : ""; });
  document.getElementById("empty").style.display = rows.length ? "none" : "";
  const frag = document.createDocumentFragment();

  if (byComplex) {
    const groups = groupByComplex(rows).sort(sortVals);
    document.getElementById("count").textContent =
      groups.length.toLocaleString() + "개 단지 · " + rows.length.toLocaleString() + "건";
    groups.slice(0, 300).forEach(g => {
      frag.appendChild(groupRow(g));
      if (expandedKey === g.key) g.items.forEach(a => frag.appendChild(articleRow(a, true)));
    });
    tb.appendChild(frag);
    if (groups.length > 300) {
      const tr = document.createElement("tr");
      tr.innerHTML = '<td colspan="12" class="sub" style="text-align:center">상위 300개 단지만 표시 — 필터를 좁혀보세요</td>';
      tb.appendChild(tr);
    }
    return;
  }

  rows.sort(sortVals);
  document.getElementById("count").textContent = rows.length.toLocaleString() + "건";
  rows.slice(0, 500).forEach(a => frag.appendChild(articleRow(a, false)));
  tb.appendChild(frag);
  if (rows.length > 500) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="12" class="sub" style="text-align:center">상위 500건만 표시 — 필터를 좁혀보세요</td>';
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
  const before = tr.getBoundingClientRect().top;
  const fix = () => {
    const after = tr.getBoundingClientRect().top;
    if (Math.abs(after - before) > 1) window.scrollBy(0, after - before);
  };
  if (openRow) { openRow.remove(); if (openRow._for === tr) { openRow = null; fix(); return; } }
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
    (vol ? fact("2021년 거래량(단지)", vol.count + "건 · 월 " + vol.per_month + "건",
                vol.per_month >= 1 ? "good" : (vol.count === 0 ? "warn" : "")) : "") +
    (vol && vol.count_59 != null ? fact("2021년 59㎡+ 거래", vol.count_59 + "건 · 월 " + vol.per_month_59 + "건") : "") +
    (a.vol_2021_pyeong ? fact("2021년 이 평형", a.vol_2021_pyeong.count + "건 · 월 " + a.vol_2021_pyeong.per_month + "건") : "") +
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
    fact("등록", a.listed_days != null
        ? (a.listed_days === 0 ? "오늘" : a.listed_days + "일 전")
          + (a.listed_date ? " (" + a.listed_date + ")" : "")
        : null, a.listed_days != null && a.listed_days <= NEW_DAYS ? "good" : "") +
    fact("처음 확인", a.first_seen ? a.first_seen.replace("T", " ") : null) +
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
  d.innerHTML = '<td colspan="12">' +
    '<div class="bars">'+bars+'</div>' +
    '<div class="facts">'+facts+'</div>' +
    (a.description ? '<div class="desc">'+a.description+'</div>' : '') +
    '<div class="sub">'+[a.direction?("향: "+a.direction):null, a.realtor].filter(Boolean).join(" · ")+'</div>' +
    '<div class="links"><a href="'+newland+'" target="_blank" rel="noopener">네이버 부동산에서 보기</a>' +
    '<a class="ghost" href="'+finland+'" target="_blank" rel="noopener">모바일 매물 페이지</a></div>' +
    vars + '</td>';
  tr.after(d); openRow = d; fix();
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
    else { sortKey = k; sortAsc = (k==="complex_name"||k==="_price"||k==="_ppp"||k==="grade_pct"||k==="station_walk_min"||k==="real_gap_pct"||k==="listed_days"); }
    render();
  }));
  buildWeightPanel();
  buildMobileSort();
  renderPresets();
  updateFavBtn();
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
            "station_name", "station_m", "station_walk_min", "station_detour",
            "real_prices", "real_summary", "vol_2021", "low_floor",
            "listed_days", "listed_date", "first_seen", "exposure_date", "vol_2021_pyeong", "real_gap_pct", "real_gap_basis", "jeonse_min", "jeonse_max",
            "pyeong_name", "pyeong_households", "poi")})
    html = (TEMPLATE
            .replace("__TITLE__", cfg["web"]["title"])
            .replace("__GENERATED__", time.strftime("%Y-%m-%d %H:%M"))
            .replace("__WEIGHTS_JSON__", json.dumps(cfg["score_weights"]))
            .replace("__DATA__", json.dumps(slim, ensure_ascii=False)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
