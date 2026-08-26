---
tags: [data-sources, registry, audit]
status: living-document
---

# Rejestr źródeł danych

Żywy katalog źródeł. Każde źródło ma status `primary`, `candidate`, `reference`, `fallback` albo `rejected`. Ceny i limity są zmienne — przed zakupem zawsze wykonujemy ponowną weryfikację.

## Macierz źródeł v3

| Źródło | Rola | Point-in-time | Koszt / limit | Status | Główne ryzyko |
|---|---|---|---|---|---|
| Football-Data.co.uk | historia, basic stats, odds | ograniczony | free | primary-history | zmiany providerów/kolumn |
| API-Football | szeroki live/prematch feed | własna archiwizacja | Free 100 req/d; płatne plany od ok. $19 | candidate-live | retention/coverage per league |
| TheStatsAPI | stats + xG + odds + szerokie ligi | do audytu | ok. $50/mies. plan szeroki | candidate-all-in-one | marketing coverage vs real completeness |
| The Odds API | current/historical odds | bardzo dobry | credit-based; history droższa | candidate-market | koszt props/historical |
| football-data.org | fixtures/lineups/cards + stats/odds add-ons | do audytu | free/paid | candidate-reconciliation | add-ons i coverage |
| Betfair Historical Data | exchange price/market/settlement | timestamped | paid packages | candidate-exchange | koszt zakupu danych i parsing |
| Pinnacle API | benchmark jakościowy | dobry jeśli dostęp | public API zamknięte od 2025-07-23 | restricted-reference | brak gwarantowanego dostępu |
| StatsBomb Open Data | event research | historyczny | free | research | selektywne coverage |
| Opta public / FotMob pages | referencja statystyk/xG | public page | free/reference | reference | licencja, nie API produkcyjne |
| Sportmonks | premium all-in-one | do audytu | paid, modular | candidate-premium | koszt/vendor lock-in |
| Open-Meteo | extreme environment | forecast history | free/low-cost | secondary-environment | niski priorytet w normalnych warunkach |
| OpenStreetMap | venue/geography | n/d | free | primary-venue | kompletność |
| UEFA / oficjalne ligi/kluby | fixture/result/competition truth | publikacja oficjalna | free/public | primary-verification | niepełne statystyki |
| Oddschecker / public bookmaker pages | darmowy benchmark bieżących kursów w pilocie | snapshot strony | free/public | research-market | ręczne pozyskanie, brak gwarancji API |
| Scores24 / PlaymakerStats / podobne public stats pages | pomocnicza walidacja xG/shots/SOT/corners | po meczu | free/public | research-validation | rozbieżności definicji/providerów |
| Euroranking / ClubElo-like ratings | darmowy prior siły drużyn | aktualizowany okresowo | free/public | research-strength | świeżość ratingu, metodologia |

## Klasy kosztowe

- `C0 cached` — dane już w bazie; koszt marginalny ≈ 0.
- `C1 free/cheap batch` — fixtures/basic odds w szerokim requestcie.
- `C2 selective paid` — świeże market data, lineup/injuries dla shortlisty.
- `C3 expensive/deep` — historical props, exchange packages, premium event/player data.

Każdy endpoint dostaje `cost_class`, `credits_per_call`, `batch_scope`, `refresh_interval` i `expected_information_gain`.

## Lekcja z pilota 27.08.2026

Darmowy research jest wystarczający, aby zbudować ręczny prototyp, ale nie jest wystarczający jako produkcyjny data layer. Wystąpiły rozbieżności xG między publicznymi źródłami dla tych samych spotkań. Dlatego:

- wyniki, terminarz i aggregate state preferujemy z UEFA/oficjalnych źródeł;
- kursy zapisujemy z timestampem i źródłem;
- xG/statystyki muszą mieć provider + definition version;
- przy konflikcie źródeł obniżamy `data_quality` albo zwracamy `NO PREDICTION`;
- przed wdrożeniem płatnego feedu wykonujemy provider shootout na tych samych meczach i polach.

## Ważne obserwacje techniczne

- API-Football pozwala pobierać wiele danych batchowo; logiczny skan setek meczów nie musi oznaczać setek requestów.
- The Odds API wycenia popularne current odds per `market×region`, a nie per mecz zwrócony przez endpoint.
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

## Zasada wyboru

Nie wybieramy providera po liczbie endpointów. Wygrywa kombinacja: **jakość + point-in-time + batchability + coverage + akceptowalny koszt + możliwość odtworzenia**.
