---
tags: [coverage, leagues, data-audit]
status: draft-v1
---

# Global Data Coverage Matrix v1

## Cel

Nie wybieramy lig po prestiżu. Chcemy zbudować universe, w którym `league×market` jest oceniane według jakości danych, historii, rynku, kosztu i późniejszej stabilności edge.

## Universe startowy

P1: Premier League, Championship, League One, League Two, La Liga, Segunda, Bundesliga, 2. Bundesliga, Serie A, Serie B, Ligue 1, Ligue 2, Eredivisie, Belgian Pro League, Primeira Liga, Süper Lig, Super League Greece, Scottish Premiership, Champions League, Europa League.

P2: Austrian Bundesliga, Danish Superliga, Eliteserien, Allsvenskan, Swiss Super League, Ekstraklasa, Romania Liga I, Conference League.

P3 / do audytu: Czech First League, Ukraine Premier League oraz kolejne ligi dodawane na podstawie coverage i rynku.

## Kategorie coverage

Dla każdej ligi sprawdzamy:

`results / fixtures / odds / xG / shots / SOT / corners / cards / fouls / players / lineups / injuries / referee / historical depth / live latency / point-in-time / price / license / bookmaker coverage`.

## Statusy

- `GREEN` — pole potwierdzone i wystarczająco stabilne dla modelowania;
- `YELLOW` — provider deklaruje coverage, ale musimy sprawdzić realną kompletność;
- `RED` — brak lub zbyt mała jakość;
- `UNKNOWN` — jeszcze niezweryfikowane.

## Wnioski v1

- Football-Data.co.uk jest mocnym darmowym fundamentem historii dla wielu głównych lig i podstawowych statystyk/odds.
- API-Football ma bardzo szerokie deklarowane coverage i nadaje się do darmowego testu live, ale jakość musi być sprawdzana per `league×season`.
- TheStatsAPI jest kandydatem all-in-one: szeroka historia, xG, match/player stats i odds za cenę zbliżoną do kombinacji kilku tańszych feedów; wymaga shootoutu jakości.
- The Odds API pozostaje kandydatem specjalistycznym dla timestamped/historical market data.
- Coverage player props i niszowych marketów jest znacznie mniej jednolite niż 1X2/O-U/BTTS.

## Następny krok

Provider Shootout na realnych meczach i dokładnie tych samych polach. Nie kupujemy feedu wyłącznie na podstawie tabeli marketingowej.
