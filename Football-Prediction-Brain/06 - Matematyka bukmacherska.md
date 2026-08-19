---
tags: [betting, odds, ev, kelly]
---

# Matematyka bukmacherska

## Od kursu do prawdopodobieństwa

Dla kursu dziesiętnego $o_i$ surowe implied probability wynosi:

$$q_i=\frac{1}{o_i}$$

W rynku 1X2 zwykle $\sum q_i>1$ z powodu marży. Proporcjonalne zdjęcie marży:

$$p_i=\frac{q_i}{\sum_jq_j}$$

To benchmark, nie jedyna poprawna metoda. Należy porównać także Shin i inne metody oraz sprawdzić favourite–longshot bias osobno dla lig i rynków.

## Fair odds, edge i EV

$$FairOdds_i=\frac{1}{p_{model,i}}$$

$$Edge_i=p_{model,i}-p_{market,i}$$

Dla stawki jednostkowej:

$$EV=p_{model}(o-1)-(1-p_{model})=p_{model}o-1$$

Dodatnie EV nie jest wystarczające bez uwzględnienia niepewności, błędu kalibracji, limitów, płynności i kosztów realizacji.

## Bankroll

Pełny Kelly dla zakładu binarnego:

$$f^*=\frac{bp-q}{b},\qquad b=o-1,\ q=1-p$$

W praktyce kandydatem jest fractional Kelly oraz limity ekspozycji. Najpierw musi istnieć stabilna kalibracja poza próbą.

## Separacja modułów

`MODEL SPORTOWY → prawdopodobieństwo → FAIR ODDS → RYNEK PO VIG → EDGE → EV → NIEPEWNOŚĆ → BET/NO BET`

Nie mylimy trafności z rentownością. Porównujemy `PURE`, `MARKET` i `HYBRID` zgodnie z [[03 - Architektura modelu]]. Metryki opisuje [[12 - Ewaluacja i backtesting]].

