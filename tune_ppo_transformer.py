#!/usr/bin/env python3
"""Hyperparameter tuning for PPO-Transformer using Ray Tune + Optuna."""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

import ray
import yaml
from ray import tune
from ray.tune.callback import Callback
from ray.tune.logger import TBXLoggerCallback
from ray.tune.progress_reporter import CLIReporter
from ray.tune.search.optuna import OptunaSearch
from ray.tune.schedulers import ASHAScheduler, FIFOScheduler

from train_ppo_transformer import build_config, load_config

_DEBUG_LOG_PATH = "/home/dk/repos/JamBuster_rfid/.cursor/debug.log"


def _dbg_log(hypothesis_id: str, location: str, message: str, data: dict, run_id: str = "pre-fix") -> None:
    payload = {
        "sessionId": "debug-session",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except Exception:
        pass


class DebugTuneCallback(Callback):
    def on_trial_result(self, iteration, trials, trial, result: dict, **info) -> None:
        custom_metrics = result.get("custom_metrics") if isinstance(result, dict) else None
        custom_keys = sorted(custom_metrics.keys()) if isinstance(custom_metrics, dict) else None
        # region agent log
        _dbg_log(
            "H15",
            "tune_ppo_transformer.py:DebugTuneCallback",
            "trial_result",
            {
                "trial_id": getattr(trial, "trial_id", None),
                "trial_logdir": getattr(trial, "logdir", None),
                "trial_local_path": getattr(trial, "local_path", None),
                "trial_storage": str(getattr(trial, "storage", None)),
                "training_iteration": result.get("training_iteration") if isinstance(result, dict) else None,
                "timesteps_total": result.get("timesteps_total") if isinstance(result, dict) else None,
                "episodes_this_iter": result.get("episodes_this_iter") if isinstance(result, dict) else None,
                "logdir": result.get("logdir") if isinstance(result, dict) else None,
                "custom_metric_keys": custom_keys,
            },
        )
        # endregion

    def on_trial_error(self, iteration, trials, trial, **info) -> None:
        # region agent log
        _dbg_log(
            "H15",
            "tune_ppo_transformer.py:DebugTuneCallback",
            "trial_error",
            {
                "trial_id": getattr(trial, "trial_id", None),
                "logdir": getattr(trial, "logdir", None),
                "error_file": getattr(trial, "error_file", None),
            },
        )
        # endregion

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


def _apply_ray_env(cfg: dict) -> None:
    ray_cfg = cfg.get("ray", {})
    threshold = ray_cfg.get("memory_usage_threshold")
    if threshold is not None:
        os.environ["RAY_memory_usage_threshold"] = str(threshold)
    refresh_ms = ray_cfg.get("memory_monitor_refresh_ms")
    if refresh_ms is not None:
        os.environ["RAY_memory_monitor_refresh_ms"] = str(int(refresh_ms))


def _get_shm_size_bytes() -> int | None:
    try:
        stats = os.statvfs("/dev/shm")
    except FileNotFoundError:
        return None
    return int(stats.f_frsize * stats.f_blocks)


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
    os.environ.setdefault("RAY_AIR_NEW_OUTPUT", "0")
    # region agent log
    removed_tune_result_dir = os.environ.pop("TUNE_RESULT_DIR", None)
    _dbg_log(
        "H14",
        "tune_ppo_transformer.py:main",
        "tune_result_dir_cleared",
        {"removed": removed_tune_result_dir is not None, "value": removed_tune_result_dir},
    )
    # endregion
    _apply_ray_env(cfg)
    resources_cfg = cfg.get("resources", {})
    object_store_gb = resources_cfg.get("object_store_memory_gb")
    object_store_bytes = None
    if object_store_gb is not None:
        object_store_bytes = int(float(object_store_gb) * 1024**3)
    shm_size = _get_shm_size_bytes()
    if object_store_bytes is not None and shm_size is not None and object_store_bytes > shm_size:
        capped = int(shm_size * 0.8)
        print(
            f"[ray] object_store_memory capped to {capped / 1024**3:.2f} GB "
            f"to fit /dev/shm size {shm_size / 1024**3:.2f} GB."
        )
        object_store_bytes = capped
    ray.init(
        num_cpus=resources_cfg.get("num_cpus"),
        num_gpus=resources_cfg.get("num_gpus"),
        object_store_memory=object_store_bytes,
    )

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
    noisy_cfg = cfg.get("noisy_eval")
    if noisy_cfg:
        base_cfg["noisy_eval"] = dict(noisy_cfg)

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

    env_cfg = base_cfg.get("env_config", {}) if isinstance(base_cfg.get("env_config"), dict) else {}
    # region agent log
    _dbg_log(
        "H2",
        "tune_ppo_transformer.py:main",
        "tune_final_config",
        {
            "config_path": str(Path(args.config).resolve()),
            "train_batch_size": base_cfg.get("train_batch_size"),
            "num_epochs": base_cfg.get("num_epochs"),
            "minibatch_size": base_cfg.get("minibatch_size"),
            "num_env_runners": base_cfg.get("num_env_runners"),
            "num_envs_per_env_runner": base_cfg.get("num_envs_per_env_runner"),
            "rollout_fragment_length": base_cfg.get("rollout_fragment_length"),
            "batch_mode": base_cfg.get("batch_mode"),
            "evaluation_interval": base_cfg.get("evaluation_interval"),
            "evaluation_duration": base_cfg.get("evaluation_duration"),
            "noisy_eval_enabled": bool(base_cfg.get("noisy_eval")),
            "episode_horizon_steps": env_cfg.get("episode_horizon_steps"),
            "soft_reset": env_cfg.get("soft_reset"),
            "sumo_cfg": env_cfg.get("sumo_cfg"),
        },
    )
    # endregion

    grace_period = int(tune_cfg.get("grace_period", 2))
    scheduler_name = str(tune_cfg.get("scheduler", "asha")).lower()
    if scheduler_name in ("asha", "asynchyperband", "async_hyperband"):
        scheduler = ASHAScheduler(metric=metric, mode=mode, grace_period=grace_period, time_attr="training_iteration")
    elif scheduler_name in ("fifo", "none", "basic"):
        scheduler = FIFOScheduler()
    else:
        raise ValueError(f"Unsupported scheduler: {scheduler_name}")
    search_alg = OptunaSearch(metric=metric, mode=mode)
    callbacks = []
    if bool(tune_cfg.get("tensorboard_hparams", True)):
        callbacks.append(TBXLoggerCallback())
    callbacks.append(DebugTuneCallback())

    metric_columns = ["training_iteration", "timesteps_total", "episodes_total", "custom_metrics/delay_mean"]
    progress_reporter = CLIReporter(metric_columns=metric_columns)
    # region agent log
    _dbg_log(
        "H16",
        "tune_ppo_transformer.py:main",
        "progress_reporter_config",
        {
            "reporter_type": type(progress_reporter).__name__,
            "metric_columns": metric_columns,
        },
    )
    # endregion

    storage_path = str(Path(storage).resolve().as_uri())
    # region agent log
    _dbg_log(
        "H13",
        "tune_ppo_transformer.py:main",
        "tuner_run_config",
        {
            "cwd": os.getcwd(),
            "name": name,
            "storage": storage,
            "storage_path": storage_path,
            "scheduler": type(scheduler).__name__,
            "search_alg": type(search_alg).__name__,
            "callbacks": [type(cb).__name__ for cb in callbacks],
            "ray_air_new_output": os.environ.get("RAY_AIR_NEW_OUTPUT"),
            "ray_dedup_logs": os.environ.get("RAY_DEDUP_LOGS"),
            "tune_disable_auto_callback_loggers": os.environ.get("TUNE_DISABLE_AUTO_CALLBACK_LOGGERS"),
            "tune_result_dir": os.environ.get("TUNE_RESULT_DIR"),
            "ray_air_progress_reporter": os.environ.get("RAY_AIR_PROGRESS_REPORTER"),
        },
    )
    # endregion
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
            progress_reporter=progress_reporter,
            verbose=1,
        ),
    )

    # region agent log
    _dbg_log(
        "H15",
        "tune_ppo_transformer.py:main",
        "tuner_fit_start",
        {"name": name, "num_samples": num_samples, "max_concurrent": max_concurrent, "stop_timesteps": stop_timesteps},
    )
    # endregion
    try:
        result = tuner.fit()
    except Exception:
        # region agent log
        _dbg_log(
            "H15",
            "tune_ppo_transformer.py:main",
            "tuner_fit_error",
            {"error": traceback.format_exc(limit=5)},
        )
        # endregion
        raise
    # region agent log
    _dbg_log(
        "H15",
        "tune_ppo_transformer.py:main",
        "tuner_fit_done",
        {
            "result_type": type(result).__name__,
            "num_errors": getattr(result, "num_errors", None),
            "num_terminated": getattr(result, "num_terminated", None),
            "num_running": getattr(result, "num_running", None),
        },
    )
    # endregion
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
