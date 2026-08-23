---
tags: [data-sources, provenance]
---

# Źródła danych

Ta notatka opisuje rolę źródeł. Szczegółowy, żywy katalog znajduje się w [[16 - Rejestr źródeł danych]].

## Stack v1

### Football-Data.co.uk — historyczny kręgosłup

Wyniki FT/HT, podstawowe statystyki meczowe i szeroki zestaw kursów dla wielu sezonów. Główne zastosowanie: historyczny baseline, benchmark rynku i walk-forward backtest. Trzeba zapisywać provider/version i flagować zmiany definicji oraz dostawców kursów.

### API-Football — kandydat na bieżący feed operacyjny

Fixtures, lineups, injuries, player/team statistics i pre-match odds. Dobre źródło do aktualnych meczów i budowania własnych snapshotów. Kluczowe ograniczenie: nie zakładamy, że pełna historia point-in-time będzie dostępna później — archiwizujemy odpowiedzi od pierwszego dnia.

### The Odds API — kandydat na dedykowany feed rynkowy

Źródło do aktualnych i historycznych snapshotów kursów. Potencjalnie ważne dla ruchu rynku, opening/current/closing i rekonstrukcji kursu dostępnego w konkretnym cutoffie. Płatność/kredyty wymagają osobnej decyzji po audycie koszt–wartość.

### StatsBomb Open Data — laboratorium event data

Eventy, składy i dla części meczów 360. Dobre do eksperymentów z xG, xT/VAEP, pressingiem, progresją i matchupami; pokrycie lig i sezonów jest selektywne.

### Opta public Betting Showcase — referencja jakościowa

Publiczne strony meczowe, statystyki graczy, xG i definicje zdarzeń. Publiczny dostęp nie oznacza prawa do masowego ani komercyjnego pobierania. Pełny feed produkcyjny wymaga osobnej licencji.

### Sportmonks — kandydat premium / fallback

Potencjalne źródło skonsolidowane dla fixtures, lineups, injuries, statystyk, xG i odds. Do porównania z API-Football pod kątem jakości, historii point-in-time, kosztu i licencji.

### Open-Meteo — pogoda point-in-time

Pogoda godzinowa, dane historyczne oraz — gdzie dostępne — archiwalne forecast runs. W backteście T−24h należy używać prognozy znanej T−24h, nie pogody zrealizowanej po meczu.

### OpenStreetMap i metadane stadionowe

Współrzędne, wysokość, typ nawierzchni i wybrane parametry venue. Dane wymagają walidacji i wersjonowania.

### Flashscore / oficjalne strony lig i klubów — weryfikacja

Źródła pomocnicze do ręcznej lub automatycznej kontroli fixture, lineup, absencji i rozbieżności między providerami. Nie zakładamy automatycznie otwartego API ani prawa do masowego scrapingu.

## Zasada archiwizacji własnej

Dla danych bieżących przechowujemy surowe snapshoty wraz z `provider_timestamp`, `fetched_at`, `known_at`, `kickoff_at`, `prediction_horizon`, provider IDs i hashem payloadu. Dotyczy to szczególnie odds, injuries, predicted/confirmed lineups i weather forecasts.

## Kryteria przyjęcia źródła

- prawa do użycia i redystrybucji;
- pokrycie lig, sezonów, rynków i statystyk;
- definicje i ich zmiany;
- point-in-time timestamps i możliwość odtworzenia stanu T−72/T−24/T−3h/T−60;
- identyfikatory drużyn, graczy i meczów;
- missingness, opóźnienie i korekty po publikacji;
- koszt oraz koszt jednego dnia/ligi/sezonu;
- niezawodność, latency i limity API;
- możliwość reprodukcji i fallback.

## Nowe źródła

Każde nowe źródło najpierw trafia do [[16 - Rejestr źródeł danych]] jako `candidate`. Nie włączamy go do pipeline'u, dopóki nie przejdzie audytu jakości, czasu dostępności, licencji i kosztu.

Powiązania: [[07 - Plan danych historycznych]], [[11 - Czas predykcji i leakage]], [[13 - Schemat danych]].
