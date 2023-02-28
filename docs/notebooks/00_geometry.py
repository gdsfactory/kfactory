# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     formats: ipynb,py
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # KCell
#
#
# A `Cell` is like an empty canvas, where you can add polygons, references to other Components and ports (to connect to other components)
#
# In KLayout geometries are in datatabase units (dbu) or microns. GDS uses an integer grid as a basis for geometries. The default is `0.001`, i.e. 1nm grid size (0.001 microns)
#
# `Point`, `Box`, `Polygon`, `Edge`, `Region` are in dbu
# `DPoint`, `DBox`, `DPolygon`, `DEdge` are in microns
#
# Most Shape types are available as microns and dbu parts. They can be converted with `<ShapeTypeDBU>.to_dtype(dbu)` to microns and with `<ShapeTypeMicrons>.to_itype(dbu)` where `dbu` is the the conversion of one database unit to microns

# Lets add a polygon

# + vscode={"languageId": "python"}
import kfactory as kf

# Create a blank component (essentially an empty GDS cell with some special features)
c = kf.KCell()

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


c.shapes(c.klib.layer(1, 0)).insert(poly1)
# show it in matplotlib and KLayout (you need to have KLayout open and install gdsfactory from the git repo with make install)

c
# -


# **Exercise** :
#
# Make a component similar to the one above that has a second polygon in layer (1, 1)

# + vscode={"languageId": "python"}
c = kf.KCell()

# Create some new geometry from the functions available in the geometry library
textgenerator = kf.kdb.TextGenerator.default_generator()
t = textgenerator.text("Hello!", c.klib.dbu)
# t = gf.components.text("Hello!")

r = kf.kdb.DBox(-2.5, -5, 2.5, 5)
# r = gf.components.rectangle(size=[5, 10], layer=(2, 0))

# Add references to the new geometry to c, our blank component

# c.shapes(layer(1,0)).insert(t)
# text1 = c.add_ref(t)  # Add the text we created as a reference
# Using the << operator (identical to add_ref()), add the same geometry a second time
# text2 = c << t
# r = c << r  # Add the rectangle we created

# Now that the geometry has been added to "c", we can move everything around:
text1 = t.transformed(
    kf.kdb.DTrans(0.0, 10.0).to_itype(c.klib.dbu)
)  # DTrans is a transformation in microns with arguments (<rotation in 90° increments>, <mirror boolean>, <x in microns>, <y in microns>)
### complex transformation example:
# args:
#     magnification(float): magnification, DO NOT USE on cells or references, only shapes, most foundries will not allow magnifications on actual cell references or cells
#     rotation(float): rotation in degrees
#     mirror(bool): boolean to mirror at x axis and then rotate if true
#     x(float): x coordinate
#     y(float): y coordinate
#
text2 = t.transformed(kf.kdb.CplxTrans(2.0, 45.0, False, 5.0, 30.0))
# text1.movey(25)
# text2.move([5, 30])
# text2.rotate(45)
r.move(
    -5, 0
)  # boxes can be moved like this, other shapes and cellss/refs need to be moved with .transform
r.move(-5, 0)


c.shapes(c.klib.layer(1, 0)).insert(text1)
c.shapes(c.klib.layer(2, 0)).insert(text2)
c.shapes(c.klib.layer(2, 0)).insert(r)

print(c)
c
# -

# ## Connect **ports**
#
# Components can have a "Port" that allows you to connect ComponentReferences together like legos.
#
# You can write a simple function to make a rectangular straight, assign ports to the ends, and then connect those rectangles together.


# + vscode={"languageId": "python"}
@kf.autocell
def straight(length=10, width=1, layer=(1, 0)):
    wg = kf.KCell()
    box = kf.kdb.DBox(length, width)
    int_box = box.to_itype(wg.klib.dbu)
    _layer = kf.klib.layer(*layer)
    wg.shapes(_layer).insert(box)
    wg.add_port(
        kf.DPort(
            name="o1",
            position=(box.left, box.center().y),
            width=width,
            angle=2,
            layer=_layer,
        )
    )
    wg.create_port(
        name="o2",
        trans=kf.kdb.Trans(int_box.right, int_box.center().y),
        layer=_layer,
        width=int_box.height(),
    )
    # wg.draw_ports()
    return wg


c = kf.KCell()

wg1 = c << straight(length=6, width=2.5, layer=(1, 0))
wg2 = c << straight(length=11, width=2.5, layer=(1, 0))
wg3 = c << straight(length=15, width=2.5, layer=(1, 0))

