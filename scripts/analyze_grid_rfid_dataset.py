"""Analyze a grid_rfid dataset (.npz + manifest) and emit report figures + stats.

Computes demand/anomaly/label statistics and renders the figures referenced by
docs/RAPORT_grid_rfid_v2.md. All numbers land in <out>/stats.json so the report
is reproducible.

  uv run python scripts/analyze_grid_rfid_dataset.py \
      --dataset datasets/grid_rfid_v2 --out docs/figures/grid_rfid_v2
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grid_rfid.export_csv import reconstruct_records, episode_plan  # noqa: E402
from grid_rfid.scenario import load_topology  # noqa: E402
from grid_rfid.vehicle_classes import get_class_set  # noqa: E402

# --- palette (dataviz reference instance, light mode) ---
CAT = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948"]
SEQ = LinearSegmentedColormap.from_list(
    "seq_blue", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
INK, INK2, MUT, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": "#c3c2b7",
    "xtick.color": MUT, "ytick.color": MUT, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "figure.dpi": 150,
})


def load_all(dataset):
    with open(os.path.join(dataset, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    cs = get_class_set(manifest.get("class_set", {}).get(
        "name", manifest["args"].get("class_set", "v1")))
    topo = load_topology(manifest["args"]["net"])
    splits = {}
    for s in ("train", "val", "test"):
        with np.load(os.path.join(dataset, f"{s}.npz")) as z:
            # materialize once — each NpzFile[key] access re-decompresses
            splits[s] = {k: z[k] for k in z.files}
    return manifest, cs, topo, splits


def per_episode_records(splits, manifest, cs, topo):
    """{episode idx: dict(records (n_rec,72,K), split, plan, meta)}"""
    stride = manifest["args"]["stride"]
    horizon = float(manifest["args"]["horizon"])
    K = cs.n_classes
    out = {}
    for split, d in splits.items():
        for e in np.unique(d["episode"]):
            Xe = d["X"][d["episode"] == e]
            R = reconstruct_records(Xe, stride).reshape(-1, topo.n_lanes, K)
            meta = manifest["episodes"][int(e)]
            out[int(e)] = {"records": R, "split": split, "meta": meta,
                           "plan": episode_plan(meta, horizon, topo)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    manifest, cs, topo, splits = load_all(args.dataset)
    a = manifest["args"]
    delta, window, horizon = a["delta"], a["window"], float(a["horizon"])
    K, classes = cs.n_classes, list(cs.classes)
    eps = per_episode_records(splits, manifest, cs, topo)
    n_rec_full = int(horizon // delta)
    stats = {"args": a, "classes": classes, "mix": cs.mix}

    # ---------- 1. episode inventory ----------
    inv = {}
    for e, d in eps.items():
        m = d["meta"]
        kind = ("healthy" if not m["closed_edges"] else
                "class_ban" if any(c is not None for c in
                                   (m.get("closed_classes") or [None])) else
                "full_closure")
        inv.setdefault(d["split"], {}).setdefault(kind, 0)
        inv[d["split"]][kind] += 1
    truncated = [e for e, d in eps.items()
                 if d["records"].shape[0] < n_rec_full]
    stats["episodes"] = inv
    stats["truncated_episodes"] = truncated

    # ---------- 2. demand: per-class share + temporal profile ----------
    healthy = [d for d in eps.values() if not d["meta"]["closed_edges"]]
    Rh = np.stack([d["records"] for d in healthy
                   if d["records"].shape[0] == n_rec_full])  # (E, n_rec, 72, K)
    cls_tot = Rh.sum(axis=(0, 1, 2))
    stats["class_count_share"] = {c: round(float(v / cls_tot.sum()), 4)
                                  for c, v in zip(classes, cls_tot)}
    prof_mean = Rh.sum(axis=(2, 3)).mean(axis=0)   # (n_rec,) total counts/record
    prof_std = Rh.sum(axis=(2, 3)).std(axis=0)
    stats["profile_peak_over_min"] = round(float(prof_mean.max() / prof_mean.min()), 2)

    t_axis = (np.arange(n_rec_full) + 1) * delta / 60.0
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.fill_between(t_axis, prof_mean - prof_std, prof_mean + prof_std,
                    color=CAT[0], alpha=0.15, linewidth=0)
    ax.plot(t_axis, prof_mean, color=CAT[0], lw=2, label="średnia (±1σ) epizodów zdrowych")
    ax.set_xlabel("czas epizodu [min]")
    ax.set_ylabel("zliczenia RFID / rekord 5 s (suma 72 pasów)")
    ax.set_title("Profil popytu φ(t): szczyt w połowie epizodu", loc="left",
                 fontsize=11, color=INK)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "f1_demand_profile.png")); plt.close(fig)

    # ---------- 3. lane x class heatmap (healthy) ----------
    lane_cls = Rh.mean(axis=(0, 1))                # (72, K) mean counts/record
    fig, ax = plt.subplots(figsize=(5.2, 9.0))
    im = ax.imshow(lane_cls, aspect="auto", cmap=SEQ)
    ax.set_xticks(range(K), classes, rotation=45, ha="right")
    ax.set_yticks(range(0, 72, 4),
                  [topo.monitored_lanes[i] for i in range(0, 72, 4)], fontsize=6)
    ax.set_title("Średnie zliczenia / rekord — pas × klasa (ruch zdrowy)",
                 loc="left", fontsize=11, color=INK)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.5, label="zliczenia / 5 s")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "f2_lane_class_heatmap.png")); plt.close(fig)

    # ---------- 4. event-aligned closure signatures ----------
    PRE, POST = 24, 48  # records around t0
    sig_full, sig_ban, sig_open = [], [], []
    reroute_before, reroute_after = [], []
    for d in eps.values():
        R = d["records"]
        for c in d["plan"].closures:
            r0 = int(c.t0 // delta)
            if r0 - PRE < 0 or r0 + POST > R.shape[0]:
                continue
            lanes = [topo.lane_index[l] for l in c.lanes]
            seg = R[r0 - PRE:r0 + POST]            # (PRE+POST, 72, K)
            if c.classes is None:
                sig_full.append(seg[:, lanes, :].sum(axis=2).mean(axis=1))
            else:
                cols = [classes.index(x) for x in c.classes]
                sig_ban.append(seg[:, lanes][:, :, cols].sum(axis=2).mean(axis=1))
            open_l = [i for i in range(72) if i not in lanes]
            sig_open.append(seg[:, open_l, :].sum(axis=2).mean(axis=1))
            reroute_before.append(R[max(0, r0 - PRE):r0][:, open_l].sum(axis=(1, 2)).mean())
            reroute_after.append(R[r0:r0 + POST][:, open_l].sum(axis=(1, 2)).mean())

    off = (np.arange(-PRE, POST) + 0.5) * delta / 60.0
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for sig, color, label in ((sig_open, MUT, "pasy otwarte (tło)"),
                              (sig_full, CAT[5], "pełne zamknięcie — suma kanałów"),
                              (sig_ban, CAT[2], "zakaz klasowy — kanał zabroniony")):
        if sig:
            m = np.mean(sig, axis=0)
            ax.plot(off, m, color=color, lw=2, label=f"{label} (n={len(sig)})")
    ax.axvline(0, color=INK2, lw=1, ls="--")
    ax.annotate("t₀ zamknięcia", (0, ax.get_ylim()[1] * 0.95), fontsize=8,
                color=INK2, ha="left", xytext=(3, 0), textcoords="offset points")
    ax.set_xlabel("czas względem t₀ [min]")
    ax.set_ylabel("zliczenia / pas / rekord 5 s")
    ax.set_title("Sygnatura anomalii wokół momentu zamknięcia", loc="left",
                 fontsize=11, color=INK)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "f3_event_aligned.png")); plt.close(fig)

    stats["signature"] = {
        "full_closure_mean_before": round(float(np.mean([s[:PRE].mean() for s in sig_full])), 2) if sig_full else None,
        "full_closure_mean_after60s": round(float(np.mean([s[PRE + 12:].mean() for s in sig_full])), 2) if sig_full else None,
        "class_ban_mean_before": round(float(np.mean([s[:PRE].mean() for s in sig_ban])), 2) if sig_ban else None,
        "class_ban_mean_after60s": round(float(np.mean([s[PRE + 12:].mean() for s in sig_ban])), 2) if sig_ban else None,
        "open_lanes_mean": round(float(np.mean([s.mean() for s in sig_open])), 2) if sig_open else None,
        "reroute_open_increase_pct": round(100 * (np.mean(reroute_after) / np.mean(reroute_before) - 1), 1) if reroute_before else None,
    }

    # ---------- 5. task difficulty: zero windows on OPEN lanes ----------
    zero_share = {}
    tot_share = []
    for cix, cname in enumerate(classes):
        zw, nw = 0, 0
        for d in eps.values():
            if d["meta"]["closed_edges"]:
                continue
            R = d["records"][:, :, cix]            # (n_rec, 72)
            for s0 in range(0, R.shape[0] - window + 1, a["stride"]):
                seg = R[s0:s0 + window]
                zw += int((seg.sum(axis=0) == 0).sum()); nw += 72
        zero_share[cname] = round(zw / nw, 4) if nw else None
    for d in eps.values():
        if d["meta"]["closed_edges"]:
            continue
        R = d["records"].sum(axis=2)
        for s0 in range(0, R.shape[0] - window + 1, a["stride"]):
            tot_share.append((R[s0:s0 + window].sum(axis=0) == 0).mean())
    stats["zero_window_share_open_lanes"] = zero_share
    stats["zero_window_share_open_lanes_total"] = round(float(np.mean(tot_share)), 4)

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    vals = [100 * zero_share[c] for c in classes]
    bars = ax.bar(classes, vals, color=CAT[:K], width=0.62)
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:.0f}%", (b.get_x() + b.get_width() / 2, v), ha="center",
                    va="bottom", fontsize=9, color=INK2)
    ax.set_ylabel("% okien 48×5 s z zerowym odczytem")
    ax.set_title("Naturalne zera na pasach OTWARTYCH (ryzyko fałszywego alarmu)",
                 loc="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "f4_zero_windows.png")); plt.close(fig)

    # ---------- 6. label balance ----------
    lb = {}
    for split, d in splits.items():
        Y = d["Y"]
        lb[split] = {
            "windows": int(Y.shape[0]),
            "anomalous_window_frac": round(float((Y.max(axis=1) > 0).mean()), 4),
            "positive_lane_frac": round(float((Y > 0).mean()), 4),
            "y_values": {f"{v:g}": int(n) for v, n in
                         zip(*np.unique(Y[Y > 0], return_counts=True))},
        }
    stats["labels"] = lb

    # ---------- 7. closure coverage per edge + banned classes ----------
    edge_n, ban_n = {}, {c: 0 for c in classes}
    for m in manifest["episodes"]:
        for e_, b in zip(m["closed_edges"],
                         m.get("closed_classes") or [None] * len(m["closed_edges"])):
            edge_n[e_] = edge_n.get(e_, 0) + 1
            if b:
                for c in b:
                    ban_n[c] += 1
    hold = set(manifest["holdout_closure_pool"])
    edges_sorted = sorted(edge_n, key=edge_n.get)
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.barh(edges_sorted, [edge_n[e] for e in edges_sorted],
            color=[CAT[1] if e in hold else CAT[0] for e in edges_sorted],
            height=0.62)
    ax.set_xlabel("liczba epizodów z zamknięciem tej krawędzi")
    ax.set_title("Pokrycie krawędzi zamknięciami — pula treningowa (niebieski)\n"
                 "vs holdout val/test (morski)", loc="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "f5_closures_per_edge.png")); plt.close(fig)
    stats["closures_per_edge"] = edge_n
    stats["ban_counts_per_class"] = ban_n

    def _np(o):
        return float(o) if isinstance(o, np.floating) else int(o)

    with open(os.path.join(args.out, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2, default=_np)
    print(json.dumps(stats, ensure_ascii=False, indent=2, default=_np))
    print(f"\nfigures + stats.json -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
