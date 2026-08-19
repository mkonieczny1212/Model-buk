---
tags: [architecture, model, state-context]
---

# Architektura modelu

## Najważniejszy podział

$$\boxed{TEAM\ STATE}+\boxed{MATCH\ CONTEXT}\rightarrow\text{rozkłady zdarzeń}$$

### TEAM STATE

Latentne, zmienne w czasie komponenty:

- attack strength;
- defence strength;
- possession/progression;
- pressing i press resistance;
- set-piece strength;
- goalkeeper/finishing form;
- siła i głębokość kadry.

### MATCH CONTEXT

- home advantage i stadion;
- konkretna XI, absencje oraz jakość zmienników;
- fatigue, odpoczynek, podróż;
- pogoda i murawa;
- sędzia;
- stawka, rozgrywki i zasady;
- tactical matchup i interakcje.

## Warstwy systemu

1. Ingestion i wersjonowanie surowych danych.
2. Point-in-time feature store według [[11 - Czas predykcji i leakage]].
3. Estymacja dynamicznego stanu drużyn.
4. Modele goli i innych statystyk.
5. Pełna macierz rozkładu wyników.
6. Agregacja do rynków 1X2, O/U, BTTS i exact score.
7. Benchmark rynkowy po zdjęciu marży.
8. Kalibracja i szacowanie niepewności.
9. Moduł decyzji: edge, EV, ograniczenia ryzyka, BET/NO BET.
10. Backtest i monitoring driftu.

## Trzy rodziny modelu

- `PURE`: wyłącznie dane sportowe;
- `MARKET`: kursy po zdjęciu marży jako benchmark;
- `HYBRID`: dane sportowe plus informacja rynku.

Nie podajemy kursów do bazowego `PURE`, aby model nie nauczył się jedynie kopiować bukmacherów. Zobacz [[06 - Matematyka bukmacherska]].

## Docelowe wyniki

Każda predykcja powinna zawierać $\lambda_H$, $\lambda_A$, macierz wyników, prawdopodobieństwa rynków, przedziały/miary niepewności, moment wygenerowania oraz wersję modelu i danych.

