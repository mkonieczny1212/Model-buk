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
- [ ] Zakończyć pilot 27.08.2026 wynikami po meczu i ocenić, które sygnały były użyteczne.
- [ ] Nadać każdej parze `league×market` Data/Market Quality Score.
- [ ] Zmierzyć koszt pobierania danych na ligę, dzień i shortlistę.
- [ ] Wykonać Provider Shootout: API-Football vs TheStatsAPI (+ Sportmonks jeśli potrzebne).
- [ ] Wybrać pierwszy realny `budget cap` na dzień/tydzień.
- [ ] Zbudować Minimum Viable Dataset oraz canonical IDs.
- [ ] Uruchomić tani kolektor fixtures/basic odds oraz archiwizację snapshotów.
- [ ] Zbudować v0.1 i walk-forward backtest.

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

## Równoległy tor: zdarzenia powtarzalne

- [ ] Zweryfikować historyczne coverage shots/SOT/corners/cards.
- [ ] Zbudować profile progów per team/venue/opponent strength/sezon.
- [ ] Dodać shrinkage, lower bounds i minimalną próbę.
- [ ] Przetestować interakcje z [[17 - Interakcje i wzorce powtarzalne]].
- [ ] Do deep-data kierować wyłącznie wzorce, które przeszły tani screening.

## Definition of done pierwszego pipeline'u

Reprodukowalny system, który może obserwować wiele lig, odrzucać słabe dane, liczyć tanie cechy lokalnie, pobierać drogie dane dopiero dla shortlisty, raportować prawdopodobieństwo/fair odds/edge oraz pełny koszt wygenerowania decyzji `BET/NO BET/NO PREDICTION`.

## Czego jeszcze nie robić

Nie kupować wielu feedów równolegle bez testu wartości. Nie odpytujemy kosztownych endpointów dla wszystkich spotkań. Nie optymalizujemy liczby zakładów — optymalizujemy wartość netto po kosztach i ryzyku. Nie traktujemy ręcznego pilota jako dowodu przewagi — służy on do testu procesu i jakości danych.
