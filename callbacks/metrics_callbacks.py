#!/usr/bin/env python3
"""Custom RLlib callbacks for logging traffic metrics to TensorBoard."""

from __future__ import annotations

from typing import Dict

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