# wg2.transform(kf.kdb.DCplxTrans(1, 10, False, 10, 0))
# wg3.transform(kf.kdb.DCplxTrans(1, 15, False, 20, 0))
# wg2.movey(10).rotate(10)
# wg3.movey(20).rotate(15)
print(c.name)
c

# + vscode={"languageId": "python"}
# Now we can connect everything together using the ports:

# Each straight has two ports: 'W0' and 'E0'.  These are arbitrary
# names defined in our straight() function above

# Let's keep wg1 in place on the bottom, and connect the other straights to it.
# To do that, on wg2 we'll grab the "W0" port and connect it to the "E0" on wg1:
wg2.connect("o1", wg1.ports["o2"])
# Next, on wg3 let's grab the "W0" port and connect it to the "E0" on wg2:
wg3.connect("o1", wg2.ports["o2"])

c

# + vscode={"languageId": "python"}
c.add_port(name="o1", port=wg1.ports["o1"])
c.add_port(name="o2", port=wg3.ports["o2"])
c
# -

# As you can see the `red` labels are for the component ports while
# `blue` labels are for the sub-ports (children ports)

# ## Move and rotate references
#
# You can move, rotate, and reflect references to Components.

# + vscode={"languageId": "python"}
c = kf.KCell()

wg1 = c << straight(length=1, layer=(1, 0))
wg2 = c << straight(length=2, layer=(2, 0))
wg3 = c << straight(length=3, layer=(3, 0))

# Create and add a polygon from separate lists of x points and y points
# e.g. [(x1, x2, x3, ...), (y1, y2, y3, ...)]
c.shapes(c.klib.layer(4, 0)).insert(
    kf.kdb.DPolygon([kf.kdb.DPoint(x, y) for x, y in zip((8, 6, 7, 9), (6, 8, 9, 5))])
)
# poly1 = c.add_polygon([(8, 6, 7, 9), (6, 8, 9, 5)], layer=(4, 0))

# Alternatively, create and add a polygon from a list of points
# e.g. [(x1,y1), (x2,y2), (x3,y3), ...] using the same function
c.shapes(c.klib.layer(4, 0)).insert(
    kf.kdb.DPolygon(
        [kf.kdb.DPoint(x, y) for (x, y) in ((0, 0), (1, 1), (1, 3), (-3, 3))]
    )
)
# poly2 = c.add_polygon([(0, 0), (1, 1), (1, 3), (-3, 3)], layer=(5, 0))

# Shift the first straight we created over by dx = 10, dy = 5
wg2.transform(kf.kdb.DTrans(10.0, 5.0))
# wg1.move([10, 5])

# Shift the second straight over by dx = 10, dy = 0
wg2.transform(kf.kdb.DTrans(10.0, 0.0))
# wg2.move(origin=[0, 0], destination=[10, 0])

# Shift the third straight over by dx = 0, dy = 4
wg3.transform(kf.kdb.DTrans(1.0, 1.0).inverted() * kf.kdb.DTrans(5, 5))
# wg3.move([1, 1], [5, 5], axis="y")

# Move "from" x=0 "to" x=10 (dx=10)
# wg3.movex(0, 10)
wg3.transform(kf.kdb.DTrans(10.0 - 0.0, 0.0))

c
# -

# ## Ports
#
# Your straights wg1/wg2/wg3 are references to other waveguide components.
#
# If you want to add ports to the new Component `c` you can use `add_port`, where you can create a new port or use an reference an existing port from the underlying reference.

# You can access the ports of a Component or ComponentReference

# + vscode={"languageId": "python"}
wg2.ports
# -

# ## References
#
# Now that we have your component `c` is a multi-straight component, you can add references to that component in a new blank Component `c2`, then add two references and shift one to see the movement.

# + vscode={"languageId": "python"}
c2 = kf.KCell(name="MultiMultiWaveguide")
wg1 = straight(layer=(2, 0))
wg2 = straight(layer=(2, 0))
mwg1_ref = c2.create_inst(wg1)
mwg2_ref = c2.create_inst(wg2)
mwg2_ref.transform(kf.kdb.DTrans(10, 10))
c2

# + vscode={"languageId": "python"}
# Like before, let's connect mwg1 and mwg2 together
mwg1_ref.connect("o2", mwg2_ref.ports["o1"])
c2
# -

