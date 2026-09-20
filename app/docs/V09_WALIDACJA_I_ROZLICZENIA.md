# Model BUK 0.9 — walidacja prospektywna i rozliczenia

## Cel

Wersja 0.9 tworzy zamkniętą pętlę badawczą. Skan zapisuje decyzję i cenę dostępną w chwili typowania. Proces utrzymaniowy przechwytuje ostatnią dostępną cenę przed rozpoczęciem meczu, pobiera oficjalny wynik i statystyki po zakończeniu oraz zapisuje rozliczenie bez nadpisywania pierwotnej predykcji.

## Obsługiwane rozliczenia

- 1X2 i BTTS z oficjalnego wyniku.
- Gole, rożne, strzały, strzały celne oraz kartki: suma, gospodarz i gość, over/under.
- Kartki są liczone jako żółta + 2 × czerwona, zgodnie z aktualnym profilem modelu.
- Linia całkowita równa wynikowi jest `VOID`; brak wymaganej statystyki daje `UNAVAILABLE` i nie jest traktowany jako przegrana.
- Kupon przegrywa po przegranej dowolnej nogi. Noga `VOID` ma kurs 1.00, więc wypłata używa wyłącznie aktywnych nóg.

## Zwrot i CLV

Jednostkowa stawka wynosi 1. Dla wygranego singla lub kuponu:

`payout = (1 - 0.12) × odds`

`pnl = payout - 1`

Podatek 12% jest nakładany raz na stawkę kuponu. CLV jest liczone jako:

`CLV = offered_odds / closing_odds - 1`

Dodatni CLV oznacza cenę lepszą niż kurs zamknięcia.

## Brama przejścia z PAPER

Single mogą zostać uznane za statystycznie gotowe dopiero wtedy, gdy wszystkie warunki są spełnione jednocześnie:

1. co najmniej 200 rozliczonych obserwacji,
2. dolna granica 95% dla średniego ROI jest dodatnia,
3. dolna granica 95% dla średniego CLV jest dodatnia,
4. ECE wynosi najwyżej 5 punktów procentowych.

Raport zawiera również Brier score, kalibrację w koszykach oraz segmenty według rynku, ligi i kursu. Kupony pozostają `PAPER`, nawet po dobrym wyniku próby, do czasu osobnej walidacji prawdopodobieństwa łącznego i zależności pomiędzy nogami.

## Automatyka

W standardowym uruchomieniu aplikacja wykonuje cykl po 30 sekundach od startu, a potem co 15 minut. Panel „Walidacja” pozwala uruchomić go ręcznie.

- `MODEL_BUK_AUTO_MAINTENANCE=0` wyłącza proces w tle.
- `MODEL_BUK_MAINTENANCE_INTERVAL=900` ustawia odstęp w sekundach; minimum to 60.
- `POST /api/maintenance/run` wykonuje pełny cykl.
- `GET /api/validation/report` zwraca aktualny raport i bramę promocji.

## Ograniczenia danych

Prawdziwego kursu zamknięcia nie da się odtworzyć po fakcie, jeśli dostawca nie przechowuje historii zmian. Aplikacja musi działać w okresie przed rozpoczęciem meczu albo zostać wdrożona na stale działającym hoście. Pełne rozliczenie rynków statystycznych zależy od zakresu i limitu planu API-Football dla zakończonych spotkań.
