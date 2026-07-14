"""Run a single SUMO episode on the 3x3 grid via TraCI: apply lane closures,
read the 72 RFID induction loops each second, aggregate per-lane class counts into
Delta-t windows, and emit sliding-window observations with per-lane labels.

Control of the traffic lights is SUMO's built-in static program (no RL here) — the
dataset is for training/validating an anomaly-localization model downstream.
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List

import numpy as np

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", "/usr/share/sumo"), "tools"))
import traci  # noqa: E402
from traci.exceptions import FatalTraCIError, TraCIException  # noqa: E402
from sumolib.miscutils import getFreeSocketPort  # noqa: E402

from .scenario import GridTopology, ClosurePlan, label_at, label_class_at
from .vehicle_classes import ClassSet, CLASS_SET_V1


def parse_loops(add_path: str) -> Dict[str, str]:
    """Return {loop_id: lane_id} from the detectors additional file."""
    root = ET.parse(add_path).getroot()
    return {el.get("id"): el.get("lane") for el in root.iter("inductionLoop")}


@dataclass
class EpisodeConfig:
    net: str
    add: str               # detectors additional file (72 loops)
    routes: str            # generated .rou.xml
    horizon: float = 600.0
    delta: int = 5         # seconds per observation record (counting window)
    window: int = 48       # L: records per sliding window
    stride: int = 4        # records between consecutive windows
    seed: int = 0
    sumo_binary: str = "sumo"
    class_set: ClassSet = CLASS_SET_V1


def run_episode(topo: GridTopology, cfg: EpisodeConfig, plan: ClosurePlan) -> Dict:
    """Returns dict with X (n_win, L, n_lanes*K), Y (n_win, n_lanes),
    Y_class (n_win, n_lanes, K), and meta."""
    loop_lane = parse_loops(cfg.add)
    loops = list(loop_lane.keys())
    n_lanes = topo.n_lanes
    class_set = cfg.class_set
    n_cls = class_set.n_classes
    n_feat = n_lanes * n_cls
    cls_idx = {c: i for i, c in enumerate(class_set.classes)}

    sumo_cmd = [
        cfg.sumo_binary, "-n", cfg.net, "-r", cfg.routes,
        "-a", cfg.add, "--step-length", "1.0", "--end", str(int(cfg.horizon)),
        "--seed", str(cfg.seed), "--time-to-teleport", "300",
        "--ignore-route-errors", "true",   # closures can strand vehicles; drop
        # them instead of letting SUMO quit-on-error and kill the episode
        "--device.rerouting.probability", "1.0",
        "--device.rerouting.period", "20",
        "--no-step-log", "true", "--no-warnings", "true",
        "--duration-log.disable", "true", "--xml-validation", "never",
        "--error-log", cfg.routes + ".err",
    ]
    traci.start(sumo_cmd, port=getFreeSocketPort(), numRetries=10)

    applied = {c.edge: False for c in plan.closures}
    records: List[np.ndarray] = []   # per-record feature vector (n_feat,)
    rec_labels: List[np.ndarray] = []  # per-record label (n_lanes,)
    rec_cls_labels: List[np.ndarray] = []  # per-record label (n_lanes, K)
    truncated = False

    try:
        t = traci.simulation.getTime()
        while t < cfg.horizon:
            window_counts = np.zeros((n_lanes, n_cls), dtype=np.float32)
            steps = 0
            while steps < cfg.delta and t < cfg.horizon:
                # apply closures whose start time has arrived
                for c in plan.closures:
                    if (not applied[c.edge]) and t >= c.t0:
                        if c.classes is None:      # full closure
                            for lid in c.lanes:
                                traci.lane.setDisallowed(lid, ["all"])
                            traci.edge.adaptTraveltime(c.edge, 1.0e6)
                        else:                      # class-conditional ban: no edge
                            # penalty — routing must repel only the banned vClasses
                            banned = class_set.vclasses_of(c.classes)
                            for lid in c.lanes:
                                traci.lane.setDisallowed(lid, banned)
                        applied[c.edge] = True
                # read detectors at the current step
                for loop in loops:
                    li = topo.lane_index.get(loop_lane[loop])
                    if li is None:
                        continue
                    for vid in traci.inductionloop.getLastStepVehicleIDs(loop):
                        try:
                            vtype = traci.vehicle.getTypeID(vid)
                        except traci.TraCIException:
                            vtype = "car"
                        window_counts[li, cls_idx.get(vtype, 0)] += 1.0
                traci.simulationStep()
                steps += 1
                t = traci.simulation.getTime()
            records.append(window_counts.reshape(-1))
            rec_labels.append(label_at(topo, plan, t, class_set))
            rec_cls_labels.append(label_class_at(topo, plan, t, class_set))
    except (FatalTraCIError, TraCIException):
        # SUMO died mid-episode (intermittent): keep the records gathered so far
        truncated = True
    finally:
        try:
            traci.close()
        except Exception:
            pass

    # --- build sliding windows over records ---
    R = np.stack(records) if records else np.zeros((0, n_feat), np.float32)
    Lr = np.stack(rec_labels) if rec_labels else np.zeros((0, n_lanes), np.float32)
    Lc = (np.stack(rec_cls_labels) if rec_cls_labels
          else np.zeros((0, n_lanes, n_cls), np.float32))
    L = cfg.window
    X, Y, Yc = [], [], []
    for end in range(L, len(R) + 1, cfg.stride):
        X.append(R[end - L:end])      # (L, n_feat)
        Y.append(Lr[end - 1])         # label at window end
        Yc.append(Lc[end - 1])
    X = np.stack(X).astype(np.float32) if X else np.zeros((0, L, n_feat), np.float32)
    Y = np.stack(Y).astype(np.float32) if Y else np.zeros((0, n_lanes), np.float32)
    Yc = (np.stack(Yc).astype(np.float32) if Yc
          else np.zeros((0, n_lanes, n_cls), np.float32))

    return {"X": X, "Y": Y, "Y_class": Yc, "n_records": len(R),
            "truncated": truncated, "anomalous": plan.is_anomalous(),
            "closed_edges": [c.edge for c in plan.closures],
            "closed_classes": [c.classes for c in plan.closures],
            # full precision: labels are recomputed from these downstream
            "closure_t0": [float(c.t0) for c in plan.closures]}
