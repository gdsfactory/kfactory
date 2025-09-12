from pathlib import Path

import erdantic as erd

import kfactory as kf


class DSchematic(kf.schematic.TSchematic[float]):
    __doc__ = kf.Schematic.__doc__


class Schematic(kf.schematic.TSchematic[int]):
    __doc__ = kf.Schematic.__doc__


print("Generating Schematic and DSchematic diagrams...")

_f = Path(__file__).parent.parent / "source/_static"
diagram_dbu = erd.create(Schematic, terminal_models=[kf.KCLayout])
diagram_dbu.models["kfactory.layout.KCLayout"].fields = {}
diagram_dbu.draw(_f / "schematic.svg")
diagram_um = erd.create(DSchematic, terminal_models=[kf.KCLayout])
diagram_um.models["kfactory.layout.KCLayout"].fields = {}
diagram_um.draw(_f / "dschematic.svg")

print("Generated Schematic and DSchematic diagrams!")
