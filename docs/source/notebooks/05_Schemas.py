# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Multi - KCLayout / PDK

# %% [markdown]
# You can also use multiple KCLayout objects as PDKs or Libraries of KCells and parametric KCell-Functions

# %% [markdown]
# ## Use multiple KCLayout objects as PDKs/Libraries
#
# KCLayouts can act as PDKs. They can be seamlessly instantiated into each other

# %%
from collections.abc import Sequence
import kfactory as kf

class LayerInfos(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1,0)
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2,0) # WG Exclude
    CLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(4,0) # cladding
    FLOORPLAN: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10,0)

# Make the layout object aware of the new layers:
LAYER = LayerInfos()
kf.kcl.infos = LAYER

kcl_default = kf.kcl

# %% [markdown]
# Empty default KCLayout

# %%
kcl_default.kcells

# %%
from typing import Any

bend90_function = kf.factories.euler.bend_euler_factory(kcl=kcl_default)
bend90 = bend90_function(width=0.500, radius=10, layer=LAYER.WG)

@kcl_default.cell
def straight(width: int, length: int) -> kf.KCell:
    c = kcl_default.kcell()
    c.shapes(LAYER.WG).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
    c.create_port(
        name="o1",
        width=width,
        trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
        layer_info=LAYER.WG,
    )
    c.create_port(
        name="o2",
        width=width,
        trans=kf.kdb.Trans(x=length, y=0),
        layer_info=LAYER.WG,
    )

    return c

@kcl_default.routing_strategy
def route_bundle(
    c: kf.ProtoTKCell[Any],
    start_ports: Sequence[kf.ProtoPort[Any]],
    end_ports: Sequence[kf.ProtoPort[Any]],
    separation: int = 5000,
) -> list[kf.routing.generic.ManhattanRoute]:
    return kf.routing.optical.route_bundle(
        c=kf.KCell(base=c.base),
        start_ports=[kf.Port(base=sp.base) for sp in start_ports],
        end_ports=[kf.Port(base=ep.base) for ep in end_ports],
        separation=separation,
        straight_factory=straight,
        bend90_cell=bend90,
    )


@kcl_default.schematic_cell(output_type=kf.KCell)
def my_schema() -> kf.schema.Schema:
    schema = kf.Schema(kcl=kcl_default)

    s1 = schema.create_inst(
        name="s1", component="straight", settings={"length": 5000, "width": 500}
    )
    s2 = schema.create_inst(
        name="s2", component="straight", settings={"length": 5000, "width": 500}
    )

    s1.place(x=1000, y=10_000)
    s2.place(x=1000, y=100_000)

    schema.add_route(
        "s1-s2", [s1["o2"]], [s2["o2"]], "route_bundle", separation=20_000
    )

    return schema

kcell = my_schema()

kcell
# %%
# There is now a a KCell in the KCLayout
kcl_default.kcells
