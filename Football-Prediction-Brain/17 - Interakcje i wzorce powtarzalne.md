---
tags: [interactions, patterns, markets, research]
status: active
---

# Interakcje i wzorce powtarzalne

## Po co ta warstwa

Mecz nie jest sumą niezależnych średnich. Ten sam zespół może zachowywać się inaczej zależnie od stadionu, przeciwnika, sędziego, składu, zmęczenia, stylu i wyjątkowego środowiska. Dlatego model szuka zarówno efektów głównych, jak i warunkowych zależności.

Jednocześnie wykrywamy zdarzenia o wysokiej powtarzalności odpowiadające rynkom: SOT, shots, corners, cards, team goals i inne progi.

## Hierarchia interakcji

### Poziom 1 — stabilne efekty główne
- team strength;
- home/away;
- opponent strength;
- referee strictness;
- rest/fatigue;
- lineup strength;
- environment shock tylko gdy istotny.

### Poziom 2 — interakcje dwuczynnikowe
- `Team×Venue`;
- `Team×Opponent`;
- `Team×Referee`;
- `TeamStyle×OpponentStyle`;
- `EnvironmentalShock×PlayingStyle`;
- `RefereeStrictness×TeamAggressiveness`;
- `Fatigue×PressingIntensity`;
- `LineupWeakness×OpponentStrength`.

### Poziom 3 — interakcje wieloczynnikowe
Np. `Team×Venue×OpponentStyle` albo `Referee×Team×Market(cards)`. Używamy ich dopiero przy dużej próbie, regularizacji i wcześniejszej hipotezie.

## Head-to-head

H2H może być sygnałem tylko warunkowo. Sprawdzamy wiek meczów, trenerów, składy, relatywną siłę drużyn, home/away, style oraz holdout. Samo „zawsze dobrze gra z X” nie wystarcza.

## Pattern miner

Dla każdej drużyny i rynku generujemy kandydatów typu `SOT>=x`, `shots>=x`, `corners>=x`, `cards>=x`, `team_goals>=x`. Dla każdego liczymy base/recent/home/away rates, opponent buckets, interakcje, effective sample size, lower bound, stabilność sezonową, kalibrację, implied probability, edge, EV i CLV.

## Cost-aware pattern discovery

Pattern miner ma dwa etapy:

1. **offline/local discovery** na własnej historii i cache — tanie skanowanie tysięcy hipotez;
2. **online enrichment** tylko dla shortlisty — pobranie aktualnych odds/lineup/injuries/props wtedy, gdy historyczny i kontekstowy screening daje wystarczający potencjał.

Nie pobieramy wszystkich dostępnych player props i micro-markets dla każdego meczu. Najpierw model musi wykazać, że dany `league×market×team/context` ma szansę przekroczyć próg opłacalności.

## Ochrona przed overfittingiem

- hipoteza przed testem, gdy możliwe;
- minimalna próbka;
- partial pooling/shrinkage;
- decay;
- chronologiczny holdout;
- multiple-testing/FDR przy masowym skanowaniu;
- paper trading;
- koszt danych uwzględniany w końcowym wyniku ekonomicznym.

## Docelowy output

```text
Market: Team A SOT >= 3
Model P: 84.1%
Market P after vig: 76.0%
Edge: +8.1 pp
Data quality: 93/100
Data cost for enrichment: 0.03 EUR-equivalent
Sample: 41 weighted matches
Key effects:
- Team baseline +5.2 pp
- Opponent SOT suppression -3.1 pp
- Home venue +2.4 pp
- Expected lineup +1.7 pp
Decision: candidate BET after cost/risk filter
```
