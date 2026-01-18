#!/usr/bin/env python3
"""Custom RLlib callbacks for logging traffic metrics to TensorBoard."""

from __future__ import annotations

from typing import Dict
import inspect

from ray.rllib.algorithms.callbacks import DefaultCallbacks


class MetricsCallbacks(DefaultCallbacks):
    def on_episode_start(self, *, worker, base_env, policies, episode, env_index, **kwargs):
        episode.user_data["delay_sum"] = 0.0
        episode.user_data["queue_sum"] = 0.0
        episode.user_data["stops_sum"] = 0.0
        episode.user_data["throughput_sum"] = 0.0
        episode.user_data["steps"] = 0

    def on_episode_step(self, *, worker, base_env, episode, env_index, **kwargs):
        for agent_id in episode.get_agents():
            info = episode.last_info_for(agent_id) or {}
            episode.user_data["delay_sum"] += float(info.get("delay", 0.0))
            episode.user_data["queue_sum"] += float(info.get("queue", 0.0))
            episode.user_data["stops_sum"] += float(info.get("stops", 0.0))
            episode.user_data["throughput_sum"] += float(info.get("throughput", 0.0))
            episode.user_data["steps"] += 1
            break

    def on_episode_end(self, *, worker, base_env, policies, episode, **kwargs):
        steps = max(1, episode.user_data.get("steps", 1))
        episode.custom_metrics["delay"] = episode.user_data.get("delay_sum", 0.0) / steps
        episode.custom_metrics["queue"] = episode.user_data.get("queue_sum", 0.0) / steps
        episode.custom_metrics["stops"] = episode.user_data.get("stops_sum", 0.0) / steps
        episode.custom_metrics["throughput"] = episode.user_data.get("throughput_sum", 0.0) / steps

    def on_train_result(self, *, algorithm, result, **kwargs):
        # Ensure the metric exists even before the first episode finishes.
        custom = result.setdefault("custom_metrics", {})
        custom.setdefault("delay_mean", float("inf"))

        noisy_cfg = self._get_noisy_eval_cfg(algorithm)
        if not noisy_cfg:
            return

        interval = int(noisy_cfg.get("interval", 0) or 0)
        if interval <= 0:
            return
        iteration = int(result.get("training_iteration", 0))
        if iteration <= 0 or (iteration % interval) != 0:
            return

        eval_config = dict(noisy_cfg.get("evaluation_config", {}))
        eval_args = {}
        for key in ("duration", "duration_unit", "num_env_runners", "num_envs_per_env_runner"):
            if noisy_cfg.get(key) is not None:
                eval_args[key] = noisy_cfg.get(key)
        if eval_config:
            eval_args["evaluation_config"] = eval_config

        if eval_args:
            allowed = set(inspect.signature(algorithm.evaluate).parameters.keys())
            eval_args = {key: value for key, value in eval_args.items() if key in allowed}

        noisy_result = algorithm.evaluate(**eval_args) if eval_args else algorithm.evaluate()
        result["evaluation_noisy"] = noisy_result

    @staticmethod
    def _get_noisy_eval_cfg(algorithm) -> Dict:
        cfg = getattr(algorithm, "config", None)
        if cfg is None:
            return {}
        if hasattr(cfg, "to_dict"):
            cfg = cfg.to_dict()
        if isinstance(cfg, dict):
            return dict(cfg.get("noisy_eval", {}) or {})
        return {}
