---
tags: [moc, projekt, football-model]
status: active
---

# Mapa projektu

## Cel

Zbudować oparty na matematyce, statystyce i danych **globalny silnik wyszukiwania value w piłce nożnej**. System nie ma być ograniczony do jednej ligi ani jednego rynku. Premier League pozostaje pierwszym poligonem walidacyjnym, ale architektura od początku ma obsługiwać wiele lig i wybierać mecze/rynki według jakości danych, przewidywalności, ceny i oczekiwanej wartości netto.

Pierwszy zakres modelowania: 1X2, Over/Under 2.5 i BTTS. **Exact score nie jest rynkiem docelowym.** Rozkład goli może pozostać wewnętrznym narzędziem matematycznym do agregacji innych rynków.

Równolegle badamy rynki zdarzeń o wysokiej powtarzalności, m.in. shots, shots on target, corners, cards, team totals i wybrane player props — wyłącznie tam, gdzie dane i kursy są wystarczająco dobre.

## Przepływ wiedzy

`Globalny universe meczów → Data Quality Gate → tani screening → stan obu drużyn → kontekst → interakcje → modele zdarzeń → market scanner → cost/risk filter → BET / NO BET / NO PREDICTION`

## Główne zasady

- nie skanujemy wszystkiego drogimi źródłami;
- koszt danych i predykcji jest częścią decyzji ekonomicznej;
- najpierw używamy danych cache/historycznych i tanich endpointów, a dopiero później płatnych szczegółów dla shortlisty;
- wszystkie informacje są point-in-time;
- każda cecha i interakcja musi przeżyć test OOS;
- `NO BET` i `NO PREDICTION` są pełnoprawnymi wynikami;
- pogoda jest przede wszystkim cechą wyjątków/extreme-environment, a nie stałym filarem każdego meczu;
- przed kodowaniem wykonujemy ręczne pilotaże na realnych meczach, aby ujawnić luki danych i złe założenia.

## Rdzeń

- [[01 - Fundamenty matematyczne]]
- [[03 - Architektura modelu]]
- [[04 - Rejestr cech]]
- [[17 - Interakcje i wzorce powtarzalne]]
- [[11 - Czas predykcji i leakage]]
- [[12 - Ewaluacja i backtesting]]

## Dane, rynek i ekonomika

- [[05 - Źródła danych]]
- [[16 - Rejestr źródeł danych]]
- [[18 - Ekonomika pipeline i cost-aware scanning]]
- [[19 - Globalny zakres lig i quality gate]]
- [[20 - Global Data Coverage Matrix v1]]
- [[07 - Plan danych historycznych]]
- [[06 - Matematyka bukmacherska]]

## Pilotaże

- [[21 - Pilot live 27-08-2026]] — pierwszy ręczny test na rewanżach eliminacji UEL/UECL przed rozpoczęciem kodowania.

## Zarządzanie badaniami

- [[08 - Wersje modelu]]
- [[09 - Pytania badawcze]]
- [[10 - Następne kroki]]
- [[13 - Schemat danych]]
- [[14 - Decyzje i założenia]]
- [[15 - Teaser projektu]]
