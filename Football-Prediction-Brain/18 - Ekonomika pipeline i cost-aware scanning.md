---
tags: [economics, api-cost, scanning, profitability]
status: active
---

# Ekonomika pipeline i cost-aware scanning

## Zasada nadrzędna

**Projekt musi zarabiać netto, nie tylko generować dobre predykcje.** Koszt danych, API, storage, compute, execution/slippage i późniejsze koszty transakcyjne są częścią wyniku ekonomicznego.

Nie interesuje nas pipeline, który kosztuje 100 EUR na weekend i znajduje 2 zakłady o łącznym oczekiwanym zysku 8 EUR.

## Funkcja ekonomiczna

Na poziomie dnia/tygodnia mierzymy:

```text
ExpectedNetValue = ExpectedBettingProfit
                 - Data/API Cost
                 - Compute/Storage Cost
                 - Execution/Slippage Cost
                 - Other Operational Cost
```

Dodatkowo raportujemy `Cost per Screened Match`, `Cost per Candidate`, `Cost per Actionable Bet`, `Credits per Actionable Bet` i `Expected Profit / Data Cost`.

## Dlaczego 9000 logicznych zakładów nie musi oznaczać 9000 requestów

Większość szerokiego skanu może odbywać się lokalnie na danych już zapisanych. Providerzy często zwracają wiele meczów jednym requestem:

- API-Football wspiera fixtures per `league/date` i grupowanie wielu fixture IDs; provider sam zaleca lazy loading i cache;
- The Odds API dla popularnych current odds nalicza koszt per `market×region`, a endpoint zwraca listę wielu meczów;
- najdroższe są zwykle event-specific props, deep player data i historical odds — dlatego trafiają dopiero na shortlistę.

## Lejek kosztowy

### Tier 0 — offline/cache (C0)

Koszt marginalny prawie zerowy:
- schedule już zapisany;
- historyczne team states;
- rolling features;
- league/market quality;
- historyczne pattern profiles;
- model baseline.

Cel: odrzucić ligi/rynki bez jakości lub bez historycznego sygnału.

### Tier 1 — broad cheap screen (C1)

Tanie batchowane dane:
- dzisiejsze/jutrzejsze fixtures;
- podstawowe market prices;
- status meczu/provider coverage;
- podstawowe aktualne informacje.

Cel: z dużego universe wyłonić np. 5–15% kandydatów do enrichmentu.

### Tier 2 — candidate enrichment (C2)

Dla shortlisty:
- aktualne odds dla konkretnych rynków;
- injuries/suspensions;
- predicted lineups;
- kluczowe player/team updates;
- referee/venue, jeśli istotne.

Cel: ponownie odrzucić przypadki, gdzie edge znika.

### Tier 3 — deep enrichment (C3)

Tylko dla top kandydatów:
- niche/player props;
- premium event data;
- exchange/liquidity;
- specjalne historyczne snapshoty;
- dodatkowy provider reconciliation.

### Tier 4 — final decision

Pełny model + uncertainty + realny kurs + risk filter + koszt pozyskania danych.

## Budget gates

Każdy run ma z góry ustalone limity:

```yaml
daily_api_budget:
weekly_data_budget:
max_credits_per_league:
max_credits_per_match:
max_cost_per_candidate:
max_cost_per_actionable_bet:
minimum_expected_profit_to_data_cost_ratio:
```

Jeżeli budżet się kończy, system nie „dopytuje dla pewności”. Zatrzymuje enrichment i zapisuje `NO PREDICTION / BUDGET GATE`.

## Marginal value of information

Przed drogim requestem pytamy:

> Czy ta informacja może z wystarczającym prawdopodobieństwem zmienić decyzję BET/NO BET na tyle, żeby uzasadnić jej koszt?

Przykład: jeżeli candidate ma edge +0.7 pp i już na tanim etapie nie spełnia progu, nie kupujemy lineup/player props. Jeżeli candidate ma +8 pp, ale niepewność wynika z kluczowego napastnika, aktualny lineup może mieć wysoką wartość informacyjną.

## Provider economics snapshot — 2026-08-24

### API-Football
- Free: 100 req/day;
- Pro: $19/mo, 7 500/day;
- Ultra: $29/mo, 75 000/day;
- Mega: $39/mo, 150 000/day.

### The Odds API
- Start Historical: $30/mo, 20k credits;
- current `/odds`: `1 × markets × regions`;
- historical odds: `10 × markets × regions`.

### football-data.org
- Free: 12 competitions;
- Standard: €49/mo, 30;
- Advanced: €99/mo, 50;
- Pro: €199/mo, 100;
- Stats add-on: +€15;
- Odds add-on: +€15.

Ceny są snapshotem do ponownej weryfikacji przed zakupem.

## KPI ekonomiczne projektu

- miesięczny koszt stały;
- koszt danych per liga;
- koszt danych per market family;
- koszt per prediction;
- koszt per actionable bet;
- expected profit / cost;
- realised profit / cost;
- API utilisation %;
- % danych pobranych, które nigdy nie wpłynęły na decyzję;
- ROI po kosztach operacyjnych.

## Zasada skalowania

Nową ligę/rynek włączamy szerzej dopiero wtedy, gdy historyczne wyniki + paper trading wskazują, że **marginalny expected value jest większy od marginalnego kosztu danych i ryzyka**.
