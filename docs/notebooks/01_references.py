# ---
# jupyter:
#   jupytext:
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

# # References and ports
#
# GDS allows your the component once in memory and Reference or Instance the component multiple times.
#
# `gdstk` and `gdspy` calls it `Reference` and `klayout` calls it `Instance`

# As you build components you can include references to other components. Adding a reference is like having a pointer to a component.
#
# The GDSII specification allows the use of references, and similarly kfactory uses them (with the `create_inst()` function).
# what is an instance? Simply put:  **A reference does not contain any geometry. It only *points* to an existing geometry**.
#
# Say you have a ridiculously large polygon with 100 billion vertices that you call BigPolygon. It's huge, and you need to use it in your design 250 times.
# Well, a single copy of BigPolygon takes up 1MB of memory, so you don't want to make 250 copies of it
# You can instead *references* the polygon 250 times.
# Each reference only uses a few bytes of memory -- it only needs to know the memory address of BigPolygon, position, rotation and mirror.
# This way, you can keep one copy of BigPolygon and use it again and again.
#
# You can start by making a blank `KFactory` and add a single polygon to it.

# +
import kfactory as kf

# Create a blank Component
p = kf.KCell()

# Add a polygon
xpts = [0, 0, 5, 6, 9, 12]
ypts = [0, 1, 1, 2, 2, 0]
p.shapes(p.klib.layer(2, 0)).insert(
    kf.kdb.DPolygon([kf.kdb.DPoint(x, y) for x, y in zip(xpts, ypts)])
)

# plot the Component with the polygon in it
p
# -

# Now, you want to reuse this polygon repeatedly without creating multiple copies of it.
#
# To do so, you need to make a second blank `Component`, this time called `c`.
#
# In this new Component you *reference* our Component `p` which contains our polygon.

c = kf.KCell(name="Component_with_references")  # Create a new blank Component
poly_ref = c.create_inst(p)  # Reference the Component "p" that has the polygon in it
c

# you just made a copy of your polygon -- but remember, you didn't actually
# make a second polygon, you just made a reference (aka pointer) to the original
# polygon.  Let's add two more references to `c`:

poly_ref2 = c.create_inst(p)  # Reference the Component "p" that has the polygon in it
poly_ref3 = c.create_inst(p)  # Reference the Component "p" that has the polygon in it
c

# Now you have 3x polygons all on top of each other.  Again, this would appear
# useless, except that you can manipulate each reference independently. Notice that
# when you called `c.add_ref(p)` above, we saved the result to a new variable each
# time (`poly_ref`, `poly_ref2`, and `poly_ref3`)?  You can use those variables to
# reposition the references.

poly_ref2.transform(
    kf.kdb.DCplxTrans(1, 15, False, 0, 0)
)  # Rotate the 2nd reference we made 15 degrees
poly_ref3.transform(
    kf.kdb.DCplxTrans(1, 30, False, 0, 0)
)  # Rotate the 3rd reference we made 30 degrees
c

# Now you're getting somewhere! You've only had to make the polygon once, but you're
# able to reuse it as many times as you want.
#
# ## Modifying the referenced geometry
#
# What happens when you change the original geometry that the reference points to?  In your case, your references in
# `c` all point to the Component `p` that with the original polygon.  Let's try
# adding a second polygon to `p`.
#
# First you add the second polygon and make sure `P` looks like you expect:

# Add a 2nd polygon to "p"
xpts = [14, 14, 16, 16]
ypts = [0, 2, 2, 0]
p.shapes(p.klib.layer(1, 0)).insert(
    kf.kdb.DPolygon([kf.kdb.DPoint(x, y) for x, y in zip(xpts, ypts)])
)
p

# That looks good.  Now let's find out what happened to `c` that contains the
# three references.  Keep in mind that you have not modified `c` or executed any
# functions/operations on `c` -- all you have done is modify `p`.

c

#  **When you modify the original geometry, all of the
# references automatically reflect the modifications.**  This is very powerful,
# because you can use this to make very complicated designs from relatively simple
# elements in a computation- and memory-efficient way.
#
# Let's try making references a level deeper by referencing `c`.  Note here we use
# the `<<` operator to add the references -- this is just shorthand, and is
# exactly equivalent to using `add_ref()`

# +
c2 = kf.KCell(name="array_sample")  # Create a new blank Component
d_ref1 = c2.create_inst(c)  # Reference the Component "c" that 3 references in it
d_ref2 = c2 << c  # Use the "<<" operator to create a 2nd reference to c
d_ref3 = c2 << c  # Use the "<<" operator to create a 3rd reference to c

d_ref1.transform(kf.kdb.DTrans(20.0, 0.0))
d_ref2.transform(kf.kdb.DTrans(40.0, 0.0))

