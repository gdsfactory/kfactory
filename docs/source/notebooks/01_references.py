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
# # Instances and ports
#
# GDS allows the cell to be used once by the memory and instance or make multiple instances of the cell

# %% [markdown]
# As you build cells you can invoke other cells. Adding an instance is like having a pointer to a cell.
#
# The GDSII specification allows the use of instances and similarly kfactory uses them (with the `create_inst()` function).
# What is an instance? Simply put:  **An instance does not contain any geometry. It only *points* to an existing geometry**.
#
# Say you have a ridiculously large polygon with 100 billion vertices that you call it BigPolygon.
# It is huge, and you need to use it in your design 250 times.
# Well, a single copy of BigPolygon takes up 1MB of memory, so you do not want to make 250 copies of it
# You can instead *instances* the polygon 250 times.
# Each instance only uses a few bytes of memory --
# It only needs to know the memory address of the BigPolygon, alongside its position, rotation and mirror.
# This way, you can keep one copy of BigPolygon and use it again and again.
#
# You can start by making a blank `KFactory` and add a single polygon to it.

# %%
import kfactory as kf

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
# Create a blank Cell
p = kf.KCell()

# Add a polygon
xpts = [0, 0, 5, 6, 9, 12]
ypts = [0, 1, 1, 2, 2, 0]
p.shapes(p.kcl.find_layer(2, 0)).insert(
    kf.kdb.DPolygon([kf.kdb.DPoint(x, y) for x, y in zip(xpts, ypts)])
)

# Plot the cell with the polygon in it
p

# %% [markdown]
# Now, you want to reuse this polygon repeatedly without creating multiple copies of it.
#
# To do so, you need to make a second blank `Cell`, this time named `c`.
#
# In this new cell you *instance* our cell `p` which contains our polygon.

# %%
c = kf.KCell(name="Cell_with_instances")  # Create a new blank cell
poly_ref = c.create_inst(p)  # instance the cell "p" that has the polygon in it
c

# %% [markdown]
# You just made a copy of your polygon -- but remember, you did not actually
# make a second polygon, you just made an instance (aka pointer) to the original
# polygon.  Let us now add two more instances to `c`:

# %%
poly_ref2 = c.create_inst(p)  # instance the Cell "p" that has the polygon in it
poly_ref3 = c.create_inst(p)  # instance the Cell "p" that has the polygon in it
c

# %% [markdown]
# Now you have 3x polygons all on top of each other. Again, this would appear
# useless, except that you can manipulate each instance independently. Notice that
# when you called `c.add_ref(p)` above, we saved the result to a new variable each
# time (`poly_ref`, `poly_ref2`, and `poly_ref3`)?
# You can use those variables to reposition the instances.

# %%
poly_ref2.transform(
    kf.kdb.DCplxTrans(1, 15, False, 0, 0)
)  # Rotate the 2nd instance we made 15 degrees
poly_ref3.transform(
    kf.kdb.DCplxTrans(1, 30, False, 0, 0)
)  # Rotate the 3rd instance we made 30 degrees
c

# %% [markdown]
# Now you are getting somewhere! You have only had to make the polygon once, but you are
# able to reuse it as many times as you want.
#
# ## Modifying the instances
#
# What happens when you change the original geometry of the instance?  In your case, your instances in
# `c` all point to the cell `p`, the cell with the original polygon.  Let us now try adding a second polygon to `p`.
# First, you add the second polygon and make sure `P` looks like you expect it to:

# %%
# Add a 2nd polygon to "p"
xpts = [14, 14, 16, 16]
ypts = [0, 2, 2, 0]
p.shapes(p.kcl.find_layer(1, 0)).insert(
    kf.kdb.DPolygon([kf.kdb.DPoint(x, y) for x, y in zip(xpts, ypts)])
)
p

# %% [markdown]
# That looks good.  Now let us find out what happened to `c` which contains the
# three instances.  Keep in mind that you have not modified `c` or executed any
# functions/operations on `c` -- all you have done is modify `p`.

# %%
c

# %% [markdown]
#  **When you modify the original geometry, all of the
# instances automatically reflect the modifications.**  This is very powerful,
# because you can use this to make very complicated designs from relatively simple
# elements in a computation- and memory-efficient way.
#
# Now try making instances a level deeper by referencing `c`.  Note here that we use
# the `<<` operator to add the instances -- this is just shorthand, and is exactly equivalent to using `add_ref()`

# %%
c2 = kf.KCell(name="array_sample")  # Create a new blank Cell
d_ref1 = c2.create_inst(c)  # instance the cell "c" that has the 3 instances in it
d_ref2 = c2 << c  # Use the "<<" operator to create a 2nd instance to c
d_ref3 = c2 << c  # Use the "<<" operator to create a 3rd instance to c

