---
tags: [data-sources, registry, audit]
status: living-document
---

# Rejestr źródeł danych

Żywy katalog źródeł. Każde źródło ma status `primary`, `candidate`, `reference`, `fallback` albo `rejected`. Ceny i limity są zmienne — przed zakupem zawsze wykonujemy ponowną weryfikację.

## Macierz źródeł v2

| Źródło | Rola | Point-in-time | Koszt / limit (2026-08-24) | Status | Główne ryzyko |
|---|---|---|---|---|---|
| Football-Data.co.uk | historia, basic stats, odds | ograniczony | free | primary-history | zmiany providerów/kolumn |
| API-Football | szeroki live/prematch feed | własna archiwizacja | Free 100 req/d; Pro $19 7.5k/d; Ultra $29 75k/d; Mega $39 150k/d | candidate-live | retention/coverage per league |
| The Odds API | current/historical odds | bardzo dobry | Start $30/20k credits; current odds 1 credit × market × region; historical 10× | candidate-market | koszt props/historical |
| football-data.org | fixtures/lineups/cards + stats/odds add-ons | do audytu | Free 12 comps; €49/30; €99/50; €199/100; stats +€15; odds +€15 | candidate-reconciliation | add-ons i coverage |
| Betfair Historical Data | exchange price/market/settlement | timestamped | paid packages | candidate-exchange | koszt zakupu danych i parsing |
| Pinnacle API | benchmark jakościowy | dobry jeśli dostęp | public API zamknięte od 2025-07-23 | restricted-reference | brak gwarantowanego dostępu |
| StatsBomb Open Data | event research | historyczny | free | research | selektywne coverage |
| Opta public | referencja statystyk/xG | niegwarantowany | public/reference | reference | licencja |
| Sportmonks | premium all-in-one | do audytu | paid, modular | candidate-premium | koszt/vendor lock-in |
| Open-Meteo | extreme environment | forecast history | free/low-cost | secondary-environment | niski priorytet w normalnych warunkach |
| OpenStreetMap | venue/geography | n/d | free | primary-venue | kompletność |
| oficjalne ligi/kluby/Flashscore | verification | różny | public | fallback | brak stabilnego API |

## Klasy kosztowe

- `C0 cached` — dane już w bazie; koszt marginalny ≈ 0.
- `C1 free/cheap batch` — fixtures/basic odds w szerokim requestcie.
- `C2 selective paid` — świeże market data, lineup/injuries dla shortlisty.
- `C3 expensive/deep` — historical props, exchange packages, premium event/player data.

Każdy endpoint dostaje `cost_class`, `credits_per_call`, `batch_scope`, `refresh_interval` i `expected_information_gain`.

## Ważne obserwacje techniczne

- API-Football sam rekomenduje pobieranie szczegółów dopiero wtedy, gdy są potrzebne i pozwala pobierać fixtures per liga/data oraz grupować wiele IDs; logiczny skan setek meczów nie musi oznaczać setek requestów.
- The Odds API wycenia popularne current odds per `market×region`, a nie per mecz zwrócony przez endpoint. To umożliwia szeroki screening rynku jednym/bardzo małą liczbą requestów per liga/sport key.
- Additional/event props mogą wymagać event-specific requestów, dlatego nie wolno odpalać ich dla całego universe bez shortlisty.
- Historical odds są dużo droższe kredytowo od bieżących; kupujemy je selektywnie do badań, a nowe snapshoty archiwizujemy sami.

## Karta audytu źródła

```yaml
source_name:
url:
status: candidate
categories: []
leagues: []
seasons: []
historical_depth:
live_latency:
point_in_time_support:
retention:
rate_limits:
pricing_model:
credits_per_request:
batch_scope:
refresh_interval:
estimated_monthly_cost:
license_notes:
identifier_quality:
missingness:
raw_snapshot_possible:
fallback_source:
last_verified_at:
owner_decision:
```

## Kolejka nowych źródeł

| Źródło | Co może wnieść | Status audytu |
|---|---|---|
| TBD-1 | alternatywny feed player props | not-started |
| TBD-2 | zaawansowane xG/event data dla wielu lig | not-started |
| TBD-3 | exchange/liquidity poza Betfair | not-started |
| TBD-4 | line movement / sharp-book benchmark | not-started |

## Zasada wyboru

Nie wybieramy providera po liczbie endpointów. Wygrywa kombinacja: **jakość + point-in-time + batchability + coverage + akceptowalny koszt + możliwość odtworzenia**.