# ## Labels
#
# You can add abstract GDS labels (annotate) to your Components, in order to record information
# directly into the final GDS file without putting any extra geometry onto any layer
# This label will display in a GDS viewer, but will not be rendered or printed
# like the polygons created by gf.components.text().

# + vscode={"languageId": "python"}
c2.shapes(c2.klib.layer(1, 0)).insert(kf.kdb.Text("First label", mwg1_ref.trans))
# c2.shapes(c2.klib.layer(1,0).insert(kf.kdb.Text("First label", position=mwg1_ref.center)
c2.shapes(c2.klib.layer(1, 0)).insert(kf.kdb.Text("Second label", mwg2_ref.trans))
# c2.add_label(text="Second label", position=mwg2_ref.center)

# It's very useful for recording information about the devices or layout
c2.shapes(c2.klib.layer(10, 0)).insert(
    kf.kdb.Text(
        f"The x size of this\nlayout is {c2.dbbox().width}",
        kf.kdb.Trans(c2.bbox().right, c2.bbox().top),
    )
)

c2
# -

# ## Boolean shapes
#
# If you want to subtract one shape from another, merge two shapes, or
# perform an XOR on them, you can do that with the `boolean()` function.
#
#
# The ``operation`` argument should be {not, and, or, xor, 'A-B', 'B-A', 'A+B'}.
# Note that 'A+B' is equivalent to 'or', 'A-B' is equivalent to 'not', and
# 'B-A' is equivalent to 'not' with the operands switched

# + vscode={"languageId": "python"}
e1 = kf.kdb.DPolygon.ellipse(kf.kdb.DBox(10, 8), 64)
e2 = kf.kdb.DPolygon.ellipse(kf.kdb.DBox(10, 6), 64).transformed(
    kf.kdb.DTrans(2.0, 0.0)
)
# -

# e1 NOT e2
c = kf.KCell()
e3 = kf.kdb.Region(e1.to_itype(c.klib.dbu)) - kf.kdb.Region(e2.to_itype(c.klib.dbu))
c.shapes(c.klib.layer(1, 0)).insert(e3)
c

# e1 AND e2
c = kf.KCell()
e3 = kf.kdb.Region(e1.to_itype(c.klib.dbu)) & kf.kdb.Region(e2.to_itype(c.klib.dbu))
c.shapes(c.klib.layer(1, 0)).insert(e3)
c

# e1 OR e2
c = kf.KCell()
e3 = kf.kdb.Region(e1.to_itype(c.klib.dbu)) + kf.kdb.Region(e2.to_itype(c.klib.dbu))
c.shapes(c.klib.layer(1, 0)).insert(e3)
c

# e1 OR e2 (merged
c = kf.KCell()
e3 = (
    kf.kdb.Region(e1.to_itype(c.klib.dbu)) + kf.kdb.Region(e2.to_itype(c.klib.dbu))
).merge()
c.shapes(c.klib.layer(1, 0)).insert(e3)
c

# e1 XOR e2
c = kf.KCell()
e3 = kf.kdb.Region(e1.to_itype(c.klib.dbu)) ^ kf.kdb.Region(e2.to_itype(c.klib.dbu))
c.shapes(c.klib.layer(1, 0)).insert(e3)
c

# ## Move Reference by port

# + vscode={"languageId": "python"}
# MMI not implemented yet

# c = kf.KCell()
# mmi = c.add_ref(gf.components.mmi1x2())
# bend = c.add_ref(gf.components.bend_circular(layer=(2, 0)))
# c

# + vscode={"languageId": "python"}
# bend.connect("o1", mmi.ports["o2"])  # connects follow Source, destination syntax
# c
# -

# ## Mirror reference
#
# By default the mirror works along the x=0 axis.

# + vscode={"languageId": "python"}
# c = gf.Component("ref_mirror")
# mmi = c.add_ref(gf.components.mmi1x2())
# bend = c.add_ref(gf.components.bend_circular(layer=(2, 0)))
# c

# + vscode={"languageId": "python"}
# mmi.mirror()
# c
# -

# ## Write GDS
#
# [GDSII](https://en.wikipedia.org/wiki/GDSII) is the Standard format for exchanging CMOS and Photonic circuits.
#
# You can write your Component to GDS file.

# + vscode={"languageId": "python"}
c.write("demo.gds")
# -

# You can see the GDS file in Klayout viewer.
#
# Sometimes you also want to save the GDS together with metadata (settings, port names, widths, locations ...) in YAML

# + vscode={"languageId": "python"}
# c.write_gds_with_metadata("demo.gds") # not implemented
