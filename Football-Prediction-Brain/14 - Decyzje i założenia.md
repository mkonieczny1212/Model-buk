---
tags: [decisions, assumptions, changelog]
---

# Decyzje i założenia

## Przyjęte

- Pierwsza liga: Premier League.
- Pierwsze rynki: 1X2, exact score, O/U 2.5, BTTS.
- Pierwszy silnik: Poisson → attack/defence → Dixon–Coles → dynamiczne rozszerzenia.
- Wynikiem jest rozkład, nie pojedynczy typ.
- Dane sportowe i informacja rynku pozostają rozdzielone w `PURE` i `MARKET`.
- Wszystkie dane są point-in-time i wersjonowane.
- Walidacja jest chronologiczna.
- Każda grupa cech musi udowodnić incremental predictive value.
- Model złożony nie wygrywa automatycznie z prostym.

## Ostrożne hipotezy, nie fakty

- pogoda, podróż, morale i stawka meczu mogą działać tylko w interakcjach lub na określonych rynkach;
- lineups mogą mieć większą wartość w modelu T−60min niż EARLY;
- referee effect powinien być silniejszy dla kartek/fauli niż 1X2;
- stare dane wymagają decay i flag structural breaks;
- closing market jest bardzo mocnym benchmarkiem, ale nie może przeciekać do wcześniejszej predykcji.

## Otwarte decyzje

- dokładny cutoff modeli;
- długość okresu treningowego i decay;
- metoda usuwania vig;
- sposób ratingu zawodników oraz beniaminków;
- minimalny próg edge i polityka stakingu;
- finalne źródła produkcyjne oraz licencje.

Aktualizuj tę notatkę po każdym rozstrzygnięciu z [[09 - Pytania badawcze]].

