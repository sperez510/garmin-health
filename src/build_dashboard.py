"""
build_dashboard.py
Lee data/garmin_data.json y genera docs/index.html (GitHub Pages)
Uso: python src/build_dashboard.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

DATA_FILE  = Path("data/garmin_data.json")
OUTPUT_DIR = Path("docs")
OUTPUT_FILE = OUTPUT_DIR / "index.html"

OUTPUT_DIR.mkdir(exist_ok=True)

# ── Load data ──────────────────────────────────────────────────────────────────
if not DATA_FILE.exists():
    print(f"ERROR: {DATA_FILE} no encontrado. Ejecuta primero fetch_garmin.py")
    sys.exit(1)

raw = json.loads(DATA_FILE.read_text())

# ── Process & normalize ────────────────────────────────────────────────────────
def normalize_sleep(records):
    out = []
    for r in records:
        total = (r.get("deep_seconds",0) + r.get("light_seconds",0) + r.get("rem_seconds",0))
        out.append({
            "date":  r["date"],
            "total": round(total/3600, 2),
            "deep":  round(r.get("deep_seconds",0)/60),
            "rem":   round(r.get("rem_seconds",0)/60),
            "light": round(r.get("light_seconds",0)/60),
            "score": r.get("score"),
            "resp":  r.get("avg_respiration"),
            "hr":    r.get("avg_hr"),
            "spo2":  r.get("avg_spo2"),
        })
    return sorted(out, key=lambda x: x["date"])

def normalize_hrv(records):
    out = []
    for r in records:
        out.append({
            "date":       r["date"],
            "weekly_avg": r.get("weekly_avg"),
            "last_night": r.get("last_night"),
            "status":     r.get("status", "").upper(),
        })
    return sorted(out, key=lambda x: x["date"])

def normalize_readiness(records):
    daily = {}
    for r in records:
        d = r.get("date","")
        if d:
            daily[d] = r
    return [v for k,v in sorted(daily.items())]

def normalize_hr(records):
    return sorted(records, key=lambda x: x["date"])

def normalize_bb(records):
    return sorted(records, key=lambda x: x["date"])

sleep_data      = normalize_sleep(raw.get("sleep", []))
hrv_data        = normalize_hrv(raw.get("hrv", []))
readiness_data  = normalize_readiness(raw.get("readiness", []))
hr_data         = normalize_hr(raw.get("heart_rate", []))
bb_data         = normalize_bb(raw.get("body_battery", []))
stress_data     = sorted(raw.get("stress", []), key=lambda x: x["date"])
activities      = sorted(raw.get("activities", []), key=lambda x: x.get("date",""), reverse=True)

fetched_at = raw.get("meta", {}).get("fetched_at", date.today().isoformat())
user_name  = (raw.get("user_profile") or {}).get("full_name", "Sebastián")

# ── Inline JSON for JS ────────────────────────────────────────────────────────
js_data = json.dumps({
    "sleep":     sleep_data,
    "hrv":       hrv_data,
    "readiness": readiness_data,
    "hr":        hr_data,
    "bb":        bb_data,
    "stress":    stress_data,
    "activities": activities[:50],
    "meta": {
        "fetched_at": fetched_at,
        "user_name":  user_name,
        "total_days": len(sleep_data),
    }
}, ensure_ascii=False)

# ── HTML Template ──────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{user_name} · Health Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#060810; --panel:#0d1117; --panel2:#141b24;
  --border:rgba(99,179,237,0.1); --border2:rgba(255,255,255,0.05);
  --text:#e2e8f0; --muted:#4a5568; --muted2:#718096;
  --cyan:#63b3ed; --green:#48bb78; --yellow:#ecc94b;
  --red:#fc8181; --purple:#b794f4; --teal:#4fd1c5; --orange:#f6ad55;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:'IBM Plex Mono',monospace;min-height:100vh;padding:0}}
body::after{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.025) 2px,rgba(0,0,0,0.025) 4px);pointer-events:none;z-index:1000}}
.topnav{{display:flex;align-items:center;justify-content:space-between;padding:14px 32px;border-bottom:1px solid var(--border);background:rgba(6,8,16,0.96);backdrop-filter:blur(8px);position:sticky;top:0;z-index:100}}
.logo-name{{font-size:14px;font-weight:600}} .logo-sub{{font-size:9px;color:var(--muted2);letter-spacing:.15em;text-transform:uppercase;margin-top:2px}}
.nav-meta{{display:flex;align-items:center;gap:20px;font-size:10px;color:var(--muted)}}
.live{{display:inline-flex;align-items:center;gap:5px;color:var(--green)}}
.live::before{{content:'';width:6px;height:6px;background:var(--green);border-radius:50%;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
.main{{display:grid;grid-template-columns:200px 1fr;min-height:calc(100vh - 57px)}}
.sidebar{{border-right:1px solid var(--border);padding:16px 0;position:sticky;top:57px;height:calc(100vh - 57px);overflow-y:auto}}
.sidebar-label{{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);padding:0 16px;margin-bottom:4px;margin-top:16px}}
.nav-item{{display:flex;align-items:center;gap:8px;padding:8px 16px;font-size:11px;color:var(--muted2);cursor:pointer;transition:.15s;border-left:2px solid transparent}}
.nav-item:hover{{background:var(--panel2);color:var(--text)}}
.nav-item.active{{background:rgba(99,179,237,0.08);color:var(--cyan);border-left-color:var(--cyan)}}
.content{{padding:28px 32px;overflow-y:auto}}
.view{{display:none}} .view.active{{display:block}}
.section-title{{display:flex;align-items:baseline;gap:12px;margin-bottom:24px}}
.section-title h2{{font-size:18px;font-weight:600;letter-spacing:-.02em}}
.period{{font-size:10px;color:var(--muted2);letter-spacing:.1em;text-transform:uppercase}}
.grid-4{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}}
.grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px}}
.grid-2-1{{display:grid;grid-template-columns:2fr 1fr;gap:14px;margin-bottom:20px}}
.stat{{background:var(--panel);border:1px solid var(--border2);border-radius:10px;padding:16px;position:relative;overflow:hidden}}
.stat::after{{content:'';position:absolute;top:0;left:0;right:0;height:1px;border-radius:10px 10px 0 0}}
.stat.c-cyan::after{{background:var(--cyan)}} .stat.c-green::after{{background:var(--green)}}
.stat.c-red::after{{background:var(--red)}} .stat.c-yellow::after{{background:var(--yellow)}}
.stat.c-purple::after{{background:var(--purple)}} .stat.c-teal::after{{background:var(--teal)}}
.stat-label{{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}}
.stat-value{{font-size:26px;font-weight:600;letter-spacing:-.03em;line-height:1}}
.stat-unit{{font-size:11px;font-weight:400;color:var(--muted2);margin-left:2px}}
.stat-sub{{font-size:10px;color:var(--muted);margin-top:5px}}
.badge{{position:absolute;top:12px;right:12px;font-size:9px;padding:2px 6px;border-radius:3px}}
.bg{{background:rgba(72,187,120,.15);color:var(--green)}} .bw{{background:rgba(236,201,75,.15);color:var(--yellow)}} .br{{background:rgba(252,129,129,.15);color:var(--red)}}
.panel{{background:var(--panel);border:1px solid var(--border2);border-radius:10px;padding:20px;margin-bottom:20px}}
.panel-title{{font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:var(--muted2);margin-bottom:16px;display:flex;align-items:center;justify-content:space-between}}
.info-tag{{font-size:9px;letter-spacing:0;text-transform:none;padding:2px 8px;background:var(--panel2);border:1px solid var(--border2);border-radius:10px;color:var(--muted)}}
canvas{{display:block}}
.data-table{{width:100%;border-collapse:collapse;font-size:11px}}
.data-table th{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);text-align:left;padding:6px 8px;border-bottom:1px solid var(--border)}}
.data-table td{{padding:7px 8px;border-bottom:1px solid var(--border2);color:var(--muted2);vertical-align:middle}}
.data-table tr:hover td{{background:var(--panel2);color:var(--text)}}
.tag{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;letter-spacing:.04em}}
.tp{{background:rgba(99,179,237,.15);color:var(--cyan)}} .th{{background:rgba(72,187,120,.15);color:var(--green)}}
.tm{{background:rgba(236,201,75,.15);color:var(--yellow)}} .tl{{background:rgba(246,173,85,.15);color:var(--orange)}}
.tpoor{{background:rgba(252,129,129,.15);color:var(--red)}}
.insight-card{{display:flex;gap:12px;padding:12px 14px;background:var(--panel2);border-radius:8px;border-left:3px solid;font-size:11px;line-height:1.55;margin-bottom:8px}}
.ic-crit{{border-color:var(--red)}} .ic-warn{{border-color:var(--yellow)}} .ic-good{{border-color:var(--green)}} .ic-info{{border-color:var(--cyan)}}
.ih{{font-weight:600;font-size:11px;margin-bottom:3px}}
.ic-crit .ih{{color:var(--red)}} .ic-warn .ih{{color:var(--yellow)}} .ic-good .ih{{color:var(--green)}} .ic-info .ih{{color:var(--cyan)}}
.ib{{color:var(--muted2)}}
.mrow{{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--border2);font-size:11px}}
.mrow:last-child{{border:none}} .mk{{color:var(--muted);font-size:10px;letter-spacing:.05em}} .mv{{font-weight:500}}
.chart-legend{{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px;font-size:10px;color:var(--muted)}}
.ll{{display:flex;align-items:center;gap:5px}}
.lb{{width:16px;height:2px;border-radius:1px}}
.sleep-bar{{display:flex;height:10px;border-radius:5px;overflow:hidden;gap:1px}}
.sd{{background:var(--teal)}} .sr{{background:var(--purple)}} .sl{{background:var(--cyan);opacity:.7}}
.goal-card{{background:var(--panel2);border:1px solid var(--border2);border-radius:8px;padding:14px;margin-bottom:12px}}
.gp{{height:4px;background:rgba(255,255,255,.06);border-radius:2px;overflow:hidden;margin:6px 0}}
.gf{{height:100%;border-radius:2px}}
.gm{{display:flex;justify-content:space-between;font-size:9px;color:var(--muted)}}
::-webkit-scrollbar{{width:4px}} ::-webkit-scrollbar-track{{background:transparent}} ::-webkit-scrollbar-thumb{{background:var(--panel2);border-radius:2px}}
@media(max-width:768px){{.main{{grid-template-columns:1fr}}.sidebar{{display:none}}.grid-4{{grid-template-columns:repeat(2,1fr)}}.grid-2,.grid-2-1{{grid-template-columns:1fr}}}}
.update-bar{{background:rgba(99,179,237,.06);border-bottom:1px solid var(--border);padding:6px 32px;font-size:10px;color:var(--muted2);text-align:right}}
</style>
</head>
<body>

<div class="topnav">
  <div>
    <div class="logo-name">{user_name} · Health Dashboard</div>
    <div class="logo-sub">Garmin Epix Gen 2 · Auto-actualizado</div>
  </div>
  <div class="nav-meta">
    <span class="live">Datos en vivo</span>
    <span id="last-update">—</span>
    <span style="color:var(--cyan)">Cali, Colombia</span>
  </div>
</div>

<div class="update-bar">Última actualización: <strong id="update-date">—</strong> · GitHub Actions actualiza cada noche automáticamente</div>

<div class="main">
  <nav class="sidebar">
    <div class="sidebar-label">Vistas</div>
    <div class="nav-item active" onclick="showView('overview')">◈ Resumen</div>
    <div class="nav-item" onclick="showView('hrv')">♥ VFC / HRV</div>
    <div class="nav-item" onclick="showView('sleep')">◑ Sueño</div>
    <div class="nav-item" onclick="showView('readiness')">⚡ Readiness</div>
    <div class="nav-item" onclick="showView('activities')">🏃 Actividades</div>
    <div class="nav-item" onclick="showView('goals')">◎ Metas</div>
    <div class="sidebar-label">Período</div>
    <div class="nav-item active" id="p7"  onclick="setPeriod(7,this)">· 7 días</div>
    <div class="nav-item" id="p30" onclick="setPeriod(30,this)">· 30 días</div>
    <div class="nav-item" id="pAll" onclick="setPeriod(999,this)">· Todo</div>
  </nav>

  <div class="content">

    <!-- OVERVIEW -->
    <div id="view-overview" class="view active">
      <div class="section-title"><h2>Resumen</h2><span class="period" id="ov-period">Últimos 7 días</span></div>
      <div class="grid-4">
        <div class="stat c-cyan"><div class="stat-label">VFC Promedio</div><div class="stat-value" id="kv-hrv">—<span class="stat-unit">ms</span></div><div class="stat-sub" id="kv-hrv-s">—</div><div class="badge" id="kv-hrv-b">—</div></div>
        <div class="stat c-purple"><div class="stat-label">Sueño Promedio</div><div class="stat-value" id="kv-sl">—<span class="stat-unit">h</span></div><div class="stat-sub" id="kv-sl-s">—</div><div class="badge" id="kv-sl-b">—</div></div>
        <div class="stat c-green"><div class="stat-label">Readiness Prom.</div><div class="stat-value" id="kv-tr">—<span class="stat-unit">/100</span></div><div class="stat-sub" id="kv-tr-s">—</div><div class="badge" id="kv-tr-b">—</div></div>
        <div class="stat c-teal"><div class="stat-label">HR Reposo</div><div class="stat-value" id="kv-hr">—<span class="stat-unit">bpm</span></div><div class="stat-sub">Frecuencia en reposo</div></div>
      </div>
      <div class="grid-2-1">
        <div class="panel">
          <div class="panel-title">VFC + Readiness <span class="info-tag" id="ov-chart-label">7 días</span></div>
          <canvas id="ov-chart" height="140"></canvas>
          <div class="chart-legend">
            <div class="ll"><div class="lb" style="background:var(--cyan)"></div>VFC (ms)</div>
            <div class="ll"><div class="lb" style="background:var(--yellow)"></div>Readiness</div>
          </div>
        </div>
        <div class="panel"><div class="panel-title">Estado Actual</div><div id="ov-insights"></div></div>
      </div>
      <div class="panel">
        <div class="panel-title">Historial de Sueño <span class="info-tag" id="sl-tbl-label">7 días</span></div>
        <table class="data-table"><thead><tr><th>Fecha</th><th>Total</th><th>Profundo</th><th>REM</th><th>Ligero</th><th>Distribución</th><th>Resp.</th><th>SpO₂</th></tr></thead>
        <tbody id="sl-tbody"></tbody></table>
      </div>
    </div>

    <!-- HRV -->
    <div id="view-hrv" class="view">
      <div class="section-title"><h2>VFC · HRV</h2><span class="period">Historial completo</span></div>
      <div class="grid-4">
        <div class="stat c-cyan"><div class="stat-label">Prom. 30 días</div><div class="stat-value" id="hv-avg">—<span class="stat-unit">ms</span></div></div>
        <div class="stat c-red"><div class="stat-label">Mínimo 30d</div><div class="stat-value" id="hv-min">—<span class="stat-unit">ms</span></div></div>
        <div class="stat c-green"><div class="stat-label">Máximo 30d</div><div class="stat-value" id="hv-max">—<span class="stat-unit">ms</span></div></div>
        <div class="stat c-yellow"><div class="stat-label">Estado Actual</div><div class="stat-value" id="hv-status" style="font-size:16px">—</div></div>
      </div>
      <div class="panel">
        <div class="panel-title">VFC Diaria <span class="info-tag">Historial completo</span></div>
        <canvas id="hrv-chart" height="160"></canvas>
      </div>
      <div class="grid-2">
        <div class="panel"><div class="panel-title">Calendario VFC (últimos 30d)</div><div id="hrv-cal"></div></div>
        <div class="panel"><div class="panel-title">Correlación VFC → Readiness</div><canvas id="hrv-scatter" height="160"></canvas></div>
      </div>
    </div>

    <!-- SLEEP -->
    <div id="view-sleep" class="view">
      <div class="section-title"><h2>Sueño</h2><span class="period">Historial completo</span></div>
      <div class="grid-4">
        <div class="stat c-purple"><div class="stat-label">Total Prom. 30d</div><div class="stat-value" id="sv-avg">—<span class="stat-unit">h</span></div><div class="stat-sub">Meta: ≥7.5h</div></div>
        <div class="stat c-teal"><div class="stat-label">Profundo Prom.</div><div class="stat-value" id="sv-deep">—<span class="stat-unit">m</span></div><div class="stat-sub">Meta: ≥60 min</div></div>
        <div class="stat c-cyan"><div class="stat-label">REM Promedio</div><div class="stat-value" id="sv-rem">—<span class="stat-unit">m</span></div><div class="stat-sub">Meta: ≥90 min</div></div>
        <div class="stat c-orange"><div class="stat-label">Resp. Nocturna</div><div class="stat-value" id="sv-resp">—<span class="stat-unit">rpm</span></div><div class="stat-sub">Normal: 12–20</div></div>
      </div>
      <div class="panel">
        <div class="panel-title">Duración por noche <span class="info-tag">Profundo · REM · Ligero</span></div>
        <canvas id="sl-chart" height="160"></canvas>
      </div>
    </div>

    <!-- READINESS -->
    <div id="view-readiness" class="view">
      <div class="section-title"><h2>Training Readiness</h2><span class="period">Historial completo</span></div>
      <div class="grid-4">
        <div class="stat c-green"><div class="stat-label">Mejor Score</div><div class="stat-value" id="tr-max">—<span class="stat-unit">/100</span></div><div class="stat-sub" id="tr-max-d">—</div></div>
        <div class="stat c-yellow"><div class="stat-label">Prom. 30d</div><div class="stat-value" id="tr-avg">—<span class="stat-unit">/100</span></div></div>
        <div class="stat c-red"><div class="stat-label">Días LOW/POOR 30d</div><div class="stat-value" id="tr-bad">—<span class="stat-unit">d</span></div></div>
        <div class="stat c-cyan"><div class="stat-label">Score Hoy</div><div class="stat-value" id="tr-today">—<span class="stat-unit">/100</span></div><div class="stat-sub" id="tr-today-l">—</div></div>
      </div>
      <div class="panel">
        <div class="panel-title">Training Readiness diario</div>
        <canvas id="tr-chart" height="150"></canvas>
      </div>
    </div>

    <!-- ACTIVITIES -->
    <div id="view-activities" class="view">
      <div class="section-title"><h2>Actividades</h2><span class="period">Recientes</span></div>
      <div class="panel">
        <div class="panel-title">Últimas actividades registradas</div>
        <table class="data-table"><thead><tr><th>Fecha</th><th>Tipo</th><th>Nombre</th><th>Duración</th><th>Distancia</th><th>HR Avg</th><th>HR Max</th><th>Cal.</th></tr></thead>
        <tbody id="act-tbody"></tbody></table>
      </div>
    </div>

    <!-- GOALS -->
    <div id="view-goals" class="view">
      <div class="section-title"><h2>Metas & Proyección</h2><span class="period">Basado en historial real</span></div>
      <div class="grid-3" id="goals-grid"></div>
      <div class="panel">
        <div class="panel-title">Plan de entrenamiento según VFC actual</div>
        <table class="data-table">
          <thead><tr><th>VFC</th><th>Estado</th><th>Natación</th><th>Series</th><th>Descanso</th><th>Intensidad</th></tr></thead>
          <tbody>
            <tr><td style="color:var(--red)">&lt;40ms</td><td><span class="tag tpoor">POOR</span></td><td>No nadar</td><td>—</td><td>—</td><td style="color:var(--red)">Solo movilidad</td></tr>
            <tr><td style="color:var(--orange)">40–55ms</td><td><span class="tag tl">LOW</span></td><td>Técnica solo</td><td>6×34m</td><td>2:00</td><td style="color:var(--orange)">Z1 &lt;120bpm</td></tr>
            <tr id="tr-current-row"><td style="color:var(--yellow)">56–70ms</td><td><span class="tag tm">MODERATE</span></td><td>Base aeróbica</td><td>10×34m</td><td>1:45</td><td style="color:var(--yellow)">Z1–Z2 120–140bpm</td></tr>
            <tr><td style="color:var(--green)">71–85ms</td><td><span class="tag th">HIGH</span></td><td>Volumen</td><td>12×34m</td><td>1:30</td><td style="color:var(--green)">Z2 130–145bpm</td></tr>
            <tr><td style="color:var(--cyan)">≥86ms</td><td><span class="tag tp">PRIME</span></td><td>Intervalos</td><td>10×50m</td><td>1:15</td><td style="color:var(--cyan)">Z3–Z4 145–170bpm</td></tr>
          </tbody>
        </table>
        <div id="goals-swim-advice" style="margin-top:12px;padding:10px;border-radius:6px;font-size:10px;"></div>
      </div>
    </div>

  </div>
</div>

<script>
const D = {js_data};

// ── Init ──────────────────────────────────────────────────────────────────────
document.getElementById('update-date').textContent = D.meta.fetched_at;
document.getElementById('last-update').textContent = 'Actualizado: ' + D.meta.fetched_at;

let currentPeriod = 7;

function getSlice(arr, days) {{
  if (days >= 999) return arr;
  return arr.slice(-days);
}}

function avg(a) {{ return a.length ? Math.round(a.reduce((s,v)=>s+v,0)/a.length) : 0; }}
function avgF(a) {{ return a.length ? (a.reduce((s,v)=>s+v,0)/a.length).toFixed(1) : '—'; }}

// ── Navigation ────────────────────────────────────────────────────────────────
function showView(name) {{
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>{{
    if(n.getAttribute('onclick')===`showView('${{name}}'`) n.classList.add('active');
    else if(n.getAttribute('onclick')&&n.getAttribute('onclick').startsWith('showView')) n.classList.remove('active');
  }});
  document.getElementById('view-'+name).classList.add('active');
  setTimeout(()=>renderView(name),50);
}}

function setPeriod(days, el) {{
  currentPeriod = days;
  document.querySelectorAll('[id^="p"]').forEach(e=>e.classList.remove('active'));
  el.classList.add('active');
  const labels={{7:'Últimos 7 días',30:'Últimos 30 días',999:'Historial completo'}};
  document.getElementById('ov-period').textContent = labels[days];
  document.getElementById('ov-chart-label').textContent = labels[days];
  document.getElementById('sl-tbl-label').textContent = labels[days];
  renderView('overview');
}}

function renderView(n) {{
  if(n==='overview') renderOverview();
  else if(n==='hrv') renderHRV();
  else if(n==='sleep') renderSleep();
  else if(n==='readiness') renderReadiness();
  else if(n==='activities') renderActivities();
  else if(n==='goals') renderGoals();
}}

// ── Canvas helpers ────────────────────────────────────────────────────────────
function sc(id) {{
  const c=document.getElementById(id); if(!c) return null;
  const W=c.parentElement.clientWidth-40, H=parseInt(c.getAttribute('height')||150);
  c.width=W; c.height=H;
  const ctx=c.getContext('2d'); ctx.clearRect(0,0,W,H);
  return {{ctx,W,H}};
}}

function grid(ctx,W,H,pt,rows=4) {{
  ctx.strokeStyle='rgba(255,255,255,0.04)'; ctx.lineWidth=1;
  for(let i=0;i<=rows;i++) {{ const y=pt+(H-pt*2)*i/rows; ctx.beginPath();ctx.moveTo(pt,y);ctx.lineTo(W-pt,y);ctx.stroke(); }}
}}

function line(ctx,pts,color,w=2,dash=false) {{
  if(!pts.length) return; ctx.save();
  ctx.strokeStyle=color;ctx.lineWidth=w;ctx.lineJoin='round';ctx.lineCap='round';
  if(dash) ctx.setLineDash([4,4]);
  ctx.beginPath(); pts.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y)); ctx.stroke(); ctx.restore();
}}

// ── Overview ──────────────────────────────────────────────────────────────────
function renderOverview() {{
  const sl = getSlice(D.sleep, currentPeriod);
  const hv = getSlice(D.hrv, currentPeriod);
  const tr = getSlice(D.readiness, currentPeriod);
  const hr = getSlice(D.hr, currentPeriod);

  const hvVals = hv.map(r=>r.weekly_avg||r.last_night).filter(Boolean);
  const slVals = sl.map(r=>r.total).filter(Boolean);
  const trVals = tr.map(r=>r.score).filter(v=>v!=null);
  const hrVals = hr.map(r=>r.resting).filter(Boolean);

  const hA=avg(hvVals), sA=parseFloat(avgF(slVals)), tA=avg(trVals), hR=avg(hrVals);

  document.getElementById('kv-hrv').innerHTML=`${{hA}}<span class="stat-unit">ms</span>`;
  document.getElementById('kv-hrv-s').textContent=`Status: ${{hv[hv.length-1]?.status||'—'}}`;
  const hb=document.getElementById('kv-hrv-b');
  if(hA>=75){{hb.textContent='↑ GOOD';hb.className='badge bg';}}
  else if(hA>=55){{hb.textContent='→ OK';hb.className='badge bw';}}
  else{{hb.textContent='↓ LOW';hb.className='badge br';}}

  document.getElementById('kv-sl').innerHTML=`${{avgF(slVals)}}<span class="stat-unit">h</span>`;
  document.getElementById('kv-sl-s').textContent=`Profundo prom: ${{avg(sl.map(r=>r.deep).filter(Boolean))}}m`;
  const sb=document.getElementById('kv-sl-b');
  if(sA>=7.5){{sb.textContent='✓ META';sb.className='badge bg';}}
  else if(sA>=6){{sb.textContent='→ OK';sb.className='badge bw';}}
  else{{sb.textContent='↓ BAJO';sb.className='badge br';}}

  document.getElementById('kv-tr').innerHTML=`${{tA}}<span class="stat-unit">/100</span>`;
  const last=tr[tr.length-1];
  document.getElementById('kv-tr-s').textContent=last?.level||'—';
  const tb=document.getElementById('kv-tr-b');
  if(tA>=75){{tb.textContent='HIGH';tb.className='badge bg';}}
  else if(tA>=55){{tb.textContent='MOD';tb.className='badge bw';}}
  else{{tb.textContent='LOW';tb.className='badge br';}}

  document.getElementById('kv-hr').innerHTML=`${{hR||'—'}}<span class="stat-unit">bpm</span>`;

  // Chart
  const cv=sc('ov-chart'); if(!cv) return; const {{ctx,W,H}}=cv;
  const pad={{t:20,b:28,l:32,r:12}}; const PW=W-pad.l-pad.r, PH=H-pad.t-pad.b;
  grid(ctx,W,H,pad.t);
  const dates=[...new Set([...hv.map(r=>r.date),...tr.map(r=>r.date)])].sort();
  const hvByDate=Object.fromEntries(hv.map(r=>[r.date,r.weekly_avg||r.last_night]));
  const trByDate=Object.fromEntries(tr.map(r=>[r.date,r.score]));
  const hvPts=dates.map((d,i)=>hvByDate[d]?{{x:pad.l+(i/(dates.length-1||1))*PW,y:pad.t+PH-(hvByDate[d]-20)/80*PH}}:null).filter(Boolean);
  const trPts=dates.map((d,i)=>trByDate[d]!=null?{{x:pad.l+(i/(dates.length-1||1))*PW,y:pad.t+PH-(trByDate[d]/100)*PH}}:null).filter(Boolean);
  if(hvPts.length>1){{
    ctx.beginPath();ctx.moveTo(hvPts[0].x,H-pad.b);hvPts.forEach(p=>ctx.lineTo(p.x,p.y));ctx.lineTo(hvPts[hvPts.length-1].x,H-pad.b);ctx.closePath();
    const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,'rgba(99,179,237,0.15)');g.addColorStop(1,'transparent');ctx.fillStyle=g;ctx.fill();
    line(ctx,hvPts,'rgba(99,179,237,0.9)',2);
  }}
  if(trPts.length>1) line(ctx,trPts,'rgba(236,201,75,0.7)',1.5,true);
  ctx.font='9px IBM Plex Mono';ctx.fillStyle='rgba(113,128,150,0.7)';ctx.textAlign='center';
  const step=Math.ceil(dates.length/8);
  dates.forEach((d,i)=>{{if(i%step!==0)return;ctx.fillText(d.slice(5),pad.l+(i/(dates.length-1||1))*PW,H-2);}});
  ctx.textAlign='right';
  [20,40,60,80,100].forEach(v=>ctx.fillText(v,pad.l-4,pad.t+PH-(v-20)/80*PH+3));

  // Insights
  const ins=document.getElementById('ov-insights'); ins.innerHTML='';
  if(last) {{
    const hv2=hv[hv.length-1]; const sl2=sl[sl.length-1];
    const hvV=hv2?.weekly_avg||hv2?.last_night;
    if(hvV&&hvV<55) ins.innerHTML+=`<div class="insight-card ic-crit"><div>⚠</div><div><div class="ih">VFC Bajo (${{hvV}}ms)</div><div class="ib">Por debajo de zona saludable. Prioriza descanso.</div></div></div>`;
    else if(hvV&&hvV>=75) ins.innerHTML+=`<div class="insight-card ic-good"><div>✓</div><div><div class="ih">VFC Saludable (${{hvV}}ms)</div><div class="ib">En zona óptima. Buen momento para entrenar.</div></div></div>`;
    else if(hvV) ins.innerHTML+=`<div class="insight-card ic-warn"><div>→</div><div><div class="ih">VFC Moderado (${{hvV}}ms)</div><div class="ib">Zona aceptable. Entrena con control de intensidad.</div></div></div>`;
    if(sl2) {{
      if(sl2.total<6) ins.innerHTML+=`<div class="insight-card ic-crit"><div>🌙</div><div><div class="ih">Sueño Insuficiente (${{sl2.total}}h)</div><div class="ib">Déficit severo. VFC y Readiness se verán afectados mañana.</div></div></div>`;
      else if(sl2.total>=7.5) ins.innerHTML+=`<div class="insight-card ic-good"><div>✓</div><div><div class="ih">Sueño Óptimo (${{sl2.total}}h)</div><div class="ib">Meta alcanzada. Continúa con este patrón.</div></div></div>`;
    }}
    if(last.score<=30) ins.innerHTML+=`<div class="insight-card ic-crit"><div>⚡</div><div><div class="ih">Readiness Crítico (${{last.score}})</div><div class="ib">Solo actividad muy suave hoy.</div></div></div>`;
    else if(last.score>=80) ins.innerHTML+=`<div class="insight-card ic-good"><div>⚡</div><div><div class="ih">Readiness Óptimo (${{last.score}})</div><div class="ib">Día ideal para entrenamiento de calidad.</div></div></div>`;
  }}

  // Sleep table
  const tb=document.getElementById('sl-tbody'); tb.innerHTML='';
  [...sl].reverse().forEach(r=>{{
    const tot=r.deep+r.rem+r.light||1;
    tb.innerHTML+=`<tr>
      <td style="color:var(--text)">${{r.date.slice(5)}}</td>
      <td style="color:${{r.total>=7.5?'var(--green)':r.total>=6?'var(--yellow)':'var(--red)'}}"><b>${{r.total}}h</b></td>
      <td style="color:${{r.deep>=60?'var(--teal)':'var(--muted2)'}}"><b>${{r.deep}}m</b></td>
      <td style="color:${{r.rem>=90?'var(--purple)':'var(--muted2)'}}"><b>${{r.rem}}m</b></td>
      <td>${{r.light}}m</td>
      <td><div class="sleep-bar" style="width:100px"><div class="sd" style="width:${{r.deep/tot*100}}%"></div><div class="sr" style="width:${{r.rem/tot*100}}%"></div><div class="sl" style="width:${{r.light/tot*100}}%"></div></div></td>
      <td style="color:var(--muted)">${{r.resp?r.resp.toFixed(1)+'rpm':'—'}}</td>
      <td style="color:var(--muted)">${{r.spo2?r.spo2+'%':'—'}}</td>
    </tr>`;
  }});
}}

// ── HRV ───────────────────────────────────────────────────────────────────────
function renderHRV() {{
  const last30=D.hrv.slice(-30);
  const vals=last30.map(r=>r.weekly_avg||r.last_night).filter(Boolean);
  document.getElementById('hv-avg').innerHTML=`${{avg(vals)}}<span class="stat-unit">ms</span>`;
  document.getElementById('hv-min').innerHTML=`${{Math.min(...vals)}}<span class="stat-unit">ms</span>`;
  document.getElementById('hv-max').innerHTML=`${{Math.max(...vals)}}<span class="stat-unit">ms</span>`;
  const last=D.hrv[D.hrv.length-1];
  document.getElementById('hv-status').textContent=last?.status||'—';

  const cv=sc('hrv-chart'); if(!cv) return; const {{ctx,W,H}}=cv;
  const d=D.hrv, pad={{t:20,b:28,l:32,r:12}}, PW=W-pad.l-pad.r, PH=H-pad.t-pad.b;
  const hMin=0,hMax=110; grid(ctx,W,H,pad.t);
  d.forEach((r,i)=>{{
    if(!r.weekly_avg&&!r.last_night) return;
    const v=r.weekly_avg||r.last_night;
    const x=pad.l+(i/(d.length-1||1))*PW, y=pad.t+PH-(v-hMin)/(hMax-hMin)*PH;
    if(i>0&&(d[i-1].weekly_avg||d[i-1].last_night)){{
      const pv=d[i-1].weekly_avg||d[i-1].last_night, px=pad.l+((i-1)/(d.length-1||1))*PW, py=pad.t+PH-(pv-hMin)/(hMax-hMin)*PH;
      ctx.strokeStyle=v>=60?'rgba(72,187,120,0.8)':'rgba(252,129,129,0.8)';
      ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(x,y);ctx.stroke();
    }}
    ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);
    ctx.fillStyle=v>=60?'var(--green)':'var(--red)';ctx.fill();
  }});
  ctx.font='9px IBM Plex Mono';ctx.fillStyle='rgba(113,128,150,0.7)';ctx.textAlign='right';
  [0,30,60,90].forEach(v=>ctx.fillText(v,pad.l-4,pad.t+PH-(v-hMin)/(hMax-hMin)*PH+3));
  ctx.textAlign='center';const step=Math.ceil(d.length/10);
  d.forEach((r,i)=>{{if(i%step)return;ctx.fillText(r.date.slice(5),pad.l+(i/(d.length-1||1))*PW,H-2);}});

  // Calendar
  const cal=document.getElementById('hrv-cal'); cal.innerHTML='<div style="display:flex;flex-wrap:wrap;gap:3px">';
  last30.forEach(r=>{{
    const v=r.weekly_avg||r.last_night||0;
    const c=v>=75?'rgba(72,187,120,0.8)':v>=55?'rgba(236,201,75,0.7)':'rgba(252,129,129,0.7)';
    cal.innerHTML+=`<div title="${{r.date}}: ${{v}}ms" style="background:${{c}};color:#0d1117;border-radius:3px;padding:3px 5px;font-size:9px;font-weight:600">${{v}}</div>`;
  }});
  cal.innerHTML+='</div>';

  // Scatter
  const sv=sc('hrv-scatter'); if(!sv) return; const {{ctx:sc2,W:sw,H:sh}}=sv;
  const trByD=Object.fromEntries(D.readiness.map(r=>[r.date,r.score]));
  grid(sc2,sw,sh,20);
  D.hrv.forEach(r=>{{
    const v=r.weekly_avg||r.last_night, tr=trByD[r.date];
    if(!v||!tr) return;
    const x=20+(v/110)*(sw-40), y=sh-20-(tr/100)*(sh-40);
    sc2.beginPath();sc2.arc(x,y,4,0,Math.PI*2);
    sc2.fillStyle=v>=60?'rgba(72,187,120,0.7)':'rgba(252,129,129,0.7)';sc2.fill();
  }});
  sc2.font='9px IBM Plex Mono';sc2.fillStyle='rgba(113,128,150,0.6)';sc2.textAlign='center';
  sc2.fillText('VFC →',sw/2,sh-2);
}}

// ── Sleep ────────────────────────────────────────────────────────────────────
function renderSleep() {{
  const last30=D.sleep.slice(-30);
  document.getElementById('sv-avg').innerHTML=`${{avgF(last30.map(r=>r.total))}}<span class="stat-unit">h</span>`;
  document.getElementById('sv-deep').innerHTML=`${{avg(last30.map(r=>r.deep).filter(Boolean))}}<span class="stat-unit">m</span>`;
  document.getElementById('sv-rem').innerHTML=`${{avg(last30.map(r=>r.rem).filter(Boolean))}}<span class="stat-unit">m</span>`;
  const resps=last30.map(r=>r.resp).filter(Boolean);
  document.getElementById('sv-resp').innerHTML=`${{resps.length?avgF(resps):'—'}}<span class="stat-unit">rpm</span>`;

  const d=D.sleep.slice(-45);
  const cv=sc('sl-chart'); if(!cv) return; const {{ctx,W,H}}=cv;
  const pad={{t:20,b:28,l:32,r:12}}, PW=W-pad.l-pad.r, PH=H-pad.t-pad.b;
  const maxH=12; grid(ctx,W,H,pad.t);
  // 7h line
  ctx.strokeStyle='rgba(113,128,150,0.3)';ctx.lineWidth=1;ctx.setLineDash([4,4]);
  const y7=pad.t+PH-(7/maxH)*PH; ctx.beginPath();ctx.moveTo(pad.l,y7);ctx.lineTo(W-pad.r,y7);ctx.stroke();
  ctx.setLineDash([]);
  const bw=Math.max(3,PW/d.length-2);
  d.forEach((r,i)=>{{
    const x=pad.l+(i/(d.length-1||1))*PW-bw/2;
    let y=pad.t+PH;
    [[r.deep,'rgba(79,209,197,0.85)'],[r.rem,'rgba(183,148,244,0.85)'],[r.light,'rgba(99,179,237,0.6)']].forEach(([m,c])=>{{
      const bh=(m/60/maxH)*PH; y-=bh; ctx.fillStyle=c; ctx.fillRect(x,y,bw,bh);
    }});
  }});
  ctx.font='9px IBM Plex Mono';ctx.fillStyle='rgba(113,128,150,0.7)';ctx.textAlign='center';
  const step=Math.ceil(d.length/10);
  d.forEach((r,i)=>{{if(i%step)return;ctx.fillText(r.date.slice(5),pad.l+(i/(d.length-1||1))*PW,H-2);}});
  ctx.textAlign='right';[0,3,6,9,12].forEach(v=>ctx.fillText(v+'h',pad.l-4,pad.t+PH-(v/maxH)*PH+3));
}}

// ── Readiness ─────────────────────────────────────────────────────────────────
function renderReadiness() {{
  const d=D.readiness; const last30=d.slice(-30);
  const scores=last30.map(r=>r.score).filter(v=>v!=null);
  const maxR=Math.max(...d.map(r=>r.score||0)); const maxRd=d.find(r=>r.score===maxR);
  document.getElementById('tr-max').innerHTML=`${{maxR}}<span class="stat-unit">/100</span>`;
  document.getElementById('tr-max-d').textContent=maxRd?.date||'—';
  document.getElementById('tr-avg').innerHTML=`${{avg(scores)}}<span class="stat-unit">/100</span>`;
  document.getElementById('tr-bad').innerHTML=`${{last30.filter(r=>r.level==='POOR'||r.level==='LOW').length}}<span class="stat-unit">d</span>`;
  const last=d[d.length-1];
  document.getElementById('tr-today').innerHTML=`${{last?.score||'—'}}<span class="stat-unit">/100</span>`;
  document.getElementById('tr-today-l').textContent=last?.level||'—';

  const cv=sc('tr-chart'); if(!cv) return; const {{ctx,W,H}}=cv;
  const pad={{t:20,b:28,l:32,r:12}}, PW=W-pad.l-pad.r, PH=H-pad.t-pad.b;
  grid(ctx,W,H,pad.t);
  // fill
  const valid=d.map((r,i)=>r.score!=null?{{x:pad.l+(i/(d.length-1||1))*PW,y:pad.t+PH-(r.score/100)*PH,l:r.level}}:null).filter(Boolean);
  if(valid.length>1){{
    ctx.beginPath();ctx.moveTo(valid[0].x,H-pad.b);valid.forEach(p=>ctx.lineTo(p.x,p.y));ctx.lineTo(valid[valid.length-1].x,H-pad.b);ctx.closePath();
    const g=ctx.createLinearGradient(0,pad.t,0,H-pad.b);g.addColorStop(0,'rgba(236,201,75,0.12)');g.addColorStop(1,'transparent');ctx.fillStyle=g;ctx.fill();
    valid.forEach((p,i)=>{{
      if(!i) return; const pv=valid[i-1];
      const c={{PRIME:'rgba(99,179,237,.9)',HIGH:'rgba(72,187,120,.9)',MODERATE:'rgba(236,201,75,.8)',LOW:'rgba(246,173,85,.8)',POOR:'rgba(252,129,129,.9)'}}[p.l]||'rgba(255,255,255,0.3)';
      ctx.strokeStyle=c;ctx.lineWidth=2;ctx.lineJoin='round';ctx.beginPath();ctx.moveTo(pv.x,pv.y);ctx.lineTo(p.x,p.y);ctx.stroke();
    }});
  }}
  ctx.font='9px IBM Plex Mono';ctx.fillStyle='rgba(113,128,150,0.7)';ctx.textAlign='right';
  [0,25,50,75,100].forEach(v=>ctx.fillText(v,pad.l-4,pad.t+PH-(v/100)*PH+3));
  ctx.textAlign='center'; const step=Math.ceil(d.length/10);
  d.forEach((r,i)=>{{if(i%step)return;ctx.fillText(r.date.slice(5),pad.l+(i/(d.length-1||1))*PW,H-2);}});
}}

// ── Activities ────────────────────────────────────────────────────────────────
function renderActivities() {{
  const tb=document.getElementById('act-tbody'); tb.innerHTML='';
  const typeLabels={{swimming:'🏊 Natación',running:'🏃 Trote',cycling:'🚴 Bici',walking:'🚶 Caminata',strength_training:'💪 Fuerza',pool_swimming:'🏊 Natación',open_water_swimming:'🌊 Aguas abiertas'}};
  D.activities.slice(0,30).forEach(a=>{{
    const dur=a.duration?Math.round(a.duration/60)+'min':'—';
    const dist=a.distance?((a.distance/1000).toFixed(1)+'km'):'—';
    tb.innerHTML+=`<tr>
      <td style="color:var(--text)">${{a.date.slice(5)}}</td>
      <td><span class="tag tm">${{typeLabels[a.type]||a.type||'—'}}</span></td>
      <td style="color:var(--muted2)">${{a.name||'—'}}</td>
      <td>${{dur}}</td><td>${{dist}}</td>
      <td style="color:${{a.avg_hr&&a.avg_hr>160?'var(--red)':a.avg_hr&&a.avg_hr>140?'var(--yellow)':'var(--green)'}}"><b>${{a.avg_hr||'—'}}</b></td>
      <td style="color:var(--muted)">${{a.max_hr||'—'}}</td>
      <td style="color:var(--muted)">${{a.calories||'—'}}</td>
    </tr>`;
  }});
  if(!D.activities.length) tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:20px">No hay actividades registradas</td></tr>';
}}

// ── Goals ─────────────────────────────────────────────────────────────────────
function renderGoals() {{
  const lastHrv=D.hrv[D.hrv.length-1]; const hvV=lastHrv?.weekly_avg||lastHrv?.last_night||0;
  const lastSl=D.sleep[D.sleep.length-1]; const lastTr=D.readiness[D.readiness.length-1];
  const last30Sl=D.sleep.slice(-30); const avgSl=parseFloat(avgF(last30Sl.map(r=>r.total)));
  const avgDeep=avg(last30Sl.map(r=>r.deep).filter(Boolean));
  const lastHr=D.hr[D.hr.length-1];

  const goals=[
    {{title:'VFC Baseline ≥75ms',val:hvV,max:100,color:'var(--cyan)',unit:'ms',sub:`Prom. 30d: ${{avg(D.hrv.slice(-30).map(r=>r.weekly_avg||r.last_night).filter(Boolean))}}ms`,advice:hvV>=75?'✓ En rango':'↑ Prioriza sueño'}},
    {{title:'Sueño Profundo ≥60min',val:Math.min(avgDeep,120),max:120,color:'var(--teal)',unit:'min',sub:`Prom. 30d: ${{avgDeep}}min`,advice:avgDeep>=60?'✓ Meta alcanzada':'↑ Evita alcohol/pantallas'}},
    {{title:'Total Sueño ≥7.5h',val:Math.min(avgSl*10,10),max:10,color:'var(--purple)',unit:'h',sub:`Prom. 30d: ${{avgSl}}h`,advice:avgSl>=7.5?'✓ Excelente':'↑ Acuéstate antes de medianoche'}},
    {{title:'Readiness ≥70',val:lastTr?.score||0,max:100,color:'var(--yellow)',unit:'/100',sub:`Nivel: ${{lastTr?.level||'—'}}`,advice:lastTr?.score>=70?'✓ Listo para entrenar':'↑ VFC y sueño primero'}},
    {{title:'HR Reposo ≤58bpm',val:Math.max(0,90-(lastHr?.resting||66)),max:90-58,color:'var(--red)',unit:'bpm actual',sub:`Actual: ${{lastHr?.resting||'—'}}bpm`,advice:(lastHr?.resting||99)<=58?'✓ Cardio fitness excelente':'↑ Entrena zona 2 regularmente'}},
    {{title:'Natación ≥10 ses./mes',val:D.activities.filter(a=>(a.type||'').includes('swim')&&a.date>=(new Date(Date.now()-30*86400000)).toISOString().slice(0,10)).length,max:10,color:'var(--green)',unit:'sesiones',sub:'Este mes',advice:'Progresivo según VFC'}},
  ];

  const grid3=document.getElementById('goals-grid'); grid3.innerHTML='';
  goals.forEach(g=>{{
    const pct=Math.min(100,Math.round(g.val/g.max*100));
    grid3.innerHTML+=`<div class="goal-card">
      <div style="font-size:11px;color:var(--muted2);margin-bottom:6px">${{g.title}}</div>
      <div style="font-size:22px;font-weight:600;color:${{g.color}}">${{typeof g.val==='number'?Math.round(g.val):g.val}}<span style="font-size:11px;color:var(--muted)"> ${{g.unit}}</span></div>
      <div class="gp"><div class="gf" style="width:${{pct}}%;background:${{g.color}}"></div></div>
      <div class="gm"><span>${{g.sub}}</span><span>${{pct}}%</span></div>
      <div style="font-size:10px;color:${{pct>=80?'var(--green)':'pct>=50?\'var(--yellow)\'':'var(--red)'}};margin-top:6px">${{g.advice}}</div>
    </div>`;
  }});

  // Swim advice
  const adv=document.getElementById('goals-swim-advice');
  if(hvV>=86) adv.style.cssText='background:rgba(99,179,237,.08);color:var(--cyan)';
  else if(hvV>=71) adv.style.cssText='background:rgba(72,187,120,.08);color:var(--green)';
  else if(hvV>=56) adv.style.cssText='background:rgba(236,201,75,.08);color:var(--yellow)';
  else adv.style.cssText='background:rgba(252,129,129,.08);color:var(--red)';
  const zoneMap=[[86,'PRIME · 10×50m, descanso 1:15, Z3–Z4'],[71,'HIGH · 12×34m, descanso 1:30, Z2'],[56,'MODERATE · 10×34m, descanso 1:45, Z1–Z2 ← ESTÁS AQUÍ'],[40,'LOW · 6×34m, descanso 2:00, Z1'],[0,'POOR · Solo caminata/movilidad']];
  const zone=zoneMap.find(([min])=>hvV>=min);
  adv.innerHTML=`📍 <strong>VFC actual: ${{Math.round(hvV)}}ms</strong> → ${{zone?zone[1]:'—'}}`;
}}

// ── Init ──────────────────────────────────────────────────────────────────────
setTimeout(()=>renderOverview(), 100);
window.addEventListener('resize',()=>{{
  const a=document.querySelector('.view.active');
  if(a) renderView(a.id.replace('view-',''));
}});
</script>
</body>
</html>"""

OUTPUT_FILE.write_text(HTML, encoding="utf-8")
print(f"✅ Dashboard generado: {OUTPUT_FILE}")
print(f"   Noches de sueño:  {len(sleep_data)}")
print(f"   Registros HRV:    {len(hrv_data)}")
print(f"   Readiness:        {len(readiness_data)}")
print(f"   Actividades:      {len(activities)}")
