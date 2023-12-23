# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Instances and ports
#
# GDS allows your the cell once in memory and instance or Instance the cell multiple times.

# %% [markdown]
# As you build cells you can instantiate other cells. Adding an instance is like having a pointer to a cell.
#
# The GDSII specification allows the use of instances, and similarly kfactory uses them (with the `create_inst()` function).
# what is an instance? Simply put:  **An instance does not contain any geometry. It only *points* to an existing geometry**.
#
# Say you have a ridiculously large polygon with 100 billion vertices that you call BigPolygon. It's huge, and you need to use it in your design 250 times.
# Well, a single copy of BigPolygon takes up 1MB of memory, so you don't want to make 250 copies of it
# You can instead *instances* the polygon 250 times.
# Each instance only uses a few bytes of memory -- it only needs to know the memory address of BigPolygon, position, rotation and mirror.
# This way, you can keep one copy of BigPolygon and use it again and again.
#
# You can start by making a blank `KFactory` and add a single polygon to it.

# %%
import kfactory as kf

# Create a blank Cell
p = kf.KCell()

# Add a polygon
xpts = [0, 0, 5, 6, 9, 12]
ypts = [0, 1, 1, 2, 2, 0]
p.shapes(p.kcl.layer(2, 0)).insert(
    kf.kdb.DPolygon([kf.kdb.DPoint(x, y) for x, y in zip(xpts, ypts)])
)

# plot the Cell with the polygon in it
p

# %% [markdown]
# Now, you want to reuse this polygon repeatedly without creating multiple copies of it.
#
# To do so, you need to make a second blank `Cell`, this time called `c`.
#
# In this new Cell you *instance* our Cell `p` which contains our polygon.

# %%
c = kf.KCell(name="Cell_with_instances")  # Create a new blank Cell
poly_ref = c.create_inst(p)  # instance the Cell "p" that has the polygon in it
c

# %% [markdown]
# you just made a copy of your polygon -- but remember, you didn't actually
# make a second polygon, you just made a instance (aka pointer) to the original
# polygon.  Let's add two more instances to `c`:

# %%
poly_ref2 = c.create_inst(p)  # instance the Cell "p" that has the polygon in it
poly_ref3 = c.create_inst(p)  # instance the Cell "p" that has the polygon in it
c

# %% [markdown]
# Now you have 3x polygons all on top of each other.  Again, this would appear
# useless, except that you can manipulate each instance independently. Notice that
# when you called `c.add_ref(p)` above, we saved the result to a new variable each
# time (`poly_ref`, `poly_ref2`, and `poly_ref3`)?  You can use those variables to
# reposition the instances.

# %%
poly_ref2.transform(
    kf.kdb.DCplxTrans(1, 15, False, 0, 0)
)  # Rotate the 2nd instance we made 15 degrees
poly_ref3.transform(
    kf.kdb.DCplxTrans(1, 30, False, 0, 0)
)  # Rotate the 3rd instance we made 30 degrees
c

# %% [markdown]
# Now you're getting somewhere! You've only had to make the polygon once, but you're
# able to reuse it as many times as you want.
#
# ## Modifying the instances
#
# What happens when you change the original geometry of the instance?  In your case, your instances in
# `c` all point to the Cell `p` that with the original polygon.  Let's try
# adding a second polygon to `p`.
#
# First you add the second polygon and make sure `P` looks like you expect:

# %%
# Add a 2nd polygon to "p"
xpts = [14, 14, 16, 16]
ypts = [0, 2, 2, 0]
p.shapes(p.kcl.layer(1, 0)).insert(
    kf.kdb.DPolygon([kf.kdb.DPoint(x, y) for x, y in zip(xpts, ypts)])
)
p

# %% [markdown]
# That looks good.  Now let's find out what happened to `c` that contains the
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
# Let's try making instances a level deeper by referencing `c`.  Note here we use
# the `<<` operator to add the instances -- this is just shorthand, and is
# exactly equivalent to using `add_ref()`

# %%
c2 = kf.KCell(name="array_sample")  # Create a new blank Cell
d_ref1 = c2.create_inst(c)  # instance the Cell "c" that 3 instances in it
d_ref2 = c2 << c  # Use the "<<" operator to create a 2nd instance to c
d_ref3 = c2 << c  # Use the "<<" operator to create a 3rd instance to c

