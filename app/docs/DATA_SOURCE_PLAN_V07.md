# Model Buk — plan domknięcia braków danych (research 2026-09-16)

Ten dokument rozdziela trzy rzeczy: **dane, które już mamy**, **dane, które możemy pobierać bieżąco**, oraz **dane, których nadal nie mamy w jakości wystarczającej do uczenia i walidacji**. Żaden brak nie może być zastępowany arbitralną wartością.

## Zasada dla aktualnej formy

Historia służy do nauczenia zależności. Predykcja bieżącego meczu ma być aktualizowana przez bieżący stan drużyny. Dla wybranego fixture pobieramy z API-Football ostatnie zakończone mecze **z tej samej ligi i bieżącego sezonu** i, gdy provider zwraca pola, wykorzystujemy gole, strzały, SOT, rożne, kartki, possession i xG. Krótkoterminowy sygnał jest shrinkowany i nie może samodzielnie zdominować modelu.

Docelowy `Current Team State` musi dodatkowo zawierać:
- krótkie i średnie okna czasowe;
- siłę przeciwników / strength-of-schedule;
- structural breaks (nowy trener, transfery, duża zmiana XI);
- odpoczynek, congestion i podróż;
- lineup strength i replacement gap;
- osobne stany dla attack, defence, shot creation/suppression, set pieces/corners i discipline.

Nie będziemy ręcznie przypisywać wag. Każda nowa grupa cech trafia do modelu dopiero po walk-forward/OOS i ablation.

## 1. API-Football — zostaje providerem operacyjnym

Użycie:
- bieżące fixtures i aktualne zespoły dla `league + current season`;
- bieżący sezon i coverage;
- ostatnie mecze i fixture statistics;
- injuries;
- confirmed lineups;
- referee/venue;
- current pre-match odds;
- player fixture stats, gdy coverage na to pozwala.

Zmiana w v0.6.1: selektor drużyn pobiera roster bieżącego sezonu z `/teams?league=...&season=...`, więc nie miesza spadkowiczów ani klubów historycznych.

Ograniczenia:
- xG nie jest gwarantowane dla każdej liga × sezon × fixture;
- predicted XI przed publikacją oficjalnego składu nie jest pełnym rozwiązaniem;
- krótka retencja części pre-match odds oznacza konieczność własnego archiwum;
- przy małym planie trzeba agresywnie cache'ować.

## 2. FootyStats — kandydat na tani drugi provider / current-form reconciliation

Mocne strony do naszego use-case:
- szeroka liczba lig;
- aktualne i historyczne team stats;
- xG/xGA;
- shots/SOT;
- corners/cards/fouls/possession;
- referee IDs;
- dane pre-match i możliwość pobierania stanu sezonu według daty.

Rola w Model Buk:
- uzupełnienie xG i process metrics poza Big Five;
- drugi provider do porównywania obecnej formy i wykrywania anomalii API-Football;
- nie traktować dostarczonych przez serwis gotowych `potential`/predictions jako wejścia PURE.

Ryzyko:
- model xG providera jest zewnętrzny i jego metodologia nie jest naszą metodologią;
- część pól to agregaty sezonowe, a nie event-level;
- przed zakupem trzeba sprawdzić pokrycie dokładnie naszych 13 rozgrywek i zakres historyczny.

## 3. Sportmonks — kandydat na główny płatny upgrade

Najlepiej domyka obecne luki jednym schematem danych:
- fixtures/history;
- match/team/player stats;
- xG, xGoT, xPTS, npxG i inne expected metrics;
- lineups;
- expected lineups jako dodatkowy produkt;
- coach/referee data;
- odds;
- UCL/UEL/UECL oraz ligi spoza Big Five;
- historyczny dostęp jako add-on.

Potencjalne zastosowanie:
1. zbudować jednolity historyczny feature store dla 10 lig + UEFA;
2. dobudować player-level xG i lineup strength;
3. uzyskać expected XI wcześniej niż confirmed XI;
4. wykorzystać referee i coach data do structural-break/context layer;
5. rozszerzyć historyczne odds, jeśli coverage rynku jest wystarczające.

Warunek zakupu: najpierw trial i coverage audit na konkretnej liście rozgrywek/metryk. Nie kupujemy na podstawie samego marketingowego `2200+ leagues`.

## 4. Transfermarkt bundle — dane już posiadane, ale wymagają modelu

Mamy raw:
- game_lineups;
- appearances;
- game_events;
- player valuations;
- transfers;
- games/players/clubs.

To wystarcza do pierwszego własnego `PlayerImpact / ReplacementGap / LineupDelta`, ale nie jest jeszcze gotową cechą. Plan:
1. canonical player/team IDs;
2. expected minutes i continuity;
3. regularized player impact z kontekstem team/opponent;
4. replacement quality;
5. `Current XI - Normal XI`;
6. OOS ablation osobno dla goals, shots/SOT, corners i cards.

## 5. Referee layer

Źródła:
- API-Football current referee;
- Transfermarkt/football-data history;
- ewentualnie Sportmonks lub Sportradar do głębszych danych.

Najpierw budujemy referee baseline ze shrinkage: cards, fouls, penalties, home/away split. Dopiero później `Referee × TeamAggressiveness` i podobne interakcje.

## 6. Tactical microdata

Dziś nie mamy jednolitego historycznego feedu dla wszystkich lig dla: field tilt, xT, VAEP, high turnovers, detailed crossing/aerial matchup i positional data.

Realistyczne opcje:
- Sportmonks dla części rozszerzonych statistics/xG;
- Sportradar Soccer Extended jako droższy provider zaawansowanych event stats;
- Opta/Stats Perform jako docelowa klasa enterprise, jeśli projekt uzasadni koszt.

Nie jest to P0. Najpierw muszą dobrze działać: dynamic team state, xG/process, current form, lineups, referee i odds archive.

## 7. Odds archive — zaczynamy od razu

Każde pobranie odds powinno być zapisane jako snapshot:
- fixture_id;
- market/line/side;
- bookmaker;
- odds;
- provider timestamp;
- fetched_at;
- prediction horizon.

To buduje własną bazę potrzebną do CLV i market validation, zwłaszcza dla corners/shots/SOT, gdzie historyczny price coverage jest najsłabszy.

## Priorytet wdrożenia

P0 — teraz:
1. API-Football: current rosters, current-season recent form, injuries, confirmed XI, referee, odds archive.
2. Naprawić entity resolution między providerami.
3. Zawsze pokazywać model probability, nawet jeśli brak porównywalnego kursu; wtedy status `MODEL ONLY`, nigdy `BET`.

P1:
4. Audyt FootyStats trial na 13 rozgrywkach.
5. Audyt Sportmonks trial na tych samych rozgrywkach i wymaganych metrykach.
6. Wybrać jednego dostawcę jako secondary provider dla xG/process poza Big Five + UEFA.

P2:
7. Zbudować własny PlayerImpact/LineupDelta z posiadanego Transfermarkt.
8. Referee model.
9. Strength-of-schedule-adjusted current form i structural-break detector.

P3:
10. Dopiero po OOS/CLV rozszerzać tactical microdata i player props.
