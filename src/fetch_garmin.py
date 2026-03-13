"""
fetch_garmin.py
Descarga datos de Garmin Connect y los guarda en data/garmin_data.json
Uso: python src/fetch_garmin.py
"""

import os
import json
import time
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    from garminconnect import Garmin, GarminConnectAuthenticationError
except ImportError:
    print("ERROR: Instala garminconnect con: pip install garminconnect")
    sys.exit(1)

# ── Credenciales desde variables de entorno ──────────────────────────────────
EMAIL    = os.environ.get("GARMIN_EMAIL", "")
PASSWORD = os.environ.get("GARMIN_PASSWORD", "")

if not EMAIL or not PASSWORD:
    print("ERROR: Define GARMIN_EMAIL y GARMIN_PASSWORD como variables de entorno")
    print("  Windows: set GARMIN_EMAIL=tu@email.com")
    print("  Mac/Linux: export GARMIN_EMAIL=tu@email.com")
    sys.exit(1)

# ── Configuración ─────────────────────────────────────────────────────────────
DAYS_BACK  = 90          # cuántos días descargar
DATA_FILE  = Path("data/garmin_data.json")
TOKEN_FILE = Path("data/.garmin_tokens")   # caché de sesión

DATA_FILE.parent.mkdir(exist_ok=True)

def login() -> Garmin:
    """Inicia sesión, reutilizando tokens si existen."""
    api = Garmin(EMAIL, PASSWORD)
    if TOKEN_FILE.exists():
        try:
            api.login(TOKEN_FILE)
            print("✓ Sesión reutilizada desde tokens")
            return api
        except Exception:
            print("  Tokens expirados, haciendo login completo...")
    api.login()
    api.garth.dump(TOKEN_FILE)
    print("✓ Login exitoso, tokens guardados")
    return api

def safe_get(fn, *args, default=None, **kwargs):
    """Llama fn con reintentos; devuelve default si falla."""
    for attempt in range(3):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == 2:
                print(f"  ⚠ No se pudo obtener dato: {e}")
                return default
            time.sleep(2 ** attempt)