d_ref1.transform(kf.kdb.DTrans(20.0, 0.0))
d_ref2.transform(kf.kdb.DTrans(40.0, 0.0))

c2

# %% [markdown]
# As you've seen you have two ways to add an instance to our cell:
#
# 1. create the instance and add it to the cell

# %%
c = kf.KCell(name="instance_sample")
w = kf.cells.straight.straight(length=10, width=0.6, layer=c.kcl.layer(1, 0))
wr = kf.kdb.CellInstArray(w._kdb_cell, kf.kdb.Trans.R0)
c.insert(wr)
c

# %% [markdown]
# 2. or do it in a single line

# %%
c = kf.KCell(name="instance_sample_shorter_syntax")
wr = c << kf.cells.straight.straight(length=10, width=0.6, layer=c.kcl.layer(1, 0))
c

# %% [markdown]
# in both cases you can move the instance `wr` after created

# %%
c = kf.KCell(name="two_instances")
wr1 = c << kf.cells.straight.straight(length=10, width=0.6, layer=c.kcl.layer(1, 0))
wr2 = c << kf.cells.straight.straight(length=10, width=0.6, layer=c.kcl.layer(1, 0))
wr2.transform(kf.kdb.DTrans(0.0, 10.0))
c.add_ports(wr1.ports, prefix="top_")
c.add_ports(wr2.ports, prefix="bot_")

# %%
c.ports

# %% [markdown]
# You can also auto_rename ports using gdsfactory default convention, where ports are numbered clockwise starting from the bottom left

# %%
c.auto_rename_ports()

# %%
c.ports

# %%
c

# %% [markdown]
# ## Arrays of instances
#
# In GDS, there's a type of structure called a "Instance" which takes a cell and repeats it NxM times on a fixed grid spacing. For convenience, `Cell` includes this functionality with the add_array() function.
# Note that CellArrays are not compatible with ports (since there is no way to access/modify individual elements in a GDS cellarray)
#
# Let's make a new Cell and put a big array of our Cell `c` in it:

# %%
# not converted yet

c3 = kf.KCell("array_of_instances")  # Create a new blank Cell
aref = c3.create_inst(
    c, na=6, nb=3, a=kf.kdb.Vector(20000, 0), b=kf.kdb.Vector(0, 15000)
)  # instance the Cell "c" 3 instances in it with a 3 rows, 6 columns array
c3

# %% [markdown]
# ## connect instances
#
# We have seen that once you create a instance you can manipulate the instance to move it to a location. Here we are going to connect that instance to a port. Remember that we follow that a certain instance `source` connects to a `destination` port

# %%
c = kf.KCell()
bend = kf.cells.euler.bend_euler(radius=5, width=1, layer=0)
b1 = c << bend
b2 = c << bend
b2.connect("o1", b1.ports["o2"])
c

# %%
c = kf.KCell()
b1 = c << kf.cells.euler.bend_euler(radius=5, width=1, layer=0, angle=30)
b2 = c << kf.cells.euler.bend_euler(radius=5, width=1, layer=0, angle=30)
b2.connect("o1", b1.ports["o2"])
c.show()
c

# %% [markdown]
# ![](https://i.imgur.com/oenlUwg.png)
#
# This non-manhattan connect will create less than 1nm gaps that you can fix by flattening the references.

# %%
c = kf.KCell()
b1 = c << kf.cells.euler.bend_euler(radius=5, width=1, layer=0, angle=30)
b2 = c << kf.cells.euler.bend_euler(radius=5, width=1, layer=0, angle=30)
b2.connect("o1", b1.ports["o2"])
b2.flatten()
c.show()
c

# %% [markdown]
# Which fixes the issue.
#
# ![](https://i.imgur.com/t0J31Wg.png)

# %% [markdown]
# ## Port naming
#
# You have the freedom to name the ports as you want, and you can use `c.auto_rename_ports` to rename them later on.
#
# Here is the default naming convention.
#
# Ports are numbered clock-wise starting from the bottom left corner
#
# Optical ports have `o` prefix and Electrical ports `e` prefix

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
# by default `KCell.show()` will add triangular pins, so you can see the direction of the port in Klayout.

# %%
c = kf.cells.euler.bend_euler(radius=5, width=1, layer=0, angle=90)
c.draw_ports()
c

# %%
