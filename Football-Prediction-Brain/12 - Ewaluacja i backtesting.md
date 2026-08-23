---
tags: [evaluation, backtest, calibration]
---

# Ewaluacja i backtesting

## Schemat

Walk-forward: model trenuje się wyłącznie na przeszłości, przewiduje kolejny okres, następnie okno przesuwa się naprzód. Wszystkie warianty używają tych samych cutoffów i meczów testowych.

## Metryki probabilistyczne

- log loss / log score;
- Brier Score dla zdarzeń binarnych;
- Ranked Probability Score dla 1X2;
- krzywe kalibracji, reliability i sharpness;
- accuracy jako metryka pomocnicza;
- kalibracja rozkładu goli i team totals;
- kalibracja progów SOT/shots/corners/cards dla zatwierdzonych rynków zdarzeń.

## Metryki rynkowe i ryzyka

- closing-line value;
- EV, ROI i yield;
- liczba zakładów oraz turnover;
- maximum drawdown i zmienność bankrolla;
- wyniki według sezonu, ligi, rynku, horyzontu i przedziału edge;
- sensitivity na metodę usunięcia marży i kurs możliwy do realizacji.

## Test wzorców powtarzalnych

Wysoka historyczna trafialność nie jest wystarczająca. Każdy próg/warunek musi przejść:

- minimalną próbę i shrinkage;
- holdout chronologiczny;
- stabilność sezon-po-sezonie;
- test home/away i strength-of-opponent;
- kalibrację prawdopodobieństwa, nie tylko hit rate;
- porównanie z ceną rynkową;
- paper trading przed realnym użyciem.

## Test inkrementalny

Każda warstwa przechodzi porównanie `Model_base` vs `Model_base+feature_group`. Z góry ustalamy hipotezę, metrykę główną, okres testowy i kryterium keep/remove. Poprawa powinna być stabilna w wielu oknach, nie tylko w jednym sezonie.

## Benchmarki

- średnia ligowa;
- independent Poisson;
- Maher/Dixon–Coles;
- proste modele empiryczne/Beta-Binomial dla progów zdarzeń;
- rynek po zdjęciu vig;
- opcjonalnie publiczna implementacja referencyjna.

## Audyt

Przed akceptacją wersji: test leakage z [[11 - Czas predykcji i leakage]], analiza braków, kalibracja, przedziały niepewności, ablation, stabilność parametrów i interakcji oraz reprodukowalny raport.
