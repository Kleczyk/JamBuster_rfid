# grid_rfid — symulacja + generacja datasetów do detekcji anomalii

Pipeline przygotowujący **oetykietowane datasety** (train/val/test) do późniejszego
treningu/walidacji/testu modelu **lokalizacji anomalii na poziomie pasa** na sygnalizowanej
siatce 3×3 z detekcją RFID (SUMO/TraCI). **Bez RL** — światłami steruje wbudowany statyczny
program SUMO; to czysta generacja danych.

## Dwa reżimy ruchu

- **Zdrowy** (`demand="healthy"`): sieć w pełni przejezdna; w każdym epizodzie losowany jest
  zbiór obciążonych wlotów (korytarze) → model uczy się rozkładu normalnego.
- **Z anomaliami**: losowo **wyłączane wewnętrzne krawędzie wlotowe** (oba pasy `disallow` przez
  TraCI) z czasem startu `t0` w pierwszej tercji epizodu → pojazdy reroutują, RFID na zamkniętym
  pasie czyta ~0. Etykieta wyznaczana **deterministycznie**.

## Klasy pojazdów i anomalie klasowo-warunkowe (wariant 2)

Presety klas w `vehicle_classes.py` (`--class-set`):

- **`v1`** (domyślny): car/bus/delivery — oryginalny układ, cechy `72×3`.
- **`v2`**: car / **ev** (ostry start) / delivery / bus / **truck** / **trailer** (wolne,
  długie) — 6 klas o różnej kinematyce i **unikalnych SUMO vClass**, cechy `72×6`.
  Tło ruchu w v2 używa pełnego mixu klas (w v1 pozostaje car-only).

**Anomalie klasowo-warunkowe** (`--class-ban-frac F`, dom. 0 = wyłączone): część epizodów
anomalnych zamiast pełnego zamknięcia dostaje **zakaz wjazdu 1–2 klas** z puli `bannable`
(v2: truck/trailer/delivery/bus) — kanał RFID zabronionej klasy gaśnie, reszta ruchu jedzie
normalnie. Sygnał niewidoczny w sumie zliczeń → wymaga kanałów per klasa (ablacja: RFID
z klasyfikacją vs zwykła pętla).

**Etykiety** w `.npz`:
- `Y (N, 72)` — ciągła: udział mixu zabronionych klas (pełne zamknięcie = 1.0, zakaz
  `delivery` = 0.10 itd.);
- `Y_class (N, 72, K)` — binarna per pas × klasa (pełna prawda podstawowa).

## Podgląd GUI (ta sama symulacja co w generatorze)

`grid_rfid.preview` odpala jeden epizod w `sumo-gui` z identycznym popytem
(korytarze+tło) i identyczną mechaniką zamknięć (`disallow` przez TraCI) jak
`grid_rfid.generate`. Zamknięte pasy są obrysowane na czerwono w momencie `t0`,
a konsola raportuje skumulowane zliczenia RFID otwarte vs zamknięte.

```bash
uv run python -m grid_rfid.preview --mode healthy --seed 7            # reżim zdrowy
uv run python -m grid_rfid.preview --mode anomaly --seed 7            # losowe 1–3 zamknięcia
uv run python -m grid_rfid.preview --mode anomaly --closed A1B1,B1B0 --t0 120
# wariant 2: zakaz klasowy (pomarańczowy zamiast czerwonego)
uv run python -m grid_rfid.preview --class-set v2 --mode anomaly \
    --closed A1B1 --ban-classes truck,trailer --t0 120
uv run python -m grid_rfid.preview --class-set v2 --mode anomaly --class-ban-frac 1.0
```

Flagi: `--horizon` (dom. 900 s), `--delay` (ms/krok GUI, dom. 80), `--n-closed MIN MAX`,
`--binary sumo` (test headless). Ten sam `--seed` ⇒ ten sam popyt w obu trybach,
więc różnicę robi wyłącznie anomalia.

## Demo "wyścig klas" (porównanie kinematyki)

Prosta droga z 6 pasami — na każdym jeden typ pojazdu (kolorowany). Pojazdy ruszają
razem, hamują na czerwonym w połowie drogi, po pauzie zielone i wspólny start.
Konsola drukuje ranking czasu na pierwsze 50 m po każdym starcie.

