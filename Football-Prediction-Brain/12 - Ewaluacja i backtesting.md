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
- jakość macierzy exact score i rozkładu goli.

## Metryki rynkowe i ryzyka

- closing-line value;
- EV, ROI i yield;
- liczba zakładów oraz turnover;
- maximum drawdown i zmienność bankrolla;
- wyniki według sezonu, ligi, rynku, horyzontu i przedziału edge;
- sensitivity na metodę usunięcia marży i kurs możliwy do realizacji.

## Test inkrementalny

Każda warstwa przechodzi porównanie `Model_base` vs `Model_base+feature_group`. Z góry ustalamy hipotezę, metrykę główną, okres testowy i kryterium keep/remove. Poprawa powinna być stabilna w wielu oknach, nie tylko w jednym sezonie.

## Benchmarki

- średnia ligowa;
- independent Poisson;
- Maher/Dixon–Coles;
- rynek po zdjęciu vig;
- opcjonalnie publiczna implementacja referencyjna.

## Audyt

Przed akceptacją wersji: test leakage z [[11 - Czas predykcji i leakage]], analiza braków, kalibracja, przedziały niepewności, ablation, stabilność parametrów i reprodukowalny raport.

