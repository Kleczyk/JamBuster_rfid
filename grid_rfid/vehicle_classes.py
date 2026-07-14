"""Vehicle-class presets for the grid_rfid pipeline.

A ClassSet defines the RFID feature layout (class order), the demand mix, the
SUMO vType kinematics, and which classes may be targeted by class-conditional
bans. Preset "v1" reproduces the original 3-class setup exactly; "v2" adds
kinematically distinct classes (EV, truck, trailer) with unique SUMO vClasses
so that per-class lane bans (`setDisallowed`) are possible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class VType:
    vclass: str            # SUMO vClass — must be unique within a ClassSet for bans
    accel: float
    decel: float
    sigma: float
    length: float
    min_gap: float
    max_speed: float
    gui_shape: str


@dataclass(frozen=True)
class ClassSet:
    name: str
    classes: Tuple[str, ...]        # order defines the feature layout (72 x K)
    mix: Dict[str, float]           # demand shares, sums to 1.0
    vtypes: Dict[str, VType]
    bannable: Tuple[str, ...]       # classes eligible for class-conditional bans
    background_mix: bool            # False = car-only background (v1 semantics)

    @property
    def n_classes(self) -> int:
        return len(self.classes)

    def vclasses_of(self, class_ids) -> list:
        return [self.vtypes[c].vclass for c in class_ids]

    def vtype_xml(self) -> str:
        lines = []
        for cid in self.classes:
            v = self.vtypes[cid]
            lines.append(
                f'  <vType id="{cid}" vClass="{v.vclass}" accel="{v.accel}" '
                f'decel="{v.decel}" sigma="{v.sigma}" length="{v.length}" '
                f'minGap="{v.min_gap}" maxSpeed="{v.max_speed}" '
                f'guiShape="{v.gui_shape}"/>\n')
        return "".join(lines)


CLASS_SET_V1 = ClassSet(
    name="v1",
    classes=("car", "bus", "delivery"),
    mix={"car": 0.80, "bus": 0.13, "delivery": 0.07},
    vtypes={
        "car": VType("passenger", 2.6, 4.5, 0.6, 5.0, 2.5, 13.9, "passenger"),
        "bus": VType("bus", 1.2, 4.0, 0.6, 12.0, 3.0, 8.3, "bus"),
        "delivery": VType("delivery", 1.5, 4.0, 0.5, 7.5, 2.5, 10.0, "delivery"),
    },
    bannable=("bus", "delivery"),
    background_mix=False,
)

CLASS_SET_V2 = ClassSet(
    name="v2",
    classes=("car", "ev", "delivery", "bus", "truck", "trailer"),
    mix={"car": 0.52, "ev": 0.18, "delivery": 0.10, "bus": 0.08,
         "truck": 0.08, "trailer": 0.04},
    vtypes={
        "car": VType("passenger", 2.6, 4.5, 0.6, 5.0, 2.5, 13.9, "passenger"),
        "ev": VType("evehicle", 3.4, 4.5, 0.4, 4.8, 2.5, 13.9, "evehicle"),
        "delivery": VType("delivery", 1.5, 4.0, 0.5, 7.5, 2.5, 10.0, "delivery"),
        "bus": VType("bus", 1.2, 4.0, 0.6, 12.0, 3.0, 8.3, "bus"),
        "truck": VType("truck", 1.0, 3.5, 0.5, 10.0, 3.0, 11.1, "truck"),
        "trailer": VType("trailer", 0.7, 3.0, 0.5, 16.5, 3.5, 11.1, "truck"),
    },
    bannable=("truck", "trailer", "delivery", "bus"),
    background_mix=True,
)

CLASS_SETS: Dict[str, ClassSet] = {"v1": CLASS_SET_V1, "v2": CLASS_SET_V2}


def get_class_set(name: str) -> ClassSet:
    try:
        return CLASS_SETS[name]
    except KeyError:
        raise SystemExit(f"unknown class set '{name}'; available: {sorted(CLASS_SETS)}")
