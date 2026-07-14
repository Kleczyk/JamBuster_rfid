#!/usr/bin/env python3
"""Figura z REALNYCH danych wygenerowanego datasetu: sygnatura RFID na pasach
zamkniętych vs otwartych w funkcji czasu oraz oś czasu etykiet (onset anomalii).

  uv run python grid_rfid/make_dataset_figure.py \
      --data datasets/grid_rfid_sample --out article/grid_rfid_dataset/figures/dataset_signature.png
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

matplotlib.rcParams.update({
    "font.family": "serif", "font.size": 10.5, "axes.titlesize": 11,
    "axes.labelsize": 10.5, "mathtext.fontset": "cm", "savefig.dpi": 300,
})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    man = json.load(open(os.path.join(args.data, "manifest.json")))
    a = man["args"]
    L, stride, delta = a["window"], a["stride"], a["delta"]

    # zbierz okna z val+test (epizody z anomaliami)
    parts = {}
    for sp in ("val", "test", "train"):
        p = os.path.join(args.data, f"{sp}.npz")
        if os.path.exists(p):
            z = np.load(p)
            if z["X"].shape[0]:
                parts[sp] = (z["X"], z["Y"], z["episode"])

    # wybierz epizod z anomalią o najmniejszej liczbie zamkniętych krawędzi i onset>0
    cand = [e for e in man["episodes"] if e["closed_edges"] and min(e["closure_t0"]) > 5]
    cand.sort(key=lambda e: (len(e["closed_edges"]), min(e["closure_t0"])))
    ep = cand[0]
    idx = ep["idx"]; onset = float(min(ep["closure_t0"]))

    X = Y = None
    for sp, (Xs, Ys, E) in parts.items():
        m = E == idx
        if m.any():
            X, Y = Xs[m], Ys[m]
            break

    W = X.shape[0]
    last = X[:, -1, :].reshape(W, 72, 3).sum(-1)        # (W, 72) zliczenia per pas, koniec okna
    closed = Y.max(0) > 0.5                              # pasy kiedykolwiek zamknięte w epizodzie
    t = np.array([(L + j * stride) * delta for j in range(W)], dtype=float)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 4.4),
                                   gridspec_kw={"width_ratios": [1.05, 1.0]})

    # (a) sygnatura: zliczenia na pasach zamkniętych vs otwartych
    axL.plot(t, last[:, closed].mean(1), color="#d62728", lw=2.0, marker="o", ms=3,
             label=f"pasy zamknięte (n={int(closed.sum())})")
    axL.plot(t, last[:, ~closed].mean(1), color="#2ca02c", lw=2.0, marker="o", ms=3,
             label=f"pasy otwarte (n={int((~closed).sum())})")
    axL.axvline(onset, color="0.4", ls="--", lw=1.2)
    axL.text(onset + 5, axL.get_ylim()[1] * 0.9, "onset zamknięcia", fontsize=8, color="0.3")
    axL.set_xlabel("czas symulacji [s]"); axL.set_ylabel("śr. zliczenia RFID / okno Δt")
    axL.set_title(f"(a) Sygnatura RFID — epizod {idx} (zamknięte: {ep['closed_edges']})")
    axL.legend(fontsize=8); axL.margins(x=0.02)

    # (b) oś czasu etykiet: tylko pasy zamknięte (czytelność) + kilka otwartych
    show = list(np.where(closed)[0]) + list(np.where(~closed)[0][:8])
    M = Y[:, show].T                                    # (n_show, W)
    axR.imshow(M, aspect="auto", cmap="Reds", vmin=0, vmax=1,
               extent=[t[0], t[-1], len(show) - 0.5, -0.5], interpolation="nearest")
    axR.axvline(onset, color="0.4", ls="--", lw=1.2)
    axR.set_yticks(range(len(show)))
    axR.set_yticklabels([f"pas {i}" + (" *" if closed[i] else "") for i in show], fontsize=7)
    axR.set_xlabel("czas symulacji [s]"); axR.set_ylabel("indeks pasa")
    axR.set_title("(b) Etykieta ground-truth $y_t$ (czerwony = anomalia; * = zamknięty)")

    fig.tight_layout()
    fig.savefig(args.out, dpi=300)
    print(f"figure: {args.out} | episode {idx} | closed lanes {int(closed.sum())} | onset {onset:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
