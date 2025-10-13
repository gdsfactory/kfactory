# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     formats: ipynb,py:percent
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
# # KCell
#
# A `KCell` is like an empty canvas, where you can add polygons and instances to other Cells and ports (which is used to connect to other cells)
#
# In KLayout geometries are in datatabase units (dbu) or microns. GDS uses an integer grid as a basis for geometries.
# The default is `0.001`, i.e. 1nm grid size (0.001 microns)
#
# - `Point`, `Box`, `Polygon`, `Edge`, `Region` are in dbu
# - `DPoint`, `DBox`, `DPolygon`, `DEdge` are in microns
#
# Most Shape types are available as microns and dbu parts. They can be converted with `<ShapeTypeDBU>.to_dtype(dbu)` to microns
#  and with `<ShapeTypeMicrons>.to_itype(dbu)` where `dbu` is the the conversion of one database unit to microns.
# Alternatively they can be converted with `c.kcl.to_um(<ShapeTypeDBU>)` or `c.kcl.to_dbu(<ShapeTypeMicrons>)`
# where `c.kcl` is the KCell and `kcl` is the `KCLayout` which owns the KCell.

# Imports: It imports the necessary libraries: kfactory for layout creation and numpy for numerical operations
# LayerInfos Class: In chip fabrication, the design is built up layer by layer.
# Each layer corresponds to a specific material or process step (e.g., silicon, metal, oxide).
# This class creates human-readable names (WG for waveguide, CLAD for cladding)
# and maps them to the GDS layer numbers ((1, 0), (4, 0))

# %%
import kfactory as kf
import numpy as np


# %%
# Define Layers

class LayerInfos(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1,0)
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2,0) # WG Exclude
    CLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(4,0) # cladding
    FLOORPLAN: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10,0)

# Make the layout object aware of the new layers:
LAYER = LayerInfos()
kf.kcl.infos = LAYER

# %%
# Create a blank cell (essentially an empty GDS cell with some special features)
c = kf.KCell()

# %%
# Create and add a polygon from separate lists of x points and y points
# (Can also be added like [(x1,y1), (x2,y2), (x3,y3), ... ]
poly1 = kf.kdb.DPolygon(
    [
        kf.kdb.DPoint(-8, -6),
        kf.kdb.DPoint(6, 8),
        kf.kdb.DPoint(7, 17),
        kf.kdb.DPoint(9, 5),
    ]
)


# %%
c.shapes(c.kcl.find_layer(1, 0)).insert(poly1)

# %%
c.show()  # show in KLayout
c.plot()

# %% [markdown]
# **Exercise** :
#
# Make a cell similar to the one above that has a second polygon in layer (2, 0)
#
# **Solution** :

# %%
c = kf.KCell()
points = np.array([(-8, -6), (6, 8), (7, 17), (9, 5)])
poly = kf.polygon_from_array(points)
c.shapes(c.kcl.find_layer(1, 0)).insert(poly1)
c.shapes(c.kcl.find_layer(2, 0)).insert(poly1)
c

# kf.kdb.TextGenerator: This creates a text object. The text "Hello!" is converted into a set of polygons that can be fabricated.
# kf.kdb.DBox(...): This creates a simple rectangle (a box).
# This box is defined by the coordinates of its lower-left corner (-2.5, -5) and upper-right corner (2.5, 5).
# Like before, these shapes are then inserted into specific layers in the cell c.
# %%
c = kf.KCell()
textgenerator = kf.kdb.TextGenerator.default_generator()
t = textgenerator.text("Hello!", c.kcl.dbu)
c.shapes(kf.kcl.find_layer(1, 0)).insert(t)
c.show()  # show in KLayout
c.plot()

# %%
r = kf.kdb.DBox(-2.5, -5, 2.5, 5)
r

# %% [markdown]
# Add instances to the new geometry to c, our blank cell

# %%
c = kf.KCell()
c.shapes(c.kcl.find_layer(1, 0)).insert(r)
c.shapes(c.kcl.find_layer(2, 0)).insert(r)
c

# %%
c = kf.KCell()
textgenerator = kf.kdb.TextGenerator.default_generator()
text1 = t.transformed(
    kf.kdb.DTrans(0.0, 10.0).to_itype(c.kcl.dbu)
)  # DTrans is a transformation in microns with arguments (<rotation in 90° increments>, <mirror boolean>, <x in microns>, <y in microns>)
# Now that the geometry has been added to "c", we can move everything around:


