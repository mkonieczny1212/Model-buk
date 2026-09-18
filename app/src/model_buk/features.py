from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_POLICY = "utc-prior-day-v1"


def utc_dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, utc=True, errors="coerce", format="mixed").dt.tz_localize(None)


def prior_day_mean(dates: pd.Series, values: pd.Series, window: int, minimum: int) -> np.ndarray:
    """Outcomes become available the next UTC day (sources lack completion times).

    Inputs must be sorted by date. All fixtures on one day share the same
    pre-day snapshot, including fixtures with a later kickoff.
    """
    dates = utc_dates(dates).reset_index(drop=True)
    means = pd.to_numeric(values, errors="coerce").reset_index(drop=True).rolling(window, min_periods=minimum).mean()
    positions = dates.searchsorted(dates.dt.normalize(), side="left") - 1
    result = np.full(len(dates), np.nan)
    valid = positions >= 0
    result[valid] = means.iloc[positions[valid]].to_numpy()
    return result


def freeze_team_day(long: pd.DataFrame, columns: list[str]) -> None:
    """Broadcast the first pre-match snapshot without skipping its missing values."""
    codes = long.groupby([long.team, long.date.dt.normalize()], sort=False).ngroup().to_numpy()
    first = ~pd.Series(codes).duplicated().to_numpy()
    snapshots = long.loc[first, columns].iloc[codes].copy()
    snapshots.index = long.index
    long[columns] = snapshots


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create strictly point-in-time rolling features.

    Every team statistic is shifted by one match before rolling/ewm aggregation,
    so the current match outcome cannot enter its own feature vector.
    """
    d = df.copy()
    d["date"] = utc_dates(d["date"])
    d = d.sort_values(["date", "internal_match_id"]).reset_index(drop=True)

    home = pd.DataFrame(
        {
            "_mid": d.internal_match_id.to_numpy(),
            "date": d.date.to_numpy(),
            "team": d.home_team.to_numpy(),
            "opponent": d.away_team.to_numpy(),
            "is_home": 1,
            "corners_for": d.home_corners.to_numpy(),
            "corners_against": d.away_corners.to_numpy(),
            "shots_for": d.home_shots.to_numpy(),
            "shots_against": d.away_shots.to_numpy(),
            "sot_for": d.home_sot.to_numpy(),
            "sot_against": d.away_sot.to_numpy(),
            "goals_for": d.home_goals.to_numpy(),
            "goals_against": d.away_goals.to_numpy(),
            "xg_for": d.home_xg.to_numpy(),
            "xg_against": d.away_xg.to_numpy(),
            "ppda": d.home_ppda.to_numpy(),
            "deep_for": d.home_deep.to_numpy(),
            "deep_against": d.away_deep.to_numpy(),
        }
    )
    away = pd.DataFrame(
        {
            "_mid": d.internal_match_id.to_numpy(),
            "date": d.date.to_numpy(),
            "team": d.away_team.to_numpy(),
            "opponent": d.home_team.to_numpy(),
            "is_home": 0,
            "corners_for": d.away_corners.to_numpy(),
            "corners_against": d.home_corners.to_numpy(),
            "shots_for": d.away_shots.to_numpy(),
            "shots_against": d.home_shots.to_numpy(),
            "sot_for": d.away_sot.to_numpy(),
            "sot_against": d.home_sot.to_numpy(),
            "goals_for": d.away_goals.to_numpy(),
            "goals_against": d.home_goals.to_numpy(),
            "xg_for": d.away_xg.to_numpy(),
            "xg_against": d.home_xg.to_numpy(),
            "ppda": d.away_ppda.to_numpy(),
            "deep_for": d.away_deep.to_numpy(),
            "deep_against": d.home_deep.to_numpy(),
        }
    )
    long = pd.concat([home, away], ignore_index=True).sort_values(["team", "date", "_mid"])

    metrics = [
        "corners_for", "corners_against", "shots_for", "shots_against",
        "sot_for", "sot_against", "goals_for", "goals_against",
        "xg_for", "xg_against", "ppda", "deep_for", "deep_against",
    ]
    for metric in metrics:
        for window in (5, 10):
            long[f"{metric}_r{window}"] = long.groupby("team", sort=False)[metric].transform(
                lambda s, w=window: s.shift(1).rolling(w, min_periods=3).mean()
            )
        long[f"{metric}_ewm8"] = long.groupby("team", sort=False)[metric].transform(
            lambda s: s.shift(1).ewm(span=8, min_periods=3, adjust=False).mean()
        )

    for metric in (
        "corners_for", "corners_against", "shots_for", "shots_against",
        "sot_for", "sot_against", "goals_for", "goals_against",
    ):
        long[f"{metric}_venue5"] = long.groupby(["team", "is_home"], sort=False)[metric].transform(
            lambda s: s.shift(1).rolling(5, min_periods=2).mean()
        )

    long["prev_date"] = long.groupby("team")["date"].shift(1)
    long["rest_days"] = (
        pd.to_datetime(long["date"]) - pd.to_datetime(long["prev_date"])
    ).dt.total_seconds() / 86400.0
    long["games_prior"] = long.groupby("team").cumcount()
    long["points"] = np.where(
        long.goals_for > long.goals_against,
        3,
        np.where(long.goals_for == long.goals_against, 1, 0),
    )
    long["points_r5"] = long.groupby("team")["points"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=3).mean()
    )

    feature_cols = [
        c for c in long.columns if any(tag in c for tag in ("_r5", "_r10", "_ewm8", "_venue5"))
    ]
    feature_cols += ["rest_days", "games_prior"]
    feature_cols = list(dict.fromkeys(feature_cols))
    freeze_team_day(long, [c for c in feature_cols if c != "rest_days"] + ["prev_date"])
    long["rest_days"] = (long.date - long.prev_date).dt.total_seconds() / 86400.0

    hfeat = long[long.is_home == 1][["_mid"] + feature_cols].copy()
    hfeat = hfeat.rename(columns={c: f"home_{c}" for c in feature_cols})
    afeat = long[long.is_home == 0][["_mid"] + feature_cols].copy()
    afeat = afeat.rename(columns={c: f"away_{c}" for c in feature_cols})

    out = d.merge(hfeat, left_on="internal_match_id", right_on="_mid", how="left").drop(columns="_mid")
    out = out.merge(afeat, left_on="internal_match_id", right_on="_mid", how="left").drop(columns="_mid")

    total = d.home_corners + d.away_corners
    groups = d.groupby("league_code", sort=False).groups.values() if "league_code" in d else [d.index]
    for idx in groups:
        for name, values in (("total", total), ("home", d.home_corners), ("away", d.away_corners)):
            out.loc[idx, f"league_{name}_corners_r100"] = prior_day_mean(d.loc[idx, "date"], values.loc[idx], 100, 20)
    out["total_corners"] = out.home_corners + out.away_corners
    return out
