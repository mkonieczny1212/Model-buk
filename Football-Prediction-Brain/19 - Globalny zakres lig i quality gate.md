---
tags: [leagues, coverage, quality-gate, global-scan]
status: active
---

# Globalny zakres lig i quality gate

## Filozofia

Model Buk nie jest modelem Premier League. Premier League jest pierwszym kontrolowanym benchmarkiem. Docelowo system obserwuje szeroki universe rozgrywek i wybiera tylko te `league×market`, dla których dane i ekonomika spełniają wymagania.

## Global Data Coverage Matrix v1

Pierwszy audyt obejmie ok. 20–30 europejskich lig oraz Champions League, Europa League i Conference League. Później coverage może być rozszerzany bez przebudowy architektury.

Dla każdej ligi zapisujemy:

```text
results_history
odds_history
current_odds
xG
shots
SOT
corners
cards
players
lineups
injuries
referee
venue
historical_depth
point_in_time_quality
live_latency
bookmaker_coverage
market_liquidity
average_margin
provider_cost
```

## League/Market Quality Score

Nie ma jednego score dla całej ligi. Oceniamy **parę liga × rynek**, bo np. 1X2 może mieć świetne dane, a player SOT słabe.

Przykładowe komponenty:

- Data completeness;
- Point-in-time reliability;
- Historical depth;
- Definition stability;
- Bookmaker coverage;
- Liquidity / achievable price;
- Average vig;
- Model calibration;
- Edge stability OOS;
- Cost to maintain coverage.

## Gate

Każda para `league×market` otrzymuje status:

- `GREEN` — można normalnie skanować;
- `YELLOW` — ograniczony screening, enrichment tylko przy mocnym sygnale;
- `RED` — brak predykcji / dane niewystarczające;
- `RESEARCH` — dane historyczne wystarczają do eksperymentu, ale nie do produkcji.

## Prestiż ligi nie jest kryterium

Nie zakładamy, że top liga jest najlepsza ani że niszowa liga jest łatwa. Niższa efektywność rynku może być zjedzona przez:

- gorsze dane;
- większy vig;
- mniejszą płynność;
- niższe limity;
- gorszy lineup/injury coverage;
- większy koszt pozyskania wiarygodnej informacji.

Ostatecznym kryterium jest **risk-adjusted net edge po kosztach**.

## European competitions i wyjątki środowiskowe

Mecze międzynarodowe są szczególnie ciekawe dla travel/climate/altitude shocks. Przykładowo klub z południa Europy grający zimą w Kazachstanie może mieć rzeczywistą zmianę środowiska; zwykłe 10–14°C w Anglii nie powinno automatycznie generować istotnej cechy.

## Skalowanie

1. Premier League — walidacja pipeline'u.
2. Top 5 + kilka lig o dobrym coverage — test portability.
3. Global Data Coverage Matrix 20–30 lig.
4. Dodawanie nowych lig tylko wtedy, gdy quality gate i ekonomika są dodatnie.

## Literatura jako wskazówka

Badania rynku pokazują, że efektywność może różnić się między ligami i market structures. To uzasadnia league/market-specific evaluation zamiast jednego globalnego założenia o „łatwych” i „trudnych” ligach.
