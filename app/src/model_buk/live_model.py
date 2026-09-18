"""Live-first, reproducible Gamma-Poisson forecasts for completed-match counts.

Recent attacking production and the opponent's concessions are independent
observations of the upcoming scoring rate. A weak, decaying historical prior
regularises sparse samples. Integrating the Gamma rate yields the negative
binomial predictive distribution (including rate uncertainty). This is a
research model, not an automatically validated betting strategy.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import gamma

from model_buk.multimarket import METRICS, rebuild_markets_from_expected
from model_buk.team_names import resolve_team_name

VERSION = "live-gamma-poisson-v0.7"
HALF_LIFE_DAYS = 90.0
MIN_OBSERVATIONS = 3
MAX_OBSERVATION_AGE_DAYS = 365


def utc(value: Any) -> pd.Timestamp:
    return pd.to_datetime(value, utc=True, errors="coerce")


def eligible_observations(rows: list[dict], cutoff: Any) -> list[dict]:
    """Conservative availability: unknown result publication is kickoff + 3h."""
    when = utc(cutoff)
    out, seen = [], set()
    for row in rows:
        date = utc(row.get("date"))
        known = utc(row.get("available_at")) if row.get("available_at") else date + pd.Timedelta(hours=3)
        identity = row.get("fixture_id") or (str(date), row.get("opponent_id") or row.get("opponent"))
        if identity in seen or pd.isna(date) or pd.isna(known) or known >= when:
            continue
        if date > when or (when - date).days > MAX_OBSERVATION_AGE_DAYS:
            continue
        if row.get("status") not in (None, "FT"):
            continue
        seen.add(identity)
        out.append(row)
    return sorted(out, key=lambda x: utc(x["date"]), reverse=True)


def historical_observations(history: pd.DataFrame, name: str, cutoff: Any) -> list[dict]:
    if history.empty:
        return []
    candidates = sorted(set(history.HomeTeam.dropna()) | set(history.AwayTeam.dropna()))
    team, _ = resolve_team_name(name, candidates)
    if team is None:
        return []
    when = utc(cutoff)
    dates = pd.to_datetime(history.MatchDate, utc=True)
    # Source dates may have day resolution. Exclude the entire prediction day.
    mask = ((history.HomeTeam == team) | (history.AwayTeam == team)) & (dates < when.normalize()) & (dates >= when - pd.Timedelta(days=1095))
    rows = []
    for _, match in history.loc[mask].tail(80).iterrows():
        home = match.HomeTeam == team
        row = {"date": str(match.MatchDate), "venue": "home" if home else "away", "opponent": match.AwayTeam if home else match.HomeTeam, "source": "history"}
        for metric, (h, a) in METRICS.items():
            row[metric + "_for"] = match[h if home else a]
            row[metric + "_against"] = match[a if home else h]
        rows.append(row)
    return rows


def _weighted(rows: list[dict], field: str, when: pd.Timestamp, venue: str | None = None) -> tuple[float, float, int, float | None]:
    total = exposure = 0.0
    count = 0
    latest = None
    for row in rows:
        value = row.get(field)
        date = utc(row.get("date"))
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(value) or value < 0 or pd.isna(date):
            continue
        age = max((when - date).total_seconds() / 86400, 0)
        weight = 2 ** (-age / HALF_LIFE_DAYS)
        # Partial pooling: other venues carry half the exposure. Explicit model
        # assumption, not a claimed learned coefficient or probability boost.
        if venue and row.get("venue") not in (venue, None):
            weight *= .5
        total += value * weight
        exposure += weight
        count += 1
        latest = age if latest is None else min(latest, age)
    return total, exposure, count, latest


def _rate(own: list[dict], opposing: list[dict], own_history: list[dict], opposing_history: list[dict], metric: str, when: pd.Timestamp, venue: str) -> dict:
    other_venue = "away" if venue == "home" else "home"
    production = _weighted(own, metric + "_for", when, venue)
    concession = _weighted(opposing, metric + "_against", when, other_venue)
    hp = _weighted(own_history, metric + "_for", when, venue)
    hc = _weighted(opposing_history, metric + "_against", when, other_venue)
    # History acts only as a bounded prior and loses mass with age; unlike the
    # previous +/-18% multiplier, live observations can determine the rate.
    historical_sum, historical_n = hp[0] + hc[0], hp[1] + hc[1]
    prior_exposure = min(3.0, historical_n)
    prior_rate = historical_sum / historical_n if historical_n > 1e-8 else 0.0
    live_sum, live_n = production[0] + concession[0], production[1] + concession[1]
    has_live = min(production[2], concession[2]) >= MIN_OBSERVATIONS and live_n >= 1.0
    has_history = min(hp[2], hc[2]) >= MIN_OBSERVATIONS and historical_n >= 1.0
    if not has_live and not has_history:
        return {"available": False, "reason": "Za mało dostępnych obserwacji produkcji i dopuszczania tej statystyki.", "production_n": production[2], "concession_n": concession[2]}
    # Jeffreys prior shape=1/2; zero observations remain meaningful evidence.
    shape = .5 + live_sum + prior_rate * prior_exposure
    rate = live_n + prior_exposure
    if rate <= 0:
        return {"available": False, "reason": "Brak efektywnej próby."}
    mean = shape / rate
    return {"available": True, "mean": float(mean), "alpha": float(1 / shape),
            "rate_interval_90": [float(x) for x in gamma.ppf([.05, .95], a=shape, scale=1 / rate)],
            "production_n": production[2], "concession_n": concession[2],
            "effective_live_exposure": round(live_n, 4), "historical_prior_exposure": round(prior_exposure, 4),
            "live_share": round(live_n / rate, 4), "latest_observation_age_days": min([x for x in (production[3], concession[3], hp[3], hc[3]) if x is not None], default=None),
            "source": "live_and_history" if live_n and prior_exposure else "live" if live_n else "history"}


def understat_observations(raw: pd.DataFrame, name: str, cutoff: Any) -> list[dict]:
    """Fallback to dated, observed goals/xG; never infer absent event counts."""
    if raw is None or raw.empty:
        return []
    team, _ = resolve_team_name(name, sorted(set(raw.home_team) | set(raw.away_team)))
    if team is None:
        return []
    dates = pd.to_datetime(raw.date, utc=True)
    when = utc(cutoff)
    rows = raw[((raw.home_team == team) | (raw.away_team == team)) & (dates < when.normalize())].tail(20)
    result = []
    for _, match in rows.iterrows():
        own, opp = ('home', 'away') if match.home_team == team else ('away', 'home')
        result.append({'date': str(match.date), 'available_at': str(utc(match.date).normalize() + pd.Timedelta(days=1)),
                       'fixture_id': 'understat-' + str(match.get('game_id')), 'venue': own, 'opponent': match[opp+'_team'],
                       'goals_for': match[own+'_goals'], 'goals_against': match[opp+'_goals'], 'xg_for': match[own+'_xg'], 'xg_against': match[opp+'_xg'],
                       'source': 'understat_public_history'})
    return result


def apply_live_model(analysis: dict, live: dict, history: pd.DataFrame, understat: pd.DataFrame | None = None) -> dict:
    result = deepcopy(analysis)
    when = utc(result["fixture"]["date"])
    observations = live.get("recent_observations") or {}
    home = eligible_observations(observations.get("home") or [], when)
    away = eligible_observations(observations.get("away") or [], when)
    def supplement(rows, name):
        days = {utc(x['date']).date() for x in rows}
        additional = eligible_observations(understat_observations(understat, name, when), when)
        return rows + [x for x in additional if utc(x['date']).date() not in days]
    home = supplement(home, result['fixture']['home_team'])
    away = supplement(away, result['fixture']['away_team'])
    hh = historical_observations(history, result["fixture"]["home_team"], when)
    ah = historical_observations(history, result["fixture"]["away_team"], when)
    # Avoid counting historical copies of the same live matches twice.
    def dedup_history(old, recent):
        days = {utc(x["date"]).date() for x in recent}
        return [x for x in old if utc(x["date"]).date() not in days]
    hh, ah = dedup_history(hh, home), dedup_history(ah, away)
    expected, samples, readiness, factors = {}, {}, {}, []
    for metric in METRICS:
        h = _rate(home, away, hh, ah, metric, when, "home")
        a = _rate(away, home, ah, hh, metric, when, "away")
        available = h["available"] and a["available"]
        samples[metric] = {"home": h.get("production_n", 0), "away": a.get("production_n", 0)}
        readiness[metric] = {"grade": "RESEARCH" if available else "UNAVAILABLE", "predictive_validated": False, "eligible_for_bet": False,
                             "reason": "Prognoza statystyczna; wymaga walidacji dla ligi i rynku." if available else h.get("reason") or a.get("reason"), "home": h, "away": a}
        if available:
            expected[metric] = {"home": h["mean"], "away": a["mean"], "total": h["mean"] + a["mean"],
                                "alpha_home": h["alpha"], "alpha_away": a["alpha"], "source": VERSION,
                                "rate_interval_90_home": h["rate_interval_90"], "rate_interval_90_away": a["rate_interval_90"]}
            factors.append({"key": "live_posterior_" + metric, "label": metric + " · atak × dopuszczanie przeciwnika", "home": {"live_share": h["live_share"], "n": h["production_n"]}, "away": {"live_share": a["live_share"], "n": a["production_n"]}, "status": "model_input", "explanation": "Rozkład Gamma–Poisson: produkcja drużyny i dopuszczanie przeciwnika, ważone aktualnością i miejscem meczu; historia jako słabnący prior. Parametry i niepewność są zapisane w analizie."})
        else:
            expected[metric] = {"home": None, "away": None, "total": None, "source": "unavailable", "reason": readiness[metric]["reason"]}
    result.update(expected=expected, model_readiness=readiness, engine_version=VERSION)
    result["markets"] = rebuild_markets_from_expected(result)
    for row in result["markets"]:
        row.update(engine=VERSION, model_grade="RESEARCH", predictive_validated=False, eligible_for_bet=False)
        if row["group"] == "cards":
            row["settlement_rule"] = "yellow_plus_two_red"
    result["factors"] = factors
    result["current_data"] = {"used_in_model": any(x.get("home", {}).get("effective_live_exposure", 0) > 0 or x.get("away", {}).get("effective_live_exposure", 0) > 0 for x in readiness.values()), "observation_samples": samples,
                              "sources": sorted({r.get('source', 'provider') for r in home + away}),
                              "policy": {"half_life_days": HALF_LIFE_DAYS, "historical_prior_max_games": 3, "minimum_observations_per_stream": MIN_OBSERVATIONS, "cutoff": str(when), "cross_competition": True}}
    available_count = sum(x["home"] is not None for x in expected.values())
    result["data_quality"] = {"score": round(100 * available_count / len(METRICS), 1), "label": "Pokrycie rynków danymi (nie pewność trafienia)", "available_metrics": available_count, "total_metrics": len(METRICS),
                              "warning": "Model badawczy: siła różnych lig i wpływ składu wymagają osobnej walidacji. Prognoza nie oznacza automatycznie BET."}
    if not result["markets"]:
        result.setdefault("warnings", []).append("Nie uzyskano minimalnej próby z API ani historii. Sprawdź komunikaty i pokrycie dostawcy.")
    return result
