# Model Buk v0.6 implementation report

## Why v0.6 exists
v0.5 proved the web/API pipeline but its broad multi-market estimates were still dominated by time-decayed historical rates. v0.6 starts moving to the architecture defined in Football-Prediction-Brain: dynamic team state + match context + interactions -> event distributions.

## First learned engine: Goals
`goal-dynamic-xg-v0.6` uses Big-Five Understat data and builds point-in-time EWMA team states for goals, xG, npxG, PPDA, deep completions and expected points, plus rest/congestion and attack×opponent-defense interactions. Separate Poisson-loss gradient-boosting models learn home and away goal intensity. Bookmaker prices are not features.

### OOS evaluation
Validation 2024/25: n=1,752; home MAE 0.9471; away MAE 0.8766; 1X2 log loss 0.9821; RPS 0.1994.

Final test 2025/26: n=1,752; home MAE 0.9721; away MAE 0.8669; 1X2 log loss 0.9994; RPS 0.2038; O2.5 Brier 0.2473; BTTS Brier 0.2472.

Naive xG-state MAE on the same final test: home 0.9883; away 0.9469. The learned engine improves the count forecast benchmark, especially away goals. This does **not** establish betting profitability.

## Betting gate
The goal engine is `predictive_validated=True` but `market_validated=False`, therefore current value candidates are labeled RESEARCH. BET remains disabled until price/calibration/CLV plus prospective paper-trading validation is completed.

## UI
- primary scope: top 10 domestic leagues + UCL/UEL/UECL;
- top five positive-value, predictive-validated candidates shown first;
- full market line grid collapsed under details;
- model grade/engine shown per row;
- unsupported/nonstrong models are labeled RESEARCH rather than silently treated as equal-quality predictions.

## Data quality
Machine-readable registry: `model_buk.data_readiness`. API-Football league-season coverage is fetched and displayed. Weather location matching is strict and falls back to geocoded fixture city; no low-confidence stadium guess is accepted.

## Automated verification
22 tests pass in this checkpoint.
