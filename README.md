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