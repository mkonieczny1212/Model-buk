---
tags: [next-actions, roadmap]
---

# Następne kroki

## Najbliższy milestone

- [x] Zamrozić pierwsze rynki badawcze: 1X2, O/U 2.5, BTTS; exact score wyłączony jako rynek docelowy.
- [x] Ustalić, że Premier League jest poligonem, a nie ograniczeniem docelowym.
- [x] Wprowadzić zasadę cost-aware scanning i lejka danych.
- [x] Zbudować wstępny Global Data Coverage Matrix dla ok. 20–30 lig + europejskich pucharów.
- [x] Uruchomić pierwszy ręczny pilot live na realnych meczach przed kodowaniem.
- [x] Utworzyć kanoniczny rejestr testowych betów oraz Excel tracker/dashboard.
- [x] Formalnie rozdzielić ręczne pilotaże od produkcyjnego, matematycznego modelu.
- [ ] Zamknąć Pilot #1 pełnym post-mortem i frozen metrics.
- [ ] Zamrozić Pilot #2 w rejestrze przed kickoffami i rozliczyć wszystkie wpisy bez hindsight.
- [ ] Zdefiniować reprodukowalny model `P_model` dla pierwszego rynku zdarzeń (np. corners lub SOT) zamiast ręcznych procentów.
- [ ] Zdefiniować uncertainty band, minimalny edge i regułę `BET/NO BET/NO PREDICTION`.
- [ ] Nadać każdej parze `league×market` Data/Market Quality Score.
- [ ] Zmierzyć koszt pobierania danych na ligę, dzień i shortlistę.
- [ ] Wykonać Provider Shootout: API-Football vs TheStatsAPI (+ Sportmonks jeśli potrzebne).
- [ ] Wykonać osobny audit polskich bookmakerów dla team props/corners/SOT/shots/cards.
- [ ] Wybrać pierwszy realny `budget cap` na dzień/tydzień.
- [ ] Zbudować Minimum Viable Dataset oraz canonical IDs.
- [ ] Uruchomić tani kolektor fixtures/basic odds oraz archiwizację snapshotów.
- [ ] Zbudować kodowy v0.1 i walk-forward backtest.

## Najbliższy eksperyment modelowy

Wybrać **jeden market family** z wystarczającą historią (preferencyjnie team corners albo team SOT) i stworzyć pierwszy formalny baseline:

1. rozkład count data (Poisson / Negative Binomial jako benchmarki);
2. team creation strength;
3. opponent suppression strength;
4. home/away;
5. time decay i strength of schedule;
6. dopiero potem interakcje;
7. chronologiczny holdout;
8. kalibracja progów `>= x`;
9. porównanie z zamrożonym kursem.

Celem jest zastąpienie ręcznego `P_model=66%` liczbą wyprodukowaną przez jednoznaczny algorytm.

## Cost-aware pipeline

- [ ] Tier 0: cache/history + fixture universe + statyczne profile lig/drużyn.
- [ ] Tier 1: tani screening wszystkich kandydatów.
- [ ] Tier 2: shortlist na podstawie quality/edge potential.
- [ ] Tier 3: płatne/świeże odds, lineup, injuries i szczegóły tylko dla shortlisty.
- [ ] Tier 4: pełny model + risk filter dla finalnych kandydatów.
- [ ] Logować `data_cost`, `compute_cost`, `api_credits_used` per run i per bet.

## Równoległy fundament danych

- [ ] Utworzyć tabele z [[13 - Schemat danych]].
- [ ] Wprowadzić `event_time`, `known_at`, `provider_timestamp` i `fetched_at`.
- [ ] Utworzyć Feature Registry według [[04 - Rejestr cech]].
- [ ] Utrzymywać Source Registry według [[16 - Rejestr źródeł danych]].
- [ ] Zmapować licencje, koszty i zakres każdego źródła.
- [ ] Oznaczyć structural breaks i zmiany providerów.
- [ ] Zbudować canonical IDs i reconciliation między providerami.

## Definition of done pierwszego pipeline'u

Reprodukowalny system, który może obserwować wiele lig, odrzucać słabe dane, liczyć tanie cechy lokalnie, pobierać drogie dane dopiero dla shortlisty, raportować skalibrowane prawdopodobieństwo/fair odds/edge oraz pełny koszt wygenerowania decyzji `BET/NO BET/NO PREDICTION`.

## Czego jeszcze nie robić

Nie kupować wielu feedów równolegle bez testu wartości. Nie odpytujemy kosztownych endpointów dla wszystkich spotkań. Nie optymalizujemy liczby zakładów — optymalizujemy wartość netto po kosztach i ryzyku. Nie traktujemy ręcznego pilota jako dowodu przewagi ani nie poprawiamy historycznych `P_model` po poznaniu wyniku.
