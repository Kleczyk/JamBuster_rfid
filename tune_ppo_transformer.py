#!/usr/bin/env python3
"""Hyperparameter tuning for PPO-Transformer using Ray Tune + Optuna."""

from __future__ import annotations

import argparse
from pathlib import Path

import ray
import yaml
from ray import tune
from ray.tune.logger import TBXLoggerCallback
from ray.tune.search.optuna import OptunaSearch
from ray.tune.schedulers import ASHAScheduler

from train_ppo_transformer import build_config, load_config


def _build_tune_param(spec: dict):
    param_type = spec.get("type")
    if param_type == "choice":
        return tune.choice(spec["values"])
    if param_type == "uniform":
        return tune.uniform(spec["low"], spec["high"])
    if param_type == "loguniform":
        return tune.loguniform(spec["low"], spec["high"])
    if param_type == "randint":
        return tune.randint(spec["low"], spec["high"])
    if param_type == "quniform":
        return tune.quniform(spec["low"], spec["high"], spec["q"])
    raise ValueError(f"Unsupported tune param type: {param_type}")


def _build_search_space(spec: dict) -> dict:
    space = {}
    for key, value in spec.items():
        if isinstance(value, dict) and "type" in value:
            space[key] = _build_tune_param(value)
        elif isinstance(value, dict):
            space[key] = _build_search_space(value)
        else:
            space[key] = value
    return space


def _deep_update(target: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/ppo_transformer.yaml", help="Config YAML")
    parser.add_argument("--num-samples", type=int, default=None, help="Number of trials")
    parser.add_argument("--max-concurrent", type=int, default=None, help="Max concurrent trials")
    parser.add_argument("--stop-timesteps", type=int, default=None, help="Stop timesteps per trial")
    parser.add_argument("--metric", default=None, help="Metric to optimize")
    parser.add_argument("--mode", default=None, help="Optimization mode (min/max)")
    parser.add_argument("--name", default=None, help="Experiment name")
    parser.add_argument("--storage", default=None, help="Results directory")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    tune_cfg = cfg.get("tune", {})
    ray.init()

    num_samples = args.num_samples or int(tune_cfg.get("num_samples", 100))
    max_concurrent = args.max_concurrent or int(tune_cfg.get("max_concurrent_trials", 4))
    stop_timesteps = args.stop_timesteps or int(tune_cfg.get("stop_timesteps", 200000))
    metric = args.metric or tune_cfg.get("metric", "episode_reward_mean")
    mode = args.mode or tune_cfg.get("mode", "max")
    name = args.name or tune_cfg.get("name", "PPO_Transformer_Tune")
    storage = args.storage or tune_cfg.get("storage", "ray_results")

    base_cfg = build_config(cfg).to_dict()
    overrides = dict(tune_cfg.get("config_overrides", {}))
    overrides.setdefault("rollout_fragment_length", "auto")
    _deep_update(base_cfg, overrides)

    search_spec = tune_cfg.get("search_space", {})
    search_space: dict = {}
    if "training" in search_spec:
        for key, value in search_spec["training"].items():
            config_key = "lambda" if key == "lambda_" else key
            if isinstance(value, dict) and "type" in value:
                search_space[config_key] = _build_tune_param(value)
            else:
                search_space[config_key] = value
    if "model" in search_spec:
        search_space["model"] = _build_search_space(search_spec["model"])
    for key, value in search_spec.items():
        if key in ("training", "model"):
            continue
        search_space[key] = _build_search_space(value) if isinstance(value, dict) else value

    _deep_update(base_cfg, search_space)

    scheduler = ASHAScheduler(metric=metric, mode=mode)
    search_alg = OptunaSearch(metric=metric, mode=mode)
    callbacks = []
    if bool(tune_cfg.get("tensorboard_hparams", True)):
        callbacks.append(TBXLoggerCallback())

    storage_path = str(Path(storage).resolve().as_uri())
    tuner = tune.Tuner(
        "PPO",
        param_space=base_cfg,
        tune_config=tune.TuneConfig(
            num_samples=num_samples,
            max_concurrent_trials=max_concurrent,
            scheduler=scheduler,
            search_alg=search_alg,
        ),
        run_config=tune.RunConfig(
            name=name,
            storage_path=storage_path,
            stop={"timesteps_total": stop_timesteps},
            callbacks=callbacks or None,
        ),
    )

    tuner.fit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
