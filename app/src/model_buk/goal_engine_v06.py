from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson

from model_buk.team_names import resolve_team_name
from model_buk.features import FEATURE_POLICY, freeze_team_day, prior_day_mean, utc_dates


UNDERSTAT_FILES = {
    "EPL": "eng_team_match_stats.csv",
    "LALIGA": "esp_team_match_stats.csv",
    "BUNDESLIGA": "ger_team_match_stats.csv",
    "SERIEA": "ita_team_match_stats.csv",
    "LIGUE1": "fra_team_match_stats.csv",
}

STATE_METRICS = [
    "goals_for", "goals_against", "xg_for", "xg_against",
    "npxg_for", "npxg_against", "ppda_for", "ppda_against",
    "deep_for", "deep_against", "xpts_for", "xpts_against",
]


@dataclass(frozen=True)
class GoalEngineArtifacts:
    home_model: Any
    away_model: Any
    feature_names: list[str]
    metadata: dict[str, Any]


def _load_one(path: Path, league_code: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = utc_dates(df["date"])
    df["league_code"] = league_code
    return df[df["date"].notna()].sort_values("date").reset_index(drop=True)


@lru_cache(maxsize=2)
def load_understat(data_dir: str | Path) -> pd.DataFrame:
    root = Path(data_dir)
    frames = []
    for code, filename in UNDERSTAT_FILES.items():
        path = root / filename
        if path.exists():
            frames.append(_load_one(path, code))
    if not frames:
        raise FileNotFoundError(f"No Understat files found in {root}")
    return pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)


