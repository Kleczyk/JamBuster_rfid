"""Demo "wyscig klas": prosta droga z 6 rownoleglymi pasami, na kazdym pasie
jeden typ pojazdu z class setu. Pojazdy ruszaja razem, zatrzymuja sie na
czerwonym swietle w polowie drogi, po pauzie dostaja zielone i startuja
jednoczesnie — widac roznice w przyspieszeniu/predkosci klas (ev vs trailer).
Po kazdym zielonym konsola drukuje ranking czasu przejechania pierwszych 50 m.

  uv run python -m grid_rfid.class_race                  # GUI, 3 rundy
  uv run python -m grid_rfid.class_race --rounds 1 --binary sumo   # test headless
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", "/usr/share/sumo"), "tools"))
import traci  # noqa: E402
from traci.exceptions import FatalTraCIError, TraCIException  # noqa: E402
from sumolib.miscutils import getFreeSocketPort  # noqa: E402

from .vehicle_classes import get_class_set

APPROACH_M = 300.0   # A -> M (swiatlo)
EXIT_M = 500.0       # M -> B
SPRINT_M = 50.0      # odcinek pomiaru po zielonym


def build_net(out_dir: str, n_lanes: int) -> str:
    """Generate a straight 2-edge road with a traffic light at node M."""
    net = os.path.join(out_dir, "race.net.xml")
    nod = os.path.join(out_dir, "race.nod.xml")
    edg = os.path.join(out_dir, "race.edg.xml")
    with open(nod, "w", encoding="utf-8") as f:
        f.write(f"""<nodes>
  <node id="A" x="0" y="0" type="priority"/>
  <node id="M" x="{APPROACH_M:.0f}" y="0" type="traffic_light"/>
  <node id="B" x="{APPROACH_M + EXIT_M:.0f}" y="0" type="priority"/>
</nodes>
""")
    with open(edg, "w", encoding="utf-8") as f:
        f.write(f"""<edges>
  <edge id="AM" from="A" to="M" numLanes="{n_lanes}" speed="15"/>
  <edge id="MB" from="M" to="B" numLanes="{n_lanes}" speed="15"/>
</edges>
""")
    subprocess.run(["netconvert", "-n", nod, "-e", edg, "-o", net,
                    "--no-turnarounds", "true"], check=True,
                   capture_output=True, text=True)
    return net


def write_routes(out_dir: str, cs) -> str:
    path = os.path.join(out_dir, "race.rou.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write("<routes>\n")
        f.write(cs.vtype_xml())
        f.write('  <route id="r" edges="AM MB"/>\n')
        f.write("</routes>\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--class-set", default="v2")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--pause", type=float, default=10.0,
                    help="postoj na czerwonym po zatrzymaniu wszystkich [s]")
    ap.add_argument("--delay", type=float, default=100.0, help="GUI ms/krok")
    ap.add_argument("--out", default="datasets/class_race")
    ap.add_argument("--binary", default="sumo-gui")
    args = ap.parse_args()

    cs = get_class_set(args.class_set)
    n = cs.n_classes
    os.makedirs(args.out, exist_ok=True)
    net = build_net(args.out, n)
    routes = write_routes(args.out, cs)

    cmd = [args.binary, "-n", net, "-r", routes, "--step-length", "0.2",
           "--no-step-log", "true", "--no-warnings", "true",
           "--duration-log.disable", "true"]
    if "gui" in args.binary:
        cmd += ["--start", "true", "--delay", str(args.delay)]
    traci.start(cmd, port=getFreeSocketPort(), numRetries=10)

    tls = traci.trafficlight.getIDList()[0]
    n_links = len(traci.trafficlight.getControlledLinks(tls))
    GREEN, RED = "G" * n_links, "r" * n_links
    print(f"klasy (pas 0..{n - 1}): {', '.join(cs.classes)}")

    def step():
        traci.simulationStep()
        return traci.simulation.getTime()

    def sprint_ranking(label):
        """Po starcie: czas od zielonego do przejechania SPRINT_M per pojazd."""
        base = {v: traci.vehicle.getDistance(v) for v in traci.vehicle.getIDList()}
        t0, done = traci.simulation.getTime(), {}
        while len(done) < len(base):
            t = step()
            for v, d0 in base.items():
                if v in done:
                    continue
                try:
                    if traci.vehicle.getDistance(v) - d0 >= SPRINT_M:
                        done[v] = t - t0
                except TraCIException:      # dojechal do celu
                    done[v] = t - t0
            if t - t0 > 60:
                break
        print(f"  {label} — czas na pierwsze {SPRINT_M:.0f} m:")
        for v, dt in sorted(done.items(), key=lambda kv: kv[1]):
            print(f"    {v.split('_')[0]:<9} {dt:5.1f} s")

    try:
        for rnd in range(args.rounds):
            print(f"== RUNDA {rnd + 1}/{args.rounds} ==")
            traci.trafficlight.setRedYellowGreenState(tls, RED)
            for i, cid in enumerate(cs.classes):
                vid = f"{cid}_{rnd}"
                traci.vehicle.add(vid, "r", typeID=cid, depart="now",
                                  departLane=str(i), departSpeed="0")
            step()
            for i, cid in enumerate(cs.classes):
                vid = f"{cid}_{rnd}"
                if vid in traci.vehicle.getIDList():
                    traci.vehicle.setLaneChangeMode(vid, 0)   # trzymaj swoj pas
            sprint_ranking("start z miejsca")

            # dojazd do czerwonego: czekaj az wszyscy stana przed M
            while True:
                t = step()
                vehs = traci.vehicle.getIDList()
                if vehs and all(traci.vehicle.getSpeed(v) < 0.05 for v in vehs):
                    break
            print(f"  wszyscy stoja na czerwonym — pauza {args.pause:.0f} s")
            t_stop = traci.simulation.getTime()
            while step() < t_stop + args.pause:
                pass

            traci.trafficlight.setRedYellowGreenState(tls, GREEN)
            sprint_ranking("start spod swiatel")

            while traci.vehicle.getIDCount() > 0:   # dojazd do mety
                step()
    except (FatalTraCIError, TraCIException):
        print("polaczenie z SUMO przerwane (GUI zamkniete recznie?)")
    finally:
        if "gui" in args.binary and sys.stdin.isatty():
            try:
                input("Koniec — Enter zamyka GUI... ")
            except EOFError:
                pass
        try:
            traci.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
