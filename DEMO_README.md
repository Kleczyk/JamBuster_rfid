# PPO-Transformer Demo Script

Skrypt demo do ewaluacji wytrenowanego modelu na trzech scenariuszach:
1. **Scenariusz treningowy** - używa `simulation.sumocfg` (scenariusz z treningu)
2. **Scenariusz baseline** - używa `simulation_test.sumocfg` bez szumu RFID
3. **Scenariusz baseline_noise** - używa `simulation_test.sumocfg` z szumem RFID (20%)

## Użycie

### Podstawowe użycie:

```bash
python demo_ppo_transformer.py \
    --config configs/ppo_transformer_baseline.yaml \
    --checkpoint ray_results/PPO_Transformer/PPO_ppo_transformer_env_<trial_id>/checkpoint_000100
```

### Z GUI SUMO (wizualizacja symulacji):

```bash
python demo_ppo_transformer.py \
    --config configs/ppo_transformer_baseline.yaml \
    --checkpoint ray_results/PPO_Transformer/PPO_ppo_transformer_env_<trial_id>/checkpoint_000100 \
    --gui
```

### Z większą liczbą epizodów ewaluacji:

```bash
python demo_ppo_transformer.py \
    --config configs/ppo_transformer_baseline.yaml \
    --checkpoint ray_results/PPO_Transformer/PPO_ppo_transformer_env_<trial_id>/checkpoint_000100 \
    --eval-episodes 10
```

## Parametry

- `--config`: Ścieżka do pliku konfiguracyjnego YAML (domyślnie: `configs/ppo_transformer_baseline.yaml`)
- `--checkpoint`: **WYMAGANE** - Ścieżka do checkpointu wytrenowanego modelu
- `--eval-episodes`: Liczba epizodów ewaluacji dla każdego scenariusza (domyślnie: 5)
- `--gui`: Pokaż GUI SUMO podczas ewaluacji

## Scenariusze

### 1. Scenariusz treningowy
- Plik konfiguracyjny: `nets/ppo_transformer_intersection/simulation.sumocfg`
- Plik tras: `routes.rou.xml`
- Szum RFID: brak (0.0)
- **Cel**: Sprawdzenie działania modelu na danych treningowych

### 2. Scenariusz baseline
- Plik konfiguracyjny: `nets/ppo_transformer_intersection/simulation_test.sumocfg`
- Plik tras: `routes_test.rou.xml`
- Szum RFID: brak (0.0)
- **Cel**: Ewaluacja na danych testowych bez szumu

### 3. Scenariusz baseline_noise
- Plik konfiguracyjny: `nets/ppo_transformer_intersection/simulation_test.sumocfg`
- Plik tras: `routes_test.rou.xml`
- Szum RFID: 20% (0.2)
- **Cel**: Ewaluacja na danych testowych z szumem RFID (symulacja błędów detekcji)

## Przykładowe wyjście

```
================================================================================
DEMO: Loading Trained Model
================================================================================
Checkpoint: ray_results/PPO_Transformer/PPO_ppo_transformer_env_abc123/checkpoint_000100
Model loaded successfully!

================================================================================
DEMO: Training Scenario (simulation.sumocfg)
================================================================================
Episode 1/5:
  Reward: -1234.56
  Length: 120
  Metrics:
    delay: 1234.56
    queue: 5.67
    stops: 12.34
...

Training Scenario (simulation.sumocfg) Summary:
  Average Reward: -1234.56
  Average Length: 120.00
  Average Metrics:
    delay: 1234.56
    queue: 5.67
    stops: 12.34

================================================================================
DEMO: Baseline Scenario (simulation_test.sumocfg, no noise)
================================================================================
...

================================================================================
DEMO: Baseline Noise Scenario (simulation_test.sumocfg, RFID noise=0.2)
================================================================================
...

================================================================================
DEMO SUMMARY
================================================================================
Checkpoint used: ray_results/PPO_Transformer/PPO_ppo_transformer_env_abc123/checkpoint_000100

Results Comparison:
  Scenario                                  Avg Reward      Avg Length    
  ---------------------------------------- --------------- ---------------
  Training (simulation.sumocfg)                  -1234.56          120.00
  Baseline (test, no noise)                       -1345.67          125.00
  Baseline Noise (test, noise=0.2)                -1456.78          130.00
================================================================================
```

## Wymagania

- Wytrenowany model (checkpoint)
- Konfiguracja zgodna z `configs/ppo_transformer_baseline.yaml`
- SUMO zainstalowane i skonfigurowane
- Pliki konfiguracyjne SUMO:
  - `nets/ppo_transformer_intersection/simulation.sumocfg`
  - `nets/ppo_transformer_intersection/simulation_test.sumocfg`

## Znajdowanie checkpointu

Checkpointy są zapisywane w katalogu `ray_results/` podczas treningu. Struktura katalogów:

```
ray_results/
└── PPO_Transformer/
    └── PPO_ppo_transformer_env_<trial_id>/
        ├── checkpoint_000000/
        ├── checkpoint_000010/
        ├── checkpoint_000020/
        └── ...
```

Najlepszy checkpoint można znaleźć sprawdzając metryki w plikach `result.jsonl` w każdym trialu.
