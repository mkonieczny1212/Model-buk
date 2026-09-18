from __future__ import annotations

from typing import Any


# This registry deliberately distinguishes "we possess the data" from
# "the API can sometimes provide it" and from "the model already uses it".
# A feature can enter probabilities only after a point-in-time historical
# pipeline and OOS ablation test exist for the relevant league/market.
DATA_READINESS: dict[str, dict[str, Any]] = {
    "fixtures_results_basic_stats": {
        "historical": "strong",
        "current": "strong",
        "sources": ["football-data.co.uk", "club-football", "API-Football"],
        "model_status": "usable",
        "note": "Broad results, shots/SOT/corners/cards coverage; provider coverage varies by league-season.",
    },
    "current_form": {
        "historical": "strong-core-partial-advanced",
        "current": "strong-for-basic-match-stats",
        "sources": ["API-Football current-season fixture stats", "Understat Big Five history", "club-football historical stats"],
        "model_status": "partial-active",
        "note": "Recent completed cross-competition match counts enter the live posterior when access and coverage permit. Full strength-of-schedule, manager-break and lineup-cause decomposition is not yet complete.",
    },
    "xg_process_big_five": {
        "historical": "strong",
        "current": "partial",
        "sources": ["Understat", "Footiqo", "API-Football when fixture coverage exposes xG"],
        "model_status": "goal-v0.6-active",
        "note": "See data/understat/source_manifest.json for refreshed seasons and provenance; training metadata distinguishes fit cutoff from latest state.",
    },
    "xg_process_other_primary_leagues": {
        "historical": "missing-uniform",
        "current": "coverage-dependent",
        "sources": ["API-Football current only where coverage exists", "candidate: FootyStats current-season", "candidate: Sportmonks xG/history"],
        "model_status": "blocked-for-grade-A",
        "note": "No uniform historical xG/PPDA/deep feature store yet for NED/POR/BEL/TUR/POL.",
    },
    "lineups_injuries": {
        "historical": "partial-raw",
        "current": "strong-when-published",
        "sources": ["Transfermarkt raw", "API-Football"],
        "model_status": "context-only",
        "note": "Raw lineups/events/valuations exist, but player-strength/replacement-gap model is not yet trained OOS.",
    },
    "predicted_lineups": {
        "historical": "missing-uniform",
        "current": "not-guaranteed",
        "sources": ["candidate: Sportmonks Expected Lineups", "fallback: own expected-XI model from confirmed lineup history + injuries"],
        "model_status": "missing",
        "note": "API-Football official lineups are typically confirmed close to kickoff; an early expected-XI feed is not guaranteed.",
    },
    "referees": {
        "historical": "partial",
        "current": "partial-strong",
        "sources": ["football-data.co.uk", "Transfermarkt raw", "API-Football"],
        "model_status": "context-only",
        "note": "Referee names/data exist for many matches, but no unified OOS referee×team model is active yet.",
    },
    "tactical_microdata": {
        "historical": "missing-uniform",
        "current": "partial",
        "sources": ["Understat PPDA/deep (Big Five)", "StatsBomb Open limited", "API-Football standard match stats", "candidate: Sportradar Extended / Sportmonks advanced statistics"],
        "model_status": "partial",
        "note": "No global historical field tilt/xT/VAEP/crosses/high-turnovers/positional feed for all primary competitions.",
    },
    "odds_main_markets": {
        "historical": "strong-main-partial-closing",
        "current": "strong-coverage-dependent",
        "sources": ["football-data.co.uk", "Footiqo", "API-Football"],
        "model_status": "usable-with-archive",
        "note": "API-Football pre-match odds have short retention; every snapshot must be archived locally.",
    },
    "odds_niche_props": {
        "historical": "weak",
        "current": "coverage-dependent",
        "sources": ["Footiqo PL corners/cards 2025/26", "API-Football current"],
        "model_status": "blocks-profit-validation",
        "note": "No broad historical team-SOT/shots/player-prop price archive yet.",
    },
    "uefa_competitions": {
        "historical": "not-integrated",
        "current": "counts-when-provider-plan-permits",
        "sources": ["API-Football"],
        "model_status": "live-research-predictions",
        "note": "UCL/UEL/UECL predictions use observed team counts across competitions. Cross-league strength calibration and prospective validation remain required.",
    },
    "weather": {
        "historical": "not-needed-as-core",
        "current": "available-with-location-confidence",
        "sources": ["Open-Meteo", "fixture venue/city", "OSM fallback"],
        "model_status": "shock-quality-gate",
        "note": "Normal weather is not a probability input; only reliable environmental shocks are candidates.",
    },
}


def readiness_summary() -> dict[str, Any]:
    missing = [k for k, v in DATA_READINESS.items() if str(v.get("historical", "")).startswith("missing") or v.get("model_status") in {"missing", "blocked-for-grade-A"}]
    return {
        "complete_for_full_target_model": False,
        "registry": DATA_READINESS,
        "critical_gaps": missing,
        "principle": "No missing feature receives an invented value or subjective probability weight.",
    }

