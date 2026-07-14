#!/usr/bin/env python3
"""
Gymnasium environment for PPO-Transformer traffic signal control in SUMO.

State (per step):
- RFID counts by approach for car/bus/delivery (4 x 3 = 12)
- current phase one-hot (2)
- normalized green elapsed time (1)

Observation is a sequence window of the last L states: shape (L, D).
Action space: MultiDiscrete([2, 3])
- phase selection: 0 (NS), 1 (EW)
- green duration adjust: 0 (-5s), 1 (0s), 2 (+5s)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import socket
import uuid
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Deque, Dict, List, Tuple

import gymnasium as gym
import numpy as np


def _ensure_sumo_tools_on_path() -> None:
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        return
    tools_path = Path(sumo_home) / "tools"
    if tools_path.exists() and str(tools_path) not in sys.path:
        sys.path.append(str(tools_path))


def _import_traci():
    _ensure_sumo_tools_on_path()
    try:
        import traci  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Could not import traci. Make sure SUMO and Python dependencies are installed."
        ) from exc
    return traci


def _parse_sumocfg(config_path: Path) -> Dict[str, str]:
    tree = ET.parse(config_path)
    root = tree.getroot()
    cfg = {}

    net_file = root.find("./input/net-file")
    if net_file is not None:
        cfg["net"] = net_file.get("value", "")

    add_file = root.find("./input/additional-files")
    if add_file is not None:
        cfg["additional"] = add_file.get("value", "")

    end = root.find("./time/end")
    if end is not None:
        cfg["end"] = end.get("value", "")

    return cfg


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


def _parse_incoming_lanes(net_path: Path, tls_id: str) -> List[str]:
    tree = ET.parse(net_path)
    root = tree.getroot()
    lanes = []
    for edge in root.findall("edge"):
        if edge.get("function") == "internal":
            continue
        if edge.get("to") != tls_id:
            continue
        for lane in edge.findall("lane"):
            lane_id = lane.get("id")
            if lane_id:
                lanes.append(lane_id)
    return lanes


def _parse_detectors(add_path: Path) -> Dict[str, List[str]]:
    tree = ET.parse(add_path)
    root = tree.getroot()
    detectors: Dict[str, List[str]] = defaultdict(list)

    for loop in root.findall("inductionLoop"):
        loop_id = loop.get("id", "")
        if loop_id.startswith("rfid_north"):
            detectors["north"].append(loop_id)
        elif loop_id.startswith("rfid_south"):
            detectors["south"].append(loop_id)
        elif loop_id.startswith("rfid_east"):
            detectors["east"].append(loop_id)
        elif loop_id.startswith("rfid_west"):
            detectors["west"].append(loop_id)

    return detectors


def _clamp(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))


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


class PPOTransformerEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: Dict):
        super().__init__()

        self.config = config
        self.traci = _import_traci()

        self.sumo_cfg = Path(config.get("sumo_cfg", ""))
        if not self.sumo_cfg.is_absolute():
            candidate = (Path(__file__).resolve().parent.parent / self.sumo_cfg).resolve()
            if candidate.exists():
                self.sumo_cfg = candidate
        if not self.sumo_cfg.exists():
            raise FileNotFoundError(f"SUMO config not found: {self.sumo_cfg}")

        self.use_gui = bool(config.get("use_gui", False))
        self.sumo_binary = config.get("sumo_binary", "sumo")
        self.sumo_threads = int(config.get("sumo_threads", 0) or 0)
        self.sumo_step_length = float(config.get("sumo_step_length", 0) or 0)
        self.sumo_extra_args = list(config.get("sumo_extra_args", []) or [])
        self.sumo_start_retries = int(config.get("sumo_start_retries", 3))
        self.sumo_start_retry_wait = float(config.get("sumo_start_retry_wait", 1.0))
        self.delta_time = int(config.get("delta_time", 5))
        self.yellow_time = int(config.get("yellow_time", 3))
        self.t_green_min = int(config.get("t_green_min", 10))
        self.t_green_max = int(config.get("t_green_max", 60))
        self.obs_window = int(config.get("obs_window", 48))
        self.queue_speed_threshold = float(config.get("queue_speed_threshold", 0.1))
        self.tls_id = config.get("tls_id", "center")
        self.episode_horizon_steps = int(config.get("episode_horizon_steps", 0) or 0)
        self.soft_reset = bool(config.get("soft_reset", True))
        self.rfid_noise_rate = _clamp(float(config.get("rfid_noise_rate", 0.0)), 0.0, 1.0)

        self.alpha = float(config.get("reward_alpha", 0.55))
        self.beta = float(config.get("reward_beta", 0.30))
        self.gamma = float(config.get("reward_gamma", 0.15))

        cfg_values = _parse_sumocfg(self.sumo_cfg)
        base_dir = self.sumo_cfg.parent

        self.net_path = _resolve_path(base_dir, cfg_values.get("net", ""))
        self.add_path = _resolve_path(base_dir, cfg_values.get("additional", ""))
        cfg_end = float(cfg_values.get("end", "0") or 0)
        self.sim_end = float(config.get("sim_end", cfg_end)) if cfg_end else float(config.get("sim_end", 0))

        self.detectors_by_approach = _parse_detectors(self.add_path)
        self.approach_order = ["north", "south", "east", "west"]
        self.incoming_lanes = _parse_incoming_lanes(self.net_path, self.tls_id)

        self.obs_dim = 12 + 2 + 1
        low = np.zeros((self.obs_window, self.obs_dim), dtype=np.float32)
        high = np.full((self.obs_window, self.obs_dim), 1e6, dtype=np.float32)
        self.observation_space = gym.spaces.Box(
            low=low,
            high=high,
            dtype=np.float32,
        )
        self.action_space = gym.spaces.MultiDiscrete([2, 3])

        self.conn = None
        self._traci_label = None
        self._started = False

        self.window_counts = None
        self.obs_history: Deque[np.ndarray] = deque(maxlen=self.obs_window)

        self.phase_elapsed = 0
        self.phase_target = 30
        self.current_phase = 0  # 0=NS, 1=EW
        self.phase_indices = {"ns": 0, "ns_y": 1, "ew": 2, "ew_y": 3}

        self.prev_wait: Dict[str, float] = {}
        self.prev_speed: Dict[str, float] = {}

        self.delay_accum = 0.0
        self.queue_accum = 0.0
        self.stops_accum = 0
        self.throughput_accum = 0
        self.throughput_tls_accum = 0
        self.episode_steps = 0
        self.prev_incoming_vehicles = set()
        self._debug_reset_count = 0
        self._debug_start_count = 0
        self._debug_simulate_count = 0

        # region agent log
        _dbg_log(
            "H3",
            "envs/ppo_transformer_env.py:__init__",
            "env_init_config",
            {
                "sumo_cfg": str(self.sumo_cfg),
                "episode_horizon_steps": self.episode_horizon_steps,
                "sim_end": self.sim_end,
                "soft_reset": self.soft_reset,
                "delta_time": self.delta_time,
                "use_gui": self.use_gui,
            },
        )
        # endregion

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.episode_steps = 0
        self._debug_reset_count += 1
        restart = True
        if self._started and self.soft_reset and self.conn is not None:
            if not self._is_done():
                restart = False
        if self._debug_reset_count <= 3:
            # region agent log
            _dbg_log(
                "H3",
                "envs/ppo_transformer_env.py:reset",
                "env_reset",
                {
                    "reset_count": self._debug_reset_count,
                    "restart": restart,
                    "started": self._started,
                    "soft_reset": self.soft_reset,
                    "episode_horizon_steps": self.episode_horizon_steps,
                    "sim_end": self.sim_end,
                },
            )
            # endregion
        if restart:
            self._close_traci()
            self._start_sumo()
            self._setup_tls_program()
            self._started = True

        self.phase_elapsed = 0
        self.phase_target = 30
        self.current_phase = 0

        self.prev_wait.clear()
        self.prev_speed.clear()
        self.prev_incoming_vehicles.clear()

        self._reset_window_counts()
        self.obs_history.clear()

        zero_obs = np.zeros(self.obs_dim, dtype=np.float32)
        for _ in range(self.obs_window):
            self.obs_history.append(zero_obs.copy())

        return np.stack(self.obs_history), {}

    def step(self, action):
        phase_action = int(action[0])
        duration_action = int(action[1])
        duration_delta = [-5, 0, 5][duration_action]
        self.phase_target = _clamp(self.phase_target + duration_delta, self.t_green_min, self.t_green_max)

        force_switch = self.phase_elapsed >= self.t_green_max
        desired_phase = phase_action
        switch_phase = None

        if force_switch:
            switch_phase = 1 - self.current_phase
        elif desired_phase != self.current_phase and self.phase_elapsed >= self.t_green_min:
            switch_phase = desired_phase
        elif desired_phase == self.current_phase and self.phase_elapsed >= self.phase_target and self.phase_elapsed >= self.t_green_min:
            switch_phase = 1 - self.current_phase

        if switch_phase is None:
            self._simulate_steps(self.delta_time)
            self.phase_elapsed += self.delta_time
        else:
            # Yellow phase
            self._set_phase(self._yellow_index(self.current_phase))
            self._simulate_steps(self.yellow_time)
            # Switch to new green
            self.current_phase = switch_phase
            self.phase_elapsed = 0
            self._set_phase(self._green_index(self.current_phase))
            remaining = max(0, self.delta_time - self.yellow_time)
            if remaining:
                self._simulate_steps(remaining)
                self.phase_elapsed += remaining

        obs = self._build_observation()
        reward, info = self._compute_reward()

        self.episode_steps += 1
        terminated = self._is_done()
        truncated = False
        if not terminated and self.episode_horizon_steps and self.episode_steps >= self.episode_horizon_steps:
            truncated = True

        return obs, reward, terminated, truncated, info

    def close(self):
        self._close_traci()

    def _start_sumo(self):
        binary = self.sumo_binary
        if self.use_gui and binary == "sumo":
            binary = "sumo-gui"
        if not self.use_gui and binary == "sumo-gui":
            binary = "sumo"

        cmd = [binary, "-c", str(self.sumo_cfg)]
        if self.sim_end:
            cmd += ["--end", str(self.sim_end)]
        if self.sumo_step_length:
            cmd += ["--step-length", str(self.sumo_step_length)]
        if self.sumo_threads:
            cmd += ["--threads", str(self.sumo_threads)]
        if self.sumo_extra_args:
            cmd.extend([str(arg) for arg in self.sumo_extra_args])
        last_error = None
        retries = max(1, self.sumo_start_retries)
        for _ in range(retries):
            self._traci_label = f"ppo-env-{uuid.uuid4().hex}"
            port = self._get_free_port()
            try:
                if self._debug_start_count < 2:
                    # region agent log
                    _dbg_log(
                        "H4",
                        "envs/ppo_transformer_env.py:_start_sumo",
                        "sumo_start_attempt",
                        {"cmd": cmd, "label": self._traci_label, "port": port},
                    )
                    # endregion
                    self._debug_start_count += 1
                self.traci.start(cmd, label=self._traci_label, port=port)
                self.conn = self.traci.getConnection(self._traci_label)
                if self._debug_start_count <= 2:
                    # region agent log
                    _dbg_log(
                        "H4",
                        "envs/ppo_transformer_env.py:_start_sumo",
                        "sumo_start_success",
                        {"label": self._traci_label, "port": port},
                    )
                    # endregion
                return
            except Exception as exc:
                last_error = exc
                if self._debug_start_count <= 2:
                    # region agent log
                    _dbg_log(
                        "H4",
                        "envs/ppo_transformer_env.py:_start_sumo",
                        "sumo_start_error",
                        {"error": repr(exc), "error_type": type(exc).__name__},
                    )
                    # endregion
                time.sleep(self.sumo_start_retry_wait)
        raise RuntimeError(f"SUMO/TraCI start failed after {retries} attempts") from last_error

    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("", 0))
            return sock.getsockname()[1]

    def _close_traci(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        if self._traci_label is not None:
            try:
                self.traci.switch(self._traci_label)
            except Exception:
                pass
            self._traci_label = None
        self._started = False

    def _setup_tls_program(self):
        if self.conn is None:
            return

        controlled_links = self.conn.trafficlight.getControlledLinks(self.tls_id)
        ns_indices = []
        ew_indices = []

        for idx, links in enumerate(controlled_links):
            if not links:
                continue
            from_lane = links[0][0]
            if from_lane.startswith("north_to_center") or from_lane.startswith("south_to_center"):
                ns_indices.append(idx)
            elif from_lane.startswith("east_to_center") or from_lane.startswith("west_to_center"):
                ew_indices.append(idx)

        state_ns = self._build_state(len(controlled_links), ns_indices, [])
        state_ns_y = self._build_state(len(controlled_links), [], ns_indices, yellow=True)
        state_ew = self._build_state(len(controlled_links), ew_indices, [])
        state_ew_y = self._build_state(len(controlled_links), [], ew_indices, yellow=True)

        Phase = self.traci.trafficlight.Phase
        Logic = self.traci.trafficlight.Logic

        logic = Logic(
            programID="ppo",
            type=0,
            currentPhaseIndex=0,
            phases=[
                Phase(30, state_ns),
                Phase(self.yellow_time, state_ns_y),
                Phase(30, state_ew),
                Phase(self.yellow_time, state_ew_y),
            ],
        )

        self.conn.trafficlight.setProgramLogic(self.tls_id, logic)
        self.conn.trafficlight.setProgram(self.tls_id, "ppo")
        self._set_phase(self._green_index(0))

    def _build_state(self, n: int, green_indices: List[int], yellow_indices: List[int], yellow: bool = False) -> str:
        state = ["r"] * n
        for idx in green_indices:
            state[idx] = "G"
        for idx in yellow_indices:
            state[idx] = "y" if yellow else "G"
        return "".join(state)

    def _green_index(self, phase: int) -> int:
        return self.phase_indices["ns"] if phase == 0 else self.phase_indices["ew"]

    def _yellow_index(self, phase: int) -> int:
        return self.phase_indices["ns_y"] if phase == 0 else self.phase_indices["ew_y"]

    def _set_phase(self, phase_index: int):
        if self.conn is not None:
            self.conn.trafficlight.setPhase(self.tls_id, int(phase_index))

    def _reset_window_counts(self):
        self.window_counts = {approach: Counter() for approach in self.approach_order}

    def _simulate_steps(self, steps: int):
        if self.conn is None:
            if self._debug_simulate_count < 2:
                # region agent log
                _dbg_log(
                    "H4",
                    "envs/ppo_transformer_env.py:_simulate_steps",
                    "simulate_steps_no_conn",
                    {"steps": steps},
                )
                # endregion
                self._debug_simulate_count += 1
            return

        log_this = self._debug_simulate_count < 2
        start_time = None
        start_sim_time = None
        if log_this:
            start_time = time.time()
            try:
                start_sim_time = self.conn.simulation.getTime()
            except Exception:
                start_sim_time = None
            # region agent log
            _dbg_log(
                "H4",
                "envs/ppo_transformer_env.py:_simulate_steps",
                "simulate_steps_begin",
                {"steps": steps, "sim_time": start_sim_time},
            )
            # endregion

        for _ in range(steps):
            self.conn.simulationStep()
            self._collect_detectors()
            self._collect_metrics()

        if log_this:
            try:
                end_sim_time = self.conn.simulation.getTime()
            except Exception:
                end_sim_time = None
            elapsed = round(time.time() - start_time, 3) if start_time is not None else None
            # region agent log
            _dbg_log(
                "H4",
                "envs/ppo_transformer_env.py:_simulate_steps",
                "simulate_steps_end",
                {"steps": steps, "sim_time": end_sim_time, "elapsed_sec": elapsed},
            )
            # endregion
            self._debug_simulate_count += 1

    def _collect_detectors(self):
        if self.conn is None:
            return

        for approach in self.approach_order:
            for loop_id in self.detectors_by_approach.get(approach, []):
                veh_ids = self.conn.inductionloop.getLastStepVehicleIDs(loop_id)
                for vid in veh_ids:
                    vtype = self.conn.vehicle.getTypeID(vid)
                    if vtype not in ("car", "bus", "delivery"):
                        vtype = "car"
                    self.window_counts[approach][vtype] += 1

    def _collect_metrics(self):
        if self.conn is None:
            return

        veh_ids = []
        for lane_id in self.incoming_lanes:
            veh_ids.extend(self.conn.lane.getLastStepVehicleIDs(lane_id))

        veh_ids = list(set(veh_ids))

        queue_count = 0
        for lane_id in self.incoming_lanes:
            queue_count += self.conn.lane.getLastStepHaltingNumber(lane_id)

        self.queue_accum += queue_count

        for vid in veh_ids:
            speed = self.conn.vehicle.getSpeed(vid)
            wait = self.conn.vehicle.getWaitingTime(vid)

            prev_wait = self.prev_wait.get(vid, wait)
            if wait >= prev_wait:
                self.delay_accum += wait - prev_wait
            self.prev_wait[vid] = wait

            prev_speed = self.prev_speed.get(vid, speed)
            if prev_speed > self.queue_speed_threshold and speed <= self.queue_speed_threshold:
                self.stops_accum += 1
            self.prev_speed[vid] = speed

        for vid in self.conn.simulation.getArrivedIDList():
            self.prev_wait.pop(vid, None)
            self.prev_speed.pop(vid, None)

        self.throughput_accum += len(self.conn.simulation.getArrivedIDList())

        if self.incoming_lanes:
            current_incoming = set()
            for lane_id in self.incoming_lanes:
                current_incoming.update(self.conn.lane.getLastStepVehicleIDs(lane_id))
            for vid in self.prev_incoming_vehicles - current_incoming:
                try:
                    lane_id = self.conn.vehicle.getLaneID(vid)
                except Exception:
                    self.throughput_tls_accum += 1
                    continue
                if lane_id not in self.incoming_lanes:
                    self.throughput_tls_accum += 1
            self.prev_incoming_vehicles = current_incoming

    def _build_observation(self) -> np.ndarray:
        phase_one_hot = [1.0, 0.0] if self.current_phase == 0 else [0.0, 1.0]
        tau = self.phase_elapsed / float(self.t_green_max)

        obs_vec = []
        for approach in self.approach_order:
            counts = self.window_counts[approach]
            car = self._apply_rfid_noise(counts.get("car", 0))
            bus = self._apply_rfid_noise(counts.get("bus", 0))
            delivery = self._apply_rfid_noise(counts.get("delivery", 0))
            obs_vec.extend([
                float(car),
                float(bus),
                float(delivery),
            ])

        obs_vec.extend(phase_one_hot)
        obs_vec.append(float(tau))

        obs = np.array(obs_vec, dtype=np.float32)
        self.obs_history.append(obs)

        # reset counters for next window
        self._reset_window_counts()

        return np.stack(self.obs_history).astype(np.float32)

    def _apply_rfid_noise(self, count: int) -> int:
        if self.rfid_noise_rate <= 0.0 or count <= 0:
            return int(count)
        rng = getattr(self, "np_random", None)
        if rng is None:
            rng = np.random.default_rng()
        return int(rng.binomial(int(count), 1.0 - self.rfid_noise_rate))

    def _compute_reward(self) -> Tuple[float, Dict]:
        avg_queue = self.queue_accum / max(1, self.delta_time)
        throughput_rate = (self.throughput_tls_accum / max(1, self.delta_time)) * 3600.0
        reward = -(
            self.alpha * self.delay_accum
            + self.beta * avg_queue
            + self.gamma * self.stops_accum
        )

        info = {
            "delay": float(self.delay_accum),
            "queue": float(avg_queue),
            "stops": float(self.stops_accum),
            "throughput": float(throughput_rate),
            "throughput_tls": float(self.throughput_tls_accum),
            "throughput_network": float(self.throughput_accum),
            "phase": int(self.current_phase),
            "phase_elapsed": float(self.phase_elapsed),
        }

        self.delay_accum = 0.0
        self.queue_accum = 0.0
        self.stops_accum = 0
        self.throughput_accum = 0
        self.throughput_tls_accum = 0

        return reward, info

    def _is_done(self) -> bool:
        if self.conn is None:
            return True
        sim_time = self.conn.simulation.getTime()
        if self.sim_end and sim_time >= self.sim_end:
            return True
        return self.conn.simulation.getMinExpectedNumber() == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="SUMO .sumocfg path")
    args = parser.parse_args()

    env = PPOTransformerEnv({"sumo_cfg": args.config})
    obs, _ = env.reset()
    done = False
    while not done:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
    env.close()