def fetch_all(api: Garmin, days: int) -> dict:
    today = date.today()
    start = today - timedelta(days=days)
    results = {
        "meta": {
            "fetched_at": today.isoformat(),
            "days_back": days,
            "email": EMAIL.split("@")[0] + "@***"
        },
        "sleep":      [],
        "hrv":        [],
        "readiness":  [],
        "training_load": [],
        "activities": [],
        "body_battery": [],
        "stress":     [],
        "steps":      [],
        "heart_rate": [],
        "endurance":  None,
        "fitness_age": None,
        "user_profile": None,
    }

    print(f"\nDescargando datos del {start} al {today}...")

    # ── Perfil ─────────────────────────────────────────────────────────────
    print("  → Perfil de usuario")
    profile = safe_get(api.get_user_profile)
    if profile:
        results["user_profile"] = {
            "display_name": profile.get("displayName"),
            "full_name":    profile.get("fullName"),
        }

    # ── Fitness age ────────────────────────────────────────────────────────
    print("  → Fitness age")
    fa = safe_get(api.get_fitnessage_data)
    if fa:
        results["fitness_age"] = fa

    # ── Por día ────────────────────────────────────────────────────────────
    current = start
    total_days = (today - start).days + 1
    processed = 0

    while current <= today:
        d_str = current.isoformat()
        processed += 1
        print(f"  [{processed}/{total_days}] {d_str}", end="\r")

        # Sueño
        sleep = safe_get(api.get_sleep_data, d_str)
        if sleep and sleep.get("dailySleepDTO"):
            dto = sleep["dailySleepDTO"]
            results["sleep"].append({
                "date":           d_str,
                "total_seconds":  dto.get("sleepTimeSeconds", 0),
                "deep_seconds":   dto.get("deepSleepSeconds", 0),
                "light_seconds":  dto.get("lightSleepSeconds", 0),
                "rem_seconds":    dto.get("remSleepSeconds", 0),
                "awake_seconds":  dto.get("awakeSleepSeconds", 0),
                "score":          dto.get("sleepScores", {}).get("overall", {}).get("value"),
                "avg_spo2":       dto.get("averageSpO2Value"),
                "avg_respiration": dto.get("averageRespiration"),
                "avg_stress":     dto.get("averageStressLevel"),
                "avg_hr":         dto.get("sleepHeartRate"),
                "start":          dto.get("sleepStartTimestampLocal"),
                "end":            dto.get("sleepEndTimestampLocal"),
            })

        # HRV
        hrv = safe_get(api.get_hrv_data, d_str)
        if hrv:
            summary = hrv.get("hrvSummary", {})
            results["hrv"].append({
                "date":        d_str,
                "weekly_avg":  summary.get("weeklyAvg"),
                "last_night":  summary.get("lastNight"),
                "last_5min":   summary.get("lastNight5MinHigh"),
                "status":      summary.get("status"),
                "baseline_low":  hrv.get("startTimestampLocal"),  # re-used field
                "readings":    [r.get("hrvValue") for r in hrv.get("hrvReadings", [])],
            })

        # Estrés diario
        stress = safe_get(api.get_stress_data, d_str)
        if stress:
            vals = [s[1] for s in stress.get("stressValuesArray", []) if s[1] and s[1] >= 0]
            if vals:
                results["stress"].append({
                    "date": d_str,
                    "avg":  round(sum(vals)/len(vals)),
                    "max":  max(vals),
                    "rest_pct":    stress.get("restStressDuration", 0),
                    "low_pct":     stress.get("lowStressDuration", 0),
                    "medium_pct":  stress.get("mediumStressDuration", 0),
                    "high_pct":    stress.get("highStressDuration", 0),
                })

        # Pasos
        steps = safe_get(api.get_steps_data, d_str)
        if steps:
            total_steps = sum(s.get("steps", 0) for s in steps)
            results["steps"].append({"date": d_str, "total": total_steps})

        # Body battery
        bb = safe_get(api.get_body_battery, d_str, d_str)
        if bb and isinstance(bb, list) and bb:
            vals = [v[1] for item in bb for v in item.get("bodyBatteryValuesArray", []) if v[1] is not None]
            if vals:
                results["body_battery"].append({
                    "date": d_str,
                    "min":  min(vals),
                    "max":  max(vals),
                    "end":  vals[-1],
                })

        # HR diaria
        hr = safe_get(api.get_heart_rates, d_str)
        if hr:
            results["heart_rate"].append({
                "date":    d_str,
                "resting": hr.get("restingHeartRate"),
                "max":     hr.get("maxHeartRate"),
                "min":     hr.get("minHeartRate"),
            })

        time.sleep(0.4)   # respetar rate limits de Garmin
        current += timedelta(days=1)

    print(f"\n  ✓ Días procesados: {processed}")

    # ── Training Readiness ────────────────────────────────────────────────
    print("  → Training Readiness")
    tr = safe_get(api.get_training_readiness, start.isoformat(), today.isoformat())
    if tr:
        results["readiness"] = [
            {
                "date":      r.get("calendarDate"),
                "score":     r.get("score"),
                "level":     r.get("level"),
                "feedback":  r.get("feedbackShort"),
                "hrv_pct":   r.get("hrvFactorPercent"),
                "sleep_pct": r.get("sleepScoreFactorPercent"),
                "sleep_score": r.get("sleepScore"),
                "acute_load": r.get("acuteLoad"),
                "hrv_weekly": r.get("hrvWeeklyAverage"),
            }
            for r in (tr if isinstance(tr, list) else [])
        ]

    # ── Actividades ───────────────────────────────────────────────────────
    print("  → Actividades recientes")
    acts = safe_get(api.get_activities, 0, 100)
    if acts:
        results["activities"] = [
            {
                "id":       a.get("activityId"),
                "date":     a.get("startTimeLocal", "")[:10],
                "name":     a.get("activityName"),
                "type":     a.get("activityType", {}).get("typeKey"),
                "duration": a.get("duration"),
                "distance": a.get("distance"),
                "avg_hr":   a.get("averageHR"),
                "max_hr":   a.get("maxHR"),
                "calories": a.get("calories"),
                "sport":    a.get("activityType", {}).get("typeKey"),
            }
            for a in acts
        ]

    # ── Health Snapshot (HRV baseline) ────────────────────────────────────
    print("  → Health snapshot / LHA")
    try:
        lha = safe_get(api.get_health_snapshot, start.isoformat(), today.isoformat())
        if lha:
            results["health_snapshot"] = lha
    except Exception:
        pass

    return results

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  Garmin Health Data Fetcher")
    print("=" * 50)

    api = login()
    data = fetch_all(api, DAYS_BACK)

    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\n✅ Datos guardados en {DATA_FILE}")
    print(f"   Sleep records:    {len(data['sleep'])}")
    print(f"   HRV records:      {len(data['hrv'])}")
    print(f"   Readiness records:{len(data['readiness'])}")
    print(f"   Activities:       {len(data['activities'])}")