d_ref1.transform(kf.kdb.DTrans(20.0, 0.0))
d_ref2.transform(kf.kdb.DTrans(40.0, 0.0))

c2

# %% [markdown]
# As you have seen you have two ways to add an instance to our cell:
#
# 1. Create the instance and add it to the cell

# %%
c = kf.KCell(name="instance_sample")
w = kf.cells.straight.straight(length=10, width=0.6, layer=LAYER.WG)
wr = kf.kdb.CellInstArray(w.kdb_cell, kf.kdb.Trans.R0)
c.insert(wr)
c

# %% [markdown]
# 2. Alternatively, you can do it in a single line

# %%
c = kf.KCell(name="instance_sample_shorter_syntax")
wr = c << kf.cells.straight.straight(length=10, width=0.6, layer=LAYER.WG)
c

# %% [markdown]
# in both cases you can move the instance `wr` after creating it

# %%
c = kf.KCell(name="two_instances")
wr1 = c << kf.cells.straight.straight(length=10, width=0.6, layer=LAYER.WG)
wr2 = c << kf.cells.straight.straight(length=10, width=0.6, layer=LAYER.WG)
wr2.transform(kf.kdb.DTrans(0.0, 10.0))
c.add_ports(wr1.ports, prefix="top_")
c.add_ports(wr2.ports, prefix="bot_")

# %%
c.ports

# %% [markdown]
# You can also auto_rename ports using gdsfactory default convention,
# in which ports are numbered clockwise starting from the bottom left.

# %%
c.auto_rename_ports()

# %%
c.ports

# %%
c

# %% [markdown]
# ## Arrays of instances
#
# In GDS, there is a type of structure called an "Instance", which takes a cell and repeats it NxM times on a fixed grid spacing.
# For convenience, `Cell` includes this functionality with the add_array() function.
# Note that CellArrays are not compatible with ports (since there is no way to access/modify individual elements in a GDS cellarray)
#
# Let us  make a new Cell and put a big array of our cell `c` in it:

# %%
import kfactory as kf

print(kf.__version__)
c = kf.cells.straight.straight(length=10, width=0.6, layer=LAYER.WG)
c3 = kf.KCell()  # Create a new blank Cell
aref = c3.create_inst(
    c, na=1, nb=3, a=(20000, 0), b=(0, 15000)
)  # Create three copies of the component named 'c' and arrange them in a vertical stack

c3.add_ports(aref.ports)
c3.draw_ports()
c3.plot()

# %% [markdown]
# You can still access the ports for each instance

# %%
aref['o1', 0, 1]

# %%
c.ports

# %% [markdown]
# ## Connect the instances
#
# We have seen that once you create a instance you can manipulate the instance to move it to a location.
# Here we are going to connect that instance to a port.
# Remember that we follow the rule that a certain instance `source` connects to a `destination` port.

# %%
c = kf.KCell()
bend = kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG)
b1 = c << bend
b2 = c << bend
b2.connect("o1", b1.ports["o2"])
c

# %%
c = kf.KCell()
b1 = c << kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, angle=30)
b2 = c << kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, angle=30)
b2.connect("o1", b1.ports["o2"])
c.show()
c

# %% [markdown]
# ![](https://i.imgur.com/oenlUwg.png)
#
# This non-manhattan connect will create less than 1nm gaps that you can fix by flattening the references.

# %%
c = kf.KCell()
b1 = c << kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, angle=30)
b2 = c << kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, angle=30)
b2.connect("o1", b1.ports["o2"])
b2.flatten()
c.show()
c

# %% [markdown]
# The non-manhattan connect previously mentioned fixes this issue.
#
# ![](https://i.imgur.com/t0J31Wg.png)

# %% [markdown]
# ## Port naming
#
# You have the freedom to name the ports as you want, and you can use `c.auto_rename_ports` to rename them later on.
# Here is the default naming convention.
# Ports are numbered clock-wise starting from the bottom left corner.
# Optical ports have `o` prefix and Electrical ports `e` prefix.

# %% [markdown]
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

# %% [markdown]
# ## pins
#
# You can add pins (port markers) to each port. Each foundry PDK does this differently, so gdsfactory supports all of them.
#
# - square with port inside the cell
# - square centered (half inside, half outside cell)
# - triangular
# - path (SiEPIC)
#
#
# by default `KCell.show()` will add triangular pins, so you can see the direction of the port in KLayout.

# %%
c = kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, angle=90)
c.draw_ports()
c

# %%
