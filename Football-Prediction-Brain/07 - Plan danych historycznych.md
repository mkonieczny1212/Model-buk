---
tags: [historical-data, pipeline, premier-league]
---

# Plan danych historycznych

## Zakres startowy

Premier League jako kontrolowane środowisko pierwszego modelu. W rozmowie wykonano wstępne pobranie 4 sezonów Football-Data (2022/23–2025/26; deklarowane 1520 meczów) i zauważono zmienność średniej goli oraz home advantage między sezonami. Te liczby wymagają ponownej, reprodukowalnej walidacji przed użyciem produkcyjnym.

## Etapy

1. Pobrać i zachować surowe dane historyczne z metadanymi źródła.
2. Od pierwszego uruchomienia kolektora archiwizować własne snapshoty danych bieżących.
3. Ujednolicić nazwy/ID drużyn, graczy, sędziów, stadionów, daty i strefy czasowe.
4. Zbudować `MATCHES` jako tabelę centralną i oddzielne tabele encji.
5. Wykonać testy zakresów, duplikatów, braków i spójności wyniku/statystyk.
6. Oznaczyć zmiany dostawcy, definicji i ery przepisów.
7. Zbudować point-in-time snapshots dla T−72h/T−24h, T−6h/T−3h i T−60min.
8. Obliczać cechy wyłącznie z wcześniejszych zdarzeń.
9. Zachować kursy opening/current/closing osobno; closing nie może wejść do modelu wcześniejszego horyzontu.
10. Rozszerzać stack kolejno o xG/event data, lineups, absencje, pogodę, venue i sędziów.
11. Budować historyczne profile zdarzeń dla SOT, shots, corners, cards i team totals, jeśli coverage jest stabilne.
12. Generować interakcje wyłącznie z informacji dostępnych w danym cutoffie.

## Wzorce i interakcje

Dane historyczne muszą pozwalać ocenić zarówno efekty główne, jak i warunkowe: `team×venue`, `team×opponent`, `team×referee`, `weather×style`, `fatigue×pressing` itd. Dla częstych progów zdarzeń przechowujemy wyniki per sezon, home/away, opponent strength i dostępny kurs, aby odróżnić prawdziwą stabilność od przypadkowej serii.

## Podział czasowy

Walk-forward/rolling origin, np. trening na przeszłości i test na kolejnym okresie. Nie używamy losowego train/test split. Starsze mecze mogą otrzymywać mniejszą wagę, a structural breaks — osobne flagi.

## Data contracts

Każda kolumna ma: definicję, jednostkę, źródło, `event_time`, `known_at`, wersję definicji i politykę braków. Szczegóły: [[13 - Schemat danych]], [[11 - Czas predykcji i leakage]].