c2
# -

# As you've seen you have two ways to add a reference to our component:
#
# 1. create the reference and add it to the component

c = kf.KCell(name="reference_sample")
w = kf.pcells.waveguide.waveguide(length=10, width=0.6, layer=c.klib.layer(1, 0))
wr = kf.kdb.CellInstArray(w._kdb_cell, kf.kdb.Trans.R0)
c.insert(wr)
c

# 2. or do it in a single line

c = kf.KCell(name="reference_sample_shorter_syntax")
wr = c << kf.pcells.waveguide.waveguide(length=10, width=0.6, layer=c.klib.layer(1, 0))
c

# in both cases you can move the reference `wr` after created

c = kf.KCell(name="two_references")
wr1 = c << kf.pcells.waveguide.waveguide(length=10, width=0.6, layer=c.klib.layer(1, 0))
wr2 = c << kf.pcells.waveguide.waveguide(length=10, width=0.6, layer=c.klib.layer(1, 0))
wr2.transform(kf.kdb.DTrans(0.0, 10.0))
c.add_ports(wr1.ports, prefix="top_")
c.add_ports(wr2.ports, prefix="bot_")

c.ports

# You can also auto_rename ports using gdsfactory default convention, where ports are numbered clockwise starting from the bottom left

c.autorename_ports()

c.ports

c

# ## Arrays of references
#
# In GDS, there's a type of structure called a "ComponentReference" which takes a cell and repeats it NxM times on a fixed grid spacing. For convenience, `Component` includes this functionality with the add_array() function.
# Note that CellArrays are not compatible with ports (since there is no way to access/modify individual elements in a GDS cellarray)
#
# gdsfactory also provides with more flexible arrangement options if desired, see for example `grid()` and `packer()`.
#
# As well as `gf.components.array`
#
# Let's make a new Component and put a big array of our Component `c` in it:

# +
# not converted yet

c3 = kf.KCell("array_of_references")  # Create a new blank Component
aref = c3.create_inst(
    c, na=6, nb=3, a=kf.kdb.Vector(20000, 0), b=kf.kdb.Vector(0, 15000)
)  # Reference the Component "c" 3 references in it with a 3 rows, 6 columns array
c3
# -

# CellArrays don't have ports and there is no way to access/modify individual elements in a GDS cellarray.
#
# gdsfactory provides you with similar functions in `gf.components.array` and `gf.components.array_2d`

# +
# c4 = gf.Component("demo_array")  # Create a new blank Component
# aref = c4 << gf.components.array(component=c, columns=3, rows=2)
# c4.add_ports(aref.get_ports_list())
# c4


# +
# # gf.components.array?
# -

# You can also create an array of references for periodic structures. Lets create a [Distributed Bragg Reflector](https://picwriter.readthedocs.io/en/latest/components/dbr.html)


# +
# @gf.cell
# def dbr_period(w1=0.5, w2=0.6, l1=0.2, l2=0.4, straight=gf.components.straight):
#     """Return one DBR period."""
#     c = gf.Component()
#     r1 = c << straight(length=l1, width=w1)
#     r2 = c << straight(length=l2, width=w2)
#     r2.connect(port="o1", destination=r1.ports["o2"])
#     c.add_port("o1", port=r1.ports["o1"])
#     c.add_port("o2", port=r2.ports["o2"])
#     return c


# l1 = 0.2
# l2 = 0.4
# n = 3
# period = dbr_period(l1=l1, l2=l2)
# period

# +
# dbr = gf.Component("DBR")
# dbr.add_array(period, columns=n, rows=1, spacing=(l1 + l2, 100))
# dbr
# -

# Finally we need to add ports to the new component

# +
# p0 = dbr.add_port("o1", port=period.ports["o1"])
# p1 = dbr.add_port("o2", port=period.ports["o2"])

# p1.center = [(l1 + l2) * n, 0]
# dbr
# -

# ## Connect references
#
# We have seen that once you create a reference you can manipulate the reference to move it to a location. Here we are going to connect that reference to a port. Remember that we follow that a certain reference `source` connects to a `destination` port

# +
# bend = gf.components.bend_circular()
# bend

# +
# c = gf.Component("sample_reference_connect")

# mmi = c << gf.components.mmi1x2()
# b = c << gf.components.bend_circular()
# b.connect("o1", destination=mmi.ports["o2"])

# c.add_port("o1", port=mmi.ports["o1"])
# c.add_port("o2", port=b.ports["o2"])
# c.add_port("o3", port=mmi.ports["o3"])
# c
# -

# You can also access the ports directly from the references

# +
# c = gf.Component("sample_reference_connect_simpler")

# mmi = c << gf.components.mmi1x2()
# b = c << gf.components.bend_circular()
# b.connect("o1", destination=mmi["o2"])

