---
tags: [moc, projekt, football-model]
status: active
---

# Mapa projektu

## Cel

Zbudować oparty na matematyce, statystyce i danych silnik, który estymuje prawdopodobieństwa zdarzeń meczowych, porównuje je z oczekiwaniami rynku i podejmuje decyzję `BET/NO BET` z kontrolą ryzyka. Pierwszy zakres: Premier League oraz rynki 1X2, Over/Under 2.5 i BTTS.

**Exact score nie jest rynkiem docelowym.** Rozkład goli może pozostać wewnętrznym narzędziem matematycznym do agregacji 1X2/O-U/BTTS, ale nie budujemy rekomendacji na dokładny wynik.

Równolegle badamy rynki zdarzeń o wysokiej powtarzalności, np. team shots, shots on target, corners, cards i team totals — dopiero po potwierdzeniu jakości danych i przewagi poza próbą.

## Przepływ wiedzy

`Dane historyczne + aktualne snapshoty → stan obu drużyn → kontekst meczu → interakcje → rozkłady zdarzeń → prawdopodobieństwa rynków → fair odds → edge/EV → ryzyko/stawka → BET lub NO BET`

## Rdzeń

- [[01 - Fundamenty matematyczne]] — Poisson, Dixon–Coles, modele dynamiczne i bayesowskie.
- [[03 - Architektura modelu]] — rozdział `STATE`, `CONTEXT`, `INTERACTIONS` i warstw systemu.
- [[04 - Rejestr cech]] — katalog kandydatów oraz definicje cech.
- [[17 - Interakcje i wzorce powtarzalne]] — relacje między czynnikami i wyszukiwanie stabilnych zdarzeń.
- [[11 - Czas predykcji i leakage]] — wersje EARLY, PRE-MATCH i LINEUP.
- [[12 - Ewaluacja i backtesting]] — test chronologiczny, kalibracja i wyniki finansowe.

## Dane i rynek

- [[05 - Źródła danych]]
- [[16 - Rejestr źródeł danych]]
- [[07 - Plan danych historycznych]]
- [[06 - Matematyka bukmacherska]]

## Zarządzanie badaniami

- [[08 - Wersje modelu]]
- [[09 - Pytania badawcze]]
- [[10 - Następne kroki]]
- [[13 - Schemat danych]]
- [[14 - Decyzje i założenia]]
- [[15 - Teaser projektu]]