def _to_team_long(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for idx, r in df.iterrows():
        for side, opp, is_home in (("home", "away", 1), ("away", "home", 0)):
            rows.append({
                "match_idx": int(idx),
                "date": r["date"],
                "season_id": int(r["season_id"]),
                "league_code": r["league_code"],
                "team": r[f"{side}_team"],
                "opponent": r[f"{opp}_team"],
                "is_home": is_home,
                "goals_for": r[f"{side}_goals"],
                "goals_against": r[f"{opp}_goals"],
                "xg_for": r[f"{side}_xg"],
                "xg_against": r[f"{opp}_xg"],
                "npxg_for": r[f"{side}_np_xg"],
                "npxg_against": r[f"{opp}_np_xg"],
                "ppda_for": r[f"{side}_ppda"],
                "ppda_against": r[f"{opp}_ppda"],
                "deep_for": r[f"{side}_deep_completions"],
                "deep_against": r[f"{opp}_deep_completions"],
                "xpts_for": r[f"{side}_expected_points"],
                "xpts_against": r[f"{opp}_expected_points"],
            })
    return pd.DataFrame(rows).sort_values(["team", "date", "match_idx"]).reset_index(drop=True)


def build_training_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    df["date"] = utc_dates(df["date"])
    df = df.sort_values("date", kind="stable").reset_index(drop=True)
    long = _to_team_long(df)
    for metric in STATE_METRICS:
        shifted = long.groupby("team")[metric].shift(1)
        long[f"{metric}_ewm5"] = shifted.groupby(long["team"]).transform(
            lambda s: s.ewm(span=5, adjust=False, min_periods=2).mean()
        )
        long[f"{metric}_ewm15"] = shifted.groupby(long["team"]).transform(
            lambda s: s.ewm(span=15, adjust=False, min_periods=3).mean()
        )
    long["matches_before"] = long.groupby("team").cumcount()
    long["prev_date"] = long.groupby("team")["date"].shift(1)
    long["rest_days"] = (long["date"] - long["prev_date"]).dt.total_seconds() / 86400.0
    long["matches_14d"] = 0.0
    for _, idxs in long.groupby("team").groups.items():
        idxs = list(idxs)
        dates = long.loc[idxs, "date"].tolist()
        left = 0
        for j, idx in enumerate(idxs):
            current = dates[j]
            while left < j and current - dates[left] > pd.Timedelta(days=14):
                left += 1
            long.at[idx, "matches_14d"] = sum(d < current.normalize() for d in dates[left:j])

    state_cols = [c for c in long.columns if c.endswith("_ewm5") or c.endswith("_ewm15")]
    state_cols += ["matches_before", "rest_days", "matches_14d"]
    freeze_team_day(long, [c for c in state_cols if c not in ("rest_days", "matches_14d")] + ["prev_date"])
    long["rest_days"] = (long.date - long.prev_date).dt.total_seconds() / 86400.0
    home = long[long.is_home.eq(1)][["match_idx"] + state_cols].rename(columns={c: f"home_{c}" for c in state_cols})
    away = long[long.is_home.eq(0)][["match_idx"] + state_cols].rename(columns={c: f"away_{c}" for c in state_cols})

    match = df[[
        "league_code", "season_id", "date", "home_goals", "away_goals",
        "home_xg", "away_xg", "home_team", "away_team"
    ]].copy().reset_index().rename(columns={"index": "match_idx"})
    match = match.merge(home, on="match_idx", how="left").merge(away, on="match_idx", how="left")

    for col in ("home_goals", "away_goals", "home_xg", "away_xg"):
        for idx in match.groupby("league_code", sort=False).groups.values():
            match.loc[idx, f"league_{col}_prior"] = prior_day_mean(match.loc[idx, "date"], match.loc[idx, col], 760, 30)

    interaction_map = {
        "xg_for": "xg_against",
        "npxg_for": "npxg_against",
        "deep_for": "deep_against",
        "ppda_for": "ppda_against",
        "goals_for": "goals_against",
    }
    for base, opp_base in interaction_map.items():
        for span in (5, 15):
            match[f"inter_home_{base}_{span}"] = match[f"home_{base}_ewm{span}"] * match[f"away_{opp_base}_ewm{span}"]
            match[f"inter_away_{base}_{span}"] = match[f"away_{base}_ewm{span}"] * match[f"home_{opp_base}_ewm{span}"]

    feature_names = [
        c for c in match.columns
        if c.startswith("home_") or c.startswith("away_") or c.startswith("league_") or c.startswith("inter_")
    ]
    for c in ("home_goals", "away_goals", "home_xg", "away_xg", "home_team", "away_team", "league_code"):
        if c in feature_names:
            feature_names.remove(c)
    return match, feature_names


def _team_history(df: pd.DataFrame, team: str) -> pd.DataFrame:
    rows = []
    for _, r in df[(df.home_team.eq(team)) | (df.away_team.eq(team))].sort_values("date").iterrows():
        is_home = r.home_team == team
        side, opp = ("home", "away") if is_home else ("away", "home")
        rows.append({
            "date": r["date"],
            "goals_for": r[f"{side}_goals"], "goals_against": r[f"{opp}_goals"],
            "xg_for": r[f"{side}_xg"], "xg_against": r[f"{opp}_xg"],
            "npxg_for": r[f"{side}_np_xg"], "npxg_against": r[f"{opp}_np_xg"],
            "ppda_for": r[f"{side}_ppda"], "ppda_against": r[f"{opp}_ppda"],
            "deep_for": r[f"{side}_deep_completions"], "deep_against": r[f"{opp}_deep_completions"],
            "xpts_for": r[f"{side}_expected_points"], "xpts_against": r[f"{opp}_expected_points"],
        })
    return pd.DataFrame(rows)


def _append_current(base: pd.DataFrame, current_rows: list[dict[str, Any]], when: pd.Timestamp | None = None) -> pd.DataFrame:
    base = base.copy()
    base["date"] = utc_dates(base["date"])
    if not current_rows:
        return base
    rows = []
    for r in current_rows:
        rows.append({
            "date": pd.to_datetime(r.get("date"), utc=True, errors="coerce").tz_localize(None),
            "goals_for": r.get("goals_for"), "goals_against": r.get("goals_against"),
            "xg_for": r.get("xg_for"), "xg_against": r.get("xg_against"),
            "npxg_for": r.get("npxg_for"), "npxg_against": r.get("npxg_against"),
            "ppda_for": r.get("ppda_for"), "ppda_against": r.get("ppda_against"),
            "deep_for": r.get("deep_for"), "deep_against": r.get("deep_against"),
            "xpts_for": r.get("xpts_for"), "xpts_against": r.get("xpts_against"),
        })
    add = pd.DataFrame(rows)
    add = add[add.date.notna()]
    if when is not None:
        cutoff = pd.to_datetime(when, utc=True).tz_localize(None).normalize()
        add = add[add.date < cutoff]
    if add.empty:
        return base
    # A team has at most one fixture per UTC day in these league feeds. Grouping
    # by day also handles providers disagreeing on kickoff times. Last non-null
    # per field preserves historical process data absent from the current feed.
    combined = pd.concat([base, add], ignore_index=True)
    combined["_day"] = combined.date.dt.normalize()
    return combined.groupby("_day", sort=True).last().reset_index(drop=True).sort_values("date").reset_index(drop=True)


def _state_at_prediction(history: pd.DataFrame, when: pd.Timestamp) -> dict[str, float]:
    when = pd.to_datetime(when, utc=True).tz_localize(None)
    history = history.copy()
    history["date"] = utc_dates(history["date"])
    hist = history[history.date < when.normalize()].sort_values("date").copy()
    out: dict[str, float] = {}
    if hist.empty:
        return out
    for metric in STATE_METRICS:
        s = pd.to_numeric(hist[metric], errors="coerce")
        out[f"{metric}_ewm5"] = float(s.ewm(span=5, adjust=False, min_periods=2).mean().iloc[-1]) if s.notna().sum() >= 2 else np.nan
        out[f"{metric}_ewm15"] = float(s.ewm(span=15, adjust=False, min_periods=3).mean().iloc[-1]) if s.notna().sum() >= 3 else np.nan
    out["matches_before"] = float(len(hist))
    last_date = pd.Timestamp(hist.date.iloc[-1])
    out["rest_days"] = float((when - last_date).total_seconds() / 86400.0)
    out["matches_14d"] = float(((hist.date >= when - pd.Timedelta(days=14)) & (hist.date < when)).sum())
    return out


def _latest_league_priors(df: pd.DataFrame, league_code: str, when: pd.Timestamp) -> dict[str, float]:
    when = pd.to_datetime(when, utc=True).tz_localize(None)
    df = df.copy()
    df["date"] = utc_dates(df["date"])
    league = df[(df.league_code.eq(league_code)) & (df.date < when.normalize())].sort_values("date", kind="stable").tail(760)
    if league.empty:
        return {}
    return {f"league_{col}_prior": float(pd.to_numeric(league[col], errors="coerce").mean()) if league[col].notna().sum() >= 30 else np.nan
            for col in ("home_goals", "away_goals", "home_xg", "away_xg")}


def _poisson_market_rows(home_lambda: float, away_lambda: float, home_name: str, away_name: str) -> list[dict[str, Any]]:
    # Adaptive support leaves less than 1e-12 mass per side outside the matrix.
    k = np.arange(int(max(poisson.ppf(1 - 1e-12, home_lambda), poisson.ppf(1 - 1e-12, away_lambda))) + 1)
    hp = poisson.pmf(k, home_lambda); ap = poisson.pmf(k, away_lambda)
    hp /= hp.sum(); ap /= ap.sum()
    matrix = np.outer(hp, ap)
    p_home = float(np.tril(matrix, k=-1).sum())
    p_draw = float(np.trace(matrix))
    p_away = float(np.triu(matrix, k=1).sum())
    p_btts = float(1.0 - hp[0] - ap[0] + hp[0] * ap[0])
    rows = [
        ("result.home", f"{home_name} wygra", "result", None, "home", p_home),
        ("result.draw", "Remis", "result", None, "draw", p_draw),
        ("result.away", f"{away_name} wygra", "result", None, "away", p_away),
        ("btts.yes", "Obie strzelą: TAK", "btts", None, "yes", p_btts),
        ("btts.no", "Obie strzelą: NIE", "btts", None, "no", 1 - p_btts),
    ]
    for line in (1.5, 2.5, 3.5, 4.5):
        threshold = int(np.floor(line))
        p_over = float(sum(matrix[i, j] for i in range(len(k)) for j in range(len(k)) if i + j > threshold))
        rows += [
            (f"goals.total.over.{line}", f"Powyżej {line} gola", "goals", line, "over", p_over),
            (f"goals.total.under.{line}", f"Poniżej {line} gola", "goals", line, "under", 1 - p_over),
        ]
    for side, team, probs in (("home", home_name, hp), ("away", away_name, ap)):
        for line in (0.5, 1.5, 2.5, 3.5):
            threshold = int(np.floor(line))
            p_over = float(probs[threshold + 1 :].sum())
            rows += [
                (f"goals.{side}.over.{line}", f"{team}: powyżej {line} gola", "goals", line, "over", p_over),
                (f"goals.{side}.under.{line}", f"{team}: poniżej {line} gola", "goals", line, "under", 1 - p_over),
            ]
    return [
        {
            "market_key": key, "label": label, "group": group, "threshold": line, "side": side,
            "probability": float(np.clip(p, 1e-8, 1 - 1e-8)), "fair_odds": float(1 / np.clip(p, 1e-8, 1 - 1e-8)),
            "engine": "goal-dynamic-xg-v0.6", "model_grade": "research",
            "predictive_validated": False, "market_validated": False, "eligible_for_bet": False,
        }
        for key, label, group, line, side, p in rows
    ]


class DynamicGoalEngineV06:
    """OOS-trained top-five goal engine built from Understat xG/process data.

    The historical data learns the relationship between dynamic team state and goals.
    Current API-Football observations can extend the state with recent goals/xG when available.
    No bookmaker odds are model inputs.
    """

    def __init__(self, data_dir: str | Path, model_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.raw = load_understat(self.data_dir)
        self.artifacts = self._load_artifacts()

    def _load_artifacts(self) -> GoalEngineArtifacts:
        meta = json.loads((self.model_dir / "metadata.json").read_text(encoding="utf-8"))
        return GoalEngineArtifacts(
            home_model=joblib.load(self.model_dir / "home_goals.joblib"),
            away_model=joblib.load(self.model_dir / "away_goals.joblib"),
            feature_names=list(meta["feature_names"]),
            metadata=meta,
        )

    @property
    def supported_leagues(self) -> set[str]:
        return set(UNDERSTAT_FILES)

    def _resolve(self, league_code: str, name: str) -> tuple[str | None, float]:
        candidates = sorted(set(self.raw.loc[self.raw.league_code.eq(league_code), "home_team"]) | set(self.raw.loc[self.raw.league_code.eq(league_code), "away_team"]))
        return resolve_team_name(name, candidates)

    def predict(
        self,
        league_code: str,
        when: str | pd.Timestamp,
        home_name: str,
        away_name: str,
        home_current: list[dict[str, Any]] | None = None,
        away_current: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if league_code not in self.supported_leagues:
            raise ValueError(f"goal-dynamic-xg-v0.6 is not trained for {league_code}")
        when_ts = pd.Timestamp(when)
        if when_ts.tzinfo is not None:
            when_ts = when_ts.tz_convert("UTC").tz_localize(None)
        home, hs = self._resolve(league_code, home_name)
        away, as_ = self._resolve(league_code, away_name)
        if not home or not away:
            raise ValueError(f"Understat team mapping failed: {home_name} ({hs:.2f}), {away_name} ({as_:.2f})")

        league = self.raw[self.raw.league_code.eq(league_code)]
        hhist = _append_current(_team_history(league, home), home_current or [], when_ts)
        ahist = _append_current(_team_history(league, away), away_current or [], when_ts)
        hstate = _state_at_prediction(hhist, when_ts)
        astate = _state_at_prediction(ahist, when_ts)
        row: dict[str, Any] = {}
        row.update({f"home_{k}": v for k, v in hstate.items()})
        row.update({f"away_{k}": v for k, v in astate.items()})
        row.update(_latest_league_priors(league, league_code, when_ts))

        interaction_map = {
            "xg_for": "xg_against", "npxg_for": "npxg_against", "deep_for": "deep_against",
            "ppda_for": "ppda_against", "goals_for": "goals_against",
        }
        for base, opp_base in interaction_map.items():
            for span in (5, 15):
                row[f"inter_home_{base}_{span}"] = row.get(f"home_{base}_ewm{span}", np.nan) * row.get(f"away_{opp_base}_ewm{span}", np.nan)
                row[f"inter_away_{base}_{span}"] = row.get(f"away_{base}_ewm{span}", np.nan) * row.get(f"home_{opp_base}_ewm{span}", np.nan)

        X = pd.DataFrame([{name: row.get(name, np.nan) for name in self.artifacts.feature_names}])
        lh = float(np.clip(self.artifacts.home_model.predict(X)[0], 0.05, 5.5))
        la = float(np.clip(self.artifacts.away_model.predict(X)[0], 0.05, 5.5))
        markets = _poisson_market_rows(lh, la, home_name, away_name)
        current_xg_n = sum(1 for r in (home_current or []) + (away_current or [])
                           if r.get("xg_for") is not None and pd.to_datetime(r.get("date"), utc=True, errors="coerce") < when_ts.tz_localize("UTC").normalize())
        feature_nonmissing = float(X.notna().mean(axis=1).iloc[0])
        return {
            "engine_version": "goal-dynamic-xg-v0.6",
            "league_code": league_code,
            "home_team": home_name,
            "away_team": away_name,
            "understat_home": home,
            "understat_away": away,
            "name_match": {"home": round(hs, 3), "away": round(as_, 3)},
            "lambda_home": round(lh, 4), "lambda_away": round(la, 4),
            "markets": markets,
            "feature_coverage": round(feature_nonmissing, 3),
            "current_xg_observations": current_xg_n,
            "training": self.artifacts.metadata.get("evaluation"),
            "feature_policy": FEATURE_POLICY,
            "artifact_compatible": self.artifacts.metadata.get("feature_policy") == FEATURE_POLICY,
            "validation_status": "research_only",
            "requires_retraining": self.artifacts.metadata.get("feature_policy") != FEATURE_POLICY,
            "note": "Research prediction; archived evaluation is not validation of this corrected pipeline. Legacy artifacts require retraining. Only observations from prior UTC days enter states.",
        }
