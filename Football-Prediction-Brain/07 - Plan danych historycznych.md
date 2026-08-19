---
tags: [historical-data, pipeline, premier-league]
---

# Plan danych historycznych

## Zakres startowy

Premier League jako kontrolowane środowisko pierwszego modelu. W rozmowie wykonano wstępne pobranie 4 sezonów Football-Data (2022/23–2025/26; deklarowane 1520 meczów) i zauważono zmienność średniej goli oraz home advantage między sezonami. Te liczby wymagają ponownej, reprodukowalnej walidacji przed użyciem produkcyjnym.

## Etapy

1. Pobrać i zachować surowe snapshoty z metadanymi źródła.
2. Ujednolicić nazwy/ID drużyn, daty, strefy czasowe i identyfikatory meczów.
3. Zbudować `MATCHES` jako tabelę centralną i oddzielne tabele encji.
4. Wykonać testy zakresów, duplikatów, braków i spójności wyniku.
5. Oznaczyć zmiany dostawcy, definicji i ery przepisów.
6. Zbudować point-in-time snapshots dla T−24h, T−3h i T−60min.
7. Obliczać cechy wyłącznie z wcześniejszych zdarzeń.
8. Zachować kursy opening/current/closing osobno; closing nie może wejść do modelu wcześniejszego horyzontu.
9. Rozszerzać stack kolejno o xG/event data, lineups, absencje, pogodę, venue i sędziów.

## Podział czasowy

Walk-forward/rolling origin, np. trening na przeszłości i test na kolejnym okresie. Nie używamy losowego train/test split. Starsze mecze mogą otrzymywać mniejszą wagę, a structural breaks — osobne flagi.

## Data contracts

Każda kolumna ma: definicję, jednostkę, źródło, `event_time`, `known_at`, wersję definicji i politykę braków. Szczegóły: [[13 - Schemat danych]], [[11 - Czas predykcji i leakage]].