# %%
### complex transformation example:ce
#     magnification(float): magnification, DO NOT USE on cells or instances, only on shapes. Most foundries will not allow magnifications on actual cell instances or cells.
#     rotation(float): rotation in degrees
#     mirror(bool): boolean to mirror at x axis and then rotate if true
#     x(float): x coordinate
#     y(float): y coordinate
#
text2 = t.transformed(
    kf.kdb.DCplxTrans(2.0, 45.0, False, 5.0, 30.0).to_itrans(c.kcl.dbu)
)
# text1.movey(25)
# text2.move([5, 30])
# text2.rotate(45)
r.move(
    -5, 0
)  # boxes can be moved like this, other shapes and cells/refs need to be moved with .transform
r.move(-5, 0)

# %%
c.shapes(c.kcl.find_layer(1, 0)).insert(text1)
c.shapes(c.kcl.find_layer(2, 0)).insert(text2)
c.shapes(c.kcl.find_layer(2, 0)).insert(r)

# %%
c.show()  # show in KLayout
c.plot()

# %% [markdown]
# This portion essentially demonstrates how to draw a shape and add connections to it.

# It defines a function named straight, which accepts the following three arguments:
# Length: The length of a waveguide in microns, the default is 10 µm.
# Width: The width of the waveguide in microns, the default is 1 µm.
# Layer: A tuple (data structure with multiple parts to it), which specifies the GDSII (Graphic Design System II) layer it will draw on.
# layer=(1, 0): This tuple holds the blueprint information.
# *layer: The asterisk * is Python's "unpacking" operator. It turns the tuple (1, 0) into two separate arguments, so kf.kcl.find_layer(*layer) is the same as calling kf.kcl.find_layer(1, 0).
# kf.kcl.find_layer: This function takes the layer and purpose numbers, in this case 1 and 0 and finds the corresponding internal layer index.
# This will then allow the KLayout software uses to manage the data efficiently.
# wg.shapes(_layer).insert(box): This is the "drawing" step.
# It instructs the software to take the rectangular box shape and place it specifically on the blueprint for Layer 1, Purpose 0.
# Without this, the shape would exist only in memory but not be part of the final chip design.
# wg = kf.KCell(): Creates a new, empty cell named wg (short for waveguide).
# box = kf.kdb.DBox(length, width): Creates a rectangular shape object using floating-point coordinates in microns.
# int_box = wg.kcl.to_dbu(box): Chip layout databases use integers for high precision, called database units (dbu).
# This line converts the box's micron coordinates into these integer units.
# Then the function adds connecting ports named "o1" and "o2".
# Finally, the function will return the completed wg cell, which now contains the rectangular shape.

# %%
@kf.cell
def straight(length=10, width=1, layer=(1, 0)) -> kf.KCell:
    wg = kf.KCell()
    box = kf.kdb.DBox(length, width)
    int_box = wg.kcl.to_dbu(box)
    _layer = kf.kcl.find_layer(*layer)
    wg.shapes(_layer).insert(box)
    wg.add_port(
        port=kf.Port(
            name="o1",
            width=wg.kcl.to_dbu(width),
            dcplx_trans=kf.kdb.DCplxTrans(1, 180, False, box.left, box.center().y),
            layer=_layer,
        )
    )
    wg.create_port(
        name="o2",
        trans=kf.kdb.Trans(int_box.right, int_box.center().y),
        layer=_layer,
        width=int_box.height(),
    )
    return wg

# The following code creates and places three separate straight waveguides, each with a different length, into a designated cell called c.

# %%
c = kf.KCell()
wg1 = c << straight(length=1, width=2.5, layer=(1, 0))
wg2 = c << straight(length=2, width=2.5, layer=(1, 0))
wg3 = c << straight(length=3, width=2.5, layer=(1, 0))
c


# %% [markdown]
# Each straight has two ports: 'o1' and 'o2'. These are arbitrary names defined in our straight() function above

# %%
# Let us keep wg1 in place on the bottom and then connect the other straights to it.
# To do that, on wg2 we will grab the "W0" port and connect it to the "E0" on wg1:
wg2.connect("o1", wg1.ports["o2"])
# Next, on wg3, take the "W0" port and connect it to the "E0" on wg2:
wg3.connect("o1", wg2.ports["o2"])
c

# %%
c.add_port(name="o1", port=wg1.ports["o1"])
c.add_port(name="o2", port=wg3.ports["o2"])
c.show()  # show in KLayout
c.plot()

# %% [markdown]
# As you can see the `red` labels are for the cell ports while
# `blue` labels are for the sub-ports (children ports)

# %% [markdown]
# ## Move and rotate instances
#
# You can move, rotate, and reflect instances to Cells.


# %%
c = kf.KCell()


# %%
# Create and add a polygon from separate lists of x points and y points
# e.g. [(x1, x2, x3, ...), (y1, y2, y3, ...)]
c.shapes(c.kcl.find_layer(4, 0)).insert(
    kf.kdb.DPolygon([kf.kdb.DPoint(x, y) for x, y in zip((8, 6, 7, 9), (6, 8, 9, 5))])
)

