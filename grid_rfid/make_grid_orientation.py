#!/usr/bin/env python3
"""Mapa orientacyjna siatki 3x3 (grid_rfid): nazwy węzłów (A0..C2) oraz 12 wlotów
brzegowych z etykietą kierunkową (N1..W3), nazwą krawędzi SUMO i węzłem docelowym.
Służy jako legenda — wszystkie późniejsze oznaczenia (zamknięte krawędzie, wloty)
odnoszą się do tej mapy.

  uv run python grid_rfid/make_grid_orientation.py \
      --net grid_rfid/assets/grid3x3.net.xml \
      --out article/grid_rfid_dataset/figures/grid_orientation.png
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", "/usr/share/sumo"), "tools"))
import sumolib  # noqa: E402

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

matplotlib.rcParams.update({
    "font.family": "serif", "font.size": 10.5, "axes.titlesize": 12,
    "axes.labelsize": 10.5, "mathtext.fontset": "cm", "savefig.dpi": 300,
})

SIDE_COLOR = {"N": "#d62728", "E": "#2ca02c", "S": "#9467bd", "W": "#1f77b4"}


def inflows(net):
    b = net.getBoundary(); tol = 20.0

    def side(x, y):
        xmin, ymin, xmax, ymax = b
        if y >= ymax - tol: return "N"
        if y <= ymin + tol: return "S"
        if x >= xmax - tol: return "E"
        if x <= xmin + tol: return "W"
        return "?"

    raw = []
    for e in net.getEdges():
        if e.isSpecial():
            continue
        fn, tn = e.getFromNode(), e.getToNode()
        if fn.getType() != "traffic_light" and tn.getType() == "traffic_light":
            fx, fy = fn.getCoord(); tx, ty = tn.getCoord()
            raw.append({"side": side(fx, fy), "edge": e.getID(), "feeds": tn.getID(),
                        "fx": fx, "fy": fy, "tx": tx, "ty": ty})
    grp = defaultdict(list)
    for r in raw:
        grp[r["side"]].append(r)
    out = []
    for s in "NESW":
        key = (lambda r: r["fx"]) if s in "NS" else (lambda r: r["fy"])
        for i, r in enumerate(sorted(grp[s], key=key), 1):
            r["label"] = f"{s}{i}"; out.append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    net = sumolib.net.readNet(args.net)
    fig, ax = plt.subplots(figsize=(8.4, 8.4))

    # drogi
    for e in net.getEdges():
        if e.isSpecial():
            continue
        xs, ys = zip(*e.getShape())
        ax.plot(xs, ys, color="0.80", lw=2.4, solid_capstyle="round", zorder=1)

    # węzły z nazwami A0..C2
    tls = [n for n in net.getNodes() if n.getType() == "traffic_light"]
    ax.scatter([n.getCoord()[0] for n in tls], [n.getCoord()[1] for n in tls],
               s=420, facecolor="white", edgecolor="black", lw=1.6, zorder=4)
    for n in tls:
        x, y = n.getCoord()
        ax.text(x, y, n.getID(), ha="center", va="center", fontsize=10.5,
                fontweight="bold", zorder=5)

    # wloty: strzałka do środka + etykieta poza siatką
    for r in inflows(net):
        c = SIDE_COLOR[r["label"][0]]
        dx, dy = r["tx"] - r["fx"], r["ty"] - r["fy"]
        nrm = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux, uy = dx / nrm, dy / nrm
        x0, y0 = r["fx"], r["fy"]
        ax.annotate("", xy=(x0 + ux * 60, y0 + uy * 60), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=2.2, mutation_scale=18),
                    zorder=3)
        ax.text(x0 - ux * 42, y0 - uy * 42,
                f"$\\bf{{{r['label']}}}$\n{r['edge']}\n$\\rightarrow${r['feeds']}",
                ha="center", va="center", fontsize=8.0, color="black",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=c, lw=1.2), zorder=6)

    # kierunki świata (odsunięte poza ramki wlotów)
    ax.text(300, 700, "PÓŁNOC (N)", ha="center", fontsize=9.5, color=SIDE_COLOR["N"], fontweight="bold")
    ax.text(300, -108, "POŁUDNIE (S)", ha="center", fontsize=9.5, color=SIDE_COLOR["S"], fontweight="bold")
    ax.text(735, 300, "WSCHÓD (E)", ha="center", va="center", rotation=90, fontsize=9.5,
            color=SIDE_COLOR["E"], fontweight="bold")
    ax.text(-128, 300, "ZACHÓD (W)", ha="center", va="center", rotation=90, fontsize=9.5,
            color=SIDE_COLOR["W"], fontweight="bold")

    ax.set_aspect("equal")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
    ax.set_title("Orientacja siatki 3×3: węzły (A0–C2) i wloty brzegowe (N1–W3)")
    ax.set_xlim(-185, 795); ax.set_ylim(-135, 730)
    fig.tight_layout()
    fig.savefig(args.out, dpi=300)
    print(f"figure: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
