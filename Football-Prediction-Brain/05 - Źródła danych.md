---
tags: [data-sources, provenance]
---

# Źródła danych

## Stack v1

### Football-Data

Kręgosłup historyczny: wyniki FT/HT, strzały, SOT, rożne, faule, kartki, sędziowie i szeroki zestaw kursów. Dane wielu sezonów umożliwiają benchmark i backtest. Trzeba zapisywać provider/version, ponieważ pokrycie i definicje zmieniały się w czasie.

### StatsBomb Open Data

Laboratorium granularnych danych: eventy, składy, a dla części meczów 360. Dobre do eksperymentów z xG, xT/VAEP, pressingiem, progresją i matchupami; pokrycie rozgrywek jest selektywne.

### Opta public Betting Showcase

Źródło referencyjne dla publicznych stron meczowych, statystyk graczy, xG oraz spójnych definicji zdarzeń. Publiczny dostęp nie oznacza automatycznie prawa do masowego lub komercyjnego wykorzystania. Produkcyjny feed wymaga sprawdzenia warunków/licencji.

### Open-Meteo

Pogoda godzinowa, dane historyczne oraz — gdzie dostępne — archiwalne prognozy/previous runs. W backteście T−24h należy użyć prognozy znanej T−24h, nie rzeczywistej pogody po meczu.

### OpenStreetMap i metadane stadionowe

Współrzędne, wysokość, typ nawierzchni i wybrane parametry venue. Dane wymagają walidacji i wersjonowania.

### Flashscore

Źródło pomocnicze i weryfikacyjne, nie zakładamy automatycznie otwartej licencji ani stabilnego API.

## Kryteria przyjęcia źródła

- prawa do użycia i redystrybucji;
- pokrycie lig, sezonów i rynków;
- definicje i ich zmiany;
- point-in-time timestamps;
- identyfikatory drużyn, graczy i meczów;
- missingness, opóźnienie i korekty po publikacji;
- koszt, niezawodność oraz możliwość reprodukcji.

Powiązania: [[07 - Plan danych historycznych]], [[11 - Czas predykcji i leakage]], [[13 - Schemat danych]].

