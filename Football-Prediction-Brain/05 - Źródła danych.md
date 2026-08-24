---
tags: [data-sources, provenance]
---

# Źródła danych

Ta notatka opisuje rolę źródeł. Szczegółowy, żywy katalog znajduje się w [[16 - Rejestr źródeł danych]]. Nie przywiązujemy projektu do żadnego providera — źródło wygrywa jakością, point-in-time, coverage i ekonomiką.

## Stack / kandydaci

### Football-Data.co.uk — historyczny kręgosłup

Wyniki FT/HT, podstawowe statystyki meczowe i szeroki zestaw kursów dla wielu sezonów. Główne zastosowanie: historyczny baseline, benchmark rynku i walk-forward backtest.

### API-Football — kandydat na szeroki bieżący feed

Aktualnie wszystkie endpointy są dostępne w planach, a koszt skaluje się głównie limitem requestów. Plan Free ma 100 requestów/dzień, Pro $19/mies. 7 500/dzień, Ultra $29/mies. 75 000/dzień, Mega $39/mies. 150 000/dzień (weryfikacja 2026-08-24). Provider sam rekomenduje cache i pobieranie szczegółów dopiero wtedy, gdy są potrzebne; fixtures można pobierać zbiorczo per liga/data, a wiele fixture IDs grupować w jednym callu.

Źródło: https://www.api-football.com/pricing oraz oficjalne materiały optymalizacji quota.

### The Odds API — dedykowany feed rynkowy

Aktualne odds można pobierać zbiorczo dla sportu/regionu/marketu; koszt aktualnego `/odds` wynosi `1 × liczba marketów × liczba regionów`, niezależnie od liczby meczów zwróconych przez request. Historical odds kosztują `10 × market × region`. Plan z 20k credits kosztuje obecnie $30/mies. (weryfikacja 2026-08-24).

To kluczowy argument za **batchingiem i lejkiem kosztowym**, a nie odpytywaniem każdego rynku każdego meczu osobno.

Źródło: https://the-odds-api.com/liveapi/guides/v4/ oraz https://the-odds-api.com/

### football-data.org — drugi provider / reconciliation

Może pełnić rolę cross-checku i drugiego źródła. Free obejmuje 12 rozgrywek i 10 calls/min; Standard €49/mies. obejmuje 30 rozgrywek, Advanced €99 — 50, Pro €199 — 100. Statistic Add-On €15 daje m.in. corners, fouls, possession, saves i shots on/off goal; Odds Add-On €15 daje pre-match 1X2 dla 40 rozgrywek (weryfikacja 2026-08-24).

Źródło: https://www.football-data.org/pricing

### Betfair Historical Data — exchange benchmark

Oficjalny, timestampowany historyczny feed Betfair Exchange z price/market/settlement data, dostępny od 2015. Potencjalnie bardzo wartościowy do CLV, price movement, płynności i backtestów wykonania. Dane są kupowane i pobierane pakietami, więc traktujemy je jako źródło selektywne, nie domyślny koszt dla całego universe.

Źródło: https://developer.betfair.com/historical-data-services-api/

### Pinnacle — benchmark jakościowy, dostęp ograniczony

Publiczny Pinnacle API jest zamknięty od 23.07.2025; dostęp jest indywidualny dla wybranych high-value/commercial/academic/pregame handicapping use cases. Nie budujemy architektury zależnej od Pinnacle, ale możemy później ubiegać się o dostęp badawczy.

Źródło: https://github.com/pinnacleapi/pinnacleapi-documentation

### StatsBomb Open Data — laboratorium event data

Eventy, składy i dla części meczów 360. Dobre do eksperymentów z xG, xT/VAEP, pressingiem, progresją i matchupami; coverage lig/sezonów jest selektywne.

### Opta public — referencja jakościowa

Publiczne strony i definicje mogą wspierać weryfikację, ale pełny produkcyjny feed wymaga osobnej licencji.

### Sportmonks — kandydat premium / fallback

Źródło skonsolidowane do porównania z API-Football pod kątem coverage, latency, historii, xG i kosztu. Nie kupujemy go automatycznie — wymagany test cost/value.

### Open-Meteo — tylko event-driven environment

Zostaje jako tanie źródło forecast/history, ale nie traktujemy pogody jako podstawowego sygnału każdego meczu. Uruchamiamy głębsze cechy środowiskowe głównie przy ekstremach lub dużym climate/travel shock.

### OpenStreetMap i metadane stadionowe

Współrzędne, wysokość, powierzchnia i venue metadata.

### Flashscore / oficjalne strony lig i klubów

Fallback i reconciliation. Nie zakładamy automatycznie prawa do masowego scrapingu.

## Zasada ekonomiczna

Nie pobieramy drogiego pola „bo może się przydać”. Każde źródło i endpoint dostaje `cost_class`, przewidywany request volume i oczekiwaną wartość informacyjną. Szczegóły: [[18 - Ekonomika pipeline i cost-aware scanning]].

## Zasada archiwizacji własnej

Dla danych bieżących przechowujemy surowe snapshoty wraz z `provider_timestamp`, `fetched_at`, `known_at`, `kickoff_at`, `prediction_horizon`, provider IDs i hashem payloadu. Dotyczy to szczególnie odds, injuries, predicted/confirmed lineups i zmian rynku.

## Kryteria przyjęcia źródła

- prawa do użycia;
- coverage lig, sezonów i rynków;
- definicje i ich zmiany;
- point-in-time;
- jakość identyfikatorów;
- missingness i latency;
- koszt jednostkowy i miesięczny;
- możliwość batchowania/cache;
- fallback i reprodukcja.

Powiązania: [[16 - Rejestr źródeł danych]], [[18 - Ekonomika pipeline i cost-aware scanning]], [[19 - Globalny zakres lig i quality gate]].
