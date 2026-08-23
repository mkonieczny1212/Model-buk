---
tags: [features, registry, blueprint]
---

# Rejestr cech

To katalog kandydatów, a nie lista cech, które automatycznie trafią do jednego modelu.

## Must-have

- dynamiczna siła ataku i obrony;
- home/away i home advantage;
- jakość przeciwników / strength of schedule;
- wynik, gole, strzały, strzały celne;
- rożne, faule i kartki tam, gdzie definicje są stabilne;
- czas i sezon;
- dni odpoczynku;
- historyczne kursy dla benchmarku;
- identyfikator źródła oraz timestamp.

## Jakość rzeczywistej gry

- xG, xGA, npxG, xG/shot, big chances;
- shot quality, wejścia i kontakty w polu karnym;
- possession, field tilt, progression, deep completions;
- xT, VAEP, kontry i atak pozycyjny;
- PPDA, pressing, high turnovers;
- stałe fragmenty, dośrodkowania i aerial strength.

## Forma i regresja do średniej

Okna 1/3/5/8/10 meczów oraz wykładniczy decay. Forma powinna korygować venue i siłę rywala. Kandydaci: xG difference, shot difference, SOT difference, corners difference, finishing, goalkeeper form, set pieces. Sygnały „luck”: goals−xG, conceded−xGA, conversion, save percentage, karne, samobóje, słupki i czerwone kartki.

## Kadra, gracze i trener

- predicted/confirmed XI, siła formacji i ławki;
- `LineupDelta = Strength(CurrentXI) - Strength(NormalXI)`;
- absencja jako `PlayerValue × ExpectedMinutesLost × ReplacementGap`;
- continuity, wspólne minuty, rotacja i ograniczenia minut;
- manager tenure/change/style oraz transfery i squad turnover.

## Obciążenie i podróż

- godziny odpoczynku, mecze i minuty w 7/14/28 dni;
- dogrywka, intensywność, accumulated load i rotacja;
- dystans i sposób podróży, strefy czasowe, puchary, aklimatyzacja;
- zawodnicy wracający z reprezentacji.

## Środowisko

- temperatura, wilgotność, wet-bulb, opady, śnieg;
- wiatr, porywy, ciśnienie i zachmurzenie;
- murawa, stan i wymiary boiska, dach, drenaż;
- wysokość n.p.m., neutral venue;
- attendance, zapełnienie i brak publiczności.

## Sędzia i dyscyplina

- kartki, faule i karne na mecz;
- foul→card conversion, added time, home/away bias;
- doświadczenie, sezon i VAR;
- `Referee×Team` i `Referee×TeamAggressiveness` wyłącznie ze shrinkage i minimalną próbą.

## Taktyka i matchup

- formation, blok, linia obrony, szerokość, directness;
- press vs press resistance;
- high line vs pace;
- aerial attack vs aerial defence;
- crosses vs box defending;
- set pieces vs set-piece defence;
- atak lewą stroną vs obrona prawą stroną.

## Kontekst i structural breaks

- tabela, kolejka, stawka, derby, dwumecz i aggregate score;
- priorytet rozgrywek i prawdopodobieństwo rotacji;
- VAR era, five-subs era, mecze bez publiczności, zmiany doliczonego czasu i przepisów;
- opening/current/closing odds, overround i ruch kursów;
- sygnały medialne i psychologiczne wyłącznie jako obiektywnie mierzone eksperymenty.

## Interakcje — obowiązkowa warstwa badawcza

Każdy ważny czynnik rozważamy zarówno samodzielnie, jak i warunkowo. Kandydaci:

`Team×Venue`, `Team×Opponent`, `OpponentStyle×TeamStyle`, `Weather×PlayingStyle`, `Wind×Crossing`, `MissingCB×AerialThreat`, `Fatigue×PressingIntensity`, `Heat×Fatigue`, `RefereeStrictness×AggressiveTeam`, `Referee×Team`, `PitchSize×HighPress`, `LineupWeakness×OpponentStrength`, `HomeAway×Team`, `RestDays×SquadDepth`.

Head-to-head nie jest automatycznie sygnałem. Może zostać użyte tylko wtedy, gdy efekt utrzymuje się po korekcie składu, trenera, siły drużyn, czasu i ma wystarczającą próbę.

## Wzorce powtarzalne i progi

Szukamy zdarzeń, które występują bardzo często i mogą odpowiadać rynkom bukmacherskim, np. `team_SOT>=3`, `team_corners>=3`, `team_cards>=1`, `team_goals>=1`. Nie wystarczy sama wysoka historyczna częstość.

Każdy wzorzec opisujemy przez:

- base rate i conditional rate;
- próbę `n` oraz effective sample size po decay;
- dolny przedział ufności / posterior lower bound;
- stabilność między sezonami;
- home/away split;
- korektę na siłę i styl przeciwnika;
- trend i recency;
- dostępny kurs, vig, edge i CLV;
- wynik OOS i paper trading.

Szczegóły: [[17 - Interakcje i wzorce powtarzalne]].

## Schemat rekordu registry

```yaml
feature_name:
definition:
entity_level:
data_source:
available_since:
known_at:
prediction_horizon:
hypothesised_effect:
interactions: []
minimum_sample:
shrinkage_policy:
missingness_policy:
data_quality:
model_version_added:
oos_effect:
decision: candidate
```
