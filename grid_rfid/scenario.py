"""Scenario building for the 3x3 RFID grid: network introspection, demand-route
generation (healthy = random corridors / test = fixed), and lane-closure sampling.

No SUMO process is started here; this module only reads the static network and
writes a .rou.xml. The actual run + detector readout lives in `runner.py`.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", "/usr/share/sumo"), "tools"))
import sumolib  # noqa: E402

from .vehicle_classes import ClassSet, CLASS_SET_V1

# backward-compatible aliases (v1 feature layout / demand mix)
VEHICLE_CLASSES = CLASS_SET_V1.classes
CLASS_MIX = CLASS_SET_V1.mix
VTYPE_XML = CLASS_SET_V1.vtype_xml()

_OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


@dataclass
class GridTopology:
    """Static facts about the grid, derived once from the .net.xml."""
    net_path: str
    monitored_lanes: List[str]                 # stable, sorted -> defines label index
    lane_index: Dict[str, int]                 # lane id -> 0..71
    entry_edges_by_side: Dict[str, List[str]]  # boundary entries grouped by side
    exit_edges_by_side: Dict[str, List[str]]   # boundary exits grouped by side
    internal_edges: List[str]                  # TLS->TLS edges (closeable approaches)
    edge_lanes: Dict[str, List[str]]           # edge id -> its lane ids

    @property
    def n_lanes(self) -> int:
        return len(self.monitored_lanes)


def _side(x, y, bbox, tol=20.0) -> str:
    (xmin, ymin, xmax, ymax) = bbox
    if y >= ymax - tol:
        return "N"
    if y <= ymin + tol:
        return "S"
    if x >= xmax - tol:
        return "E"
    if x <= xmin + tol:
        return "W"
    return "?"


def load_topology(net_path: str) -> GridTopology:
    net = sumolib.net.readNet(net_path)
    b = net.getBoundary()  # (xmin, ymin, xmax, ymax)

    monitored, edge_lanes, internal = [], {}, []
    entry_by_side: Dict[str, List[str]] = {s: [] for s in "NSEW"}
    exit_by_side: Dict[str, List[str]] = {s: [] for s in "NSEW"}

    for e in net.getEdges():
        if e.isSpecial():
            continue
        fn, tn = e.getFromNode(), e.getToNode()
        lanes = [ln.getID() for ln in e.getLanes()]
        edge_lanes[e.getID()] = lanes
        from_tls = fn.getType() == "traffic_light"
        to_tls = tn.getType() == "traffic_light"
        if to_tls:                       # incoming approach -> monitored
            monitored.extend(lanes)
        if from_tls and to_tls:          # internal link between two TLS -> closeable
            internal.append(e.getID())
        if (not from_tls) and to_tls:    # boundary entry
            fx, fy = fn.getCoord()
            entry_by_side[_side(fx, fy, b)].append(e.getID())
        if from_tls and (not to_tls):    # boundary exit
            tx, ty = tn.getCoord()
            exit_by_side[_side(tx, ty, b)].append(e.getID())

    monitored = sorted(monitored)
    lane_index = {lid: i for i, lid in enumerate(monitored)}
    return GridTopology(net_path, monitored, lane_index, entry_by_side,
                        exit_by_side, internal, edge_lanes)


# --------------------------------------------------------------------------- #
# Demand
# --------------------------------------------------------------------------- #

def _phi(t: float, t_peak: float, sigma: float, phi_min: float) -> float:
    return phi_min + (1.0 - phi_min) * float(np.exp(-((t - t_peak) ** 2) / (2 * sigma ** 2)))


def _entry_side(topo: GridTopology, edge: str) -> str:
    for s, edges in topo.entry_edges_by_side.items():
        if edge in edges:
            return s
    return "?"


def build_routes(
    topo: GridTopology,
    out_path: str,
    rng: np.random.Generator,
    horizon: float,
    regime: str = "healthy",
    n_corridors: Tuple[int, int] = (2, 3),
    intervals: int = 4,
    class_set: ClassSet = CLASS_SET_V1,
) -> Dict:
    """Write a .rou.xml realizing the corridor+background demand. Returns metadata.

    healthy: random subset of boundary entries act as heavy corridors (per episode).
    test:    fixed corridors (first entry of W, E, N) for a reproducible held-out demand.
    """
    all_entries = [e for s in "NSEW" for e in topo.entry_edges_by_side[s]]
    if regime == "test":
        corridors = [topo.entry_edges_by_side[s][0] for s in ("W", "E", "N")
                     if topo.entry_edges_by_side[s]]
        peaks = {corridors[0]: 1800.0, corridors[1]: 900.0, corridors[2]: 1200.0}
    else:
        k = int(rng.integers(n_corridors[0], n_corridors[1] + 1))
        corridors = list(rng.choice(all_entries, size=k, replace=False))
        peaks = {c: float(rng.uniform(900.0, 1800.0)) for c in corridors}

    t_peak, sigma, phi_min, bg_total = horizon / 2.0, horizon / 5.0, 0.20, 600.0
    edges = np.linspace(0, horizon, intervals + 1)
    flows = []

    def pick_exit(entry: str) -> str:
        opp = _OPPOSITE.get(_entry_side(topo, entry), "?")
        pool = topo.exit_edges_by_side.get(opp) or [e for s in "NSEW" for e in topo.exit_edges_by_side[s]]
        return str(rng.choice(pool))

    fid = 0
    for i in range(intervals):
        t0, t1 = float(edges[i]), float(edges[i + 1])
        ph = _phi((t0 + t1) / 2.0, t_peak, sigma, phi_min)
        # corridors
        for c in corridors:
            ex = pick_exit(c)
            for cls in class_set.classes:
                rate = peaks[c] * class_set.mix[cls] * ph
                if rate < 1.0:
                    continue
                flows.append((fid, cls, c, ex, t0, t1, rate)); fid += 1
        # background: every entry, low rate (car-only in v1; full mix otherwise so
        # every internal edge carries bannable classes)
        for e in all_entries:
            ex = pick_exit(e)
            base = bg_total / len(all_entries) * ph
            if class_set.background_mix:
                for cls in class_set.classes:
                    rate = base * class_set.mix[cls]
                    if rate >= 1.0:
                        flows.append((fid, cls, e, ex, t0, t1, rate)); fid += 1
            elif base >= 1.0:
                flows.append((fid, "car", e, ex, t0, t1, base)); fid += 1

    with open(out_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<routes>\n')
        f.write(class_set.vtype_xml())
        for fid, cls, frm, to, t0, t1, rate in flows:
            f.write(f'  <flow id="f{fid}_{cls}" type="{cls}" begin="{t0:.0f}" end="{t1:.0f}" '
                    f'from="{frm}" to="{to}" vehsPerHour="{rate:.1f}" '
                    f'departLane="free" departSpeed="max"/>\n')
        f.write("</routes>\n")

    return {"regime": regime, "corridors": [str(c) for c in corridors],
            "peaks": {str(k): round(v, 1) for k, v in peaks.items()}, "n_flows": len(flows)}


# --------------------------------------------------------------------------- #
# Anomalies: lane/edge closures
# --------------------------------------------------------------------------- #

@dataclass
class Closure:
    edge: str
    lanes: List[str]
    t0: float
    t1: float
    classes: List[str] | None = None   # None = full closure; else class-conditional ban


@dataclass
class ClosurePlan:
    closures: List[Closure] = field(default_factory=list)

    def is_anomalous(self) -> bool:
        return len(self.closures) > 0


def sample_closures(
    topo: GridTopology,
    rng: np.random.Generator,
    horizon: float,
    n_closed: Tuple[int, int] = (1, 3),
    allowed_edges: List[str] | None = None,
    ban_frac: float = 0.0,
    n_ban_classes: Tuple[int, int] = (1, 2),
    class_set: ClassSet = CLASS_SET_V1,
) -> ClosurePlan:
    """Close whole internal approach edges (both lanes) -> forces rerouting. Closure
    starts in the first third of the episode and lasts until the end.

    With probability `ban_frac` the episode uses class-conditional bans instead of
    full closures: each closed edge disallows a random subset of `class_set.bannable`
    (only that channel goes dark, the rest of the traffic keeps flowing). All RNG
    draws for bans are guarded behind `ban_frac > 0` so the default keeps the exact
    v1 random stream.
    """
    use_ban = ban_frac > 0.0 and float(rng.uniform()) < ban_frac
    pool = allowed_edges if allowed_edges is not None else topo.internal_edges
    k = int(rng.integers(n_closed[0], n_closed[1] + 1))
    k = min(k, len(pool))
    chosen = rng.choice(pool, size=k, replace=False)
    plan = ClosurePlan()
    for edge in chosen:
        t0 = float(rng.uniform(0.0, horizon / 3.0))
        classes = None
        if use_ban:
            nb = int(rng.integers(n_ban_classes[0], n_ban_classes[1] + 1))
            nb = min(nb, len(class_set.bannable))
            classes = [str(c) for c in rng.choice(class_set.bannable, size=nb,
                                                  replace=False)]
        plan.closures.append(Closure(str(edge), list(topo.edge_lanes[str(edge)]),
                                     t0, horizon, classes))
    return plan


def label_class_at(topo: GridTopology, plan: ClosurePlan, t: float,
                   class_set: ClassSet = CLASS_SET_V1) -> np.ndarray:
    """Ground-truth per-lane, per-class label y in {0,1}^(n_lanes x K) at time t.
    A full closure marks every class channel; a class ban only the banned ones."""
    y = np.zeros((topo.n_lanes, class_set.n_classes), dtype=np.float32)
    for c in plan.closures:
        # closed interval: closures never reopen, so the final record at
        # t == t1 == horizon is still physically closed
        if c.t0 <= t <= c.t1:
            cls_ids = c.classes if c.classes is not None else list(class_set.classes)
            cols = [class_set.classes.index(cid) for cid in cls_ids]
            for lid in c.lanes:
                idx = topo.lane_index.get(lid)
                if idx is not None:
                    y[idx, cols] = 1.0
    return y


def label_at(topo: GridTopology, plan: ClosurePlan, t: float,
             class_set: ClassSet = CLASS_SET_V1) -> np.ndarray:
    """Per-lane label in [0,1]: demand-mix share of the banned classes. A full
    closure is exactly 1.0 (the original binary semantics)."""
    y = np.zeros(topo.n_lanes, dtype=np.float32)
    for c in plan.closures:
        if c.t0 <= t <= c.t1:
            val = (1.0 if c.classes is None
                   else min(1.0, sum(class_set.mix[cid] for cid in c.classes)))
            for lid in c.lanes:
                idx = topo.lane_index.get(lid)
                if idx is not None:
                    y[idx] = max(y[idx], np.float32(val))
    return y
