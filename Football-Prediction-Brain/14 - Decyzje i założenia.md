---
tags: [decisions, assumptions, changelog]
---

# Decyzje i założenia

## Przyjęte

- Premier League jest pierwszym środowiskiem walidacyjnym, nie docelowym ograniczeniem.
- Docelowo system ma obsługiwać szeroki universe lig i europejskich pucharów, a później więcej, jeśli dane/rynek uzasadniają koszt.
- Pierwsze rynki modelowe: 1X2, O/U 2.5, BTTS.
- Exact score jest wyłączony jako rynek docelowy/rekomendacja.
- Rynki zdarzeń shots/SOT/corners/cards/team totals/player props są kandydatami badawczymi.
- Każda para `league×market` przechodzi osobny quality gate.
- Nie wykonujemy pełnego drogiego skanu wszystkich potencjalnych zakładów; stosujemy lejek kosztowy.
- Koszt danych, kredytów API, compute i wykonania jest częścią ekonomiki zakładu.
- `NO BET` i `NO PREDICTION` są pełnoprawnymi wynikami.
- Dane sportowe i rynek pozostają rozdzielone w `PURE` i `MARKET`.
- Wszystkie dane są point-in-time i wersjonowane.
- Walidacja jest chronologiczna.
- Każda grupa cech i interakcja musi udowodnić incremental predictive value.
- H2H ani seria nie są samodzielnym dowodem przewagi.
- Pogoda ma niski priorytet w normalnych warunkach; badamy głównie environment/climate shocks i interakcje.

## Ostrożne hipotezy, nie fakty

- niszowe ligi mogą być mniej efektywne, ale równocześnie mieć gorsze dane, wyższą marżę i niższą płynność;
- najlepszym źródłem zysku może być selection engine, a nie modelowanie każdego meczu;
- szeroki screening może być tani, jeśli opiera się na cache, batchowanych endpointach i lokalnych cechach;
- szczegółowe player/lineup/prop data powinny być pobierane dopiero dla shortlisty;
- market movement i exchange liquidity mogą zwiększyć jakość filtra;
- Asian Handicap może być bardziej efektywnym benchmarkiem niż 1X2 i należy go później zbadać jako osobny rynek.

## Otwarte decyzje

- liczba lig w Global Coverage Matrix v1;
- minimalny `League/Market Quality Score`;
- dzienny i miesięczny budget cap na API/data;
- maksymalny koszt danych na jednego actionable candidate;
- dokładny cutoff modeli;
- metoda usuwania vig;
- pierwsze rynki zdarzeń do produkcyjnego testu;
- próg edge po uwzględnieniu niepewności i kosztów;
- finalny provider stack i licencje.

Aktualizuj tę notatkę po każdym rozstrzygnięciu z [[09 - Pytania badawcze]].
