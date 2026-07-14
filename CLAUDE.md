# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Reinforcement-learning traffic-signal control for a single SUMO intersection. The active research project is **PPO-Transformer**: a PPO policy with a Transformer encoder that observes a sliding window of RFID-style vehicle counts and controls a 4-phase traffic light. There is also a legacy `train.py` baseline built directly on `sumo-rl`'s `SumoEnvironment` — it is unrelated to the PPO-Transformer code and shares no modules with it.

## Environment & commands

- Python is pinned to `>=3.11,<3.12` (`.python-version` = 3.11.14). Dependency/venv management is via **`uv`**; run everything through `uv run python ...`.
- **`SUMO_HOME` must be set** (e.g. `/usr/share/sumo`). The env appends `$SUMO_HOME/tools` to `sys.path` to import `traci`.
- **Do not set `LIBSUMO_AS_TRACI=1`** when using more than one env runner — libsumo is single-threaded and breaks parallel rollouts. The env spawns SUMO subprocesses via `traci.start` on a free port with a unique label per worker, so multiple parallel SUMO processes is the intended mode.

```bash
# Setup
make setup                       # uv venv .venv + uv pip install -e .
make install                     # reinstall/update deps

# PPO-Transformer training (the real project)
uv run python train_ppo_transformer.py --config configs/ppo_transformer.yaml
uv run python train_ppo_transformer.py --config configs/ppo_transformer_baseline.yaml   # train + periodic test eval

# Hyperparameter tuning (Optuna + Ray Tune; reads the `tune:` section of the config)
uv run python tune_ppo_transformer.py --config configs/ppo_transformer.yaml \
  --num-samples 100 --stop-timesteps 200000 --max-concurrent 4

# Evaluate a checkpoint on train / test / test+noise scenarios
uv run python demo_ppo_transformer.py --config configs/ppo_transformer_baseline.yaml \
  --checkpoint ray_results/PPO_Transformer/PPO_ppo_transformer_env_<trial>/checkpoint_000100 [--gui]

# Metrics
tensorboard --logdir ray_results
uv run python tools/collect_intersection_metrics.py --config nets/simple_intersection/simulation.sumocfg --output-dir outputs/metrics --end 60

# Legacy sumo-rl baseline (separate from PPO-Transformer)
make train        # or: python train.py --num-seconds 100000 --num-env-runners 4 ...
```

There is **no test suite for the RL code** (the only `test_*.py` files live under `scripts/article/` and concern an unrelated article/kie.ai pipeline). `pytest` is declared as a dev extra but no RL tests exist.

## Architecture (PPO-Transformer pipeline)

Four modules wired together by `train_ppo_transformer.py:build_config`, all driven from a single YAML config:

1. **`envs/ppo_transformer_env.py` — `PPOTransformerEnv(gym.Env)`** (single-agent, NOT a `sumo-rl` env). On `reset` it launches SUMO via TraCI and **installs its own 4-phase `tlLogic`** (`ns`, `ns_yellow`, `ew`, `ew_yellow`) by inspecting the network's controlled links. Each `step` advances `delta_time` sim seconds, handling yellow transitions and min/max green clamping internally.
   - **Observation**: `(obs_window, 15)` float32, a sliding window (`obs_window`, default 48) of per-step feature vectors. The 15 features = RFID counts for car/bus/delivery on each of N/S/E/W (`4×3 = 12`) + current-phase one-hot (2) + normalized green-elapsed time (1). Counts come from E1 induction-loop detectors parsed out of the `additional-files` XML by `rfid_*` id prefix.
   - **Action**: `MultiDiscrete([2, 3])` = (phase: NS/EW, green-duration delta: −5/0/+5 s).
   - **Reward**: `-(alpha·delay + beta·avg_queue + gamma·stops)`, weights from config (`reward_alpha/beta/gamma`).
   - Network/detector/end-time are auto-derived by parsing the `.sumocfg` and `.net.xml` (`_parse_sumocfg`, `_parse_incoming_lanes`, `_parse_detectors`); `tls_id` defaults to `center`.
   - `rfid_noise_rate` simulates detection dropout via binomial thinning of counts — used for the noisy-eval scenario. `soft_reset` reuses a running SUMO process across episodes when not yet done.

