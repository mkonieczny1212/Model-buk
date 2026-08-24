---
tags: [literatura, papers, research]
---

# Literatura i publikacje

## Fundament ogólny

- Ronald J. Gould, *Mathematics in Games, Sports, and Gambling* — prawdopodobieństwo, Poisson, statystyka, regresja, testy hipotez i wartość oczekiwana.
- Wayne L. Winston, *Mathletics* — regresja, symulacja Monte Carlo, power ratings i Kelly.

## Piłka nożna i modelowanie

- Leonardo Egidi, Dimitris Karlis, Ioannis Ntzoufras, *Predictive Modelling for Football Analytics* (2025) — pełny pipeline predykcyjny i podejście bayesowskie.
- Clive Beggs, *Soccer Analytics: An Introduction Using R* (2024) — praktyka modelowania wyników, Elo, Poisson i strategie bettingowe.
- Daniel Memmert, Dominik Raabe, *Data Analytics in Football* — dane pozycyjne, przestrzeń i performance analytics.
- Maher (1982), *Modelling association football scores* — parametry ataku i obrony.
- Dixon & Coles (1997), *Modelling Association Football Scores and Inefficiencies in the Football Betting Market* — zależność niskich wyników i ważenie czasowe.
- Karlis & Ntzoufras — bivariate Poisson dla wyników sportowych.
- Baio & Blangiardo — hierarchiczny model bayesowski wyników piłkarskich.
- Constantinou, Fenton & Neil — modele bayesowskie łączące dane ilościowe z informacją kontekstową; potencjalnie istotne dla `STATE + CONTEXT + INTERACTIONS`.

## Efektywność rynku i wybór lig/rynków

- Angelini & De Angelis (2019), *Efficiency of online football betting markets* — 41 bookmakerów, 11 europejskich lig i 33 tys. meczów; efektywność różni się między ligami, a najlepsze dostępne kursy mogą zmieniać ekonomiczny wynik strategii.
- Hegarty & Whelan (2025), *Forecasting soccer matches with betting odds: A tale of two markets* — tradycyjny 1X2 wykazuje favourite–longshot bias, podczas gdy Asian Handicap może być znacznie efektywniejszym forecastem; ważny benchmark dla przyszłego market selection.
- Franke (2020), *Do market participants misprice lottery-type assets? Evidence from the European soccer betting market* — favourite–longshot bias zarówno u bookmakerów, jak i na exchange.
- Buhagiar, Cortis & Newall (2018) — analiza 163 992 kursów z 10 lig europejskich; potwierdza potrzebę traktowania longshotów i implied probability bardzo ostrożnie.
- Kossmeier & Weinberger — pan-europejska analiza efektywności kursów i biasów rynkowych.

## Zaawansowane kierunki

- xG, xT, VAEP i EPV — jakość sytuacji oraz wartość działań zamiast samych wyników;
- modele state-space — zmienna w czasie siła drużyn i structural breaks;
- badania lineups/player ratings — należy testować marginalną wartość składów;
- workload, congestion i travel — możliwe przejście przez zmęczenie, ryzyko urazu i dostępność;
- pogoda/środowisko — priorytet tylko przy ekstremach, dużej zmianie klimatu, wysokości, nietypowej murawie lub interakcji ze stylem;
- modele sędziów — heterogeniczność ważna szczególnie dla kartek i fauli;
- modele wielu statystyk i graczy — dalszy kierunek po stabilnym modelu przedmeczowym.

## Rynek bukmacherski

- *The Economics of Sports Betting* — pricing, efektywność rynku i prawdopodobieństwa.
- literatura o usuwaniu marży, modelu Shina i favourite–longshot bias.
- betting exchange jako benchmark ceny, płynności i market movement.

## Zasada korzystania z literatury

Publikacja daje hipotezę i metodę, ale nie dowód, że zadziała w naszym zbiorze. Każdy pomysł trafia do [[09 - Pytania badawcze]] i przechodzi procedurę z [[12 - Ewaluacja i backtesting]]. Literatura może również wskazać, że dany rynek jest zbyt efektywny — to cenna informacja dla selekcji kapitału.
