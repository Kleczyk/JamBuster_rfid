#!/usr/bin/env python3
"""
Trim SUMO tlLogic <phase state="..."/> to max(connection@linkIndex)+1 per tls.
Fixes: Warning: Unused states in tlLogic ... after tl-index N

Usage (z korzenia JamBuster_rfid):
  uv run python scripts/fix_sumo_tl_phases.py JamBuster/src/map_p05/map.net.xml
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def max_link_index_per_tls(root: ET.Element) -> dict[str, int]:
    out: dict[str, int] = {}
    for conn in root.iter("connection"):
        tl = conn.get("tl")
        li = conn.get("linkIndex")
        if tl is None or li is None:
            continue
        try:
            idx = int(li)
        except ValueError:
            continue
        out[tl] = max(out.get(tl, -1), idx)
    return out


def fix_net(path: Path, dry_run: bool = False) -> tuple[int, int]:
    tree = ET.parse(path)
    root = tree.getroot()
    max_link = max_link_index_per_tls(root)
    if not max_link:
        raise SystemExit(
            f"{path.resolve()}: brak <connection tl=... linkIndex=...> — "
            "to nie wygląda na map.net.xml SUMO albo ścieżka jest zła."
        )
    trimmed = 0
    tls_touched = 0

    for tllogic in root.iter("tlLogic"):
        tid = tllogic.get("id")
        if not tid or tid not in max_link:
            continue
        n = max_link[tid] + 1
        changed_here = False
        for phase in tllogic.findall("phase"):
            st = phase.get("state")
            if not st:
                continue
            if len(st) > n:
                phase.set("state", st[:n])
                trimmed += 1
                changed_here = True
            elif len(st) < n:
                phase.set("state", st + "r" * (n - len(st)))
                trimmed += 1
                changed_here = True
        if changed_here:
            tls_touched += 1

    if not dry_run and trimmed:
        tree.write(str(path), encoding="UTF-8", xml_declaration=True)
    return tls_touched, trimmed


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("net_file", type=Path, help="ścieżka do map.net.xml")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    path = args.net_file.resolve()
    if not path.is_file():
        print(f"Błąd: plik nie istnieje: {path}", file=sys.stderr)
        return 1
    tls_n, phase_n = fix_net(path, dry_run=args.dry_run)
    if phase_n == 0:
        print(f"{path}: OK — nic do zmiany (fazy już zgodne z linkIndex lub sieć już poprawiona).")
    else:
        print(f"{path}: zaktualizowano {phase_n} faz w {tls_n} sygnalizacjach (dry_run={args.dry_run}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