# %%
# Alternatively, create and add a polygon from a list of points
# e.g. [(x1,y1), (x2,y2), (x3,y3), ...] using the same function
c.shapes(c.kcl.find_layer(4, 0)).insert(
    kf.kdb.DPolygon(
        [kf.kdb.DPoint(x, y) for (x, y) in ((0, 0), (1, 1), (1, 3), (-3, 3))]
    )
)


# %%
c.show()  # show in KLayout
c.plot()

# %% [markdown]
# ## Ports
#
# Your straights wg1/wg2/wg3 are instances to other straight cells.
#
# If you want to add ports to the new cell `c` you can use `add_port`, where you can create a new port or use an instance an existing port from the underlying instance.

# %% [markdown]
# You can access the ports of a cell or instance


# %%
wg2.ports

# Here we create a new design cell (MultiMultiWaveguide) and place to identical straight waveguides into it.
# We then place the physical copies into the c2 canvas via mwg1_ref = c2.create_inst(wg1) and mwg2_ref = c2.create_inst(wg2)
# After that, we move wg2 by 10 microns in the x and y directions with mwg2_ref.transform(kf.kdb.DTrans(10, 10))
# In an interactive environment like a Jupyter Notebook, the last line c2 would then show you two waveguides. One at (0, 0) and one at (10, 10)

# %%
c2 = kf.KCell(name="MultiMultiWaveguide")
wg1 = straight(layer=(2, 0))
wg2 = straight(layer=(2, 0))
mwg1_ref = c2.create_inst(wg1)
mwg2_ref = c2.create_inst(wg2)
mwg2_ref.transform(kf.kdb.DTrans(10, 10))
c2

# %%
# Like before, now we connect mwg1 and mwg2 together
mwg1_ref.connect("o2", mwg2_ref.ports["o1"])

# %%
c2

# This block creates and mirrors 2 Euler bend components horizontally, this creates a U turn. An Euler bend is a curve designed to minimize light loss.
# Setup: A new cell c is created, and a 90-degree Euler bend component is defined.
# Placement: Two identical instances of the bend, b1 and b2, are placed in c at the origin (0, 0), one on top of the other.
# Transformation: b2.mirror_x(x=0) takes the second instance (b2) and mirrors it horizontally across the y-axis (the vertical line where x=0).
# Result: The final cell c contains the original bend (b1) and its horizontal mirror image (b2).
# %%
c = kf.KCell()
bend = kf.cells.euler.bend_euler(radius=10, width=1, layer=LAYER.WG)
b1 = c << bend
b2 = c << bend
b2.mirror_x(x=0)
c

# Next, we will mirror them vertically, which will create 2 back to back curves.
# Setup & Placement: This is identical to the first block; two bend instances are placed at the origin.
# Transformation: b2.mirror_y(y=0) takes the second instance (b2) and mirrors it vertically across the x-axis (the horizontal line where y=0).
# Result: The cell c now contains the original bend and its vertical mirror image. They are positioned back-to-back, but their connection points are still overlapping at the origin.
# %%
c = kf.KCell()
bend = kf.cells.euler.bend_euler(radius=10, width=1, layer=LAYER.WG)
b1 = c << bend
b2 = c << bend
b2.mirror_y(y=0)
c

# After that, we expand on the previous structure and make it a S-bend waveguide.
# Setup & Mirroring: The code starts exactly like Block 2, creating two bends (b1, b2) and mirroring b2 vertically. They are still overlapping.
# Alignment: b1.ymin = b2.ymax is the key step. This is a powerful kfactory feature for alignment.
# It moves the entire b1 instance vertically until its bottom edge (ymin) is perfectly aligned with the top edge (ymax) of the mirrored b2 instance.
# Result: The two mirrored bends are now perfectly stitched together to form a seamless S-bend.
# This is a common component for shifting the path of a waveguide.
# %%
c = kf.KCell()
bend = kf.cells.euler.bend_euler(radius=10, width=1, layer=LAYER.WG)
b1 = c << bend
b2 = c << bend
b2.mirror_y(y=0)
b1.ymin = b2.ymax
c

# %% [markdown]
#
# ## Labels
#
# You can add abstract GDS labels (annotate) to your cells, in order to record information
# directly into the final GDS file without putting any extra geometry onto any layer.
# This label will display in a GDS viewer, but will not be rendered or printed
# like the polygons created by gf.cells.text().


# %%
c2.shapes(c2.kcl.find_layer(1, 0)).insert(kf.kdb.Text("First label", mwg1_ref.trans))
c2.shapes(c2.kcl.find_layer(1, 0)).insert(kf.kdb.Text("Second label", mwg2_ref.trans))

