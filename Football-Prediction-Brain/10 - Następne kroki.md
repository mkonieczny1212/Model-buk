---
tags: [next-actions, roadmap]
---

# Następne kroki

## Najbliższy milestone: Football Model v0.1

- [ ] Zamrozić zakres: Premier League, 1X2, exact score, O/U 2.5, BTTS.
- [ ] Pozyskać i zwalidować historyczne mecze oraz kursy.
- [ ] Zaimplementować league-average Poisson.
- [ ] Dodać parametry attack/defence i home advantage.
- [ ] Wygenerować macierz wyników oraz wszystkie cztery rynki.
- [ ] Zbudować chronologiczny walk-forward backtest.
- [ ] Raportować log loss, Brier/RPS, kalibrację i benchmark rynku.
- [ ] Dodać Dixon–Coles i time decay jako pierwszy eksperyment inkrementalny.

## Równoległy fundament danych

- [ ] Utworzyć tabele z [[13 - Schemat danych]].
- [ ] Wprowadzić `event_time` i `known_at`.
- [ ] Utworzyć Feature Registry według [[04 - Rejestr cech]].
- [ ] Zmapować licencje i zakres każdego źródła z [[05 - Źródła danych]].
- [ ] Oznaczyć structural breaks i zmiany providerów.

## Definition of done v0.1

Reprodukowalny pipeline od surowych danych do predykcji, brak znanego leakage, raport walk-forward z benchmarkami, wersjonowanie artefaktów oraz przykładowy output zawierający $\lambda_H$, $\lambda_A$, macierz score probabilities, 1X2, O/U 2.5 i BTTS.

## Czego jeszcze nie robić

Nie budować strony produktowej ani dużego modelu ML przed solidnym benchmarkiem. Nie dodawać wszystkich cech naraz. Nie optymalizować wyłącznie ROI ani accuracy.

