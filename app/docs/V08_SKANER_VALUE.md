# Model BUK 0.8 — skaner value PAPER

## Aktywny profil

- końcowy kurs rekomendacji: 1,30–2,00;
- preferowany koszyk analityczny: 1,65–1,80;
- konserwatywny edge: minimum 3 p.p.;
- konserwatywne EV netto: minimum 5%;
- podatek od stawki: 12%;
- maksymalny wiek kursu: 6 godzin;
- wymagany de-vig na podstawie pełnego rynku;
- przy braku przedziału model stosuje jawny bufor 3 p.p. do P w trybie PAPER;
- status BET wymaga poprawnego, zwalidowanego przedziału prawdopodobieństwa;
- najwyżej jeden single z meczu;
- kupony: dwie nogi, różne mecze, ten sam bukmacher;
- status: PAPER.

Zakres kursu dotyczy całej rekomendacji. Single musi sam mieć kurs 1,30–2,00.
Kupon może łączyć niższe kursy, np. 1,30 × 1,30 = 1,69.

## Matematyka kuponu

Dla nóg z różnych meczów pierwsza wersja przyjmuje:

```
O = O1 * O2
P = P1 * P2
P_conservative = P1_lower * P2_lower
net_return = 0.88 * O
conservative_EV = P_conservative * net_return - 1
```

Podatek jest naliczany raz od całej stawki. Każda noga musi mieć dodatni
konserwatywny edge i dodatnie EV przed podatkiem. Cały kupon musi mieć minimum
5% konserwatywnego EV netto i minimum 3 p.p. konserwatywnego edge.

Iloczyn prawdopodobieństw jest pierwszą, jeszcze niezwalidowaną metodą przybliżenia
prawdopodobieństwa łącznego dla różnych meczów. Kupony pozostają PAPER do zebrania
osobnej próby i sprawdzenia zależności. Zdarzeń z jednego meczu nie łączymy bez
modelu łącznego rozkładu oraz rzeczywistego kursu same-game combo.

## API i zapis

- `POST /api/scan` — skanuje ograniczoną liczbę fixture;
- `GET /api/scans` — zwraca zamrożone skany;
- `scan_runs` — pełny snapshot profilu i wyniku;
- `scan_selections` — single;
- `scan_tickets` — kupony;
- `ticket_legs` — osobno zapisane nogi kuponów do późniejszego rozliczenia i CLV;
- `selection_settlements` — przygotowana tabela przyszłych rozliczeń.
- `ticket_leg_settlements` — przygotowana tabela rozliczeń nóg kuponów.

Skan częściowo udany zachowuje wyniki pozostałych meczów i osobno zwraca błędy.
Tryb `deep=false` pobiera tylko kontekst potrzebny skanerowi i ogranicza koszt
API. Szczegółowa analiza pojedynczego meczu nadal pobiera szerszy kontekst.

## Warunek promocji do BET

Status BET nie jest nadawany przez sam filtr kursowy. Wymaga prospektywnej
walidacji osobno dla modelu, rynku, ligi oraz kuponów. Należy rozliczać ROI po
podatku, Brier Score, kalibrację, CLV i maksymalne obsunięcie.
