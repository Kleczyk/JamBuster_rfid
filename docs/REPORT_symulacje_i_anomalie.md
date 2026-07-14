# Raport: obecne symulacje JamBuster-RFID i plan rozszerzenia o anomalie

Dokument roboczy. Stan repozytorium: gałąź `main`, data 2026-06-24.
Cel: (1) przegląd obecnych symulacji RL sterowania sygnalizacją z detekcją RFID,
(2) projekt rozszerzenia w stronę symulacji z **anomaliami** i treningu modelu **detekcji anomalii**.

---

## 1. Struktura projektu — dwie warstwy

Projekt obejmuje dwa poziomy, odpowiadające dwóm artykułom. Mają wspólny rdzeń koncepcyjny
(PPO + Transformer + detekcja RFID), ale różny stan dojrzałości implementacyjnej.

| | Warstwa 1 — pojedyncze skrzyżowanie | Warstwa 2 — sieć 3×3 (9 skrzyżowań) |
|---|---|---|
| Artykuł | `article/ppo_transformer_paper*` (ASTRJ, „zakłócenia") | `article/complex_systems_paper/` |
| Architektura | PPO-Transformer, jednoagentowy | hierarchiczny **Manager–Worker**, wieloagentowy (CTDE) |
| Kod symulacji | ✅ `envs/`, `models/`, `callbacks/`, `configs/`, `nets/ppo_transformer_intersection/` | ❌ brak — planowana implementacja `grid_rfid` |
| Topologia | ✅ realna, używana w treningu | ✅ wygenerowana poglądowo (`figures/grid3x3.net.xml`, 9 TLS) |
| Wyniki | ✅ **zmierzone** | 🟡 **orientacyjne (placeholder)** — w tym raporcie pomijane |

> **Uwaga o wynikach warstwy 2.** Artykuł `complex_systems_paper` jest wersją roboczą; wszystkie
> liczby wynikowe to wartości ilustracyjne zakotwiczone w warstwie 1, nie pomiary (potwierdzone
> w `complex_systems_paper/README.md` i `CHANGELOG.md`). W tym raporcie świadomie nie przytaczamy
> tych liczb — zostaną wstawione po uruchomieniu `grid_rfid`.

---

## 2. Warstwa 1 — pojedyncze skrzyżowanie (zaimplementowana, zmierzona)

### 2.1 Sieć i sygnalizacja
- `nets/ppo_transformer_intersection/network.net.xml`: skrzyżowanie 4-wlotowe, symetryczne;
  węzeł `center` sterowany. Każdy wlot/wylot 2 pasy, ~190 m, v_max 13,89 m/s (~50 km/h).
- TLS bazowy (statyczny, w pliku sieci): 4 fazy — NS-zielona 42 s, NS-żółta 3 s, EW-zielona 42 s,
  EW-żółta 3 s; cykl 90 s. Środowisko RL instaluje własny `tlLogic` i nadpisuje sterowanie.

### 2.2 Scenariusze ruchu
Trzy klasy pojazdów: **car** (5 m, 50 km/h), **bus** (12 m, 30 km/h), **delivery** (7,5 m, 36 km/h).
Symulacja 7200 s (2 h), krok 1 s.
- **Trening** (`routes.rou.xml`, seed 42): symetryczny profil dobowy, identyczny na 4 wlotach
  (niski 600 → średni 1200 → szczyt 1800 → … → niski 600 poj/h na wlot).
- **Test** (`routes_test.rou.xml`, seed 43): asymetryczny, N/S obciążone ~2× mocniej niż E/W —
  test generalizacji poza rozkład treningowy.
- Konfiguracje: `simulation.sumocfg` vs `simulation_test.sumocfg`.

### 2.3 Detekcja RFID
- `rfid_detectors.add.xml`: 8 pętli indukcyjnych E1 (2 na wlot × 4 wloty), 5 m przed skrzyżowaniem,
  próbkowanie 1 s. Id z prefiksem `rfid_<kierunek>_<pas>`.

### 2.4 Środowisko RL (`envs/ppo_transformer_env.py`)
- **Obserwacja**: macierz (48, 15) — okno przesuwne 48 kroków decyzyjnych. 15 cech = 12 zliczeń RFID
  (4 kierunki × 3 typy) + 2 one-hot fazy (NS/EW) + 1 znormalizowany czas zielonego `τ = elapsed/60`.
- **Akcja**: `MultiDiscrete([2, 3])` = (faza NS/EW) × (zmiana zielonego −5/0/+5 s).
- **Nagroda**: `r = −(0,55·delay + 0,30·queue + 0,15·stops)`.
- **Ograniczenia bezpieczeństwa**: zielone 10–60 s, żółte 3 s, krok decyzyjny `delta_time` = 5 s.
- **Zakłócenia RFID** (stan obecny): `_apply_rfid_noise` (linia 620) — rozrzedzenie binomialne
  `ñ ~ Binomial(n, 1 − p_noise)`, sterowane jednym skalarem `rfid_noise_rate` (linia 173).

### 2.5 Model i trening
- `models/ppo_transformer_model.py`: `Linear(15→64)` → uczona pozycja (48×64) → `TransformerEncoder`
  (2 warstwy, 4 głowice, d=64, FFN=128, dropout=0,1) → ostatni token → głowice: faza (2), czas (3),
  wartość (1).
- Stos: RLlib (stary API stack) + Ray Tune. Configi: `ppo_transformer.yaml` (klaster, 110 env runnerów)
  vs `ppo_transformer_baseline.yaml` (lokalny, 1 runner + GUI). HP: lr 3e-4, γ 0,99, λ 0,95, clip 0,2.
- Ewaluacja trójpoziomowa (callbacki `metrics_callbacks.py`): train / `baseline_eval` (test, `p=0,0`) /
  `baseline_noisy_eval` (test, `p=0,2`). Metryki: delay, queue, stops, throughput.

### 2.6 Wyniki zmierzone (z artykułu ASTRJ)
Scenariusz testowy: opóźnienie 8,12 s → 8,78 s przy 20% utracie odczytów (+8,1%; różnica nieistotna
statystycznie, n=5). Wniosek: model odporny na jednorodny szum 20%.

---

## 3. Warstwa 2 — sieć 3×3 (artykuł `complex_systems_paper`, wersja robocza)

### 3.1 Co już istnieje (artefakty w repo)
- **Topologia 3×3**: `figures/grid3x3.net.xml`, 9 sygnalizacji (`netgenerate`, dwupasmowe krawędzie,
  2 fazy niekonfliktowe N↔S / W↔E, 12 wlotów brzegowych).
- **72 detektory RFID** (E1, jeden na pas wlotowy każdego z 9 węzłów) — `make_rfid_overlay.py`.
- **Model popytu „korytarzowy z tłem"** (specyfikacja projektowa, `demand_profile.json`):
  natężenie per-wlot `λ_e(t)` = (korytarze + tło·waga) × profil dobowy `φ(t)` (gaussowski szczyt).
  Korytarze: C1 W→E 1800, C1' E→W 900, C2 N→S 1200 poj/h; tło ≈600 poj/h (`randomTrips`).
  Miks klas 80% car / 13% bus / 7% delivery.
- **Pełna metodologia**: per-węzeł ten sam wektor obserwacji (15-D); nagroda sieciowa
  `R = mean_i r_i − w_b·std_i(queue_i)`; CTDE (scentralizowana wartość); warianty koordynacji
  niezależny / GAT-sąsiedzki / manager (ablacje).

### 3.2 Czego brakuje — implementacja `grid_rfid`
1. Środowisko wieloagentowe dla siatki 3×3 (odpowiednik `PPOTransformerEnv` dla 9 sprzężonych węzłów).
2. Model Manager–Worker (wspólny enkoder workera + manager z uwagą nad węzłami + scentralizowana wartość).
3. Pliki scenariusza SUMO: `.rou.xml` (realizacja modelu korytarzowego), `.sumocfg`, wpięcie detektorów.
4. Configi treningowe wariantów koordynacji + `manager_interval`, `w_b`.
5. Baseline'y w kodzie: stałoczasowy (Webster), Miller, max-pressure; odtworzone PressLight/CoLight/MPLight.
6. Realne przebiegi treningu/ewaluacji → zastąpienie liczb orientacyjnych zmierzonymi.

---

## 4. Punkt wyjścia do anomalii: dzisiejszy „szum" to nie anomalia

Obecne zakłócenie (`rfid_noise_rate`) jest **stacjonarnym, jednorodnym, niezależnym (i.i.d.)** gubieniem
odczytów. Nie ma struktury czasowej ani przestrzennej, więc **nie nadaje się jako anomalia do wykrycia** —
detektor anomalii nie ma czego „zauważyć". Docelowa anomalia ma być **strukturalna, zlokalizowana i
etykietowana** — to prowadzi do reżimu z wyłączaniem pasów opisanego niżej.

---

## 5. Docelowy plan: dwa reżimy ruchu na kracie 3×3

Plan dla detekcji anomalii opiera się na **dwóch zbiorach danych** generowanych na tej samej kracie
3×3 (warstwa 2). Różnią się tym, czy sieć jest sprawna, oraz tym, czego model się uczy.

### 5.1 Zbiór 1 — TRENING ZDROWY z losowym obciążeniem wlotów

Sieć działa **normalnie** (wszystkie pasy przejezdne). Ruch = korytarze + tło, jak w obecnym modelu
popytu, ale z **kluczową losowością**: w każdym epizodzie losowane jest, **które** z 12 wlotów
brzegowych pełnią rolę ciężkich korytarzy. Raz obciążone są jedne wjazdy, raz inne — dzięki temu
model uczy się **normalnych wzorców ruchu** niezależnie od konkretnego układu popytu i nie „zapamiętuje"
jednego rozkładu. To jest rozkład odniesienia, względem którego anomalia ma być wykrywalna.

Kontrast: dotychczasowy `demand_profile.json` (stałe korytarze W2/E2/N1) jest **ustalony** — nadaje się
jako układ testowy/odniesienia, nie jako rozkład treningowy.

**Rysunek:** `article/complex_systems_paper/figures/train_demand_randomization.png`
(skrypt `make_train_demand_randomization.py`):
- (a) heatmapa **epizody × 12 wlotów** — widoczna losowość, które wjazdy są obciążone;
- (b) częstość obciążenia per-wlot nad wieloma epizodami ≈ **jednorodna** (~0,20 każdy → brak
  uprzywilejowanego wlotu), ze stałymi korytarzami zbioru testowego zaznaczonymi dla kontrastu.

### 5.2 Zbiór 2 — TRENING+WALIDACJA DOCELOWA z anomaliami (wyłączane pasy)

Do sieci wprowadzamy **anomalię strukturalną**: losowo **wyłączane pasy/połączenia** w skrzyżowaniach.
W SUMO realizowane najprościej przez **usunięcie połączenia** (`<connection ... >`/`<deletion>` lub
zakaz `disallow="all"` na pasie) — w efekcie pojazdy nie mogą przejechać danym pasem i **muszą jechać
inaczej** (rerouting). To zmienia rzeczywisty ruch, a w konsekwencji **detektor RFID czyta dany pas
inaczej** (spadek/zanik zliczeń na pasie zamkniętym, wzrost na pasach objazdu).

**Zadanie modelu (nowe):** oprócz sterowania — **zlokalizować pas z anomalią**, tj. wskazać pas, który
nie jest w pełni przepustowy lub w ogóle zamknięty. Etykieta jest zasadniczo **binarna (0/1)**:
przejazd / brak przejazdu; opcjonalnie ciągła (**% przepustowości** pasa, np. 0,0–1,0).

**Rysunek:** `article/complex_systems_paper/figures/anomaly_lane_closures.png`
(skrypt `make_anomaly_lane_closures.py`):
- (a) krata z przykładowym **losowym zestawem wyłączonych pasów** (czerwone) + objazd + detektory RFID;
- (b) **losowość zamknięć**: epizody × monitorowane pasy, różny podzbiór wyłączonych pasów co epizod
  (to jest cel etykiety lokalizacji);
- (c) **sygnatura RFID anomalii**: zliczenia na pasie zamkniętym spadają do ~0, na pasie objazdu rosną —
  to wzorzec, który model ma się nauczyć rozpoznawać.

### 5.3 Zestawienie reżimów

| | Zbiór 1 (zdrowy) | Zbiór 2 (anomalie) |
|---|---|---|
| Stan sieci | wszystkie pasy przejezdne | losowo wyłączane pasy/połączenia |
| Źródło losowości | które wloty obciążone | które pasy wyłączone (+ obciążenie) |
| Rola | trening rozkładu normalnego | trening+walidacja detekcji/lokalizacji |
| Etykieta anomalii | wszędzie 0 | 1 na pasach wyłączonych (opcj. % przepustowości) |
| Ruch realny | normalny | rerouting wokół zamknięć |
| Odczyt RFID | normalny | zaburzony lokalnie (spadek/wzrost zliczeń) |

---

## 6. Zadanie modelu: lokalizacja anomalii (etykieta per-pas)

- **Przestrzeń etykiet** = **72 monitorowane pasy wjazdowe** (po jednym detektorze RFID na pas) —
  potwierdzone enumeracją sieci (`make_anomaly_lane_closures.py` → `monitored lanes: 72`). To naturalna
  i zgodna z detektorami przestrzeń lokalizacji.
- **Wyjście modelu**: dodatkowa **głowica lokalizacji** obok głowic sterowania (faza/czas/wartość) —
  wektor `[0,1]^72` (sigmoid per pas; lub per pas w obrębie węzła, zgodnie z dekompozycją Worker).
  Wariant binarny: przejazd/brak; wariant ciągły: szacowana % przepustowości pasa.
- **Strata**: binary cross-entropy (lub MSE dla wariantu ciągłego) względem etykiety ground-truth z SUMO,
  **niezależna od nagrody RL** — sterowanie i detekcja to dwa cele (multi-task), które można ważyć.
- **Metryki detekcji**: precision / recall / F1 per pas, dokładność lokalizacji (IoU/top-k),
  **opóźnienie detekcji** (po ilu krokach od zamknięcia model je wykrywa).

---

## 7. Realizacja w SUMO i kanał etykiet (ground-truth)

1. **Generacja zamknięć**: na starcie epizodu losowo wybrać podzbiór pasów do wyłączenia (liczba i
   lokalizacja z rozkładu — patrz `make_anomaly_lane_closures.py`, panel b). Zastosować w SUMO
   (usunięcie połączenia / `disallow`), opcjonalnie z oknem czasowym `[t0, t1]` (anomalia pojawia się
   i znika w trakcie epizodu).
2. **Ground-truth**: w każdym kroku znana jest maska wyłączonych pasów → wektor etykiet `y ∈ {0,1}^72`
   (lub `[0,1]^72` dla % przepustowości). Generowany deterministycznie ze stanu scenariusza.
3. **Kanał danych dla modelu**: ten sam strumień RFID (zliczenia per pas/klasa w oknie) — model
   wnioskuje anomalię z **rozbieżności obserwowanego wzorca względem normy** (zbiór 1).
4. **Zapis**: rozszerzyć `info` środowiska o `info["lane_anomaly"] = {"label": y, "passability": p}`;
   callbacki zbierają parę (obserwacja RFID ↔ etykieta) do zbioru uczącego/ewaluacyjnego.

> Uwaga implementacyjna: to wymaga środowiska kraty (`grid_rfid`, §3.2). W obecnym, jednoskrzyżowaniowym
> env można najtaniej **zaprototypować mechanikę** (wyłączenie pasa + etykieta + sygnatura RFID) zanim
> powstanie pełna krata.

---

## 8. Anomalie sensoryczne RFID — tor wtórny (opcjonalny)

Niezależnie od anomalii strukturalnych (wyłączone pasy), kanał RFID może podlegać **awariom sensora**.
To osobny, komplementarny tor (do rozważenia później): random/bursty dropout, martwy detektor,
stuck-at, fałszywe zliczenia, dryf, desync, błędna klasyfikacja typu. Hak istnieje już dziś
(`_apply_rfid_noise`, warstwa 1). Trudność: model musi **odróżnić** awarię sensora (dane złe, ruch OK)
od anomalii ruchowej (dane dobre, ruch zaburzony — wyłączony pas). W pierwszej kolejności skupiamy się
na anomaliach strukturalnych z §5–7.

---

## 9. Mapa drogowa i otwarte kwestie

**Kolejność prac:**
1. Figury reżimów (✅ zrobione: `train_demand_randomization.png`, `anomaly_lane_closures.png`).
2. Generator scenariuszy `grid_rfid`: krata 3×3 + losowy popyt (zbiór 1) + losowe zamknięcia pasów (zbiór 2).
3. Kanał etykiet ground-truth (maska wyłączonych pasów → `y ∈ {0,1}^72`).
4. Głowica lokalizacji w modelu + strata multi-task (sterowanie + detekcja).
5. Trening na zbiorze 1+2, ewaluacja detekcji (P/R/F1, opóźnienie detekcji) na held-out zamknięciach.
6. (Opcjonalnie) tor anomalii sensorycznych (§8) i odróżnianie awarii sensora od anomalii ruchowej.

**Otwarte kwestie do decyzji:**
- Etykieta **binarna** (przejazd/brak) czy **ciągła** (% przepustowości)? Plan zakłada binarną z
  opcją ciągłej.
- Granulacja etykiety: per pas (72) — przyjęte; alternatywnie per połączenie/skręt.
- Ile pasów wyłączać na epizod i czy z oknem czasowym (statyczne vs pojawiające się/znikające).
- Czy detekcja ma **sprzęgać się ze sterowaniem** (np. fallback/priorytet przy wykrytym zamknięciu),
  czy działać jako równoległa głowica raportująca.
- Czy zbiór 2 służy też do treningu sterowania (robustness na zamknięcia), czy tylko do detekcji.