# c.add_port("o1", port=mmi["o1"])
# c.add_port("o2", port=b["o2"])
# c.add_port("o3", port=mmi["o3"])
# c
# -

# ## Port naming
#
# You have the freedom to name the ports as you want, and you can use `gf.port.auto_rename_ports(prefix='o')` to rename them later on.
#
# Here is the default naming convention.
#
# Ports are numbered clock-wise starting from the bottom left corner
#
# Optical ports have `o` prefix and Electrical ports `e` prefix
#
# The port naming comes in most cases from the `gdsfactory.cross_section`. For example
#
# - `gdsfactory.cross_section.strip`  has ports `o1` for input and `o2` for output
# - `gdsfactory.cross_section.metal1` has ports `e1` for input and `e2` for output

# +
# size = 4
# c = gf.components.nxn(west=2, south=2, north=2, east=2, xsize=size, ysize=size)
# c

# +
# c = gf.components.straight_heater_metal(length=30)
# c

# +
# c.ports
# -

# You can get the optical ports by `layer`

# +
# c.get_ports_dict(layer=(1, 0))
# -

# or by `width`

# +
# c.get_ports_dict(width=0.5)

# +
# c0 = gf.components.straight_heater_metal()
# c0.ports

# +
# c1 = c0.copy()
# c1.auto_rename_ports_layer_orientation()
# c1.ports

# +
# c2 = c0.copy()
# c2.auto_rename_ports()
# c2.ports
# -

# You can also rename them with a different port naming convention
#
# - prefix: add `e` for electrical `o` for optical
# - clockwise
# - counter-clockwise
# - orientation `E` East, `W` West, `N` North, `S` South
#
#
# Here is the default one we use (clockwise starting from bottom left west facing port)
#
# ```
#              3   4
#              |___|_
#          2 -|      |- 5
#             |      |
#          1 -|______|- 6
#              |   |
#              8   7
#
# ```

# +
# c = gf.Component("demo_ports")
# nxn = gf.components.nxn(west=2, north=2, east=2, south=2, xsize=4, ysize=4)
# ref = c.add_ref(nxn)
# c.add_ports(ref.ports)
# c

# +
# ref.get_ports_list()  # by default returns ports clockwise starting from bottom left west facing port

# +
# c.auto_rename_ports()
# c
# -

# You can also get the ports counter-clockwise
#
# ```
#              4   3
#              |___|_
#          5 -|      |- 2
#             |      |
#          6 -|______|- 1
#              |   |
#              7   8
#
# ```

# +
# c.auto_rename_ports_counter_clockwise()
# c

# +
# c.get_ports_list(clockwise=False)

# +
# c.ports_layer

# +
# c.port_by_orientation_cw("W0")

# +
# c.port_by_orientation_ccw("W1")
# -

# Lets extend the East facing ports (orientation = 0 deg)

# +
# cross_section = gf.cross_section.strip()

# nxn = gf.components.nxn(
#     west=2, north=2, east=2, south=2, xsize=4, ysize=4, cross_section=cross_section
# )
# c = gf.components.extension.extend_ports(component=nxn, orientation=0)
# c

# +
# c.ports

# +
# df = c.get_ports_pandas()
# df

# +
# df[df.port_type == "optical"]
# -

# ## pins
#
# You can add pins (port markers) to each port. Each foundry PDK does this differently, so gdsfactory supports all of them.
#
# - square with port inside the component
# - square centered (half inside, half outside component)
# - triangular
# - path (SiEPIC)
#
#
# by default Component.show() will add triangular pins, so you can see the direction of the port in Klayout.

# +
# gf.components.mmi1x2(decorator=gf.add_pins.add_pins)

# +
# gf.components.mmi1x2(decorator=gf.add_pins.add_pins_triangle)
# -

# ## component_sequence
#
# When you have repetitive connections you can describe the connectivity as an ASCII map

# +
# bend180 = gf.components.bend_circular180()
# wg_pin = gf.components.straight_pin(length=40)
# wg = gf.components.straight()

# # Define a map between symbols and (component, input port, output port)
# symbol_to_component = {
#     "D": (bend180, "o1", "o2"),
#     "C": (bend180, "o2", "o1"),
#     "P": (wg_pin, "o1", "o2"),
#     "-": (wg, "o1", "o2"),
# }

# # Generate a sequence
# # This is simply a chain of characters. Each of them represents a component
# # with a given input and and a given output

# sequence = "DC-P-P-P-P-CD"
# component = gf.components.component_sequence(
#     sequence=sequence, symbol_to_component=symbol_to_component
# )
# component.name = "component_sequence"
# component
# -

# As the sequence is defined as a string you can use the string operations to easily build complex sequences
