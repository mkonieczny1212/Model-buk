---
tags: [schema, database, master-table]
---

# Schemat danych

## MATCHES — tabela centralna

```text
match_id, competition_id, season, kickoff_utc
home_team_id, away_team_id
home_goals, away_goals, halftime_goals
home_xg, away_xg
shots, shots_on_target, corners, fouls, cards
referee_id, venue_id
source_id, definition_version
```

## Tabele domenowe

- `TEAM_STATE` — dynamiczne parametry i rolling features;
- `PLAYER_STATE` — wartość, forma, minuty i dostępność;
- `LINEUPS` — predicted/confirmed XI, ławka, formation i timestamp;
- `INJURIES` — status, źródło, prawdopodobieństwo gry i `known_at`;
- `WEATHER_FORECASTS` — run time, target time, lead time i parametry;
- `REFEREES` — historyczne efekty z shrinkage;
- `VENUES` — współrzędne, wysokość, murawa i wymiary;
- `ODDS_SNAPSHOTS` — bookmaker, market, selection, odds i captured_at;
- `EVENTS` — granularne zdarzenia, jeżeli dostępne;
- `PREDICTIONS` — model_version, data_version, cutoff i rozkład;
- `FEATURE_REGISTRY` — definicje i wyniki testów cech.

## Przykładowe pola master feature view

```text
match_id, prediction_time, horizon
home_attack_state, home_defence_state
away_attack_state, away_defence_state
home_advantage
rest_days_home, rest_days_away
lineup_delta_home, lineup_delta_away
weather_forecast_*
market_probability_*
target_home_goals, target_away_goals
```

Master view jest generowany dla konkretnego cutoffu; nie jest jedną niekontrolowaną tabelą z setkami kolumn. Reguły czasu: [[11 - Czas predykcji i leakage]].

