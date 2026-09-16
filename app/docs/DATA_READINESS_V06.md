# Model Buk v0.6 — Data Readiness Audit

This document is intentionally conservative. "Provider can expose a field" is not the same as "we have a uniform historical point-in-time training set" and neither is the same as "the feature is validated in production probabilities".

## Strong enough now

### Core match history
- football-data.co.uk: 92,327 matches, 12 seasons × 22 leagues; broad stats and closing main-market odds.
- club-football: 230,557 matches / 38 leagues; Elo/Form and ~114k matches with shots/SOT/corners/cards.
- Footiqo: PL 2025/26 closing corners/cards; Big Five 2025/26 xG + closing main markets.

### Big Five xG/process history
Local Understat files contain **19,763 matches** across EPL, LaLiga, Bundesliga, Serie A and Ligue 1, from 2014/15 through 2025/26. Fields include xG, npxG, expected points, PPDA and deep completions.

### Player/lineup raw history
Transfermarkt raw bundle is present (~872 MB): game_lineups, game_events, appearances, player valuations, games, players, transfers, clubs. This is raw material, not yet a validated player-impact feature store.

### Current/live layer
API-Football connection can provide fixture metadata and, where league-season coverage allows, statistics, injuries, confirmed lineups, players and odds. Coverage must be checked per league-season; a provider coverage flag does not guarantee every field for every fixture.

## Critical gaps

1. No uniform historical xG/process set yet for Eredivisie, Primeira Liga, Belgium, Turkey or Ekstraklasa.
2. UCL/UEL/UECL are live-visible but competition-specific historical feature backfill is not yet integrated.
3. No validated predicted-lineup feed before official XI. API-Football lineups are typically near kickoff.
4. Transfermarkt raw player data has not yet been canonicalized into `PlayerImpact`, `LineupDelta`, replacement gap and continuity features.
5. Referee history is partial and not yet a unified OOS referee×team/discipline model.
6. No uniform historical tactical microdata (field tilt, xT, VAEP, crosses, high turnovers, positional data) across all primary leagues.
7. Historical odds for niche props are weak: team shots/SOT/player props are not broadly archived. API-Football pre-match odds have short retention, therefore every current snapshot must be archived locally.
8. Executable Polish bookmaker coverage is not yet proven market-by-market. It must be audited from actual API responses rather than assumed.
9. Weather/stadium location data is not complete enough to allow fuzzy guessing; low-confidence weather is deliberately suppressed.

## Consequence for the model

A feature is a probability input only if it has:
1. a point-in-time historical definition,
2. sufficient coverage/sample,
3. a reproducible feature pipeline,
4. chronological OOS/ablation evidence,
5. an explicit missingness policy.

Otherwise it is shown as context or a quality gate. Missing values never receive subjective weights.
