---
tags: [roadmap, versions, experiments]
---

# Wersje modelu

| Wersja | Zakres | Warunek przejścia |
|---|---|---|
| M0 | Market benchmark po zdjęciu marży | wiarygodne kursy point-in-time |
| v0.1 | League-average independent Poisson | działająca macierz wyników |
| v0.2 | Maher attack/defence + home advantage | lepszy OOS od v0.1 |
| v0.3 | Dixon–Coles + time decay | lepszy log loss/kalibracja |
| v0.4 | Dynamic team strength / Elo | stabilna poprawa walk-forward |
| v0.5 | Bivariate lub Bayesian hierarchical | wartość ponad prostszy model |
| v1 | xG, shots, SOT, strength of schedule | udowodniona poprawa OOS |
| v2 | lineups, injuries, player strength | wartość szczególnie T−60min |
| v3 | fatigue, congestion, travel | stabilny incremental value |
| v4 | referee, weather, venue, context | poprawa ogólna lub dla rynku |
| v5 | tactical matchups i interakcje | reprodukowalna poprawa |
| v6 | ensemble i HYBRID market-aware | przewaga nad MARKET benchmark |

## Osobne modele czasu

- `EARLY` — T−72h/T−24h;
- `PRE-MATCH` — około T−6h/T−3h;
- `LINEUP` — około T−60min po potwierdzeniu XI.

Każda wersja ma zamrożone dane, kod, hiperparametry, datę treningu, zakres treningowy, metryki, wykresy kalibracji i decyzję keep/remove. Procedura: [[12 - Ewaluacja i backtesting]].

