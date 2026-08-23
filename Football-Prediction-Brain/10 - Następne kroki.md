---
tags: [next-actions, roadmap]
---

# Następne kroki

## Najbliższy milestone: Football Model v0.1

- [x] Zamrozić pierwszy zakres: Premier League, 1X2, O/U 2.5, BTTS; exact score odrzucony jako rynek docelowy.
- [ ] Wykonać Data Audit v1 według [[16 - Rejestr źródeł danych]].
- [ ] Pozyskać i zwalidować historyczne mecze, statystyki oraz kursy.
- [ ] Uruchomić archiwizację bieżących snapshotów odds/injuries/lineups/weather.
- [ ] Zaimplementować league-average Poisson.
- [ ] Dodać parametry attack/defence i home advantage.
- [ ] Wyprowadzić prawdopodobieństwa 1X2, O/U 2.5 i BTTS.
- [ ] Zbudować chronologiczny walk-forward backtest.
- [ ] Raportować log loss, Brier/RPS, kalibrację i benchmark rynku.
- [ ] Dodać Dixon–Coles i time decay jako pierwszy eksperyment inkrementalny.

## Równoległy fundament danych

- [ ] Utworzyć tabele z [[13 - Schemat danych]].
- [ ] Wprowadzić `event_time`, `known_at`, `provider_timestamp` i `fetched_at`.
- [ ] Utworzyć Feature Registry według [[04 - Rejestr cech]].
- [ ] Utrzymywać Source Registry według [[16 - Rejestr źródeł danych]].
- [ ] Zmapować licencje, koszty i zakres każdego źródła.
- [ ] Oznaczyć structural breaks i zmiany providerów.
- [ ] Zbudować canonical IDs i mapowania providerów.

## Równoległy tor: zdarzenia powtarzalne

- [ ] Zweryfikować historyczne coverage shots/SOT/corners/cards.
- [ ] Zbudować proste profile częstości progów per team, venue, opponent strength i sezon.
- [ ] Dodać shrinkage, przedziały ufności i minimalną próbę.
- [ ] Przetestować interakcje z [[17 - Interakcje i wzorce powtarzalne]].
- [ ] Nie traktować serii/H2H jako sygnału bez testu OOS.
- [ ] Dopiero po kalibracji połączyć prawdopodobieństwa z realnymi kursami.

## Definition of done v0.1

Reprodukowalny pipeline od surowych danych do predykcji, brak znanego leakage, raport walk-forward z benchmarkami, wersjonowanie artefaktów oraz przykładowy output zawierający $\lambda_H$, $\lambda_A$, 1X2, O/U 2.5, BTTS, fair odds, jakość danych i decyzję `BET/NO BET`.

## Czego jeszcze nie robić

Nie budować strony produktowej ani dużego modelu ML przed solidnym benchmarkiem. Nie dodawać wszystkich cech naraz. Nie optymalizować wyłącznie ROI ani accuracy. Nie wybierać progów/rynków dlatego, że wyglądają dobrze na całej historii — decyzje muszą przeżyć holdout i paper trading.