2. **`models/ppo_transformer_model.py` — `PPOTransformerModel(TorchModelV2)`**: input projection → learned positional embedding → `nn.TransformerEncoder` → takes the **last timestep** → two action heads (phase=2, duration=3) concatenated into a 5-dim logits vector for the MultiDiscrete action, plus a value head.

3. **`callbacks/metrics_callbacks.py` — `MetricsCallbacks(DefaultCallbacks)`**: the most intricate file. It accumulates per-step env `info` (delay/queue/stops/throughput) into episode and training-iteration means, then in `on_train_result` reconciles them across env runners through several fallback paths (because RLlib's worker/env-runner accessors differ across versions). It mirrors metrics into `env_runners.custom_metrics` and aliases them under TensorBoard prefixes (`train_tune/`, `baseline_eval/`, `baseline_noisy_eval/`). It also **manually triggers a second "noisy" evaluation pass** by setting `rfid_noise_rate` on the eval env runners and calling `algorithm.evaluate()` — config lives under the YAML `noisy_eval:` key, which `train_ppo_transformer.py` injects into the config dict.

4. **`train_ppo_transformer.py` / `tune_ppo_transformer.py`**: build the `PPOConfig`, register the env + custom model, and run `tune.run("PPO", ...)` / `tune.Tuner`. `tune_ppo_transformer.py` reuses `build_config` then deep-merges `tune.config_overrides` and the flattened `tune.search_space` into the param space; `lambda_` is renamed to `lambda` for the RLlib config key.

### Critical: this uses RLlib's OLD API stack

`build_config` sets `.api_stack(enable_rl_module_and_learner=False, enable_env_runner_and_connector_v2=False)`. That is why the code uses `TorchModelV2` + `ModelCatalog.register_custom_model` and `DefaultCallbacks` with `on_episode_*`/`on_train_result` hooks rather than the new RLModule/Learner/ConnectorV2 APIs. **Do not migrate models or callbacks to the new API stack** unless you also flip this flag and rewrite all four modules together.

## Config conventions

- **`configs/ppo_transformer.yaml`** is provisioned for a large cluster (`num_cpus: 220`, `num_gpus: 4`, `num_env_runners: 110`). For local runs use **`configs/ppo_transformer_baseline.yaml`** (1 env runner, GUI on, small batch) — it is the one wired for the train+test+noisy-eval flow and matches `demo_ppo_transformer.py`'s defaults.
- CLI flags override YAML in the entry-point scripts.
- Scenario files live in `nets/ppo_transformer_intersection/`: `simulation.sumocfg` (train demand) vs `simulation_test.sumocfg` (held-out test demand, `routes_test.rou.xml`). Detectors: `rfid_detectors.add.xml`.
- Results/checkpoints go to `ray_results/` (gitignored). `object_store_memory_gb` is auto-capped to fit `/dev/shm`.

## Gotchas

- Every PPO-Transformer module is littered with `_dbg_log(...)` calls inside `# region agent log` blocks that append JSON to a **hardcoded absolute path** `/home/dk/repos/JamBuster_rfid/.cursor/debug.log`. This is debug instrumentation, not load-bearing logic; failures are swallowed. The path will not exist on other machines (writes silently no-op).
- `train.py` (legacy) and `train_ppo_transformer.py` are entirely separate stacks — don't conflate their hyperparameters or env config.

## JamBuster (Rzeszów GUI sub-project)

`JamBuster/` is a separate cloned repo (https://github.com/Kleczyk/JamBuster), placed alongside this code. Helper scripts in `scripts/` operate on it from the repo root:

```bash
./scripts/run_jam_buster_map_p05.sh            # fix tlLogic phases + launch sumo-gui
./scripts/run_jam_buster_map_p05.sh headless 600
uv run python scripts/fix_sumo_tl_phases.py JamBuster/src/map_p05/map.net.xml   # trim unused tlLogic states
```

Run these from the `JamBuster_rfid` root, not from inside `JamBuster/src/map_p05`.
