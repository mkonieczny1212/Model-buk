from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, mean_poisson_deviance

from model_buk.goal_engine_v06 import build_training_frame, load_understat, _poisson_market_rows
from model_buk.features import FEATURE_POLICY

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "understat"
OUT = ROOT / "models" / "goal_v06"


def event_metrics(frame, home_model, away_model, features):
    lh = np.clip(home_model.predict(frame[features]), 0.05, 5.5)
    la = np.clip(away_model.predict(frame[features]), 0.05, 5.5)
    probs = []
    over25 = []
    btts = []
    for x, y in zip(lh, la):
        markets = {m["market_key"]: m["probability"] for m in _poisson_market_rows(x, y, "home", "away")}
        probs.append([markets["result.home"], markets["result.draw"], markets["result.away"]])
        over25.append(markets["goals.total.over.2.5"])
        btts.append(markets["btts.yes"])
    probs = np.asarray(probs)
    over25 = np.asarray(over25)
    btts = np.asarray(btts)
    y3 = np.where(frame.home_goals > frame.away_goals, 0, np.where(frame.home_goals == frame.away_goals, 1, 2))
    yoh = np.eye(3)[y3]
    rps = float(np.mean(np.sum((np.cumsum(probs, axis=1)[:, :-1] - np.cumsum(yoh, axis=1)[:, :-1]) ** 2, axis=1) / 2))
    o25_y = (frame.home_goals + frame.away_goals >= 3).astype(int)
    btts_y = ((frame.home_goals > 0) & (frame.away_goals > 0)).astype(int)
    return {
        "1x2_log_loss": float(log_loss(y3, probs, labels=[0, 1, 2])),
        "1x2_rps": rps,
        "over25_brier": float(brier_score_loss(o25_y, over25)),
        "over25_log_loss": float(log_loss(o25_y, np.c_[1 - over25, over25])),
        "btts_brier": float(brier_score_loss(btts_y, btts)),
        "btts_log_loss": float(log_loss(btts_y, np.c_[1 - btts, btts])),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = load_understat(DATA)
    frame, features = build_training_frame(raw)
    train = frame[frame.season_id <= 2023].copy()
    validation = frame[frame.season_id == 2024].copy()
    test = frame[frame.season_id == 2025].copy()

    params = dict(
        loss="poisson", learning_rate=0.045, max_iter=350, max_leaf_nodes=20,
        min_samples_leaf=35, l2_regularization=3.0, random_state=42,
        early_stopping=False,
    )
    home_model = HistGradientBoostingRegressor(**params).fit(train[features], train.home_goals)
    away_model = HistGradientBoostingRegressor(**params).fit(train[features], train.away_goals)

    evaluation = {}
    for name, part in (("validation_2024_25", validation), ("test_2025_26", test)):
        hp = np.clip(home_model.predict(part[features]), 0.05, 5.5)
        ap = np.clip(away_model.predict(part[features]), 0.05, 5.5)
        evaluation[name] = {
            "n": int(len(part)),
            "home_mae": float(mean_absolute_error(part.home_goals, hp)),
            "away_mae": float(mean_absolute_error(part.away_goals, ap)),
            "home_poisson_deviance": float(mean_poisson_deviance(part.home_goals, hp)),
            "away_poisson_deviance": float(mean_poisson_deviance(part.away_goals, ap)),
            **event_metrics(part, home_model, away_model, features),
        }

    # Simple xG-state benchmark for interpretability, only on final test.
    h0 = np.sqrt(test.home_xg_for_ewm5 * test.away_xg_against_ewm5).fillna(train.home_xg.mean())
    a0 = np.sqrt(test.away_xg_for_ewm5 * test.home_xg_against_ewm5).fillna(train.away_xg.mean())
    evaluation["test_2025_26"]["naive_xg_home_mae"] = float(mean_absolute_error(test.home_goals, h0))
    evaluation["test_2025_26"]["naive_xg_away_mae"] = float(mean_absolute_error(test.away_goals, a0))

    joblib.dump(home_model, OUT / "home_goals.joblib")
    joblib.dump(away_model, OUT / "away_goals.joblib")
    metadata = {
        "engine_version": "goal-dynamic-xg-v0.6",
        "trained_through": str(train.date.max()),
        "state_data_through": str(raw.date.max()),
        "training_matches": int(len(train)),
        "feature_policy": FEATURE_POLICY,
        "validation_status": "research_only",
        "validation_registry": {},
        "matches": int(len(raw)),
        "leagues": sorted(raw.league_code.unique().tolist()),
        "feature_names": features,
        "feature_count": len(features),
        "model": "HistGradientBoostingRegressor(loss=poisson)",
        "state": "point-in-time EWMA spans 5/15 + rest/congestion + learned interactions",
        "no_market_inputs": True,
        "evaluation": evaluation,
        "limitations": [
            "Historical xG/process coverage is Big Five only.",
            "Current API-Football xG is used only when returned by provider coverage.",
            "Lineup/player, referee and tactical microdata are not probability inputs until their historical feature pipelines are trained OOS.",
        ],
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evaluation, indent=2))


if __name__ == "__main__":
    main()


