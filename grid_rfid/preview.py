"""Podglad GUI jednego epizodu na kracie 3x3 — ten sam popyt (korytarze+tlo)
i ta sama mechanika zamkniec (disallow przez TraCI) co w `grid_rfid.generate`,
ale w sumo-gui: pelne zamkniecia podswietlane na czerwono, zakazy klasowe na
pomaranczowo, a konsola raportuje zliczenia RFID per kanal.

  uv run python -m grid_rfid.preview --mode healthy --seed 7
  uv run python -m grid_rfid.preview --mode anomaly --seed 7
  uv run python -m grid_rfid.preview --mode anomaly --closed A1B1,B1B0 --t0 120
  # wariant 2: zakaz klasowy (np. tiry) na wskazanej krawedzi
  uv run python -m grid_rfid.preview --class-set v2 --mode anomaly \\
      --closed A1B1 --ban-classes truck,trailer --t0 120
  # wariant 2: losowe anomalie wylacznie klasowe
  uv run python -m grid_rfid.preview --class-set v2 --mode anomaly --class-ban-frac 1.0
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", "/usr/share/sumo"), "tools"))
import traci  # noqa: E402
from traci.exceptions import FatalTraCIError, TraCIException  # noqa: E402
from sumolib.miscutils import getFreeSocketPort  # noqa: E402

from .scenario import load_topology, build_routes, sample_closures, Closure, ClosurePlan
from .runner import parse_loops
from .vehicle_classes import get_class_set

HERE = os.path.dirname(__file__)
DEF_NET = os.path.join(HERE, "assets", "grid3x3.net.xml")
DEF_ADD = os.path.join(HERE, "assets", "rfid_detectors.add.xml")

RED = (255, 40, 40, 255)       # full closure
ORANGE = (255, 165, 0, 255)    # class-conditional ban


def _highlight_closure(c: Closure) -> None:
    """Draw the closed lanes inside the GUI (polygon along each lane): red for a
    full closure, orange for a class ban. Best-effort: GUI-only cosmetics."""
    color = RED if c.classes is None else ORANGE
    for lid in c.lanes:
        try:
            shape = traci.lane.getShape(lid)
            try:
                traci.polygon.add(f"closed_{lid}", shape, color, fill=False,
                                  polygonType="closure", layer=50, lineWidth=4)
            except TypeError:  # older traci without lineWidth
                traci.polygon.add(f"closed_{lid}", shape, color, fill=False,
                                  polygonType="closure", layer=50)
        except TraCIException:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["healthy", "anomaly"], default="anomaly")
    ap.add_argument("--net", default=DEF_NET)
    ap.add_argument("--out", default="datasets/gui_preview",
                    help="katalog na wygenerowany .rou.xml epizodu")
    ap.add_argument("--horizon", type=float, default=900.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--delay", type=float, default=80.0,
                    help="opoznienie GUI [ms/krok]")
    ap.add_argument("--closed", default=None,
                    help="konkretne krawedzie do zamkniecia, np. A1B1,B1B0 "
                         "(domyslnie losowane jak w generatorze)")
    ap.add_argument("--t0", type=float, default=None,
                    help="czas startu zamkniecia [s] dla --closed "
                         "(domyslnie horizon/6)")
    ap.add_argument("--n-closed", type=int, nargs=2, default=(1, 3),
                    metavar=("MIN", "MAX"))
    ap.add_argument("--class-set", default="v1", choices=("v1", "v2"),
                    help="preset klas pojazdow (v2 = 6 klas o roznej kinematyce)")
    ap.add_argument("--ban-classes", default=None,
                    help="zakaz klasowy zamiast pelnego zamkniecia dla --closed, "
                         "np. truck,trailer")
    ap.add_argument("--class-ban-frac", type=float, default=0.0,
                    help="przy losowych anomaliach: prawdopodobienstwo zakazu "
                         "klasowego zamiast pelnego zamkniecia")
    ap.add_argument("--binary", default="sumo-gui",
                    help="sumo-gui (domyslnie) lub sumo do testu headless")
    args = ap.parse_args()

    cs = get_class_set(args.class_set)
    topo = load_topology(args.net)
    rng = np.random.default_rng(args.seed)
    os.makedirs(args.out, exist_ok=True)
    routes = os.path.join(args.out,
                          f"preview_{args.mode}_{cs.name}_seed{args.seed}.rou.xml")
    dmeta = build_routes(topo, routes, rng, args.horizon, regime="healthy",
                         class_set=cs)

    ban_classes = None
    if args.ban_classes:
        ban_classes = [c.strip() for c in args.ban_classes.split(",") if c.strip()]
        bad = [c for c in ban_classes if c not in cs.classes]
        if bad:
            raise SystemExit(f"nieznane klasy: {bad}; klasy w {cs.name}: {cs.classes}")

    if args.mode == "anomaly":
        if args.closed:
            edges = [e.strip() for e in args.closed.split(",") if e.strip()]
            unknown = [e for e in edges if e not in topo.edge_lanes]
            if unknown:
                raise SystemExit(f"nieznane krawedzie: {unknown}\n"
                                 f"zamykalne wewnetrzne: {sorted(topo.internal_edges)}")
            t0 = args.t0 if args.t0 is not None else args.horizon / 6.0
            plan = ClosurePlan([Closure(e, list(topo.edge_lanes[e]), float(t0),
                                        args.horizon, ban_classes) for e in edges])
        else:
            plan = sample_closures(topo, rng, args.horizon,
                                   n_closed=tuple(args.n_closed),
                                   ban_frac=args.class_ban_frac, class_set=cs)
    else:
        plan = ClosurePlan()

    print(f"klasy ({cs.name}): {cs.classes}")
    print(f"popyt: korytarze={dmeta['corridors']} peaks={dmeta['peaks']} "
          f"flows={dmeta['n_flows']}")
    if plan.closures:
        for c in plan.closures:
            idxs = [topo.lane_index[l] for l in c.lanes if l in topo.lane_index]
            what = ("PELNE zamkniecie" if c.classes is None
                    else f"ZAKAZ klas {c.classes}")
            print(f"ANOMALIA: {what} edge={c.edge} pasy={c.lanes} "
                  f"(indeksy etykiety: {idxs}) start t0={c.t0:.0f}s -> koniec epizodu")
    else:
        print("tryb ZDROWY — zero zamkniec, etykieta y=0 dla wszystkich 72 pasow")

    loop_lane = parse_loops(DEF_ADD)
    cls_idx = {c: i for i, c in enumerate(cs.classes)}
    counts = np.zeros((topo.n_lanes, cs.n_classes))
    full_idx = sorted({topo.lane_index[l] for c in plan.closures if c.classes is None
                       for l in c.lanes if l in topo.lane_index})
    ban_lane_cols = {}  # lane idx -> lista kolumn zabronionych klas
    for c in plan.closures:
        if c.classes is not None:
            cols = [cls_idx[cid] for cid in c.classes]
            for l in c.lanes:
                li = topo.lane_index.get(l)
                if li is not None:
                    ban_lane_cols[li] = cols
    affected = set(full_idx) | set(ban_lane_cols)
    open_idx = [i for i in range(topo.n_lanes) if i not in affected]
    applied = {c.edge: False for c in plan.closures}

    cmd = [
        args.binary, "-n", args.net, "-r", routes, "-a", DEF_ADD,
        "--step-length", "1.0", "--end", str(int(args.horizon)),
        "--seed", str(args.seed), "--time-to-teleport", "300",
        "--ignore-route-errors", "true",
        "--device.rerouting.probability", "1.0",
        "--device.rerouting.period", "20",
        "--no-step-log", "true", "--no-warnings", "true",
        "--duration-log.disable", "true", "--xml-validation", "never",
    ]
    if "gui" in args.binary:
        cmd += ["--start", "true", "--delay", str(args.delay)]
    traci.start(cmd, port=getFreeSocketPort(), numRetries=10)

    try:
        t = traci.simulation.getTime()
        next_report = 150.0
        while t < args.horizon:
            for c in plan.closures:
                if (not applied[c.edge]) and t >= c.t0:
                    if c.classes is None:
                        for lid in c.lanes:
                            traci.lane.setDisallowed(lid, ["all"])
                        traci.edge.adaptTraveltime(c.edge, 1.0e6)
                        print(f"[t={t:.0f}s] ZAMKNIETO {c.edge} (czerwony) — "
                              f"ruch reroutuje sie w ~20 s")
                    else:
                        banned = cs.vclasses_of(c.classes)
                        for lid in c.lanes:
                            traci.lane.setDisallowed(lid, banned)
                        print(f"[t={t:.0f}s] ZAKAZ {c.classes} na {c.edge} "
                              f"(pomaranczowy) — reszta klas jezdzi dalej")
                    applied[c.edge] = True
                    _highlight_closure(c)
            for loop, lane in loop_lane.items():
                li = topo.lane_index.get(lane)
                if li is None:
                    continue
                for vid in traci.inductionloop.getLastStepVehicleIDs(loop):
                    try:
                        vtype = traci.vehicle.getTypeID(vid)
                    except TraCIException:
                        vtype = cs.classes[0]
                    counts[li, cls_idx.get(vtype, 0)] += 1
            traci.simulationStep()
            t = traci.simulation.getTime()
            if t >= next_report:
                msg = (f"[t={t:.0f}s] skumulowane zliczenia RFID/pas: "
                       f"otwarte={counts[open_idx].sum(axis=1).mean():.1f}")
                if full_idx:
                    msg += f" | pelne zamkniecie={counts[full_idx].sum(axis=1).mean():.1f}"
                if ban_lane_cols:
                    b = np.mean([counts[li, cols].sum()
                                 for li, cols in ban_lane_cols.items()])
                    o = np.mean([np.delete(counts[li], cols).sum()
                                 for li, cols in ban_lane_cols.items()])
                    msg += (f" | pas z zakazem: kanal zabroniony={b:.1f}, "
                            f"pozostale kanaly={o:.1f}")
                print(msg)
                next_report += 150.0
    except (FatalTraCIError, TraCIException):
        print("polaczenie z SUMO przerwane (GUI zamkniete recznie?)")
    finally:
        if "gui" in args.binary and sys.stdin.isatty():
            try:
                input("Koniec epizodu — Enter zamyka GUI... ")
            except EOFError:
                pass
        try:
            traci.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
