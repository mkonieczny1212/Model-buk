---
tags: [interactions, patterns, markets, research]
status: active
---

# Interakcje i wzorce powtarzalne

## Po co ta warstwa

Mecz nie jest sumą niezależnych średnich. Ten sam zespół może zachowywać się inaczej zależnie od stadionu, przeciwnika, sędziego, pogody, składu, zmęczenia i stylu gry. Dlatego model musi szukać zarówno efektów głównych, jak i **warunkowych zależności**.

Jednocześnie chcemy wykrywać zdarzenia o wysokiej powtarzalności, które mogą odpowiadać konkretnym rynkom: SOT, shots, corners, cards, team goals i inne progi dostępne u bukmacherów.

## Hierarchia interakcji

### Poziom 1 — stabilne efekty główne
- team strength;
- home/away;
- opponent strength;
- referee strictness;
- weather;
- rest/fatigue;
- lineup strength.

### Poziom 2 — interakcje dwuczynnikowe
- `Team×Venue`;
- `Team×Opponent`;
- `Team×Referee`;
- `TeamStyle×OpponentStyle`;
- `Weather×PlayingStyle`;
- `RefereeStrictness×TeamAggressiveness`;
- `Fatigue×PressingIntensity`;
- `LineupWeakness×OpponentStrength`.

### Poziom 3 — interakcje wieloczynnikowe
Np. `Team×Venue×OpponentStyle` albo `Referee×Team×Market(cards)`. Używamy ich dopiero przy dużej próbie, regularizacji i wcześniejszej hipotezie. Nie generujemy tysięcy kombinacji bez kontroli.

## Head-to-head

H2H może być sygnałem tylko warunkowo. Sam fakt, że zespół „zawsze dobrze gra z X”, nie jest wystarczający. Sprawdzamy:

- jak stare są mecze;
- czy zmienili się trenerzy i składy;
- jaka była relatywna siła drużyn;
- home/away;
- styl i formation;
- czy efekt przeżywa shrinkage i holdout.

## Pattern miner — stałe/f częste zdarzenia

Dla każdej drużyny i rynku generujemy kandydatów typu:

- `SOT >= 2/3/4/5`;
- `shots >= x`;
- `corners >= 2/3/4/5`;
- `cards >= 1/2`;
- `team goals >= 1/2`;
- inne progi dopiero po potwierdzeniu definicji i coverage.

### Dla każdego kandydata liczymy

1. `base_rate` — częstość bez warunków.
2. `recent_rate` — częstość z decay.
3. `home_rate` / `away_rate`.
4. `vs_strength_bucket` — przeciw słabym/średnim/mocnym rywalom.
5. `conditional_rate` dla hipotez interakcji.
6. `n` i effective sample size.
7. przedział ufności / posterior credible interval.
8. lower bound prawdopodobieństwa.
9. stabilność sezon-po-sezonie.
10. kalibrację na holdoucie.
11. market implied probability po vig.
12. edge, EV i później CLV.

## Przykład interpretacji

Jeżeli drużyna osiąga `SOT>=3` w 92% ostatnich spotkań, nie oznacza to automatycznie zakładu. Model powinien sprawdzić, czy:

- wynik nie pochodzi z małej próby;
- nie jest efektem serii słabych przeciwników;
- utrzymuje się home/away;
- obecny przeciwnik nie tłumi SOT wyjątkowo dobrze;
- skład nie zmienił profilu ataku;
- kurs po zdjęciu marży nadal daje dodatni edge.

Dopiero wtedy zdarzenie staje się kandydatem `BET`.

## Ochrona przed overfittingiem

- hipoteza przed testem, gdy to możliwe;
- minimalna próbka per interakcja;
- partial pooling/shrinkage;
- decay dla starych obserwacji;
- oddzielny chronologiczny holdout;
- korekta multiple testing/FDR przy masowym skanowaniu;
- nie wybieramy progu po obejrzeniu całej historii i nie testujemy go na tej samej próbce;
- paper trading przed użyciem kapitału.

## Docelowy output interakcji

Dla meczu system powinien zwracać nie tylko prawdopodobieństwo, ale także diagnostykę, np.:

```text
Market: Team A SOT >= 3
Model P: 84.1%
Market P after vig: 76.0%
Edge: +8.1 pp
Data quality: 93/100
Sample: 41 weighted matches
Key effects:
- Team baseline +5.2 pp
- Opponent SOT suppression -3.1 pp
- Home venue +2.4 pp
- Expected lineup +1.7 pp
- Referee/weather: negligible
Decision: candidate BET after risk filter
```

To jest kierunek docelowego explanation layer, a nie obietnica, że każda interakcja będzie użyteczna.
