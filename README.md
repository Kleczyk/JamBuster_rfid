# Single Intersection SUMO‑RL with PPO via RLlib

This repository contains a minimal setup for training a reinforcement‑learning
policy to control traffic lights at a single intersection using the
[SUMO‑RL](https://github.com/LucasAlegre/sumo-rl) environment and Ray RLlib.
The configuration is inspired by the official SUMO‑RL examples and has been
adapted to work with the [`uv`](https://github.com/astral-sh/uv) package
manager, PyTorch, Ray Tune and RLlib.

## Prerequisites

1. **Install SUMO.**  SUMO‑RL depends on the SUMO traffic simulator.  On Ubuntu
   systems you can install the latest release via the PPA【600372978409980†L303-L339】:

   ```bash
   sudo add-apt-repository ppa:sumo/stable
   sudo apt-get update
   sudo apt-get install sumo sumo-tools sumo-doc
   ```

   After installation set the `SUMO_HOME` environment variable to point to the
   SUMO installation (by default `/usr/share/sumo`)【600372978409980†L313-L317】:

   ```bash
   echo 'export SUMO_HOME="/usr/share/sumo"' >> ~/.bashrc
   source ~/.bashrc
   ```

   For a performance boost you may set `LIBSUMO_AS_TRACI=1`【600372978409980†L319-L325】,
   but **do not** enable this when running multiple simulations in parallel: the
   libsumo interface is single‑threaded and will prevent RLlib from spinning up
   multiple rollout workers.

2. **Install Python and uv.**  This project uses `uv`, a high‑performance
   package manager written in Rust.  Follow the installation instructions in the
   [uv documentation](https://docs.astral.sh/uv/).

3. **Clone this repository** and create a virtual environment.  With `uv`
   installed you can create a new environment and install all dependencies from
   the included `pyproject.toml`:

   ```bash
   cd sumo_single_intersection_project
   uv venv .venv
   source .venv/bin/activate
   uv pip install -e .
   ```

   The dependencies include `sumo-rl`, `ray[rllib]`, `torch`, `gymnasium`,
   `pettingzoo`, `traci`, `numpy` and `pandas`.  They are declared in
   `pyproject.toml` using uv’s `dependencies` syntax.

## Running the training script

The entry‑point for training is `train.py`.  This script registers a custom
environment with RLlib based on the single‑intersection network shipped with
SUMO‑RL (located under `sumo_rl/nets/2way-single-intersection/`), and sets up a
PPO training loop.  Notable configuration choices include:

* **Parallel rollouts.**  The RLlib `PPOConfig` is set to use multiple rollout
  workers (`num_rollout_workers=4`), meaning four independent SUMO simulations
  will run concurrently【879576100760610†L24-L74】.  You can increase or decrease
  this number based on your CPU resources.  Avoid enabling libsumo when doing this.

* **Training hyperparameters.**  The script follows the PPO configuration used
  in the official SUMO‑RL 4×4 grid example【879576100760610†L24-L74】 but with
  modest batch sizes appropriate for a single intersection:

  - `train_batch_size=512` and `rollout_fragment_length=128` control how many
    experiences are collected before each SGD phase.
  - `lr=2e-5`, `gamma=0.95`, `lambda_=0.9`, `clip_param=0.4` and other
    parameters are taken directly from the example and can be tuned further.

* **Network and route files.**  The environment factory uses Python’s
  `importlib.resources` to locate the default network (`single‑intersection.net.xml`)
  and route file (`single‑intersection-vhvh.rou.xml`) bundled with SUMO‑RL.
  You can swap these for your own SUMO network by adjusting the paths in
  `train.py` or passing them via the `env_config` dictionary.

To start training, simply run:

```bash
python train.py
```

Training progress and checkpoints will be written under
`~/ray_results/single_intersection`.  You can monitor the training by watching
the logs produced by Ray Tune.

## Customising the environment

The `SumoEnvironment` class exposes many parameters to control the simulation,
including the simulation length (`num_seconds`), time between agent actions
(`delta_time`), yellow light duration (`yellow_time`) and minimum green time
(`min_green`).  Refer to the class documentation【490013650830991†L60-L123】 for
the full parameter list.  For example, to change the simulation length you can
override the default in `env_config` when registering the environment.

You can also implement a custom reward function by passing a Python callable to
the `reward_fn` argument【600372978409980†L382-L392】, or design your own
observation by subclassing `ObservationFunction`【600372978409980†L357-L359】.

## Next steps

This setup provides a solid baseline for experimenting with single‑intersection
traffic signal control.  To extend it to multi‑intersection scenarios you can:

* Use the multi‑agent API by instantiating a parallel PettingZoo environment
  via `sumo_rl.parallel_env()` and wrapping it with `ParallelPettingZooEnv` as
  shown in the official PPO example【879576100760610†L24-L74】.
* Increase `num_rollout_workers` to collect experience from more intersections.
* Tune hyperparameters using Ray Tune’s search algorithms.

Feel free to experiment and adapt the network/route files to your own traffic
scenarios.

## PPO-Transformer (RFID, SUMO, RLlib)

This repo includes a reproducible **PPO-Transformer** setup based on the paper
*Adaptive traffic signal control using PPO-Transformer and RFID-based vehicle
detection in the SUMO environment*. The scenario uses RFID-like E1 detectors
and trains a PPO policy with a Transformer encoder and two action heads.

### Scenario

- Network: `nets/ppo_transformer_intersection/`
- RFID detectors: `rfid_detectors.add.xml` (E1 loops on all incoming lanes)
- SUMO config: `simulation.sumocfg`

### Train PPO-Transformer

```bash
uv run python train_ppo_transformer.py \
  --config configs/ppo_transformer.yaml
```

### Baseline train+test (periodic evaluation)

This baseline trains on `simulation.sumocfg` and periodically evaluates on
`simulation_test.sumocfg` (different demand profile). Evaluation metrics are
logged to TensorBoard under the `evaluation/` prefix. A second evaluation pass
with RFID dropout noise (20%) is logged under `evaluation_noisy/`.

```bash
uv run python train_ppo_transformer.py \
  --config configs/ppo_transformer_baseline.yaml
```

### Hyperparameter tuning (Optuna + Ray Tune)

Tune uses the `tune` section in `configs/ppo_transformer.yaml` for search space,
metric, and budget. CLI flags override the YAML values.
Hyperparameters are logged to TensorBoard (hparams tab) when each trial ends.

```bash
uv run python tune_ppo_transformer.py \
  --config configs/ppo_transformer.yaml \
  --num-samples 100 \
  --stop-timesteps 200000 \
  --max-concurrent 4
```

### TensorBoard (real-time metrics)

Custom metrics (`delay`, `queue`, `stops`, `throughput`) are logged to
TensorBoard by `callbacks/metrics_callbacks.py`.

```bash
tensorboard --logdir ray_results
```

## JamBuster — symulacja Rzeszów (GUI)

Sklonuj [JamBuster](https://github.com/Kleczyk/JamBuster) obok tego repozytorium jako `JamBuster/` (ścieżka:
`JamBuster_rfid/JamBuster/...`).

**Z korzenia `JamBuster_rfid`** (nie wchodź drugi raz w `JamBuster/src/map_p05`, bo wtedy `cd JamBuster/...` się wywali):

```bash
# Poprawa ostrzeżeń tlLogic + uruchomienie SUMO GUI
./scripts/run_jam_buster_map_p05.sh

# Samo przycięcie faz (uv run, jak w reszcie projektu):
uv run python scripts/fix_sumo_tl_phases.py JamBuster/src/map_p05/map.net.xml

# Tylko GUI (jeśli sieć już poprawiona):
sumo-gui -c JamBuster/src/map_p05/sim.sumocfg
```

Symulacja **z oknem** wymaga `sumo-gui`, nie `sumo`. Headless: `./scripts/run_jam_buster_map_p05.sh headless 600`

## Realtime Traffic Metrics (TraCI)

To collect **per‑lane** and **per‑junction** metrics in real time (queues, speeds,
waiting times, stops, vehicle mix), use the TraCI collector:

```bash
uv run python tools/collect_intersection_metrics.py \
  --config nets/simple_intersection/simulation.sumocfg \
  --output-dir outputs/metrics \
  --end 60
```

Outputs:

- `outputs/metrics/lane_metrics.csv`
- `outputs/metrics/junction_metrics.csv`

Key fields include `veh_count`, `halt_count`, `queue_length_m`, `mean_speed`,
`avg_waiting_time`, `avg_time_loss`, `stop_events`, and `type_counts_json`.

Useful options:

- `--sample-interval 5` (collect every N steps)
- `--queue-speed-threshold 0.1` (queue detection)
- `--gui` (run with SUMO‑GUI)

## Downloading SUMO Documentation

This repository includes a script to download the complete SUMO documentation
and convert it to well-linked Markdown files. This is useful for offline
reference or for processing the documentation.

To download and process the SUMO documentation:

```bash
# Using uv (recommended)
uv run python download_sumo_docs.py

# Or with custom output directory
uv run python download_sumo_docs.py --output ./my_sumo_docs

# Keep temporary cloned repository (useful for debugging)
uv run python download_sumo_docs.py --keep-temp
```

The script will:
1. Clone the SUMO repository from GitHub (or update if already exists)
2. Extract all Markdown documentation files from `docs/web/docs/`
3. Fix internal links to be relative paths
4. Copy images and other assets
5. Create an `index.md` file with links to all documentation pages
6. Clean up temporary files (unless `--keep-temp` is used)

The processed documentation will be saved in `./sumo_docs_md/` by default (or in
the directory specified with `--output`). You can then browse the documentation
using any Markdown viewer or convert it to other formats as needed.








