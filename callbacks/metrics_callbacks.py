#!/usr/bin/env python3
"""Custom RLlib callbacks for logging traffic metrics to TensorBoard."""

from __future__ import annotations

from typing import Dict
from pathlib import Path
import inspect
import math
import json
import time

from ray.rllib.algorithms.callbacks import DefaultCallbacks

_DEBUG_LOG_PATH = "/home/dk/repos/JamBuster_rfid/.cursor/debug.log"


def _dbg_log(hypothesis_id: str, location: str, message: str, data: Dict, run_id: str = "pre-fix") -> None:
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


class MetricsCallbacks(DefaultCallbacks):
    def __init__(self):
        super().__init__()
        self._debug_episode_end_count = 0
        self._debug_episode_step_count = 0
        self._debug_no_agent_count = 0
        self._train_metric_sums = {
            "delay": 0.0,
            "queue": 0.0,
            "stops": 0.0,
            "throughput": 0.0,
            "throughput_tls": 0.0,
            "throughput_network": 0.0,
        }
        self._train_metric_counts = 0
        self._train_step_sums = {
            "delay": 0.0,
            "queue": 0.0,
            "stops": 0.0,
            "throughput": 0.0,
            "throughput_tls": 0.0,
            "throughput_network": 0.0,
        }
        self._train_step_counts = 0
        self._last_train_step_iter = None
        self._last_train_step_metrics = None
        # region agent log
        _dbg_log(
            "H10",
            "callbacks/metrics_callbacks.py:__init__",
            "callbacks_init",
            {"module_file": __file__, "class_name": type(self).__name__},
        )
        # endregion

    def _ensure_train_accumulators(self):
        if not hasattr(self, "_train_metric_sums") or not hasattr(self, "_train_metric_counts"):
            # region agent log
            _dbg_log(
                "H2",
                "callbacks/metrics_callbacks.py:_ensure_train_accumulators",
                "train_accumulators_initialized",
                {},
            )
            # endregion
            self._train_metric_sums = {
                "delay": 0.0,
                "queue": 0.0,
                "stops": 0.0,
                "throughput": 0.0,
                "throughput_tls": 0.0,
                "throughput_network": 0.0,
            }
            self._train_metric_counts = 0
        if not hasattr(self, "_train_step_sums") or not hasattr(self, "_train_step_counts"):
            self._train_step_sums = {
                "delay": 0.0,
                "queue": 0.0,
                "stops": 0.0,
                "throughput": 0.0,
                "throughput_tls": 0.0,
                "throughput_network": 0.0,
            }
            self._train_step_counts = 0
        if not hasattr(self, "_last_train_step_iter"):
            self._last_train_step_iter = None
            self._last_train_step_metrics = None

    def _drain_train_metrics(self):
        self._ensure_train_accumulators()
        sums = dict(self._train_metric_sums)
        count = int(self._train_metric_counts)
        self._train_metric_sums = {
            "delay": 0.0,
            "queue": 0.0,
            "stops": 0.0,
            "throughput": 0.0,
            "throughput_tls": 0.0,
            "throughput_network": 0.0,
        }
        self._train_metric_counts = 0
        return sums, count

    def _drain_train_step_metrics(self, training_iteration: int | None):
        self._ensure_train_accumulators()
        if (
            training_iteration is not None
            and self._last_train_step_iter == training_iteration
            and self._last_train_step_metrics is not None
        ):
            return self._last_train_step_metrics
        sums = dict(self._train_step_sums)
        count = int(self._train_step_counts)
        self._train_step_sums = {
            "delay": 0.0,
            "queue": 0.0,
            "stops": 0.0,
            "throughput": 0.0,
            "throughput_tls": 0.0,
            "throughput_network": 0.0,
        }
        self._train_step_counts = 0
        self._last_train_step_iter = training_iteration
        self._last_train_step_metrics = (sums, count)
        return sums, count

    def _collect_train_metrics_from_workers(self, algorithm):
        totals = {
            "delay": 0.0,
            "queue": 0.0,
            "stops": 0.0,
            "throughput": 0.0,
            "throughput_tls": 0.0,
            "throughput_network": 0.0,
        }
        total_count = 0
        used_group = None
        results = None

        # region agent log
        _dbg_log(
            "H4",
            "callbacks/metrics_callbacks.py:_collect_train_metrics_from_workers",
            "collect_enter",
            {
                "algorithm_type": type(algorithm).__name__,
                "has_workers": getattr(algorithm, "workers", None) is not None,
                "has_worker_group": getattr(algorithm, "worker_group", None) is not None,
                "has_env_runner_group": getattr(algorithm, "env_runner_group", None) is not None,
            },
        )
        # endregion

        def _try_local(group, group_name: str):
            for attr in ("local_worker", "local_env_runner", "_local_worker", "_local_env_runner"):
                if not hasattr(group, attr):
                    continue
                try:
                    candidate = getattr(group, attr)
                    worker = candidate() if callable(candidate) else candidate
                except Exception:
                    continue
                if worker is None:
                    continue
                # region agent log
                _dbg_log(
                    "H4",
                    "callbacks/metrics_callbacks.py:_collect_train_metrics_from_workers",
                    "collect_local",
                    {"group": group_name, "attr": attr},
                )
                # endregion
                item = _fetch(worker)
                if item:
                    sums, count = item
                    if isinstance(sums, dict):
                        for key in totals:
                            totals[key] += float(sums.get(key, 0.0) or 0.0)
                    return True, int(count or 0), f"{group_name}:{attr}"
            return False, 0, None

        def _fetch(worker):
            try:
                if getattr(worker, "config", None) and getattr(worker.config, "in_evaluation", False):
                    return None
            except Exception:
                return None
            callbacks = getattr(worker, "callbacks", None)
            if callbacks is None or not hasattr(callbacks, "_drain_train_metrics"):
                return None
            return callbacks._drain_train_metrics()

        groups = [
            ("workers", getattr(algorithm, "workers", None)),
            ("worker_group", getattr(algorithm, "worker_group", None)),
            ("env_runner_group", getattr(algorithm, "env_runner_group", None)),
        ]
        for name, group in groups:
            if callable(group):
                try:
                    group = group()
                except Exception:
                    group = None
            if group is None:
                continue
            used_local, local_count, local_group = _try_local(group, name)
            if used_local:
                total_count += local_count
                used_group = local_group
                break
            if hasattr(group, "foreach_worker"):
                # region agent log
                _dbg_log(
                    "H4",
                    "callbacks/metrics_callbacks.py:_collect_train_metrics_from_workers",
                    "collect_foreach_worker",
                    {"group": name},
                )
                # endregion
                results = group.foreach_worker(_fetch)
                used_group = name
                break
            if hasattr(group, "foreach_env_runner"):
                if name == "env_runner_group":
                    # Avoid potential deadlock in foreach_worker/foreach_env_runner on env_runner_group.
                    continue
                # region agent log
                _dbg_log(
                    "H4",
                    "callbacks/metrics_callbacks.py:_collect_train_metrics_from_workers",
                    "collect_foreach_env_runner",
                    {"group": name},
                )
                # endregion
                results = group.foreach_env_runner(
                    lambda env_runner: _fetch(getattr(env_runner, "worker", env_runner))
                )
                used_group = name
                break

        if isinstance(results, list):
            # region agent log
            _dbg_log(
                "H4",
                "callbacks/metrics_callbacks.py:_collect_train_metrics_from_workers",
                "collect_results",
                {"group": used_group, "result_len": len(results)},
            )
            # endregion
            for item in results:
                if not item:
                    continue
                sums, count = item
                if isinstance(sums, dict):
                    for key in totals:
                        totals[key] += float(sums.get(key, 0.0) or 0.0)
                total_count += int(count or 0)
        return totals, total_count, used_group

    def on_episode_start(self, *, worker, base_env, policies, episode, env_index, **kwargs):
        episode.user_data["delay_sum"] = 0.0
        episode.user_data["queue_sum"] = 0.0
        episode.user_data["stops_sum"] = 0.0
        episode.user_data["throughput_sum"] = 0.0
        episode.user_data["throughput_tls_sum"] = 0.0
        episode.user_data["throughput_network_sum"] = 0.0
        episode.user_data["throughput_min"] = float("inf")
        episode.user_data["throughput_max"] = float("-inf")
        episode.user_data["throughput_tls_min"] = float("inf")
        episode.user_data["throughput_tls_max"] = float("-inf")
        episode.user_data["throughput_network_min"] = float("inf")
        episode.user_data["throughput_network_max"] = float("-inf")
        episode.user_data["steps"] = 0

    def on_episode_step(self, *, worker, base_env, episode, env_index, **kwargs):
        agents = list(episode.get_agents())
        if not agents and self._debug_no_agent_count < 3:
            # region agent log
            _dbg_log(
                "H2",
                "callbacks/metrics_callbacks.py:on_episode_step",
                "episode_step_no_agents",
                {"episode_id": getattr(episode, "episode_id", None)},
            )
            # endregion
            self._debug_no_agent_count += 1
        agent_id = agents[0] if agents else None
        info = self._get_info_for_episode(episode, agent_id)
        if info is None:
            return
        worker_in_eval = bool(getattr(worker, "config", None) and getattr(worker.config, "in_evaluation", False))
        is_eval = bool(getattr(episode, "is_evaluation", False) or getattr(episode, "evaluation", False) or worker_in_eval)
        for agent_id in [agent_id]:
            episode.user_data["delay_sum"] += float(info.get("delay", 0.0))
            episode.user_data["queue_sum"] += float(info.get("queue", 0.0))
            episode.user_data["stops_sum"] += float(info.get("stops", 0.0))
            episode.user_data["throughput_sum"] += float(info.get("throughput", 0.0))
            episode.user_data["throughput_tls_sum"] += float(info.get("throughput_tls", 0.0))
            episode.user_data["throughput_network_sum"] += float(info.get("throughput_network", 0.0))
            throughput = float(info.get("throughput", 0.0))
            throughput_tls = float(info.get("throughput_tls", 0.0))
            throughput_network = float(info.get("throughput_network", 0.0))
            episode.user_data["throughput_min"] = min(episode.user_data["throughput_min"], throughput)
            episode.user_data["throughput_max"] = max(episode.user_data["throughput_max"], throughput)
            episode.user_data["throughput_tls_min"] = min(episode.user_data["throughput_tls_min"], throughput_tls)
            episode.user_data["throughput_tls_max"] = max(episode.user_data["throughput_tls_max"], throughput_tls)
            episode.user_data["throughput_network_min"] = min(
                episode.user_data["throughput_network_min"], throughput_network
            )
            episode.user_data["throughput_network_max"] = max(
                episode.user_data["throughput_network_max"], throughput_network
            )
            episode.user_data["steps"] += 1
            if not is_eval:
                self._train_step_sums["delay"] += float(info.get("delay", 0.0))
                self._train_step_sums["queue"] += float(info.get("queue", 0.0))
                self._train_step_sums["stops"] += float(info.get("stops", 0.0))
                self._train_step_sums["throughput"] += float(info.get("throughput", 0.0))
                self._train_step_sums["throughput_tls"] += float(info.get("throughput_tls", 0.0))
                self._train_step_sums["throughput_network"] += float(info.get("throughput_network", 0.0))
                self._train_step_counts += 1
            if self._debug_episode_step_count < 3:
                # region agent log
                _dbg_log(
                    "H2",
                    "callbacks/metrics_callbacks.py:on_episode_step",
                    "episode_step_info",
                    {
                        "agent_id": agent_id,
                        "info_keys": list(info.keys()),
                        "delay": info.get("delay"),
                        "queue": info.get("queue"),
                        "stops": info.get("stops"),
                        "throughput": info.get("throughput"),
                        "is_eval": is_eval,
                        "train_step_counts": self._train_step_counts,
                    },
                )
                # endregion
                self._debug_episode_step_count += 1
            break

    def on_episode_end(self, *, worker, base_env, policies, episode, **kwargs):
        self._ensure_train_accumulators()
        steps = max(1, episode.user_data.get("steps", 1))
        episode.custom_metrics["delay"] = episode.user_data.get("delay_sum", 0.0) / steps
        episode.custom_metrics["queue"] = episode.user_data.get("queue_sum", 0.0) / steps
        episode.custom_metrics["stops"] = episode.user_data.get("stops_sum", 0.0) / steps
        episode.custom_metrics["throughput"] = episode.user_data.get("throughput_sum", 0.0) / steps
        episode.custom_metrics["throughput_tls"] = episode.user_data.get("throughput_tls_sum", 0.0) / steps
        episode.custom_metrics["throughput_network"] = episode.user_data.get("throughput_network_sum", 0.0) / steps
        episode.custom_metrics["throughput_min"] = episode.user_data.get("throughput_min", 0.0)
        episode.custom_metrics["throughput_max"] = episode.user_data.get("throughput_max", 0.0)
        episode.custom_metrics["throughput_tls_min"] = episode.user_data.get("throughput_tls_min", 0.0)
        episode.custom_metrics["throughput_tls_max"] = episode.user_data.get("throughput_tls_max", 0.0)
        episode.custom_metrics["throughput_network_min"] = episode.user_data.get("throughput_network_min", 0.0)
        episode.custom_metrics["throughput_network_max"] = episode.user_data.get("throughput_network_max", 0.0)
        worker_in_eval = bool(getattr(worker, "config", None) and getattr(worker.config, "in_evaluation", False))
        is_eval = bool(getattr(episode, "is_evaluation", False) or getattr(episode, "evaluation", False) or worker_in_eval)
        if not is_eval:
            self._train_metric_sums["delay"] += episode.custom_metrics.get("delay", 0.0)
            self._train_metric_sums["queue"] += episode.custom_metrics.get("queue", 0.0)
            self._train_metric_sums["stops"] += episode.custom_metrics.get("stops", 0.0)
            self._train_metric_sums["throughput"] += episode.custom_metrics.get("throughput", 0.0)
            self._train_metric_sums["throughput_tls"] += episode.custom_metrics.get("throughput_tls", 0.0)
            self._train_metric_sums["throughput_network"] += episode.custom_metrics.get("throughput_network", 0.0)
            self._train_metric_counts += 1
        if self._debug_episode_end_count < 3:
            # region agent log
            _dbg_log(
                "H2",
                "callbacks/metrics_callbacks.py:on_episode_end",
                "episode_end_custom_metrics",
                {
                    "episode_id": getattr(episode, "episode_id", None),
                    "steps": steps,
                    "is_eval": is_eval,
                    "delay": episode.custom_metrics.get("delay"),
                    "queue": episode.custom_metrics.get("queue"),
                    "stops": episode.custom_metrics.get("stops"),
                    "throughput": episode.custom_metrics.get("throughput"),
                    "worker_in_evaluation": bool(getattr(worker, "config", None) and getattr(worker.config, "in_evaluation", False)),
                    "worker_is_evaluation": bool(getattr(worker, "is_evaluation", False)),
                },
            )
            _dbg_log(
                "H7",
                "callbacks/metrics_callbacks.py:on_episode_end",
                "episode_end_worker_flags",
                {
                    "episode_id": getattr(episode, "episode_id", None),
                    "is_eval": is_eval,
                    "episode_is_evaluation_attr": getattr(episode, "is_evaluation", None),
                    "episode_evaluation_attr": getattr(episode, "evaluation", None),
                    "worker_in_evaluation": bool(getattr(worker, "config", None) and getattr(worker.config, "in_evaluation", False)),
                    "worker_is_evaluation": bool(getattr(worker, "is_evaluation", False)),
                    "worker_type": type(worker).__name__,
                },
            )
            # endregion
            self._debug_episode_end_count += 1

    def on_train_result(self, *, algorithm, result, **kwargs):
        self._ensure_train_accumulators()
        # Ensure the metric exists even before the first episode finishes.
        custom = result.setdefault("custom_metrics", {})
        custom.setdefault("delay_mean", float("inf"))
        custom.setdefault("queue_mean", float("nan"))
        custom.setdefault("stops_mean", float("nan"))
        custom.setdefault("throughput_mean", float("nan"))
        custom.setdefault("throughput_tls_mean", float("nan"))
        custom.setdefault("throughput_network_mean", float("nan"))
        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            _dbg_log(
                "H8",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_result_custom_pre",
                {
                    "custom_keys": list(custom.keys()) if isinstance(custom, dict) else None,
                    "custom_delay_mean": custom.get("delay_mean") if isinstance(custom, dict) else None,
                },
            )
        # endregion

        env_runners = result.get("env_runners", {})
        env_custom = env_runners.get("custom_metrics") if isinstance(env_runners, dict) else None
        worker_sums = {"delay": 0.0, "queue": 0.0, "stops": 0.0, "throughput": 0.0}
        worker_counts = 0
        worker_group = None
        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            _dbg_log(
                "H5",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_metric_collect_start",
                {
                    "training_iteration": result.get("training_iteration"),
                    "timesteps_total": result.get("timesteps_total"),
                },
            )
        # endregion
        try:
            worker_sums, worker_counts, worker_group = self._collect_train_metrics_from_workers(algorithm)
        except Exception as exc:
            # region agent log
            if int(result.get("training_iteration", 0)) <= 2:
                _dbg_log(
                    "H12",
                    "callbacks/metrics_callbacks.py:on_train_result",
                    "train_metric_worker_error",
                    {"error": repr(exc), "error_type": type(exc).__name__},
                )
            # endregion
        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            _dbg_log(
                "H5",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_metric_collect_done",
                {
                    "training_iteration": result.get("training_iteration"),
                    "worker_counts": worker_counts,
                    "worker_group": worker_group,
                },
            )
        # endregion
        if worker_counts:
            for key in self._train_metric_sums:
                self._train_metric_sums[key] += worker_sums.get(key, 0.0)
            self._train_metric_counts += worker_counts
        step_sums, step_counts = self._drain_train_step_metrics(result.get("training_iteration"))
        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            _dbg_log(
                "H12",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_metric_worker_aggregate",
                {
                    "worker_counts": worker_counts,
                    "worker_group": worker_group,
                    "worker_sums": worker_sums,
                },
            )
            _dbg_log(
                "H12",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_metric_step_fallback",
                {"step_counts": step_counts, "step_sums": step_sums},
            )
        # endregion
        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            _dbg_log(
                "H6",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_result_context",
                {
                    "trial_id": result.get("trial_id"),
                    "logdir": result.get("logdir"),
                    "experiment_tag": result.get("experiment_tag"),
                    "training_iteration": result.get("training_iteration"),
                    "timesteps_total": result.get("timesteps_total"),
                    "num_env_steps_sampled_this_iter": result.get("num_env_steps_sampled_this_iter"),
                    "num_env_steps_trained_this_iter": result.get("num_env_steps_trained_this_iter"),
                    "num_env_steps_sampled": result.get("num_env_steps_sampled"),
                    "num_env_steps_trained": result.get("num_env_steps_trained"),
                    "has_evaluation": isinstance(result.get("evaluation"), dict),
                    "has_evaluation_noisy_pre": "evaluation_noisy" in result,
                    "env_custom_keys": list(env_custom.keys()) if isinstance(env_custom, dict) else None,
                    "train_metric_counts": self._train_metric_counts,
                    "result_key_count": len(result.keys()) if isinstance(result, dict) else None,
                },
            )
            _dbg_log(
                "H11",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_result_config",
                {
                    "config_input": result.get("config", {}).get("input") if isinstance(result.get("config"), dict) else None,
                    "config_num_env_runners": result.get("config", {}).get("num_env_runners") if isinstance(result.get("config"), dict) else None,
                    "config_num_envs_per_env_runner": result.get("config", {}).get("num_envs_per_env_runner") if isinstance(result.get("config"), dict) else None,
                    "config_num_rollout_workers": result.get("config", {}).get("num_rollout_workers") if isinstance(result.get("config"), dict) else None,
                    "config_create_local_env_runner": result.get("config", {}).get("create_local_env_runner") if isinstance(result.get("config"), dict) else None,
                    "config_rollout_fragment_length": result.get("config", {}).get("rollout_fragment_length") if isinstance(result.get("config"), dict) else None,
                    "config_train_batch_size": result.get("config", {}).get("train_batch_size") if isinstance(result.get("config"), dict) else None,
                    "config_evaluation_interval": result.get("config", {}).get("evaluation_interval") if isinstance(result.get("config"), dict) else None,
                },
            )
        # endregion

        def _pick_metric(name: str):
            if isinstance(env_custom, dict):
                value = env_custom.get(name)
                if isinstance(value, (int, float)) and math.isfinite(value):
                    return value
            if self._train_metric_counts > 0:
                return self._train_metric_sums[name.replace("_mean", "")] / self._train_metric_counts
            if step_counts > 0:
                return step_sums[name.replace("_mean", "")] / step_counts
            return custom.get(name)

        custom["delay_mean"] = _pick_metric("delay_mean")
        custom["queue_mean"] = _pick_metric("queue_mean")
        custom["stops_mean"] = _pick_metric("stops_mean")
        custom["throughput_mean"] = _pick_metric("throughput_mean")
        custom["throughput_tls_mean"] = _pick_metric("throughput_tls_mean")
        custom["throughput_network_mean"] = _pick_metric("throughput_network_mean")
        mean_keys = (
            "delay_mean",
            "queue_mean",
            "stops_mean",
            "throughput_mean",
            "throughput_tls_mean",
            "throughput_network_mean",
        )
        fallback_value = 1.0e9
        for key in mean_keys:
            value = custom.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                custom[key] = fallback_value
        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            _dbg_log(
                "H2",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_metric_sources",
                {
                    "train_metric_counts": self._train_metric_counts,
                    "delay_sum": self._train_metric_sums.get("delay"),
                    "queue_sum": self._train_metric_sums.get("queue"),
                    "stops_sum": self._train_metric_sums.get("stops"),
                    "throughput_sum": self._train_metric_sums.get("throughput"),
                    "env_custom_delay_mean": env_custom.get("delay_mean") if isinstance(env_custom, dict) else None,
                    "env_custom_queue_mean": env_custom.get("queue_mean") if isinstance(env_custom, dict) else None,
                },
            )
        # endregion

        self._train_metric_sums = {
            "delay": 0.0,
            "queue": 0.0,
            "stops": 0.0,
            "throughput": 0.0,
            "throughput_tls": 0.0,
            "throughput_network": 0.0,
        }
        self._train_metric_counts = 0

        self._mirror_training_custom_metrics(result)
        self._alias_metric_prefix(result, "train_tune", custom)
        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            algo_logdir = getattr(algorithm, "logdir", None)
            algo_internal_logdir = getattr(algorithm, "_logdir", None)
            local_worker_logdir = None
            try:
                workers = getattr(algorithm, "workers", None)
                if callable(workers):
                    workers = workers()
                if workers is not None and hasattr(workers, "local_worker"):
                    local_worker = workers.local_worker()
                    local_worker_logdir = getattr(local_worker, "logdir", None)
            except Exception:
                local_worker_logdir = None
            _dbg_log(
                "H13",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_result_logdirs",
                {
                    "result_logdir": result.get("logdir"),
                    "algo_logdir": algo_logdir,
                    "algo__logdir": algo_internal_logdir,
                    "local_worker_logdir": local_worker_logdir,
                    "has_train_tune": any(str(key).startswith("train_tune/") for key in result.keys()),
                },
            )
            event_counts = {}
            for label, raw_path in (
                ("result_logdir", result.get("logdir")),
                ("algo_logdir", algo_logdir),
                ("algo__logdir", algo_internal_logdir),
            ):
                if not raw_path:
                    continue
                try:
                    path = Path(str(raw_path))
                    if not path.exists():
                        event_counts[label] = {"exists": False, "count": 0}
                        continue
                    files = list(path.rglob("events.out.tfevents.*"))
                    event_counts[label] = {
                        "exists": True,
                        "count": len(files),
                        "first": str(files[0]) if files else None,
                    }
                except Exception as exc:
                    event_counts[label] = {"error": type(exc).__name__}
            _dbg_log(
                "H13",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_result_event_files",
                event_counts,
            )
        _dbg_log(
            "H2",
            "callbacks/metrics_callbacks.py:on_train_result",
            "train_result_custom_metrics",
            {
                "training_iteration": result.get("training_iteration"),
                "episodes_total": result.get("episodes_total"),
                "episodes_this_iter": result.get("episodes_this_iter"),
                "custom_metrics_keys": list(custom.keys()),
                "delay_mean": custom.get("delay_mean"),
                "queue_mean": custom.get("queue_mean"),
                "stops_mean": custom.get("stops_mean"),
                "throughput_mean": custom.get("throughput_mean"),
                "train_tune_delay_mean": result.get("train_tune/delay_mean"),
                "train_tune_queue_mean": result.get("train_tune/queue_mean"),
            },
        )
        # endregion

        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            env_runners = result.get("env_runners", {})
            _dbg_log(
                "H2",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_result_env_runners",
                {
                    "env_runners_type": type(env_runners).__name__,
                    "env_runners_keys": list(env_runners.keys()) if isinstance(env_runners, dict) else None,
                    "env_runners_custom_metrics": env_runners.get("custom_metrics") if isinstance(env_runners, dict) else None,
                    "env_runners_num_episodes": env_runners.get("num_episodes") if isinstance(env_runners, dict) else None,
                    "env_runners_episodes_this_iter": env_runners.get("episodes_this_iter") if isinstance(env_runners, dict) else None,
                },
            )
        # endregion

        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            env_runners = result.get("env_runners", {})
            hist_stats = env_runners.get("hist_stats", {}) if isinstance(env_runners, dict) else {}
            _dbg_log(
                "H4",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_result_hist_stats",
                {
                    "hist_stats_keys": list(hist_stats.keys()) if isinstance(hist_stats, dict) else None,
                    "delay_hist_len": len(hist_stats.get("custom_metrics/delay", [])) if isinstance(hist_stats, dict) else None,
                    "queue_hist_len": len(hist_stats.get("custom_metrics/queue", [])) if isinstance(hist_stats, dict) else None,
                    "stops_hist_len": len(hist_stats.get("custom_metrics/stops", [])) if isinstance(hist_stats, dict) else None,
                    "throughput_hist_len": len(hist_stats.get("custom_metrics/throughput", [])) if isinstance(hist_stats, dict) else None,
                },
            )
        # endregion

        eval_result = result.get("evaluation")
        if isinstance(eval_result, dict):
            self._alias_metric_prefix(result, "baseline_eval", eval_result.get("custom_metrics"))
        noisy_cfg = self._get_noisy_eval_cfg(algorithm)
        if not noisy_cfg:
            # region agent log
            _dbg_log(
                "H1",
                "callbacks/metrics_callbacks.py:on_train_result",
                "noisy_eval_config_missing",
                {"config_keys": list(result.keys())},
            )
            # endregion
            return

        sampled_this_iter = result.get("num_env_steps_sampled_this_iter")
        trained_this_iter = result.get("num_env_steps_trained_this_iter")
        if not sampled_this_iter or not trained_this_iter:
            # region agent log
            _dbg_log(
                "H1",
                "callbacks/metrics_callbacks.py:on_train_result",
                "noisy_eval_skipped_no_train_steps",
                {
                    "sampled_this_iter": sampled_this_iter,
                    "trained_this_iter": trained_this_iter,
                    "training_iteration": result.get("training_iteration"),
                },
            )
            # endregion
            return

        interval = int(noisy_cfg.get("interval", 0) or 0)
        if interval <= 0:
            # region agent log
            _dbg_log(
                "H1",
                "callbacks/metrics_callbacks.py:on_train_result",
                "noisy_eval_interval_invalid",
                {"interval": interval, "noisy_cfg": noisy_cfg},
            )
            # endregion
            return
        iteration = int(result.get("training_iteration", 0))
        if iteration <= 0 or (iteration % interval) != 0:
            # region agent log
            _dbg_log(
                "H1",
                "callbacks/metrics_callbacks.py:on_train_result",
                "noisy_eval_skipped_by_interval",
                {"iteration": iteration, "interval": interval},
            )
            # endregion
            return

        eval_config = dict(noisy_cfg.get("evaluation_config", {}))
        eval_env_config = dict(eval_config.get("env_config", {}))
        noise_rate = eval_env_config.get("rfid_noise_rate", noisy_cfg.get("rfid_noise_rate", 0.0))
        set_ok, used_group = self._set_eval_env_attr(algorithm, "rfid_noise_rate", noise_rate)
        # region agent log
        _dbg_log(
            "H1",
            "callbacks/metrics_callbacks.py:on_train_result",
            "noisy_eval_env_override",
            {
                "noise_rate": noise_rate,
                "set_ok": set_ok,
                "used_group": used_group,
                "eval_env_config_keys": list(eval_env_config.keys()),
            },
        )
        # endregion
        start_noisy = time.time()
        # region agent log
        _dbg_log(
            "H1",
            "callbacks/metrics_callbacks.py:on_train_result",
            "noisy_eval_start",
            {
                "training_iteration": result.get("training_iteration"),
                "duration": noisy_cfg.get("duration"),
                "duration_unit": noisy_cfg.get("duration_unit"),
                "num_env_runners": noisy_cfg.get("num_env_runners"),
            },
        )
        # endregion
        noisy_result = algorithm.evaluate()
        # region agent log
        _dbg_log(
            "H1",
            "callbacks/metrics_callbacks.py:on_train_result",
            "noisy_eval_done",
            {
                "training_iteration": result.get("training_iteration"),
                "elapsed_sec": round(time.time() - start_noisy, 3),
                "noisy_result_type": type(noisy_result).__name__,
            },
        )
        # endregion
        result["evaluation_noisy"] = self._normalize_noisy_result(noisy_result)
        if isinstance(result.get("evaluation_noisy"), dict):
            self._alias_metric_prefix(result, "baseline_noisy_eval", result["evaluation_noisy"].get("custom_metrics"))
        if set_ok:
            self._set_eval_env_attr(algorithm, "rfid_noise_rate", 0.0)
        # region agent log
        if int(result.get("training_iteration", 0)) <= 2:
            _dbg_log(
                "H3",
                "callbacks/metrics_callbacks.py:on_train_result",
                "train_result_final_keys",
                {
                    "top_level_keys": sorted(list(result.keys())) if isinstance(result, dict) else None,
                    "evaluation_noisy_keys": list(result.get("evaluation_noisy", {}).keys())
                    if isinstance(result.get("evaluation_noisy"), dict)
                    else None,
                    "evaluation_noisy_has_custom_metrics": isinstance(result.get("evaluation_noisy"), dict)
                    and "custom_metrics" in result.get("evaluation_noisy", {}),
                },
            )
        # endregion
        # region agent log
        _dbg_log(
            "H3",
            "callbacks/metrics_callbacks.py:on_train_result",
            "noisy_eval_custom_metrics_present",
            {
                "has_custom_metrics": isinstance(result.get("evaluation_noisy"), dict) and "custom_metrics" in result.get("evaluation_noisy", {}),
                "evaluation_noisy_keys": list(result.get("evaluation_noisy", {}).keys()) if isinstance(result.get("evaluation_noisy"), dict) else None,
            },
        )
        # endregion
        # region agent log
        eval_noisy = result.get("evaluation_noisy", {})
        eval_env = eval_noisy.get("env_runners", {}) if isinstance(eval_noisy, dict) else {}
        eval_hist = eval_env.get("hist_stats", {}) if isinstance(eval_env, dict) else {}
        _dbg_log(
            "H5",
            "callbacks/metrics_callbacks.py:on_train_result",
            "noisy_eval_env_runners",
            {
                "eval_custom_metrics": eval_env.get("custom_metrics") if isinstance(eval_env, dict) else None,
                "eval_hist_keys": list(eval_hist.keys()) if isinstance(eval_hist, dict) else None,
            },
        )
        # endregion
        # region agent log
        _dbg_log(
            "H3",
            "callbacks/metrics_callbacks.py:on_train_result",
            "noisy_eval_result_shapes",
            {
                "raw_keys": list(noisy_result.keys()) if isinstance(noisy_result, dict) else type(noisy_result).__name__,
                "normalized_keys": list(result["evaluation_noisy"].keys())
                if isinstance(result.get("evaluation_noisy"), dict)
                else type(result.get("evaluation_noisy")).__name__,
            },
        )
        # endregion

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

    @staticmethod
    def _normalize_noisy_result(noisy_result) -> Dict:
        if not isinstance(noisy_result, dict):
            return {"result": noisy_result}
        if isinstance(noisy_result.get("evaluation"), dict):
            eval_dict = dict(noisy_result["evaluation"])
        else:
            eval_dict = dict(noisy_result)
        if "custom_metrics" not in eval_dict and "custom_metrics" in noisy_result:
            eval_dict["custom_metrics"] = noisy_result["custom_metrics"]
        if "custom_metrics" not in eval_dict:
            env_runners = eval_dict.get("env_runners", {}) if isinstance(eval_dict, dict) else {}
            if isinstance(env_runners, dict) and "custom_metrics" in env_runners:
                eval_dict["custom_metrics"] = env_runners.get("custom_metrics")
        return eval_dict

    @staticmethod
    def _mirror_training_custom_metrics(result) -> None:
        custom = result.get("custom_metrics")
        if not isinstance(custom, dict):
            return
        env_runners = result.setdefault("env_runners", {})
        env_custom = env_runners.setdefault("custom_metrics", {})
        if not isinstance(env_custom, dict):
            return
        for key, value in custom.items():
            if isinstance(value, (int, float)) and math.isfinite(value):
                env_custom[key] = value


    @staticmethod
    def _alias_metric_prefix(result: Dict, prefix: str, metrics: Dict) -> None:
        if not isinstance(metrics, dict):
            return
        for key, value in metrics.items():
            if isinstance(value, (int, float)) and math.isfinite(value):
                result[f"{prefix}/{key}"] = value

    def _get_info_for_episode(self, episode, agent_id):
        if agent_id is not None:
            info = episode.last_info_for(agent_id)
            if info:
                return info
        for candidate in (0, "default_policy", "agent0", "default_agent"):
            info = episode.last_info_for(candidate)
            if info:
                return info
        return None

    @staticmethod
    def _set_eval_env_attr(algorithm, attr: str, value):
        groups = [
            ("evaluation_workers", getattr(algorithm, "evaluation_workers", None)),
            ("evaluation_env_runner_group", getattr(algorithm, "evaluation_env_runner_group", None)),
            ("evaluation_env_runners", getattr(algorithm, "evaluation_env_runners", None)),
            ("evaluation_worker_set", getattr(algorithm, "evaluation_worker_set", None)),
        ]
        # region agent log
        _dbg_log(
            "H1",
            "callbacks/metrics_callbacks.py:_set_eval_env_attr",
            "noisy_eval_group_scan",
            {
                "groups": [name for name, grp in groups if grp is not None],
                "attr": attr,
                "value": value,
            },
        )
        # endregion
        for name, group in groups:
            if callable(group):
                try:
                    group = group()
                except Exception:
                    group = None
            if group is None:
                continue
            has_foreach_env = hasattr(group, "foreach_env")
            has_foreach_worker = hasattr(group, "foreach_worker")
            # region agent log
            _dbg_log(
                "H1",
                "callbacks/metrics_callbacks.py:_set_eval_env_attr",
                "noisy_eval_group_methods",
                {
                    "group": name,
                    "type": type(group).__name__,
                    "has_foreach_env": has_foreach_env,
                    "has_foreach_worker": has_foreach_worker,
                },
            )
            # endregion
            if group is None:
                continue
            try:
                if hasattr(group, "foreach_env"):
                    group.foreach_env(lambda env: setattr(env, attr, value))
                    return True, name
                if hasattr(group, "foreach_worker"):
                    def _set(worker):
                        if hasattr(worker, "foreach_env"):
                            worker.foreach_env(lambda env: setattr(env, attr, value))
                    group.foreach_worker(_set)
                    return True, name
            except Exception as exc:
                # region agent log
                _dbg_log(
                    "H1",
                    "callbacks/metrics_callbacks.py:_set_eval_env_attr",
                    "noisy_eval_group_error",
                    {"group": name, "error": str(exc)},
                )
                # endregion
                continue
        return False, None
