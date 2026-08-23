---
tags: [decisions, assumptions, changelog]
---

# Decyzje i założenia

## Przyjęte

- Pierwsza liga: Premier League.
- Pierwsze rynki: 1X2, O/U 2.5, BTTS.
- Exact score jest wyłączony jako rynek docelowy/rekomendacja; rozkład goli może pozostać technicznym narzędziem wewnętrznym.
- Rynki zdarzeń (shots/SOT/corners/cards/team totals) są kandydatami badawczymi po audycie danych.
- Pierwszy silnik goli: Poisson → attack/defence → Dixon–Coles → dynamiczne rozszerzenia.
- Wynikiem jest rozkład prawdopodobieństwa, nie pojedynczy typ.
- Dane sportowe i informacja rynku pozostają rozdzielone w `PURE` i `MARKET`.
- Wszystkie dane są point-in-time i wersjonowane.
- Walidacja jest chronologiczna.
- Każda grupa cech musi udowodnić incremental predictive value.
- Interakcje są traktowane jako osobna hipoteza i wymagają shrinkage/minimalnej próby.
- Head-to-head ani seria nie są samodzielnym dowodem przewagi bez korekt i testu OOS.
- Model złożony nie wygrywa automatycznie z prostym.

## Ostrożne hipotezy, nie fakty

- pogoda, podróż, morale i stawka meczu mogą działać tylko w interakcjach lub na określonych rynkach;
- lineups mogą mieć większą wartość w modelu T−60min niż EARLY;
- referee effect powinien być silniejszy dla kartek/fauli niż 1X2;
- `Team×Venue`, `Team×Opponent` i `Team×Referee` mogą być użyteczne, ale ryzyko overfittingu jest wysokie;
- częste progi typu `SOT>=3` lub `corners>=3` mogą być wartościowe tylko wtedy, gdy prawdopodobieństwo jest stabilne i rynek je niedoszacowuje;
- stare dane wymagają decay i flag structural breaks;
- closing market jest bardzo mocnym benchmarkiem, ale nie może przeciekać do wcześniejszej predykcji.

## Otwarte decyzje

- dokładny cutoff modeli;
- długość okresu treningowego i decay;
- metoda usuwania vig;
- sposób ratingu zawodników oraz beniaminków;
- minimalne próbki dla interakcji i wzorców powtarzalnych;
- pierwsze rynki zdarzeń do produkcyjnego testu;
- minimalny próg edge i polityka stakingu;
- finalne źródła produkcyjne oraz licencje.

Aktualizuj tę notatkę po każdym rozstrzygnięciu z [[09 - Pytania badawcze]].
