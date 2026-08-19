---
tags: [matematyka, poisson, dixon-coles, bayes]
---

# Fundamenty matematyczne

## Niezależny Poisson

Liczby goli gospodarzy i gości zaczynamy modelować jako:

$$X\sim Poisson(\lambda_H),\qquad Y\sim Poisson(\lambda_A)$$

$$P(X=k)=e^{-\lambda_H}\frac{\lambda_H^k}{k!}$$

Z iloczynu prawdopodobieństw budujemy macierz dokładnych wyników. Sumowanie odpowiednich komórek daje 1X2, Over/Under, BTTS, handicapy i team totals.

## Siły ataku i obrony (Maher)

$$\log \lambda_H=\mu+A_H-D_A+HA+\beta^TX_H$$

$$\log \lambda_A=\mu+A_A-D_H+\gamma^TX_A$$

Parametry ataku i obrony są dynamicznym stanem zespołu, a nie średnią z całego sezonu. Powiązania: [[03 - Architektura modelu]], [[04 - Rejestr cech]].

## Dixon–Coles

Rozszerzenie koryguje zbyt proste założenie niezależności przy niskich wynikach (0:0, 1:0, 0:1, 1:1). Starsze obserwacje otrzymują mniejszą wagę:

$$w_i=e^{-\xi\Delta t_i}$$

Parametr $\xi$ i half-life należy wyznaczyć poza próbą, nie intuicyjnie.

## Modele alternatywne

- bivariate Poisson — wspólna struktura liczb goli, potencjalnie lepsza dla remisów;
- negative binomial — kandydat przy nadmiernej dyspersji;
- hierarchiczny Bayes — partial pooling i niepewność parametrów przy małej próbie;
- dynamic state-space — siła zespołu ewoluuje w czasie;
- Elo + Poisson — rating jako dodatkowa dynamiczna informacja;
- ML/ensemble — dopiero po zbudowaniu mocnych benchmarków statystycznych.

## Zasady estymacji

- identyfikowalność parametrów, np. suma sił ataku równa zero;
- regularizacja i shrinkage przy małej próbie;
- brak losowego podziału danych czasowych;
- raportowanie rozkładu i niepewności, a nie tylko wartości punktowej;
- każdy bardziej złożony model porównujemy z poprzednim według [[12 - Ewaluacja i backtesting]].

