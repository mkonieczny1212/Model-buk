---
tags: [research-questions, hypotheses]
---

# Pytania badawcze

## Rdzeń modelu

- Czy Dixon–Coles poprawia kalibrację niskich wyników względem Mahera?
- Jaki half-life informacji jest optymalny i czy zależy od ligi/rynku?
- Czy bivariate Poisson lub hierarchiczny Bayes poprawia wyniki po uwzględnieniu złożoności?
- Jak dynamiczne jest home advantage i gdzie występują structural breaks?

## Cechy

- Czy xG wnosi informację ponad gole, strzały i SOT?
- Czy lineups/absencje poprawiają EARLY i ile wartości pojawia się po ogłoszeniu XI?
- Czy `LineupDelta` jest lepsze niż liczba absencji?
- Czy fatigue wymaga minut graczy, podróży i intensywności zamiast samych rest days?
- Czy pogoda pomaga w 1X2/golach, czy mocniej w SOT/corners/tempo?
- Czy referee effect jest stabilny i szczególnie użyteczny dla kartek/fauli?
- Które interakcje stylów są stabilne poza próbą?

## Interakcje i powtarzalność

- Czy `Team×Venue` daje stabilny efekt po korekcie siły przeciwnika?
- Czy `Team×Referee` wnosi informację ponad osobny efekt drużyny i sędziego?
- Czy `RefereeStrictness×TeamAggressiveness` przewiduje kartki lepiej niż proste średnie?
- Czy `Weather×PlayingStyle` lub `Wind×Crossing` poprawia rynki zdarzeń?
- Czy konkretne matchupy stylów powtarzają się przy zmianach trenerów i składów?
- Które progi (`SOT>=x`, `corners>=x`, `cards>=x`, `team_goals>=x`) mają najwyższy stabilny lower bound prawdopodobieństwa?
- Czy wysoka częstość zdarzenia pozostaje po korekcie home/away, opponent strength i recency?
- Jak duża musi być próbka, żeby traktować zależność H2H jako coś więcej niż szum?

## Rynek

- Która metoda usuwania vig daje najlepiej skalibrowany benchmark?
- Czy `PURE` wnosi informację ponad `MARKET`?
- Czy `HYBRID` poprawia log loss i closing-line value bez kopiowania closing odds?
- Czy edge utrzymuje się po kosztach, limitach i niepewności modelu?
- Na których rynkach częstych zdarzeń marża i błędy wyceny dają najlepszy risk-adjusted edge?

## Dane

- Jak zmiany providerów i definicji wpływają na cechy?
- Czy archiwalne forecasty pogodowe różnią się od użycia pogody zrealizowanej?
- Jak imputować braki bez wprowadzania informacji z przyszłości?
- Jak przenosić parametry między sezonami oraz dla beniaminków?
- Które źródło ma najlepszą zgodność i timestampy dla SOT, corners, cards, lineups i injuries?

Każde pytanie powinno otrzymać kartę eksperymentu z hipotezą, baseline, splitami czasowymi, minimalną próbą, metrykami, wynikiem i decyzją.
