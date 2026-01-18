#!/usr/bin/env python3
"""Train PPO-Transformer on the RFID-based SUMO intersection scenario."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import ray
import yaml
from ray import tune
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.models import ModelCatalog
from ray.tune.registry import register_env

from envs.ppo_transformer_env import PPOTransformerEnv
from models.ppo_transformer_model import PPOTransformerModel
from callbacks.metrics_callbacks import MetricsCallbacks


def load_config(path: Path) -> dict:
    with path.open("r") as f:
        return yaml.safe_load(f)


def build_config(cfg: dict) -> PPOConfig:
    env_name = cfg.get("env_name", "ppo_transformer_env")

    env_config = cfg.get("env_config", {})
    sumo_cfg = env_config.get("sumo_cfg")
    if sumo_cfg:
        sumo_path = Path(sumo_cfg)
        if not sumo_path.is_absolute():
            sumo_path = (Path(__file__).resolve().parent / sumo_path).resolve()
        env_config["sumo_cfg"] = str(sumo_path)

    register_env(env_name, lambda env_cfg: PPOTransformerEnv(env_cfg))
    ModelCatalog.register_custom_model("ppo_transformer_model", PPOTransformerModel)

    config = (
        PPOConfig()
        .api_stack(
            enable_rl_module_and_learner=False,
            enable_env_runner_and_connector_v2=False,
        )
        .environment(
            env=env_name,
            disable_env_checking=True,
            env_config=env_config,
        )
        .env_runners(
            num_env_runners=cfg["rollout"].get("num_env_runners", 1),
            num_envs_per_env_runner=cfg["rollout"].get("num_envs_per_env_runner", 1),
            rollout_fragment_length=cfg["rollout"].get("rollout_fragment_length", 200),
            batch_mode=cfg["rollout"].get("batch_mode", "truncate_episodes"),
        )
        .training(
            train_batch_size=cfg["training"].get("train_batch_size", 4000),
            num_epochs=cfg["training"].get("num_epochs", 10),
            minibatch_size=cfg["training"].get("minibatch_size", 256),
            lr=cfg["training"].get("lr", 3e-4),
            gamma=cfg["training"].get("gamma", 0.99),
            lambda_=cfg["training"].get("lambda_", 0.95),
            clip_param=cfg["training"].get("clip_param", 0.2),
            entropy_coeff=cfg["training"].get("entropy_coeff", 0.0),
            vf_loss_coeff=cfg["training"].get("vf_loss_coeff", 1.0),
            use_gae=True,
        )
        .framework(framework="torch")
        .resources(num_gpus=cfg.get("resources", {}).get("num_gpus", 0))
        .debugging(log_level=cfg.get("logging", {}).get("log_level", "INFO"))
        .callbacks(callbacks_class=MetricsCallbacks)
    )

    config.model = {
        **config.model,
        "custom_model": cfg["model"].get("custom_model", "ppo_transformer_model"),
        "custom_model_config": cfg["model"].get("custom_model_config", {}),
    }

    return config


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
    parser.add_argument("--stop-timesteps", type=int, default=None, help="Override stop timesteps")
    parser.add_argument("--name", default="PPO_Transformer", help="Run name")
    parser.add_argument("--storage", default="ray_results", help="Results directory")

    args = parser.parse_args()

    cfg = load_config(Path(args.config))
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

    ppo_cfg = build_config(cfg)
    stop = {"timesteps_total": cfg.get("stopping", {}).get("timesteps_total", 200000)}
    if args.stop_timesteps is not None:
        stop["timesteps_total"] = args.stop_timesteps

    storage_path = str(Path(args.storage).resolve().as_uri())
    tune.run(
        "PPO",
        name=args.name,
        stop=stop,
        config=ppo_cfg.to_dict(),
        storage_path=storage_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
