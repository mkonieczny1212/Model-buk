---
tags: [timestamps, leakage, point-in-time]
---

# Czas predykcji i leakage

## Trzy snapshoty

### EARLY — T−24h (opcjonalnie T−72h)

Historia zespołów, prognoza pogody znana wtedy, publiczne informacje o absencjach i kursy z tego momentu. Bez oficjalnej XI.

### PRE-MATCH — T−3h / T−6h

Nowsza pogoda, aktualizacje dostępności, predicted XI i ruch kursów do wyznaczonego cutoffu.

### LINEUP — około T−60min

Potwierdzona XI i ławka, najnowsze dozwolone dane oraz aktualizacja predykcji.

## Reguła point-in-time

Każdy rekord ma co najmniej:

- `event_time` — kiedy zdarzenie nastąpiło;
- `published_at` — kiedy źródło je opublikowało;
- `ingested_at` — kiedy system je pobrał;
- `known_at` — od kiedy model mógł legalnie użyć informacji.

Feature dla cutoffu może korzystać wyłącznie z rekordów, których `known_at <= prediction_time`.

## Typowe źródła leakage

- potwierdzony skład w modelu T−24h;
- rzeczywista pogoda zamiast archiwalnej prognozy;
- closing odds w modelu generowanym wcześniej;
- statystyki lub korekty opublikowane po meczu;
- rolling average zawierająca bieżący mecz;
- losowy train/test split;
- normalizacja lub imputacja dopasowana na całym zbiorze;
- aktualna nazwa/status zawodnika użyte do odtworzenia przeszłości.

Kontrolę opisuje [[12 - Ewaluacja i backtesting]], a magazyn danych [[13 - Schemat danych]].

