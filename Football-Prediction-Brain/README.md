# Football Prediction Brain

Vault badawczy do budowy ilościowego modelu predykcyjnego meczów piłkarskich i systemu decyzji bettingowych.

## Start

Otwórz ten folder jako vault w Obsidianie, a następnie zacznij od [[00 - Mapa projektu]]. Krótki stan projektu: [[15 - Teaser projektu]].

## Zasady projektu

- model zwraca skalibrowane prawdopodobieństwa, nie pojedynczy „typ”;
- exact score nie jest rynkiem docelowym;
- każda nowa cecha lub interakcja musi poprawić wynik poza próbą;
- każda informacja ma znacznik czasu i musi być dostępna w chwili predykcji;
- model sportowy, benchmark rynkowy i decyzja bettingowa są oddzielnymi warstwami;
- częsty wzorzec nie jest przewagą, dopóki nie przeżyje holdoutu i porównania z kursem;
- prostszy model pozostaje, jeżeli bardziej złożony nie daje mierzalnej poprawy.

## Główne mapy treści

- [[01 - Fundamenty matematyczne]]
- [[02 - Literatura i publikacje]]
- [[03 - Architektura modelu]]
- [[04 - Rejestr cech]]
- [[05 - Źródła danych]]
- [[06 - Matematyka bukmacherska]]
- [[07 - Plan danych historycznych]]
- [[08 - Wersje modelu]]
- [[09 - Pytania badawcze]]
- [[10 - Następne kroki]]
- [[11 - Czas predykcji i leakage]]
- [[12 - Ewaluacja i backtesting]]
- [[13 - Schemat danych]]
- [[14 - Decyzje i założenia]]
- [[15 - Teaser projektu]]
- [[16 - Rejestr źródeł danych]]
- [[17 - Interakcje i wzorce powtarzalne]]

> [!warning] Odpowiedzialność
> Model ma służyć do badań probabilistycznych. Dodatnia wartość oczekiwana w backteście nie gwarantuje zysku, a zakłady wiążą się z ryzykiem utraty kapitału.