# %%
# First we insert a new shape into the c2 cell:
# c2.kcl.find_layer(10, 0): This specifies that the new shape will be drawn on GDSII layer 10, purpose 0.
# This layer is often used for documentation or labels.
# c2.shapes(...).insert(...): This is the command to add the shape (in this case, a text object) to the specified layer.
# Then we define the text object:
# The String: f"The x size of this\nlayout is {c2.dbbox().width()}"
# The \n creates a line break.
# c2.dbbox().width() is a function call that dynamically calculates the total width of the entire c2 cell in database units (dbu).
# This number then gets embedded directly into the text.
# kf.kdb.Trans(c2.bbox().right, c2.bbox().top) sets the location for the text label, in this case at the top right corner.
# Lastly, there are 2 ways to visualize the final design:
# c2.show(): If you are running the script inside the main KLayout application, this command will render the cell in the layout viewer.
# c2.plot(): This command generates a 2D plot of the cell, which is useful for viewing the layout directly in environments like a Jupyter Notebook.
c2.shapes(c2.kcl.find_layer(10, 0)).insert(
    kf.kdb.Text(
        f"The x size of this\nlayout is {c2.dbbox().width()}",
        kf.kdb.Trans(c2.bbox().right, c2.bbox().top),
    )
)
c2.show()
c2.plot()

# %% [markdown]
# ## Boolean shapes
#
# If you want to subtract one shape from another, merge two shapes, or
# perform an XOR on them, you can do that with the `boolean()` function.
#
#
# The ``operation`` argument should be {not, and, or, xor, 'A-B', 'B-A', 'A+B'}.
# Note that 'A+B' is equivalent to 'or', 'A-B' is equivalent to 'not', and
# 'B-A' is equivalent to 'not' with the operands switched.


# %%
e1 = kf.kdb.DPolygon.ellipse(kf.kdb.DBox(10, 8), 64)
e2 = kf.kdb.DPolygon.ellipse(kf.kdb.DBox(10, 6), 64).transformed(
    kf.kdb.DTrans(2.0, 0.0)
)

# %%
c = kf.KCell()
c.shapes(c.kcl.find_layer(2, 0)).insert(e1)
c.shapes(c.kcl.find_layer(4, 0)).insert(e2)
c

# %%
# e1 NOT e2
c = kf.KCell()
e3 = kf.kdb.Region(c.kcl.to_dbu(e1)) - kf.kdb.Region(c.kcl.to_dbu(e2))
c.shapes(c.kcl.find_layer(1, 0)).insert(e3)
c

# %%
# e1 AND e2
c = kf.KCell()
e3 = kf.kdb.Region(c.kcl.to_dbu(e1)) & kf.kdb.Region(c.kcl.to_dbu(e2))
c.shapes(c.kcl.find_layer(1, 0)).insert(e3)
c

# %%
# e1 OR e2
c = kf.KCell()
e3 = kf.kdb.Region(c.kcl.to_dbu(e1)) + kf.kdb.Region(c.kcl.to_dbu(e2))
c.shapes(c.kcl.find_layer(1, 0)).insert(e3)
c

# %%
# e1 OR e2 (merged)
c = kf.KCell()
e3 = (
    kf.kdb.Region(c.kcl.to_dbu(e1)) + kf.kdb.Region(c.kcl.to_dbu(e2))
).merge()
c.shapes(c.kcl.find_layer(1, 0)).insert(e3)
c

# %%
# e1 XOR e2
c = kf.KCell()
e3 = kf.kdb.Region(c.kcl.to_dbu(e1)) ^ kf.kdb.Region(c.kcl.to_dbu(e2))
c.shapes(c.kcl.find_layer(1, 0)).insert(e3)
c

# %% [markdown]
# ## Move the instance by port


# %%
c = kf.KCell()
wg = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)
bend = c << kf.cells.euler.bend_euler(width=0.5, radius=1, layer=LAYER.WG)

bend.connect("o1", wg.ports["o2"])  # connects follow source, the destination is the syntax
c

# %% [markdown]
# ## Rotate instance
#
# You can rotate in degrees using `Instance.drotate` or in multiples of 90 deg.


# %%
c = kf.KCell(name="mirror_example3")
bend = kf.cells.euler.bend_euler(width=0.5, radius=1, layer=LAYER.WG)
b1 = c << bend
b2 = c << bend
b2.drotate(90)
c

# %%
c = kf.KCell(name="mirror_example4")
bend = kf.cells.euler.bend_euler(width=0.5, radius=1, layer=LAYER.WG)
b1 = c << bend
b2 = c << bend
b2.rotate(1)
c

# %% [markdown]
# By default the mirror works along the x=0 axis.

# %% [markdown]
# ## Write GDS
#
# [GDSII](https://en.wikipedia.org/wiki/GDSII) is the standard format for exchanging CMOS circuits with foundries
#
# You can write your cell to a GDS file.


# %%
c.write("demo.gds")
