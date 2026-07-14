# Prosta symulacja skrzyżowania z 4 wlotami

Ta symulacja przedstawia pojedyncze skrzyżowanie z sygnalizacją świetlną, z wysokim natężeniem ruchu zawierającym samochody osobowe, busy i karetki.

## Struktura plików

- **network.net.xml** - Sieć drogowa z pojedynczym skrzyżowaniem z 4 wlotami (2 pasy w każdym kierunku)
- **routes.rou.xml** - Definicje pojazdów i przepływy ruchu
- **simulation.sumocfg** - Główny plik konfiguracyjny symulacji

## Charakterystyka symulacji

### Topologia sieci
- Pojedyncze skrzyżowanie z 4 wlotami: północ, południe, wschód, zachód
- Każdy wlot: 2 pasy ruchu w każdym kierunku
- Długość dróg przed/za skrzyżowaniem: 200m
- Prędkość maksymalna: 50 km/h (~13.89 m/s)

### Sygnalizacja świetlna
Program światła z 4 fazami:
1. **Faza 1 (30s)**: Zielone dla kierunku północ-południe
2. **Faza 2 (3s)**: Żółte światła
3. **Faza 3 (30s)**: Zielone dla kierunku wschód-zachód
4. **Faza 4 (3s)**: Żółte światła

Całkowity czas cyklu: 66 sekund

### Typy pojazdów

#### 1. Samochody osobowe (80% ruchu)
- Klasa: `passenger`
- Prędkość max: 50 m/s
- Przyspieszenie: 2.6 m/s²
- Hamowanie: 4.5 m/s²
- Długość: 5m
- Kolor: żółty

#### 2. Busy (15% ruchu)
- Klasa: `bus`
- Prędkość max: 30 m/s
- Przyspieszenie: 1.2 m/s²
- Hamowanie: 4.0 m/s²
- Długość: 12m
- Kolor: niebieski
- Pojemność: 85 osób

#### 3. Karetki (5% ruchu)
- Klasa: `emergency`
- Prędkość max: 50 m/s (z możliwością przekroczenia: speedFactor=1.5)
- Przyspieszenie: 2.9 m/s²
- Hamowanie: 4.5 m/s²
- Długość: 6m
- Kolor: czerwony

### Natężenie ruchu
- **Wysokie natężenie**: ~1200 pojazdów na godzinę
- **Rozkład**: równomierny z 4 kierunków (po ~300 pojazd./h z każdego)
- **Czas symulacji**: 3600 sekund (1 godzina)

## Jak uruchomić symulację

### 1. Z interfejsem graficznym (sumo-gui)

```bash
cd nets/simple_intersection
sumo-gui -c simulation.sumocfg
```

Po uruchomieniu:
- Kliknij przycisk ▶️ (Play), aby rozpocząć symulację
- Użyj Ctrl+A, aby dostosować prędkość symulacji
- Kliknij na pojazdy, aby zobaczyć ich parametry

### 2. Bez interfejsu graficznego (sumo)

```bash
cd nets/simple_intersection
sumo -c simulation.sumocfg
```

Szybsza opcja do analizy danych - bez wizualizacji.

### 3. Z użyciem TraCI (Python)

Przykład uruchomienia z TraCI dla kontroli programowej:

```python
import traci
import os

# Ścieżka do konfiguracji
sumo_cfg = "nets/simple_intersection/simulation.sumocfg"

# Uruchom SUMO
traci.start(["sumo", "-c", sumo_cfg])

# Główna pętla symulacji
step = 0
while step < 3600:
    traci.simulationStep()
    
    # Tutaj możesz dodać własną logikę sterowania
    # np. zmiana programu świateł, priorytet dla karetek, itp.
    
    step += 1

traci.close()
```

### 4. Integracja z istniejącym skryptem train.py

Możesz użyć tej sieci do treningu agenta RL:

```bash
python train.py \
    --net-file nets/simple_intersection/network.net.xml \
    --route-file nets/simple_intersection/routes.rou.xml \
    --num-seconds 3600
```

## Pliki wyjściowe

Po zakończeniu symulacji wygenerowane zostaną następujące pliki:

- **tripinfo.xml** - Szczegółowe informacje o każdej podróży (czas, prędkość, opóźnienia)
- **summary.xml** - Statystyki zbiorcze dla każdego kroku czasowego
- **simulation.log** - Log przebiegu symulacji

### Analiza wyników

Przykład analizy czasu podróży:

```bash
# Średni czas podróży
python $SUMO_HOME/tools/xml/xml2csv.py tripinfo.xml
```

## Modyfikacje

### Zmiana natężenia ruchu

Edytuj wartości `probability` w pliku `routes.rou.xml`:

```xml
<!-- Obecna wartość dla samochodów: 0.267 -->
<flow id="flow_north_cars" type="car" probability="0.267" .../>

<!-- Zwiększ wartość dla większego natężenia:-->
<flow id="flow_north_cars" type="car" probability="0.4" .../>
```

### Zmiana programu świateł

Edytuj sekcję `<tlLogic>` w pliku `network.net.xml`:

```xml
<tlLogic id="center" type="static" programID="0" offset="0">
    <!-- Zmień duration dla różnych czasów faz -->
    <phase duration="30" state="GGGgrrrGGGgrrr"/>
    ...
</tlLogic>
```

### Dodanie nowych typów pojazdów

Dodaj nową definicję `<vType>` w pliku `routes.rou.xml`:

```xml
<vType id="truck" vClass="truck" accel="1.0" decel="4.0" 
      length="15.0" maxSpeed="25.0" color="0.5,0.5,0.5"/>
```

## Rozwiązywanie problemów

### Pojazdy się teleportują
Jeśli pojazdy znikają i pojawiają się w innym miejscu:
- Zwiększ `time-to-teleport` w `simulation.sumocfg`
- Zmniejsz natężenie ruchu (zmniejsz `probability` w flows)

### Zbyt duże korki
- Zwiększ czas zielonego światła w programie sygnalizacji
- Zmniejsz natężenie ruchu
- Włącz adaptacyjną sygnalizację (wymaga TraCI)

### Karetki nie mają priorytetu
Priorytet dla pojazdów ratunkowych wymaga dodatkowej logiki w TraCI:

```python
# Przykład: zmień światła na zielone, gdy zbliża się karetka
ambulance_ids = traci.vehicle.getIDList()
for veh_id in ambulance_ids:
    if "ambulance" in veh_id:
        # Logika zmiany świateł
        pass
```

## Walidacja

Sprawdź poprawność plików:

```bash
# Walidacja sieci
netconvert --sumo-net-file network.net.xml -o test_net.net.xml

# Test symulacji (pierwsze 10 sekund)
sumo -c simulation.sumocfg --begin 0 --end 10 --verbose
```

## Dalsze kroki

1. **Optymalizacja świateł**: Użyj TraCI lub SUMO-RL do trenowania adaptacyjnej sygnalizacji
2. **Analiza wydajności**: Porównaj różne programy świateł
3. **Rozszerzenie sieci**: Dodaj więcej skrzyżowań dla większego scenariusza
4. **Symulacja wydarzeń**: Dodaj wypadki, zamknięcia dróg, itp.

## Linki

- [Dokumentacja SUMO](../../sumo_docs/GUIDE.md)
- [SUMO TraCI](../../sumo_docs/TraCI.md)
- [Skrypt treningowy](../../train.py)








