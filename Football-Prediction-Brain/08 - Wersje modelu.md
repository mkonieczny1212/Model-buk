---
tags: [roadmap, versions, experiments]
---

# Wersje modelu

| Wersja | Zakres | Warunek przejścia |
|---|---|---|
| M0 | Market benchmark po zdjęciu marży | wiarygodne kursy point-in-time |
| v0.1 | League-average independent Poisson dla 1X2/O-U/BTTS | poprawny rozkład goli i kalibracja bazowa |
| v0.2 | Maher attack/defence + home advantage | lepszy OOS od v0.1 |
| v0.3 | Dixon–Coles + time decay | lepszy log loss/kalibracja |
| v0.4 | Dynamic team strength / Elo | stabilna poprawa walk-forward |
| v0.5 | Bivariate lub Bayesian hierarchical | wartość ponad prostszy model |
| v1 | xG, shots, SOT, strength of schedule | udowodniona poprawa OOS |
| v1-E | bazowe modele/progi SOT, shots, corners, cards | stabilna kalibracja i coverage danych |
| v2 | lineups, injuries, player strength | wartość szczególnie T−60min |
| v3 | fatigue, congestion, travel | stabilny incremental value |
| v4 | referee, weather, venue, context | poprawa ogólna lub dla konkretnego rynku |
| v5 | tactical matchups, interakcje i pattern miner | reprodukowalna poprawa na holdoucie |
| v6 | ensemble i HYBRID market-aware | przewaga nad MARKET benchmark |

## Exact score

Exact score nie jest rynkiem docelowym i nie będzie optymalizowany bettingowo. Wewnętrzny rozkład goli może pozostać częścią modeli goli, jeśli jest potrzebny do agregacji 1X2/O-U/BTTS.

## Osobne modele czasu

- `EARLY` — T−72h/T−24h;
- `PRE-MATCH` — około T−6h/T−3h;
- `LINEUP` — około T−60min po potwierdzeniu XI.

Każda wersja ma zamrożone dane, kod, hiperparametry, datę treningu, zakres treningowy, metryki, wykresy kalibracji i decyzję keep/remove. Procedura: [[12 - Ewaluacja i backtesting]].
