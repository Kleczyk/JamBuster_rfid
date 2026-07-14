"""Export a grid_rfid .npz dataset to a portable CSV package for external teams.

The .npz stores overlapping sliding windows (L=window, stride) — heavily redundant.
This exporter reconstructs the unique per-record time series (one record = `delta`
seconds of RFID counts), recomputes exact per-record labels from the manifest, and
writes gzipped CSVs plus static metadata tables (lanes, classes, episodes) and an
English data-dictionary README. `--verify` rebuilds the original X/Y windows from
the CSVs and checks exact equality against the .npz.

  uv run python -m grid_rfid.export_csv --dataset datasets/grid_rfid_v2 \
      --out export/grid_rfid_v2_csv --verify
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import shutil
import xml.etree.ElementTree as ET

import numpy as np

from .scenario import load_topology, Closure, ClosurePlan, label_at, label_class_at
from .vehicle_classes import get_class_set

HERE = os.path.dirname(__file__)
DEF_ADD = os.path.join(HERE, "assets", "rfid_detectors.add.xml")

SPLITS = ("train", "val", "test")


# --------------------------------------------------------------------------- #
# Window -> record reconstruction
# --------------------------------------------------------------------------- #

def reconstruct_records(Xe: np.ndarray, stride: int) -> np.ndarray:
    """Rebuild the unique record series (n_rec, n_feat) from one episode's
    overlapping windows Xe (n_win, L, n_feat). Consecutive windows overlap by
    L - stride records; the overlaps must agree exactly (sanity-checked)."""
    n_win, L, n_feat = Xe.shape
    recs = [Xe[0]]
    for w in range(1, n_win):
        if not np.array_equal(Xe[w][:L - stride], Xe[w - 1][stride:]):
            raise AssertionError("window overlap mismatch — stride/window wrong?")
        recs.append(Xe[w][L - stride:])
    return np.concatenate(recs, axis=0)


def episode_plan(meta: dict, horizon: float, topo) -> ClosurePlan:
    """Rebuild the ClosurePlan of an episode from its manifest entry."""
    plan = ClosurePlan()
    closed_classes = meta.get("closed_classes") or [None] * len(meta["closed_edges"])
    for edge, t0, cls in zip(meta["closed_edges"], meta["closure_t0"], closed_classes):
        plan.closures.append(Closure(edge, list(topo.edge_lanes[edge]),
                                     float(t0), horizon, cls))
    return plan


# --------------------------------------------------------------------------- #
# CSV writers
# --------------------------------------------------------------------------- #

def _gz_writer(path):
    fh = gzip.open(path, "wt", encoding="utf-8", newline="")
    return fh, csv.writer(fh)


def export_split(split, data, manifest, topo, class_set, out_dir):
    """Write timeseries / labels / windows CSVs for one split. Returns stats."""
    args = manifest["args"]
    delta, window, stride = args["delta"], args["window"], args["stride"]
    horizon = float(args["horizon"])
    X, ep_ids = data["X"], data["episode"]
    K = class_set.n_classes
    n_lanes = topo.n_lanes

    ts_path = os.path.join(out_dir, f"timeseries_{split}.csv.gz")
    lb_path = os.path.join(out_dir, f"labels_records_{split}.csv.gz")
    win_path = os.path.join(out_dir, f"windows_{split}.csv.gz")

    ts_fh, ts_w = _gz_writer(ts_path)
    lb_fh, lb_w = _gz_writer(lb_path)
    win_fh, win_w = _gz_writer(win_path)

    ts_w.writerow(["episode", "record", "t_end_s"]
                  + [f"cnt__{lane}__{cls}" for lane in topo.monitored_lanes
                     for cls in class_set.classes])
    lb_w.writerow(["episode", "record", "t_end_s", "lane_index", "lane_id",
                   "class", "y_class", "y_lane"])
    win_w.writerow(["window_id", "episode", "start_record", "end_record", "t_end_s"])

    n_rec_total, n_lbl_rows, win_id = 0, 0, 0
    for e in np.unique(ep_ids):
        rows = np.where(ep_ids == e)[0]
        Xe = X[rows]                                   # (n_win, L, n_feat)
        R = reconstruct_records(Xe, stride)            # (n_rec, n_feat)
        n_rec = R.shape[0]
        n_rec_total += n_rec
        meta = manifest["episodes"][int(e)]
        plan = episode_plan(meta, horizon, topo)

        for r in range(n_rec):
            t_end = (r + 1) * delta
            ts_w.writerow([int(e), r, t_end]
                          + [f"{v:g}" for v in R[r]])
            yc = label_class_at(topo, plan, t_end, class_set)   # (72, K)
            if yc.any():
                yl = label_at(topo, plan, t_end, class_set)     # (72,)
                for li, ci in zip(*np.nonzero(yc)):
                    lb_w.writerow([int(e), r, t_end, int(li),
                                   topo.monitored_lanes[li],
                                   class_set.classes[ci], 1, f"{yl[li]:g}"])
                    n_lbl_rows += 1

        for w, _ in enumerate(rows):
            end_rec = window + w * stride              # exclusive
            win_w.writerow([win_id, int(e), end_rec - window, end_rec - 1,
                            end_rec * delta])
            win_id += 1

    for fh in (ts_fh, lb_fh, win_fh):
        fh.close()
    return {"split": split, "episodes": int(len(np.unique(ep_ids))),
            "records": n_rec_total, "windows": int(X.shape[0]),
            "label_rows": n_lbl_rows}


def export_static(manifest, topo, class_set, out_dir, add_path=DEF_ADD):
    # lanes.csv — detector positions from the additional file
    det_pos = {}
    for el in ET.parse(add_path).getroot().iter("inductionLoop"):
        det_pos[el.get("lane")] = float(el.get("pos"))
    import sumolib
    net = sumolib.net.readNet(manifest["args"]["net"])
    with open(os.path.join(out_dir, "lanes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lane_index", "lane_id", "edge", "from_node", "to_node",
                    "length_m", "detector_pos_m"])
        for i, lid in enumerate(topo.monitored_lanes):
            eid = lid.rsplit("_", 1)[0]
            e = net.getEdge(eid)
            w.writerow([i, lid, eid, e.getFromNode().getID(), e.getToNode().getID(),
                        round(e.getLanes()[0].getLength(), 2), det_pos.get(lid, "")])

    with open(os.path.join(out_dir, "classes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "sumo_vclass", "mix_share", "accel_ms2", "decel_ms2",
                    "length_m", "max_speed_ms", "bannable"])
        for cid in class_set.classes:
            v = class_set.vtypes[cid]
            w.writerow([cid, v.vclass, class_set.mix[cid], v.accel, v.decel,
                        v.length, v.max_speed, int(cid in class_set.bannable)])

    with open(os.path.join(out_dir, "episodes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["episode", "split", "demand_regime", "anomalous", "seed",
                    "corridors", "corridor_peaks_vph", "closed_edges",
                    "banned_classes", "closure_t0_s"])
        for m in manifest["episodes"]:
            closed = m["closed_edges"]
            bans = m.get("closed_classes") or [None] * len(closed)
            w.writerow([m["idx"], m["regime"], m["demand"]["regime"],
                        int(bool(closed)), m["seed"],
                        "|".join(m["demand"]["corridors"]),
                        "|".join(f"{v:g}" for v in m["demand"]["peaks"].values()),
                        "|".join(closed),
                        "|".join("FULL" if b is None else "+".join(b) for b in bans),
                        "|".join(f"{t:g}" for t in m["closure_t0"])])


def write_readme(out_dir, manifest, class_set, stats):
    a = manifest["args"]
    K = class_set.n_classes
    rows = "\n".join(
        f"| {s['split']} | {s['episodes']} | {s['records']} | {s['windows']} | "
        f"{s['label_rows']} |" for s in stats)
    txt = f"""# grid_rfid — lane-level anomaly localization dataset (SUMO, RFID counts)

