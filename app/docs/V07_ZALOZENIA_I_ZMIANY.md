# Model BUK 0.7 — założenia i aktualny stan

## Założenia zachowane z rozmowy i Football-Prediction-Brain

1. PURE: kursy bukmacherów nie są wejściem modelu sportowego.
2. Głównym wejściem analizy nadchodzącego spotkania są dostępne ostatnie zakończone mecze drużyn. Historia stabilizuje małe próby; nie blokuje UEFA samym brakiem nazwy ligi w lokalnej tabeli.
3. Zależność produkcja drużyny / dopuszczanie przeciwnika jest liczona osobno dla każdej statystyki. Dane są ważone aktualnością i miejscem meczu.
4. Wysokie P nie oznacza opłacalności. Wyświetlamy najbardziej prawdopodobne zdarzenie, do pięciu propozycji z różnych grup oraz pełną tabelę wyliczonych rynków. Zdarzenia z jednego meczu nie są niezależnymi zakładami.
5. BET wymaga dopuszczenia modelu, aktualnego kursu, zgodnych zasad rozliczenia i dodatniej wartości po zadanych kosztach. W przeciwnym razie NO BET z powodem; prognoza nadal pozostaje widoczna.
6. Brak danych to brak danych. Nie zastępujemy null zerem, nie pokazujemy sztucznej wartości 1 i nie podstawiamy podobnie nazwanej drużyny.
7. Predykcja jest przedmeczowa, dla 90 minut. Mecze trwające, zakończone i odwołane nie otrzymują nowej prognozy udającej zapis przedmeczowy.

## Obliczenia

Silnik `live-gamma-poisson-v0.7`: dla oczekiwanej liczby zdarzeń gospodarza łączymy obserwacje jego produkcji i dopuszczania przez gościa; analogicznie dla gościa. Obserwacje mają wagę `2^(-wiek_dni/90)`, a mecze w innym miejscu połowę ekspozycji. Parametry te są jawnie ustalonymi założeniami modelu badawczego, nie współczynnikami rzekomo wyuczonymi z danych.

Prior historyczny ma najwyżej trzy efektywne mecze i słabnie z wiekiem danych. Z prioru Jeffreysa i ważonych obserwacji wyznaczamy posterior Gamma intensywności. Całkowanie modelu Poissona względem tego posterioru daje rozkład ujemny dwumianowy. Powyżej/powyżej dla sum liczymy przez splot; 1X2 i BTTS z rozkładów obu drużyn. Ogony nie są obcinane i renormalizowane do sztucznej pewności. Przedziały 90% zapisane w `expected` dotyczą intensywności zdarzeń warunkowo względem modelu, nie gwarantowanego zakresu wyniku ani skalibrowanej pewności trafienia.

Każdy rynek wymaga co najmniej trzech obserwacji odpowiednich strumieni produkcji i dopuszczania. Parametr intensywności nie obejmuje jeszcze osobno całej zmienności między meczami, zmiany trenera, zawodników ani siły różnych lig. Model pozostaje badawczy. Nie wolno interpretować samego zastosowania matematyki jako dowodu kalibracji.

Wyuczony model goli HGB/Poisson nadal jest dostępny jako oddzielny model porównawczy. Poprawiono chronologię cech, ujednolicono trening i inferencję, uzupełniono 2021/22, ponownie wytrenowano artefakty. Dane aktualizujące stan nie zmieniają daty ostatniego treningu parametrów. Użycie modelu z API innym niż źródło treningowe wymaga osobnej oceny.

## Źródła i ograniczenia potwierdzone 17.09.2026

- Understat: pobrano brakujący sezon 2021/22 w pięciu ligach (1826 spotkań) oraz dostępne mecze 2026/27 (200). Manifest źródeł i hashy: `data/understat/source_manifest.json`. Stan zbioru: 21 789 spotkań.
- Podłączone API-Football: aktywny plan Free, 100 zapytań dziennie. Dostawca rzeczywiście zwrócił odmowę dla parametru `last` i sezonu 2026. Zmiana kodu nie nadaje uprawnień abonamentu. Nie obchodzimy ograniczeń dostępu.
- FootyStats i Sportmonks nie były skonfigurowane w środowisku tej weryfikacji. Ich dotychczasowe integracje nadal pełnią rolę kontekstu/uzgadniania danych.
- Baza wielu lig nadal ma stare dane i niekompletne statystyki Polski. Braki są teraz blokowane per rynek. Do ich uzupełnienia potrzebne jest dostępne źródło bieżących statystyk albo import danych użytkownika.
- Understat stanowi jawny fallback goli dla rozpoznanych drużyn Big Five; nie dostarcza w tym adapterze rożnych, strzałów ani kartek.

## Weryfikacja rzeczywista

Analiza API meczu UEL Real Sociedad–Bournemouth, fixture 1636321, zwróciła 29 rynków goli/1X2/BTTS i trzy propozycje z różnych grup, z wykorzystaniem po 20 spotkań Understat na drużynę. Kursy i kontekst pochodziły z API. Odmowy dostępu do szczegółowej historii API były jawne. Przykład Crystal Palace–Lech Poznan nadal nie miał wystarczającej aktualnej podstawy obu drużyn przy tym abonamencie. Nie oznaczono go jako naprawionego pełnymi danymi.

Model live został też sprawdzony chronologicznie na co dwudziestym meczu po 01.07.2024 z lokalnej historii. Raport `models/live_v07/evaluation.json` obejmuje 261 prognoz goli i po 256 prognoz pozostałych statystyk. To test krajowej historii, nie walidacja UEFA, wszystkich linii ani rentowności. Nowego modelu nie dopuszczono automatycznie do BET.

## Naprawy techniczne

- UTC i konserwatywna dostępność wyników; brak wpływu przyszłych i równoległych spotkań na historyczne cechy.
- Zachowanie znanych pól przy scalaniu danych oraz odrzucanie duplikatów.
- Puste statystyki pozostają null; kartki wymagają znanych żółtych i czerwonych. Ich definicja `yellow_plus_two_red` musi zgadzać się z ofertą bukmachera.
- Ścisłe mapowanie nazw/aliasów; zgodność kraju w FootyStats i geokodowaniu.
- Bezpieczne błędy dostawców, bez URL i kluczy; prawidłowe komunikaty o planie i limitach.
- Systemowy magazyn certyfikatów TLS, bez wyłączania sprawdzania certyfikatów.
- Pogoda tylko z właściwego horyzontu; `persist=false` nie zapisuje prognoz ani kursów.
- Widoczna wersja faktycznie używanego silnika, ostrzeżenia, lokalny czas meczu, rozdział pokrycia danych od prawdopodobieństwa.
- Zgodne wersje bibliotek, manifest artefaktów, testy regresji i procedura wydania.

## Nadal do wykonania po uzyskaniu danych

Pełne bieżące statystyki wszystkich lig/UEFA, walidacja przesunięcia dostawcy, kalibracja per liga i rynek, wyuczone efekty składu/sędziego/trenera, normalizacja siły lig oraz prospektywny rejestr skuteczności i CLV wymagają dodatkowych danych i oceny. Nie są zastąpione ręcznie nadanymi wagami ani etykietą „A”.
