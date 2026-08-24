---
tags: [teaser, status, overview]
status: active
---

# Model Buk — teaser projektu

## Co budujemy

Model Buk ma być **globalnym systemem wyszukiwania value w piłce nożnej**, a nie typsterem jednej ligi. System zbiera tylko dane potrzebne na danym etapie, ocenia jakość meczu/rynku, wylicza skalibrowane prawdopodobieństwa, porównuje je z ceną i kończy decyzją `BET`, `NO BET` albo `NO PREDICTION`.

Nie chcemy zgadywać każdego meczu. Chcemy znaleźć niewielką liczbę sytuacji, w których przewaga jest wystarczająco duża **po uwzględnieniu kosztu danych, marży, niepewności i ryzyka**.

## Co już wiemy

- Premier League służy do walidacji procesu, ale docelowo system nie ogranicza się do ligi.
- Startowe rynki: 1X2, O/U 2.5, BTTS; exact score odpada jako rynek docelowy.
- Zdarzenia powtarzalne (SOT, corners, cards itd.) są osobnym ważnym torem badawczym.
- Każda informacja musi być point-in-time.
- `PURE`, `MARKET` i docelowo `HYBRID` pozostają oddzielone.
- Każda cecha, liga, rynek i interakcja musi przeżyć chronologiczny holdout.
- Pogoda nie jest głównym filarem; liczą się przede wszystkim ekstremalne warunki i interakcje.
- Największym ryzykiem projektu są dane i prawdziwy edge, nie koszt obliczeń.

## Kluczowa ekonomika

Nie wykonujemy 9000 drogich analiz tylko dlatego, że istnieje 9000 potencjalnych zakładów. Stosujemy **cost-aware funnel**:

1. cache/history + tani universe;
2. lokalny screening wielu meczów/rynków;
3. shortlist;
4. świeże/płatne dane tylko dla shortlisty;
5. pełny model i risk filter;
6. actionable bets tylko wtedy, gdy oczekiwany zysk uzasadnia również koszt skanu.

## Co jest teraz najważniejsze

1. [[19 - Globalny zakres lig i quality gate]] — coverage 20–30 lig i pucharów.
2. [[18 - Ekonomika pipeline i cost-aware scanning]] — koszt per run/league/candidate.
3. [[16 - Rejestr źródeł danych]] — aktualny provider stack i fallbacki.
4. Minimum Viable Dataset i własne snapshoty.
5. v0.1 + walk-forward + paper trading.

## Docelowy outcome

Dla każdego meczu/rynku: `data quality → model P → fair odds → market price → edge/EV → uncertainty → data cost → risk → BET/NO BET/NO PREDICTION`.
