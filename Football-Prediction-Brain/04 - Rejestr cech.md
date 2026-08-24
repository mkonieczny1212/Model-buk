---
tags: [features, registry, blueprint]
---

# Rejestr cech

To katalog kandydatów, a nie lista cech, które automatycznie trafią do jednego modelu.

## Must-have

- dynamiczna siła ataku i obrony;
- home/away i team-specific home advantage;
- jakość przeciwników / strength of schedule;
- wynik, gole, strzały, strzały celne;
- rożne, faule i kartki tam, gdzie definicje są stabilne;
- czas, sezon i liga;
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

Okna 1/3/5/8/10 meczów oraz wykładniczy decay. Forma powinna korygować venue i siłę rywala. Kandydaci: xG difference, shot/SOT difference, corners difference, finishing, goalkeeper form, set pieces. Sygnały „luck”: goals−xG, conceded−xGA, conversion, save percentage, karne, samobóje, słupki i czerwone kartki.

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

## Środowisko — niski priorytet bazowy, wysoki przy ekstremach

Nie używamy normalnych różnic pogodowych jako dominującego sygnału. Priorytet mają cechy typu `EnvironmentalShock`:

- skrajna temperatura lub wilgotność;
- bardzo silny wiatr/opady/śnieg;
- wysoka wysokość n.p.m.;
- nietypowa murawa/sztuczna nawierzchnia;
- duża różnica klimatu pomiędzy miejscem pochodzenia zespołu a venue;
- daleka podróż połączona z ekstremalnym środowiskiem.

Kandydaci: `TemperatureShock`, `PrecipitationShock`, `WindShock`, `AltitudeShock`, `ClimateDifference`, `TravelClimateDifference`. Normalna brytyjska pogoda bez wyraźnego odchylenia powinna mieć niski priorytet.

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

`Team×Venue`, `Team×Opponent`, `OpponentStyle×TeamStyle`, `WeatherShock×PlayingStyle`, `WindShock×Crossing`, `MissingCB×AerialThreat`, `Fatigue×PressingIntensity`, `HeatShock×Fatigue`, `RefereeStrictness×AggressiveTeam`, `Referee×Team`, `PitchSize×HighPress`, `LineupWeakness×OpponentStrength`, `HomeAway×Team`, `RestDays×SquadDepth`.

Head-to-head nie jest automatycznie sygnałem. Może zostać użyte tylko wtedy, gdy efekt utrzymuje się po korekcie składu, trenera, siły drużyn, czasu i ma wystarczającą próbę.

## Wzorce powtarzalne i progi

Szukamy zdarzeń, które występują bardzo często i mogą odpowiadać rynkom bukmacherskim, np. `team_SOT>=3`, `team_corners>=3`, `team_cards>=1`, `team_goals>=1`. Nie wystarczy sama wysoka historyczna częstość.

Każdy wzorzec opisujemy przez base rate, conditional rate, próbę, effective sample size, lower bound, stabilność sezonową, home/away, opponent adjustment, recency, dostępny kurs, vig, edge, CLV i wynik OOS.

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
retrieval_cost_class: free|cached|cheap|expensive
model_version_added:
oos_effect:
decision: candidate
```
