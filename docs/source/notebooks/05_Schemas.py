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
# KCLayouts can act as PDKs. They can be seamlessly incooperated into each other

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

# bend90 = bend90_function: This creates a standard, pre-configured 90-degree bend component. 
# This will be used for making turns in the routes.
# @kcl_default.cell def straight: This defines a simple, reusable straight waveguide component.
# It is parametric, meaning you can specify its width and length. 
# Crucially, it has two connection points, o1 (input) and o2 (output), called ports.
# This section will serve as basic building blocks, so that the router knows what a bend and a straight looks like.

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

# @kcl_default.routing_strategy: This decorator registers the route_bundle function as a named set of instructions.
# The schematic will be able call upon these instructions when necessary 
# def route_bundle: The function takes a list of starting ports and ending ports. 
# It then calls kf.routing.optical.route_bundle, which is a smart, built-in algorithm designed to connect multiple waveguides simultaneously.
# This ensures that they run parallel to each other with a specified separation.
# This is where the first section comes into play. The algorithm is being told to use the straight and bend90 components defined there.
# In essence, this section created a custom routing command named "route_bundle" and is defined as a rule for how to connect things.


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

# @kcl_default.schematic_cell: This decorator signifies that the function will return an abstract Schema, not a physical KCell with polygons.
# schema = kf.Schema: This creates an abstract canvas.
# schema.create_inst: This places two instances of the "straight" component into the schematic.
# It is like putting two parts on a circuit diagram.
# schema.add_route: This is the key command. It does not draw a route; it issues a connection request. 
# It says: "I need to connect port o2 of component s1 to port o2 of component s2."
# Crucially, it specifies how to make the connection by referencing the rule you just created: "route_bundle".

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

# Although deceivingly simple looking, the my_schema function is powerful. It makes kfactory's layout engine read the abstract schema.
# This has the following effects:
# It creates a physical KCell
# It places s1 and s2
# It reads the add_route request
# It looks up and incooperates the previously added "route_bundle" routing strategy
# Lastly, it calls upon the "route_bundle" function,
# which automatically calculates the optimal path between the bends and straights. It also physically connects them.


kcell = my_schema()

kcell
# %%
# There is now a a KCell in the KCLayout
kcl_default.kcells
