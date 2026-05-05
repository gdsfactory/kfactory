# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
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
# # Enclosures
# This code uses kfactory to demonstrate how to create enclosures,
# which are geometries that surround or are derived from a main shape.
# This is a crucial technique for defining things like cladding layers, doping regions, or keep-out zones around a central component like a waveguide.

# %%
import kfactory as kf


class LayerInfos(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    SLAB: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    NPP: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)

LAYER = LayerInfos()
kf.kcl.infos = LAYER

# %%

# This first block creates a simple enclosure with one extra layer.
# kf.enclosure.LayerEnclosure(...): This defines a set of rules for creating new layers based on a main layer.
# main_layer=LAYER.WG: This specifies that the enclosure rules will be applied to any shapes on the WG (waveguide) layer.
# (LAYER.SLAB, 2000): This is the core rule. It means:
# "Create a new shape on the SLAB layer by taking the WG shape and expanding it outwards by 2000 database units (which is 2 µm, since the default dbu is 1 nm)."
# kf.cells.euler.bend_euler(...): This function creates an Euler bend, a type of curved waveguide.
# enclosure=enc: By passing our enc rule into the bend component, the component automatically creates the SLAB layer around the WG layer according to the rule.
# The result is a waveguide bend on LAYER.WG surrounded by a larger slab shape on LAYER.SLAB.

enc = kf.enclosure.LayerEnclosure(
    [
        (LAYER.SLAB, 2000),
    ],
    name="WGSLAB",
    main_layer=LAYER.WG,
)
c = kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, enclosure=enc)
c.show()
c.plot()

# %%

# (LAYER.SLAB, 2000): This rule is the same as before, creating a 2 µm expansion on the SLAB layer.
# (LAYER.NPP, 1000, 2000): This rule is more advanced. It has three parts: (layer, enclosure, offset).
# It targets the NPP layer (likely for N-type doping).
# The enclosure value of 1000 means the new shape will be 1 µm wider than the main WG shape.
# The offset value of 2000 means the new shape will also be shifted outwards by 2 µm from the edge of the WG.
# This creates a doped region that is separated from the waveguide core.
# This more complex enc object is then applied to a new Euler bend,
# which then results in a component with three layers: the core WG, the SLAB, and the offset NPP doping region.
enc = kf.enclosure.LayerEnclosure(
    [
        (LAYER.SLAB, 2000),
        (LAYER.NPP, 1000, 2000),
    ],
    name="SLAB_DOPED",
    main_layer=LAYER.WG,
)
c = kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, enclosure=enc)
c.show()
c.plot()

# %%

# kcell_enc = kf.KCellEnclosure([enc]): This creates a wrapper, a KCellEnclosure, that can hold one or more LayerEnclosure rule sets.
# Here, it holds the SLAB_DOPED rules from the previous step.
# @kf.cell def two_bends(...): This defines a new, reusable component that contains two separate Euler bends.
# It is important to note that the bends themselves are created without any enclosure.
# if enclosure:: The function checks if an enclosure object was passed to it.
# enclosure.apply_minkowski_tiled(c): This is the key command.
# It takes the final geometry of the two_bends cell (both bends combined) and applies the enclosure rules to the whole thing at once.
# This correctly merges the enclosures of the two bends into a single, continuous shape, which is often the desired result.
# The final output is the two_bends component, where a single, unified SLAB and NPP region correctly surrounds the combined geometry of both bends.
# This method is more robust for complex cells than applying enclosures to each sub-component individually.

kcell_enc = kf.KCellEnclosure([enc])

@kf.cell
def two_bends(
    radius: float,
    width: float,
    layer: kf.kdb.LayerInfo,
    enclosure: kf.KCellEnclosure | None = None,
) -> kf.KCell:
    c = kf.KCell()
    b1 = c << kf.cells.euler.bend_euler(radius=radius, width=width, layer=layer)
    b2 = c << kf.cells.euler.bend_euler(radius=radius, width=width, layer=layer)
    b2.drotate(90)
    b2.dmovey(-11)
    b2.dmovex(b2.dxmin, 0)

    c.add_ports(b1.ports)
    c.add_ports(b2.ports)
    c.auto_rename_ports()

    if enclosure:
        enclosure.apply_minkowski_tiled(c)
    return c


c = two_bends(radius=5, width=1, layer=LAYER.WG, enclosure=kcell_enc)
c.show()
c.plot()

# %%
