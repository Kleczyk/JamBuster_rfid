#!/usr/bin/env python3
"""
Collect real-time traffic metrics from SUMO for every junction in the network.

This script:
- Starts SUMO via TraCI (sumo or sumo-gui)
- Detects all junctions and incoming lanes from the net file
- Streams per-lane and per-junction metrics to CSV

Example:
    uv run python tools/collect_intersection_metrics.py \
        --config nets/simple_intersection/simulation.sumocfg \
        --output-dir outputs/metrics \
        --end 60
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


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
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Could not import traci. Make sure SUMO and Python dependencies are installed."
        ) from exc
    return traci


def _parse_sumocfg_net_file(config_path: Path) -> Path:
    tree = ET.parse(config_path)
    root = tree.getroot()
    net_file = root.find("./input/net-file")
    if net_file is None or not net_file.get("value"):
        raise ValueError("Missing <net-file> in sumocfg")

    net_value = net_file.get("value")
    net_path = Path(net_value)
    if not net_path.is_absolute():
        net_path = (config_path.parent / net_path).resolve()

    if not net_path.exists():
        raise FileNotFoundError(f"Net file not found: {net_path}")
    return net_path


def _parse_net_incoming_lanes(net_path: Path) -> Dict[str, List[str]]:
    tree = ET.parse(net_path)
    root = tree.getroot()

    junction_types: Dict[str, str] = {}
    for junction in root.findall("junction"):
        jid = junction.get("id")
        jtype = junction.get("type", "")
        if jid:
            junction_types[jid] = jtype

    lanes_by_junction: Dict[str, List[str]] = defaultdict(list)

    for edge in root.findall("edge"):
        if edge.get("function") == "internal":
            continue
        to_node = edge.get("to")
        if not to_node:
            continue
        if junction_types.get(to_node) == "internal":
            continue
        for lane in edge.findall("lane"):
            lane_id = lane.get("id")
            if lane_id:
                lanes_by_junction[to_node].append(lane_id)

    # Remove junctions without any lanes (just in case)
    return {jid: lanes for jid, lanes in lanes_by_junction.items() if lanes}


def _build_lane_index(lanes_by_junction: Dict[str, List[str]]) -> List[str]:
    all_lanes = set()
    for lanes in lanes_by_junction.values():
        all_lanes.update(lanes)
    return sorted(all_lanes)


def _safe_float(value: float | None) -> float:
    return float(value) if value is not None else 0.0


def collect_metrics(
    config_path: Path,
    sumo_binary: str,
    gui: bool,
    output_dir: Path,
    sample_interval: int,
    end_time: float | None,
    queue_speed_threshold: float,
    flush_every: int,
) -> None:
    traci = _import_traci()

    config_path = config_path.resolve()
    net_path = _parse_sumocfg_net_file(config_path)

    lanes_by_junction = _parse_net_incoming_lanes(net_path)
    tracked_lanes = _build_lane_index(lanes_by_junction)

    if not tracked_lanes:
        raise RuntimeError("No incoming lanes detected in network")

    output_dir.mkdir(parents=True, exist_ok=True)
    lane_csv_path = output_dir / "lane_metrics.csv"
    junction_csv_path = output_dir / "junction_metrics.csv"

    # Resolve SUMO binary
    binary = sumo_binary
    if gui and sumo_binary == "sumo":
        binary = "sumo-gui"
    if not gui and sumo_binary == "sumo-gui":
        binary = "sumo"

    sumo_cmd = [binary, "-c", str(config_path)]
    if end_time is not None:
        sumo_cmd += ["--end", str(end_time)]

    traci.start(sumo_cmd)

    lane_ids_in_sim = set(traci.lane.getIDList())

    lane_headers = [
        "wall_time",
        "sim_time",
        "step",
        "lane_id",
        "veh_count",
        "halt_count",
        "queue_length_m",
        "mean_speed",
        "occupancy",
        "avg_waiting_time",
        "avg_time_loss",
        "stop_events",
        "type_counts_json",
    ]

    junction_headers = [
        "wall_time",
        "sim_time",
        "step",
        "junction_id",
        "veh_count",
        "halt_count",
        "queue_length_m",
        "mean_speed",
        "occupancy",
        "avg_waiting_time",
        "avg_time_loss",
        "stop_events",
        "type_counts_json",
    ]

    prev_speed: Dict[str, float] = {}
    lane_stop_events: Dict[str, int] = {lane_id: 0 for lane_id in tracked_lanes}

    rows_since_flush = 0

    with lane_csv_path.open("w", newline="") as lane_csv, junction_csv_path.open("w", newline="") as junction_csv:
        lane_writer = csv.writer(lane_csv)
        junction_writer = csv.writer(junction_csv)
        lane_writer.writerow(lane_headers)
        junction_writer.writerow(junction_headers)

        step_index = 0
        try:
            while traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()
                sim_time = traci.simulation.getTime()

                if end_time is not None and sim_time >= end_time:
                    break

                # Collect per-vehicle data once per step
                veh_ids = traci.vehicle.getIDList()
                veh_speed: Dict[str, float] = {}
                veh_lane: Dict[str, str] = {}
                veh_type: Dict[str, str] = {}
                veh_wait: Dict[str, float] = {}
                veh_loss: Dict[str, float] = {}
                veh_len: Dict[str, float] = {}
                veh_gap: Dict[str, float] = {}

                for vid in veh_ids:
                    speed = traci.vehicle.getSpeed(vid)
                    lane_id = traci.vehicle.getLaneID(vid)

                    veh_speed[vid] = speed
                    veh_lane[vid] = lane_id
                    veh_type[vid] = traci.vehicle.getTypeID(vid)
                    veh_wait[vid] = traci.vehicle.getWaitingTime(vid)
                    veh_loss[vid] = traci.vehicle.getTimeLoss(vid)
                    veh_len[vid] = traci.vehicle.getLength(vid)
                    veh_gap[vid] = traci.vehicle.getMinGap(vid)

                    if lane_id in lane_stop_events:
                        prev = prev_speed.get(vid, speed)
                        if prev > queue_speed_threshold and speed <= queue_speed_threshold:
                            lane_stop_events[lane_id] += 1

                    prev_speed[vid] = speed

                for vid in traci.simulation.getArrivedIDList():
                    prev_speed.pop(vid, None)

                # Map vehicles to lanes
                lane_vehicle_ids: Dict[str, List[str]] = {lane_id: [] for lane_id in tracked_lanes}
                for vid, lane_id in veh_lane.items():
                    if lane_id in lane_vehicle_ids:
                        lane_vehicle_ids[lane_id].append(vid)

                if step_index % sample_interval == 0:
                    wall_time = time.time()

                    lane_metrics: Dict[str, Dict[str, float | int | str]] = {}
                    lane_stop_snapshot: Dict[str, int] = {}

                    for lane_id in tracked_lanes:
                        lane_vids = lane_vehicle_ids.get(lane_id, [])
                        veh_count = len(lane_vids)

                        if veh_count > 0:
                            halt_count = sum(1 for v in lane_vids if veh_speed[v] <= queue_speed_threshold)
                            queue_length = sum(
                                veh_len[v] + veh_gap[v]
                                for v in lane_vids
                                if veh_speed[v] <= queue_speed_threshold
                            )
                            mean_speed = sum(veh_speed[v] for v in lane_vids) / veh_count
                            avg_wait = sum(veh_wait[v] for v in lane_vids) / veh_count
                            avg_loss = sum(veh_loss[v] for v in lane_vids) / veh_count
                            type_counts = Counter(veh_type[v] for v in lane_vids)
                        else:
                            halt_count = 0
                            queue_length = 0.0
                            mean_speed = 0.0
                            avg_wait = 0.0
                            avg_loss = 0.0
                            type_counts = Counter()

                        occupancy = _safe_float(traci.lane.getLastStepOccupancy(lane_id)) if lane_id in lane_ids_in_sim else 0.0
                        stop_events = lane_stop_events.get(lane_id, 0)

                        lane_stop_snapshot[lane_id] = stop_events

                        lane_metrics[lane_id] = {
                            "veh_count": veh_count,
                            "halt_count": halt_count,
                            "queue_length": queue_length,
                            "mean_speed": mean_speed,
                            "occupancy": occupancy,
                            "avg_wait": avg_wait,
                            "avg_loss": avg_loss,
                            "stop_events": stop_events,
                            "type_counts": json.dumps(type_counts),
                        }

                        lane_writer.writerow(
                            [
                                wall_time,
                                sim_time,
                                step_index,
                                lane_id,
                                veh_count,
                                halt_count,
                                round(queue_length, 3),
                                round(mean_speed, 3),
                                round(occupancy, 3),
                                round(avg_wait, 3),
                                round(avg_loss, 3),
                                stop_events,
                                json.dumps(type_counts),
                            ]
                        )

                        lane_stop_events[lane_id] = 0

                    for junction_id, lanes in lanes_by_junction.items():
                        junc_vids: List[str] = []
                        for lane_id in lanes:
                            junc_vids.extend(lane_vehicle_ids.get(lane_id, []))

                        if junc_vids:
                            veh_count = len(junc_vids)
                            halt_count = sum(1 for v in junc_vids if veh_speed[v] <= queue_speed_threshold)
                            queue_length = sum(
                                veh_len[v] + veh_gap[v]
                                for v in junc_vids
                                if veh_speed[v] <= queue_speed_threshold
                            )
                            mean_speed = sum(veh_speed[v] for v in junc_vids) / veh_count
                            avg_wait = sum(veh_wait[v] for v in junc_vids) / veh_count
                            avg_loss = sum(veh_loss[v] for v in junc_vids) / veh_count
                            type_counts = Counter(veh_type[v] for v in junc_vids)
                        else:
                            veh_count = 0
                            halt_count = 0
                            queue_length = 0.0
                            mean_speed = 0.0
                            avg_wait = 0.0
                            avg_loss = 0.0
                            type_counts = Counter()

                        occ_values = [
                            _safe_float(traci.lane.getLastStepOccupancy(lane_id))
                            for lane_id in lanes
                            if lane_id in lane_ids_in_sim
                        ]
                        occupancy = sum(occ_values) / len(occ_values) if occ_values else 0.0

                        stop_events = sum(lane_stop_snapshot.get(lane_id, 0) for lane_id in lanes)

                        junction_writer.writerow(
                            [
                                wall_time,
                                sim_time,
                                step_index,
                                junction_id,
                                veh_count,
                                halt_count,
                                round(queue_length, 3),
                                round(mean_speed, 3),
                                round(occupancy, 3),
                                round(avg_wait, 3),
                                round(avg_loss, 3),
                                stop_events,
                                json.dumps(type_counts),
                            ]
                        )

                    rows_since_flush += 1
                    if rows_since_flush >= flush_every:
                        lane_csv.flush()
                        junction_csv.flush()
                        rows_since_flush = 0

                step_index += 1

        finally:
            traci.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect real-time SUMO metrics per lane and per junction",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--config", required=True, help="Path to SUMO .sumocfg file")
    parser.add_argument("--sumo-binary", default="sumo", help="SUMO binary (sumo or sumo-gui)")
    parser.add_argument("--gui", action="store_true", help="Run with SUMO-GUI")
    parser.add_argument("--output-dir", default="outputs/metrics", help="Output directory for CSV files")
    parser.add_argument("--sample-interval", type=int, default=1, help="Collect metrics every N steps")
    parser.add_argument("--end", type=float, default=None, help="End time of simulation (seconds)")
    parser.add_argument("--queue-speed-threshold", type=float, default=0.1, help="Speed threshold for queues/stops")
    parser.add_argument("--flush-every", type=int, default=20, help="Flush CSV buffers every N samples")

    args = parser.parse_args()

    config_path = Path(args.config)
    output_dir = Path(args.output_dir)

    collect_metrics(
        config_path=config_path,
        sumo_binary=args.sumo_binary,
        gui=args.gui,
        output_dir=output_dir,
        sample_interval=max(1, args.sample_interval),
        end_time=args.end,
        queue_speed_threshold=args.queue_speed_threshold,
        flush_every=max(1, args.flush_every),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
