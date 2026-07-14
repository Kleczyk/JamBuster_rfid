"""Generate labelled anomaly-localization datasets on the 3x3 RFID grid.

Produces train/val/test .npz shards of sliding-window RFID observations with
per-lane closure labels, plus a manifest.json describing every episode. Validation
and test episodes use held-out closure edges, disjoint from the training pool, so
the model is evaluated on unseen anomaly locations.

  uv run python -m grid_rfid.generate --out datasets/grid_rfid_sample \
      --train 4 --val 2 --test 2 --horizon 600
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from .scenario import load_topology, build_routes, sample_closures
from .runner import EpisodeConfig, run_episode
from .vehicle_classes import get_class_set

HERE = os.path.dirname(__file__)
DEF_NET = os.path.join(HERE, "assets", "grid3x3.net.xml")
DEF_ADD = os.path.join(HERE, "assets", "rfid_detectors.add.xml")


def _episode(topo, scen_dir, idx, *, regime, demand, closures, horizon, delta,
             window, stride, seed, class_set):
    routes = os.path.join(scen_dir, f"ep{idx:04d}.rou.xml")
    rng = np.random.default_rng(seed)
    dmeta = build_routes(topo, routes, rng, horizon, regime=demand,
                         class_set=class_set)
    cfg = EpisodeConfig(net=topo.net_path, add=DEF_ADD, routes=routes,
                        horizon=horizon, delta=delta, window=window,
                        stride=stride, seed=seed, class_set=class_set)
    res = run_episode(topo, cfg, closures)
    res["meta"] = {"idx": idx, "regime": regime, "demand": dmeta, "seed": seed,
                   "closed_edges": res["closed_edges"],
                   "closed_classes": res["closed_classes"],
                   "closure_t0": res["closure_t0"]}
    return res


def _save_split(out_dir, name, results):
    keep = [r for r in results if r["X"].shape[0] > 0]
    X = (np.concatenate([r["X"] for r in keep])
         if keep else np.zeros((0,), np.float32))
    Y = (np.concatenate([r["Y"] for r in keep])
         if keep else np.zeros((0,), np.float32))
    Yc = (np.concatenate([r["Y_class"] for r in keep])
          if keep else np.zeros((0,), np.float32))
    ep = (np.concatenate([np.full(r["X"].shape[0], r["meta"]["idx"], dtype=np.int32)
                          for r in keep])
          if keep else np.zeros((0,), np.int32))
    path = os.path.join(out_dir, f"{name}.npz")
    np.savez_compressed(path, X=X, Y=Y, Y_class=Yc, episode=ep)
    pos = float(Y.mean()) if Y.size else 0.0
    print(f"  {name}: {X.shape[0]} windows | X{X.shape} Y{Y.shape} | "
          f"frac anomalous lanes={pos:.4f} -> {path}")
    return {"name": name, "windows": int(X.shape[0]), "x_shape": list(X.shape),
            "y_shape": list(Y.shape), "anomalous_lane_fraction": pos}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--net", default=DEF_NET)
    ap.add_argument("--train", type=int, default=4)
    ap.add_argument("--val", type=int, default=2)
    ap.add_argument("--test", type=int, default=2)
    ap.add_argument("--horizon", type=float, default=600.0)
    ap.add_argument("--delta", type=int, default=5)
    ap.add_argument("--window", type=int, default=48)
    ap.add_argument("--stride", type=int, default=4)
    ap.add_argument("--healthy-frac", type=float, default=0.5,
                    help="fraction of TRAIN episodes that are healthy (no closures)")
    ap.add_argument("--seed", type=int, default=2025)
    ap.add_argument("--class-set", default="v1", choices=("v1", "v2"),
                    help="vehicle-class preset (v1 = original 3 classes)")
    ap.add_argument("--class-ban-frac", type=float, default=0.0,
                    help="fraction of anomalous episodes using class-conditional "
                         "bans instead of full closures (0 = off)")
    ap.add_argument("--n-ban-classes", type=int, nargs=2, default=(1, 2),
                    metavar=("MIN", "MAX"),
                    help="classes banned per closed edge in class-ban episodes")
    args = ap.parse_args()
    class_set = get_class_set(args.class_set)

    os.makedirs(args.out, exist_ok=True)
    scen_dir = os.path.join(args.out, "scenarios")
    os.makedirs(scen_dir, exist_ok=True)

    topo = load_topology(args.net)
    print(f"grid: {len(topo.internal_edges)} closeable internal edges | "
          f"{topo.n_lanes} monitored lanes | classes={class_set.name} "
          f"{class_set.classes} (bannable={class_set.bannable}, "
          f"ban_frac={args.class_ban_frac})")

    # held-out closure pools: split internal edges so val/test see unseen locations
    rng = np.random.default_rng(args.seed)
    edges = list(topo.internal_edges)
    rng.shuffle(edges)
    n_hold = max(1, len(edges) // 3)
    holdout = edges[:n_hold]              # val/test closures
    train_pool = edges[n_hold:]           # train closures
    print(f"closure pools: train={len(train_pool)} edges | holdout={len(holdout)} edges")

    manifest = {"args": vars(args), "n_lanes": topo.n_lanes,
                "class_set": {"name": class_set.name,
                              "classes": list(class_set.classes),
                              "mix": class_set.mix,
                              "bannable": list(class_set.bannable)},
                "train_closure_pool": train_pool, "holdout_closure_pool": holdout,
                "episodes": []}
    idx = 0

    def make(n, *, split, demand, anomalous, pool):
        nonlocal idx
        out = []
        for _ in range(n):
            seed = args.seed + 1000 + idx
            erng = np.random.default_rng(seed)
            if anomalous:
                closures = sample_closures(topo, erng, args.horizon, allowed_edges=pool,
                                           ban_frac=args.class_ban_frac,
                                           n_ban_classes=tuple(args.n_ban_classes),
                                           class_set=class_set)
            else:
                from .scenario import ClosurePlan
                closures = ClosurePlan()
            r = _episode(topo, scen_dir, idx, regime=split, demand=demand,
                         closures=closures, horizon=args.horizon, delta=args.delta,
                         window=args.window, stride=args.stride, seed=seed,
                         class_set=class_set)
            if r["X"].shape[0] == 0:  # SUMO died very early — retry once
                r = _episode(topo, scen_dir, idx, regime=split, demand=demand,
                             closures=closures, horizon=args.horizon, delta=args.delta,
                             window=args.window, stride=args.stride, seed=seed + 50000,
                             class_set=class_set)
            flag = " TRUNCATED" if r.get("truncated") else ""
            bans = ("" if all(c is None for c in r["closed_classes"])
                    else f" banned_classes={r['closed_classes']}")
            print(f"  ep{idx:04d} [{split}/{demand}] anomalous={r['anomalous']} "
                  f"closed={r['closed_edges']}{bans} windows={r['X'].shape[0]}{flag}")
            manifest["episodes"].append(r["meta"])
            out.append(r); idx += 1
        return out

    print("== TRAIN ==")
    n_healthy = int(round(args.train * args.healthy_frac))
    train = (make(n_healthy, split="train", demand="healthy", anomalous=False, pool=None)
             + make(args.train - n_healthy, split="train", demand="healthy",
                    anomalous=True, pool=train_pool))
    print("== VAL ==")
    val = make(args.val, split="val", demand="healthy", anomalous=True, pool=holdout)
    print("== TEST ==")
    test = make(args.test, split="test", demand="test", anomalous=True, pool=holdout)

    print("== SAVE ==")
    summary = [_save_split(args.out, s, r) for s, r in
               (("train", train), ("val", val), ("test", test))]
    manifest["splits"] = summary
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"manifest -> {os.path.join(args.out, 'manifest.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
