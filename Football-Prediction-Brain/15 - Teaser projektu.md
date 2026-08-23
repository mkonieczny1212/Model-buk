---
tags: [teaser, status, overview]
status: active
---

# Model Buk — teaser projektu

## Co budujemy

Model Buk ma być systemem, który przed meczem zbiera dostępne w danym momencie dane, ocenia oba zespoły i konkretny kontekst spotkania, wylicza skalibrowane prawdopodobieństwa rynków, porównuje je z kursem bukmachera i kończy decyzją `BET/NO BET`.

Nie chcemy „zgadywać wyniku”. Chcemy znaleźć sytuacje, w których nasza wycena prawdopodobieństwa jest trwale lepsza od ceny rynkowej.

## Co już wiemy

- Startujemy od Premier League.
- Pierwsze rynki: **1X2, Over/Under 2.5 i BTTS**.
- **Exact score odrzucamy jako rynek docelowy**; rozkład goli może pozostać wyłącznie technicznym narzędziem modelu.
- Pierwszy benchmark: Poisson → attack/defence + home advantage → Dixon–Coles → modele dynamiczne.
- Budujemy osobne predykcje EARLY, PRE-MATCH i LINEUP.
- Każda informacja musi być point-in-time: model nie może wiedzieć niczego, co pojawiło się po cutoffie.
- Rynek jest benchmarkiem, nie odpowiedzią: oddzielamy `PURE`, `MARKET` i docelowo `HYBRID`.
- Każda nowa cecha, interakcja i strategia musi przeżyć chronologiczny holdout.

## Drugi ważny tor

Oprócz goli i wyniku będziemy wyszukiwać **stabilne, częste zdarzenia**, np. progi strzałów celnych, rożnych czy kartek. Interesuje nas nie tylko średnia drużyny, ale warunki konkretnego meczu: stadion, przeciwnik, sędzia, pogoda, skład, zmęczenie i ich wzajemne interakcje.

Przykład hipotezy: drużyna bardzo często osiąga `SOT>=3`, ale model sprawdza, czy efekt nadal istnieje na wyjeździe, przeciw mocnym rywalom, przy konkretnym stylu przeciwnika i po uwzględnieniu ceny rynku.

## Co jest teraz najważniejsze

1. **Data Audit v1** — jakość, dostępność, historia, point-in-time i cena źródeł.
2. Uruchomienie własnego archiwum aktualnych odds, injuries, lineups i weather snapshots.
3. Zbudowanie v0.1 oraz walk-forward backtestu.
4. Zbudowanie rejestru interakcji i pattern minera dla powtarzalnych zdarzeń.
5. Dopiero później: polityka stawek, bankroll, limity ryzyka i realne paper trading.

## Docelowy outcome

Dla każdego meczu chcemy otrzymać: aktualność i jakość danych → prawdopodobieństwa → fair odds → kurs rynkowy → edge/EV → confidence → najważniejsze czynniki i interakcje → rekomendowaną ekspozycję albo `NO BET`.

**Największym ryzykiem projektu nie jest koszt obliczeń. Jest nim jakość i dostępność danych oraz udowodnienie, że znaleziony edge działa także na nowych meczach.**