RFID-style vehicle counts from 72 induction-loop detectors on a signalized 3×3
grid (SUMO {a.get('net', '')}), with **lane-level anomaly labels**: randomly
closed internal approach edges (full closures) and **class-conditional bans**
(a vehicle class forbidden on an edge — only that class's channel goes dark).

Generated with `grid_rfid.generate` (JamBuster_rfid repo), seed {a['seed']}:
episode horizon {a['horizon']:.0f} s, one record per {a['delta']} s, sliding
windows of {a['window']} records with stride {a['stride']}.
Class set **{class_set.name}**: {', '.join(class_set.classes)} (see `classes.csv`).

| split | episodes | records | windows | label rows |
|---|---|---|---|---|
{rows}

## Files

- **`timeseries_<split>.csv.gz`** — the raw data. One row = one {a['delta']}-second
  record of one episode: `episode, record, t_end_s` + {72 * K} count columns
  `cnt__<lane_id>__<class>`. Counts are **detector presence-seconds** within the
  record (a vehicle standing on the loop for 3 s counts 3), so slow/long classes
  read higher than their trip share. Records of an episode are contiguous
  (`record` = 0,1,2,…; `t_end_s` = end of the record's counting interval).
- **`labels_records_<split>.csv.gz`** — sparse ground truth. One row per
  (record, lane, class) **with an active anomaly only**: `y_class` = 1 when that
  class is banned on that lane at `t_end_s`; `y_lane` ∈ (0,1] is the lane-level
  target = demand-mix share of the banned classes (full closure = 1.0). Rows are
  emitted from the closure start `t0` until the episode end. Anything not listed
  is healthy (label 0).
- **`windows_<split>.csv.gz`** — mapping to the canonical training windows:
  `window_id, episode, start_record, end_record` (inclusive), `t_end_s`. A window
  input is the {a['window']}×{72 * K} slice of `timeseries` rows
  `start_record..end_record`; its target is the label state at `end_record`.
- **`episodes.csv`** — per-episode metadata: split, demand regime, seed, heavy
  corridors + their peak rates (veh/h), closed edges, banned classes
  (`FULL` = full closure), closure start times. `|`-separated lists.
- **`lanes.csv`** — the 72 monitored lanes: stable `lane_index` (column order of
  the label matrices), SUMO lane/edge ids, geometry, detector position.
- **`classes.csv`** — vehicle classes: SUMO vClass, demand-mix share, kinematics,
  whether the class can be targeted by a ban.
- **`manifest.json`** — full generation record (per-episode seeds, closure pools).

## Splits & evaluation protocol

Anomaly locations are **disjoint between train and val/test**: closures in train
episodes come from a 16-edge pool, val/test only from the held-out 8-edge pool
(`manifest.json`: `train_closure_pool` / `holdout_closure_pool`). Val/test
episodes are all anomalous; train mixes healthy and anomalous episodes
(healthy fraction {a['healthy_frac']}). Test episodes additionally use a fixed,
held-out demand pattern. Evaluate localization per lane (and per class for
class bans) on unseen anomaly locations.

## Rebuilding training windows (pandas)

```python
import pandas as pd, numpy as np
ts   = pd.read_csv("timeseries_train.csv.gz")
wins = pd.read_csv("windows_train.csv.gz")
lbl  = pd.read_csv("labels_records_train.csv.gz")
feat = [c for c in ts.columns if c.startswith("cnt__")]
lanes = pd.read_csv("lanes.csv"); classes = pd.read_csv("classes.csv")
li = dict(zip(lanes.lane_id, lanes.lane_index))
ci = dict(zip(classes["class"], range(len(classes))))
by_ep = {{e: g.reset_index(drop=True) for e, g in ts.groupby("episode")}}
X = np.stack([by_ep[w.episode].loc[w.start_record:w.end_record, feat].to_numpy()
              for w in wins.itertuples()])          # (N, {a['window']}, {72 * K})
Y = np.zeros((len(wins), 72)); Yc = np.zeros((len(wins), 72, {K}))
end_lbl = lbl.merge(wins, left_on=["episode", "record"],
                    right_on=["episode", "end_record"])
for _, r in end_lbl.iterrows():
    Y[r["window_id"], li[r["lane_id"]]] = r["y_lane"]
    Yc[r["window_id"], li[r["lane_id"]], ci[r["class"]]] = 1
```

(Or simply use the original `.npz` files if numpy is an option — this CSV package
round-trips to them exactly.)

## Known characteristics

- Counts are presence-seconds, not unique passages (consistent across time, so
  relative changes are meaningful).
- An open lane can legitimately read 0 for a while (no arrivals) — telling that
  apart from a closure requires temporal + spatial context; that is the task.
- Closures force rerouting (SUMO rerouting device, 20 s period): expect traffic
  increases on alternative approaches after `t0`.
"""
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(txt)


# --------------------------------------------------------------------------- #
# Verification: rebuild X/Y windows from the CSVs, compare to npz
# --------------------------------------------------------------------------- #

def verify_split(split, data, out_dir, topo, class_set, manifest):
    import pandas as pd
    args = manifest["args"]
    delta, window, stride = args["delta"], args["window"], args["stride"]
    K = class_set.n_classes

    ts = pd.read_csv(os.path.join(out_dir, f"timeseries_{split}.csv.gz"))
    wins = pd.read_csv(os.path.join(out_dir, f"windows_{split}.csv.gz"))
    lbl = pd.read_csv(os.path.join(out_dir, f"labels_records_{split}.csv.gz"))

    feat_cols = [c for c in ts.columns if c.startswith("cnt__")]
    X_ref, Y_ref, Yc_ref, ep_ref = (data["X"], data["Y"], data["Y_class"],
                                    data["episode"])
    lane_pos = {lid: i for i, lid in enumerate(topo.monitored_lanes)}
    cls_pos = {c: i for i, c in enumerate(class_set.classes)}

    ok = True
    for w_i, row in wins.iterrows():
        e, s, t = int(row["episode"]), int(row["start_record"]), int(row["end_record"])
        sub = ts[(ts["episode"] == e) & (ts["record"] >= s) & (ts["record"] <= t)]
        Xw = sub[feat_cols].to_numpy(dtype=np.float32)
        if not np.array_equal(Xw, X_ref[w_i]):
            print(f"  MISMATCH X: {split} window {w_i}"); ok = False
        # labels at the window-end record
        yc = np.zeros((topo.n_lanes, K), np.float32)
        y = np.zeros(topo.n_lanes, np.float32)
        sub_l = lbl[(lbl["episode"] == e) & (lbl["record"] == t)]
        for _, lr in sub_l.iterrows():
            yc[lane_pos[lr["lane_id"]], cls_pos[lr["class"]]] = 1.0
            y[lane_pos[lr["lane_id"]]] = lr["y_lane"]
        if not (np.array_equal(yc, Yc_ref[w_i]) and np.allclose(y, Y_ref[w_i])):
            print(f"  MISMATCH Y: {split} window {w_i}"); ok = False
    print(f"  verify {split}: {'OK' if ok else 'FAILED'} "
          f"({len(wins)} windows, exact X + labels)")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", required=True, help="dir with *.npz + manifest.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify", action="store_true",
                    help="rebuild windows from CSVs and compare to the .npz")
    args = ap.parse_args()

    with open(os.path.join(args.dataset, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    cs_name = manifest.get("class_set", {}).get("name",
                                                manifest["args"].get("class_set", "v1"))
    class_set = get_class_set(cs_name)
    topo = load_topology(manifest["args"]["net"])
    os.makedirs(args.out, exist_ok=True)

    print(f"dataset: {args.dataset} | class_set={cs_name} "
          f"({class_set.n_classes} classes) | {topo.n_lanes} lanes")
    stats = []
    datas = {}
    for split in SPLITS:
        datas[split] = np.load(os.path.join(args.dataset, f"{split}.npz"))
        s = export_split(split, datas[split], manifest, topo, class_set, args.out)
        stats.append(s)
        print(f"  {split}: {s['episodes']} episodes | {s['records']} records | "
              f"{s['windows']} windows | {s['label_rows']} label rows")

    export_static(manifest, topo, class_set, args.out)
    shutil.copy(os.path.join(args.dataset, "manifest.json"),
                os.path.join(args.out, "manifest.json"))
    write_readme(args.out, manifest, class_set, stats)
    print(f"static tables + manifest + README.md -> {args.out}")

    if args.verify:
        print("verification (CSV -> windows -> compare with .npz):")
        all_ok = all(verify_split(s, datas[s], args.out, topo, class_set, manifest)
                     for s in SPLITS)
        if not all_ok:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