```bash
uv run python -m grid_rfid.class_race                # GUI, 3 rundy
uv run python -m grid_rfid.class_race --rounds 5 --pause 15 --delay 150
```

## Generacja datasetu

```bash
# szybki sample
uv run python -m grid_rfid.generate --out datasets/grid_rfid_sample \
    --train 10 --val 4 --test 4 --horizon 500

# docelowy dataset v1 (3 klasy, pełne zamknięcia)
uv run python -m grid_rfid.generate --out datasets/grid_rfid_v1 \
    --train 200 --val 50 --test 50 --horizon 1800 --healthy-frac 0.5 --seed 2025

# wariant 2: 6 klas + 50% anomalii jako zakazy klasowe
uv run python -m grid_rfid.generate --out datasets/grid_rfid_v2 \
    --train 200 --val 50 --test 50 --horizon 1800 --healthy-frac 0.5 --seed 2025 \
    --class-set v2 --class-ban-frac 0.5
```

## Eksport do CSV (paczka dla zewnętrznych zespołów)

`export_csv.py` zamienia `.npz` na przenośną paczkę CSV (gzip): unikalny szereg
czasowy rekordów 5 s (`timeseries_*`), rzadkie etykiety per rekord×pas×klasa
(`labels_records_*`), mapowanie okien treningowych (`windows_*`), metadane
(`episodes/lanes/classes.csv`) i angielski data-dictionary `README.md`.
`--verify` odbudowuje okna z CSV i porównuje 1:1 z `.npz`.

```bash
uv run python -m grid_rfid.export_csv --dataset datasets/grid_rfid_v2 \
    --out export/grid_rfid_v2_csv --verify
```

Analiza datasetu (figury + statystyki do raportu):

```bash
uv run python scripts/analyze_grid_rfid_dataset.py \
    --dataset datasets/grid_rfid_v2 --out docs/figures/grid_rfid_v2
```

Kluczowe flagi: `--horizon` (s), `--delta` (s/rekord, dom. 5), `--window` (L, dom. 48),
`--stride` (rekordy między oknami, dom. 4), `--healthy-frac` (udział zdrowych epizodów w train).

## Wyjście

Katalog `--out` zawiera:
- `train.npz`, `val.npz`, `test.npz` — `X (N, L, 216)` (216 = 72 pasy × 3 klasy car/bus/delivery),
  `Y (N, 72)` (etykieta per-pas), `episode (N,)` (id epizodu);
- `scenarios/ep*.rou.xml` — wygenerowane trasy per epizod (reprodukowalne);
- `manifest.json` — konfiguracja, seedy, zamknięte krawędzie, pule zamknięć.

**Podział anomalii:** pule krawędzi train vs holdout są **rozłączne**; val/test zamykają wyłącznie
krawędzie z holdout → ewaluacja na **nieoglądanych** lokalizacjach. Train miesza epizody zdrowe
(`--healthy-frac`) i z anomaliami.

## Moduły

- `scenario.py` — introspekcja sieci (72 monitorowane pasy, indeks etykiety; 24 zamykalne krawędzie
  wewnętrzne), generacja tras (model korytarzowy + tło, profil dobowy φ), próbkowanie zamknięć,
  etykieta `label_at(t)`.
- `runner.py` — jeden epizod SUMO/TraCI: wolny port, statyczne światła, odczyt 72 pętli E1 per
  sekundę z klasyfikacją typu, agregacja w oknach Δt, budowa okien przesuwnych + etykiet. Odporny
  na sporadyczne padnięcia SUMO (zachowuje dane częściowe, `truncated`).
- `generate.py` — pętla epizodów, podziały train/val/test, eksport `.npz`, manifest.

## Uwagi / TODO

- Zamknięcia są **krawędziowe** (oba pasy) → pas zamknięty czyta dokładnie 0. Wariant ciągły
  (% przepustowości) wymaga zamknięć **pojedynczego pasa** — proste rozszerzenie `sample_closures`.
- Zadanie jest nietrywialne: pas otwarty też bywa chwilowo 0 (brak pojazdów); odróżnienie wymaga
  okna czasowego + kontekstu przestrzennego.
- Sporadyczne padnięcia SUMO przy szybkim start/stop są obsłużone (retry + dane częściowe).
