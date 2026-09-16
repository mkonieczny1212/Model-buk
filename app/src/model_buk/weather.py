from __future__ import annotations

import json
from datetime import datetime, timezone
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

from model_buk.team_names import normalize_name


@lru_cache(maxsize=2)
def load_stadiums(path: str | Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    output = []
    for element in raw.get("elements", []):
        tags = element.get("tags") or {}
        sport = str(tags.get("sport") or "").lower()
        if sport and "soccer" not in sport and "football" not in sport:
            continue
        point = element.get("center") or element
        if point.get("lat") is None or point.get("lon") is None:
            continue
        output.append({
            "name": tags.get("name") or tags.get("name:en"),
            "city": tags.get("addr:city"),
            "lat": float(point["lat"]),
            "lon": float(point["lon"]),
            "capacity": tags.get("capacity"),
        })
    return output


def find_stadium(path: str | Path, venue_name: str | None, city: str | None = None) -> dict[str, Any] | None:
    if not venue_name:
        return None
    target = normalize_name(venue_name)
    best = None
    best_score = 0.0
    for stadium in load_stadiums(path):
        if not stadium.get("name"):
            continue
        score = SequenceMatcher(None, target, normalize_name(stadium["name"])).ratio()
        if city and stadium.get("city") and normalize_name(city) == normalize_name(stadium["city"]):
            score += 0.08
        if score > best_score:
            best, best_score = stadium, score
    # Deliberately strict. Wrong location is worse than no weather.
    if best and best_score >= 0.90:
        return {**best, "match_score": round(best_score, 3), "source": "osm_stadium_high_confidence"}
    return None


def geocode_city(city: str | None, country: str | None = None, timeout: int = 10) -> dict[str, Any] | None:
    if not city:
        return None
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 8, "language": "en", "format": "json"},
        timeout=timeout,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None
    target_city = normalize_name(city)
    target_country = normalize_name(country or "")

    def score(row: dict[str, Any]) -> float:
        s = SequenceMatcher(None, target_city, normalize_name(row.get("name") or "")).ratio()
        if target_country:
            c = normalize_name(row.get("country") or "")
            if c == target_country or target_country in c or c in target_country:
                s += 0.20
        return s

    best = max(results, key=score)
    best_score = score(best)
    if best_score < 0.72:
        return None
    return {
        "name": best.get("name"),
        "country": best.get("country"),
        "admin1": best.get("admin1"),
        "lat": float(best["latitude"]),
        "lon": float(best["longitude"]),
        "match_score": round(float(best_score), 3),
        "source": "open_meteo_city_geocoding",
    }


def forecast_for_kickoff(lat: float, lon: float, kickoff: str, timeout: int = 10) -> dict[str, Any] | None:
    dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,snowfall",
        "timezone": "UTC",
        "forecast_days": 16,
    }
    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return None
    target = dt.astimezone(timezone.utc).replace(tzinfo=None)
    parsed = [datetime.fromisoformat(t) for t in times]
    idx = min(range(len(parsed)), key=lambda i: abs((parsed[i] - target).total_seconds()))

    def value(field: str):
        arr = hourly.get(field) or [None] * len(times)
        return arr[idx] if idx < len(arr) else None

    return {
        "time_utc": times[idx],
        "temperature_c": value("temperature_2m"),
        "humidity_pct": value("relative_humidity_2m"),
        "precipitation_mm": value("precipitation"),
        "wind_kmh": value("wind_speed_10m"),
        "gusts_kmh": value("wind_gusts_10m"),
        "snowfall_cm": value("snowfall"),
    }


def weather_context(stadium_path: str | Path, fixture: dict[str, Any]) -> dict[str, Any]:
    venue = fixture.get("venue") or {}
    country = fixture.get("country")
    stadium = None
    try:
        stadium = find_stadium(stadium_path, venue.get("name"), venue.get("city"))
    except (FileNotFoundError, json.JSONDecodeError):
        stadium = None

    location = stadium
    if location is None:
        try:
            location = geocode_city(venue.get("city"), country)
        except Exception as exc:
            return {
                "available": False,
                "reason": f"Nie udało się wiarygodnie ustalić lokalizacji: {exc}",
                "model_usage": "monitor_only",
            }
    if not location:
        return {
            "available": False,
            "reason": "Brak wiarygodnej lokalizacji stadionu/miasta. Pogoda celowo nie jest zgadywana.",
            "model_usage": "monitor_only",
        }

    try:
        forecast = forecast_for_kickoff(location["lat"], location["lon"], fixture["kickoff"])
    except Exception as exc:
        return {"available": False, "location": location, "reason": str(exc), "model_usage": "monitor_only"}
    if not forecast:
        return {"available": False, "location": location, "reason": "Brak prognozy w zakresie Open-Meteo.", "model_usage": "monitor_only"}

    wind = float(forecast.get("wind_kmh") or 0)
    gusts = float(forecast.get("gusts_kmh") or 0)
    rain = float(forecast.get("precipitation_mm") or 0)
    snow = float(forecast.get("snowfall_cm") or 0)
    temp = forecast.get("temperature_c")
    humidity = float(forecast.get("humidity_pct") or 0)
    extreme = bool(
        wind >= 35 or gusts >= 55 or rain >= 5 or snow >= 1
        or (temp is not None and (float(temp) <= -5 or float(temp) >= 32))
        or (temp is not None and float(temp) >= 29 and humidity >= 75)
    )
    return {
        "available": True,
        "location": location,
        "forecast": forecast,
        "extreme": extreme,
        "model_usage": "quality_gate_only" if extreme else "monitor_only",
        "note": "Normal weather does not move probabilities. Only validated environmental shocks may enter a future model.",
    }
