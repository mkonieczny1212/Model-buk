---
tags: [architecture, model, state-context]
---

# Architektura modelu

## Najważniejszy podział

$$\boxed{TEAM\ STATE_H}+\boxed{TEAM\ STATE_A}+\boxed{MATCH\ CONTEXT}+\boxed{INTERACTIONS}\rightarrow\text{rozkłady zdarzeń}$$

### TEAM STATE

Latentne, zmienne w czasie komponenty dla obu zespołów:

- attack strength;
- defence strength;
- possession/progression;
- pressing i press resistance;
- shot/SOT creation i suppression;
- set-piece i corner strength;
- discipline/card profile;
- goalkeeper/finishing form;
- siła i głębokość kadry.

### MATCH CONTEXT

- home advantage i konkretny stadion;
- konkretna XI, absencje oraz jakość zmienników;
- fatigue, odpoczynek, podróż;
- pogoda i murawa;
- sędzia;
- stawka, rozgrywki i zasady;
- tactical matchup.

### INTERACTIONS

Nie zakładamy, że czynniki działają niezależnie. Testujemy m.in. `Team×Venue`, `Team×Opponent`, `Team×Referee`, `Referee×Aggressiveness`, `Weather×PlayingStyle`, `Fatigue×Pressing`, `MissingPlayer×OpponentThreat`, `HomeAdvantage×Team` oraz interakcje trójstronne, jeżeli próbka pozwala. Szczegóły: [[17 - Interakcje i wzorce powtarzalne]].

## Warstwy systemu

1. Ingestion i wersjonowanie surowych danych.
2. Canonical entity layer dla meczów, drużyn, graczy, stadionów, sędziów i providerów.
3. Point-in-time feature store według [[11 - Czas predykcji i leakage]].
4. Estymacja dynamicznego stanu obu drużyn.
5. Interaction engine budujący cechy warunkowe konkretnego meczu.
6. Modele goli i osobne modele innych zdarzeń (SOT, corners, cards itd.).
7. Pattern miner wykrywający stabilne progi i zdarzenia o wysokiej częstości.
8. Agregacja do rynków docelowych: 1X2, O/U, BTTS oraz zatwierdzonych rynków zdarzeń.
9. Benchmark rynkowy po zdjęciu marży.
10. Kalibracja i szacowanie niepewności.
11. Moduł decyzji: edge, EV, jakość danych, ograniczenia ryzyka, BET/NO BET.
12. Backtest, paper trading i monitoring driftu.

## Trzy rodziny modelu

- `PURE`: wyłącznie dane sportowe;
- `MARKET`: kursy po zdjęciu marży jako benchmark;
- `HYBRID`: dane sportowe plus informacja rynku.

Nie podajemy kursów do bazowego `PURE`, aby model nie nauczył się jedynie kopiować bukmacherów. Zobacz [[06 - Matematyka bukmacherska]].

## Docelowe wyniki

Każda predykcja powinna zawierać: prawdopodobieństwa zatwierdzonych rynków, fair odds, edge względem rynku, miarę niepewności, jakość/kompletność danych, najważniejsze czynniki i interakcje, moment wygenerowania oraz wersję modelu i danych. Dla modeli goli przechowujemy również $\lambda_H$ i $\lambda_A$ jako diagnostykę. Exact score nie jest rekomendowanym rynkiem.
