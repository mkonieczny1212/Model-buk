---
tags: [data-sources, registry, audit]
status: living-document
---

# Rejestr źródeł danych

Żywy katalog źródeł. Każde źródło ma status `primary`, `candidate`, `reference`, `fallback` albo `rejected`. Ceny i limity są zmienne — przed zakupem zawsze wykonujemy ponowną weryfikację.

## Macierz źródeł v1

| Źródło | Rola | Historia | Bieżące dane | Point-in-time | Koszt | Status | Główne ryzyko |
|---|---|---:|---:|---:|---|---|---|
| Football-Data.co.uk | wyniki, basic stats, historyczne odds | wysoka | częściowa | ograniczona | free | primary-history | zmiany providerów/kolumn |
| API-Football | fixtures, teams, players, lineups, injuries, stats, odds | średnia | wysoka | musimy archiwizować | free/paid | candidate-live | retencja historii i jakość pól |
| The Odds API | odds i market snapshots | wysoka dla płatnej historii | wysoka | wysoka | credit-based | candidate-market | koszt przy częstych snapshotach |
| StatsBomb Open Data | event data, lineups, 360 dla części meczów | selektywna | niska | historyczna | free | research | niepełne coverage lig/sezonów |
| Opta public | referencja statystyk/xG/definicji | selektywna publicznie | wysoka publicznie | niegwarantowana | public/reference | reference | licencja i brak pełnego feedu |
| Sportmonks | skonsolidowany football feed, opcjonalnie xG/odds | zależna od planu | wysoka | do audytu | paid | candidate-premium | koszt i vendor lock-in |
| Open-Meteo | weather forecasts/history/previous runs | wysoka | wysoka | wysoka dla forecast runs | free/low-cost | primary-weather | mapping stadion/czas/model forecastu |
| OpenStreetMap | venue/geography | wysoka | średnia | n/d | free | primary-venue | kompletność metadanych stadionu |
| Flashscore / oficjalne strony | weryfikacja fixtures/lineups/news | różna | wysoka | różna | free/public | fallback-verification | brak stabilnego otwartego API |

## Kategorie danych do pokrycia

### A. Match backbone
- fixtures i kickoff;
- wynik FT/HT;
- liga/sezon/kolejka;
- home/away/venue;
- canonical match/team IDs.

### B. Market
- bookmaker;
- market;
- selection;
- odds;
- opening/current/closing;
- provider timestamp i `captured_at`;
- overround oraz dostępność kursu w cutoffie.

### C. Team performance
- goals/xG/xGA;
- shots/SOT;
- corners;
- possession/progression;
- pressing/set pieces;
- cards/fouls.

### D. Players/lineups
- predicted XI;
- confirmed XI;
- bench;
- minutes;
- injuries/suspensions;
- player value/strength;
- `known_at` każdego statusu.

### E. Context
- referee;
- venue;
- weather forecast point-in-time;
- rest/fatigue/travel;
- competition context;
- manager/formation/style.

## Karta audytu źródła

```yaml
source_name:
url:
provider:
status: candidate
categories: []
leagues: []
seasons: []
fields: []
historical_depth:
live_latency:
point_in_time_support:
retention:
rate_limits:
pricing_model:
estimated_monthly_cost:
license_notes:
commercial_use:
identifier_quality:
missingness:
known_definition_changes: []
raw_snapshot_possible:
fallback_source:
last_verified_at:
owner_decision:
```

## Kolejka nowych źródeł

Dodawaj tutaj nowe kandydaty bez zmiany pipeline'u:

| Źródło | Co może wnieść | Dlaczego sprawdzić | Status audytu |
|---|---|---|---|
| TBD-1 |  |  | not-started |
| TBD-2 |  |  | not-started |
| TBD-3 |  |  | not-started |

## Zasada wyboru

Nie wybieramy źródła dlatego, że ma najwięcej endpointów. Wygrywa źródło, które daje wystarczającą jakość i point-in-time przy akceptowalnym koszcie oraz da się archiwizować i odtworzyć w backteście.
