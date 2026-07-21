# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     formats: py:percent
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
# # Schematic Ports & Pins
#
# A schematic exposes connectivity to the outside world through two complementary
# objects:
#
# - **Ports** — individual terminals (single waveguide port, single electrical
#   contact). They get materialized as `KCell.ports` on the resulting cell.
# - **Pins** — *named bundles of ports*. They group one or more cell-level ports under
#   a single logical terminal (e.g. a DC pad's two contacts, a multi-mode bus).
#
# This tutorial covers both APIs end-to-end: how to expose ports at the schematic
# level, how to pin them together, how the schematic stores everything as Pydantic
# data, and how the YAML round-trip works.
#
# For schematic basics (instances, placements, connections) see
# [Schematic-Driven Design](overview.py).

# %%
import kfactory as kf

# %% [markdown]
# ## PDK setup
#
# A minimal PDK with a single `straight` cell. The cell exposes two waveguide ports
# (`o1`, `o2`) and groups them under one cell-level pin called `"dc"`.


# %%
class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)


L = LAYER()
pdk = kf.KCLayout("SCHEM_PORTS_PINS", infos=LAYER)


@pdk.cell
def straight(width: int = 500, length: int = 10_000) -> kf.KCell:
    """Straight waveguide. Both optical ports are also grouped under a `"dc"` pin."""
    c = pdk.kcell()
    c.shapes(L.WG).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
    p1 = c.create_port(
        name="o1",
        width=width,
        trans=kf.kdb.Trans(rot=2, x=0, y=0),
        layer_info=L.WG,
    )
    p2 = c.create_port(
        name="o2",
        width=width,
        trans=kf.kdb.Trans(x=length, y=0),
        layer_info=L.WG,
    )
    c.create_pin(name="dc", ports=[p1, p2], pin_type="DC", info={"role": "bus"})
    return c


# %% [markdown]
# ## Part 1 — Ports on a schematic
#
# A `KCell` exposes ports via `c.create_port(...)`. A *schematic* exposes ports via
# `schematic.ports` — a dict mapping name → one of three things:
#
# | Stored as | Created with | Meaning |
# |-----------|--------------|---------|
# | `PortRef` / `PortArrayRef` | `schematic.add_port(name, port=inst.ports[...])` | Forward an instance port up to the top level |
# | `Port[T]` | `schematic.create_port(name, cross_section, x, y, ...)` | A new placeable top-level port whose position is computed at build time |
#
# Schematic ports are materialized as `KCell.ports` when the cell is built.
# For `PortRef`, the underlying instance port is added to the top-level cell under
# the schematic-port key name.

# %% [markdown]
# ### `add_port` — forward an instance port
#
# Use `add_port` whenever you want a top-level port that simply mirrors an existing
# instance port. The schematic stores a `PortRef` lazily; the cell port is created
# when `create_cell` runs.


# %%
@pdk.schematic_cell
def forwarded_ports() -> kf.Schematic:
    schematic = kf.Schematic(kcl=pdk)

    s = schematic.create_inst(
        name="s", component="straight", settings={"width": 500, "length": 10_000}
    )
    s.place(x=0, y=0)

    # forward each instance port up to the top level. the schematic-port key name
    # becomes the cell-port name on the resulting KCell — it does not have to match
    # the instance's port name.
    schematic.add_port(name="left", port=s.ports["o1"])
    schematic.add_port(name="right", port=s.ports["o2"])

    return schematic


cell = forwarded_ports()
print("cell ports:", [p.name for p in cell.ports])

# %% [markdown]
# Inside the schematic, the entries are `PortRef` objects pointing at the underlying
# instance:

# %%
for name, port in cell.schematic.ports.items():
    print(f"  {name!r}: {port}")

# %% [markdown]
# ### `create_port` — placeable top-level port
#
# Use `create_port` when the top-level port is *not* a copy of an instance port —
# typically when you want a port at a fixed location, or whose position/orientation
# is a function of an instance's geometry but not directly any port.
#
# Both absolute coordinates and `PortRef`s are accepted for `x`, `y`, and
# `orientation`, so you can pin the new port to an instance:


# %%
@pdk.schematic_cell
def fanout_port() -> kf.Schematic:
    schematic = kf.Schematic(kcl=pdk)

    s = schematic.create_inst(
        name="s", component="straight", settings={"width": 500, "length": 10_000}
    )
    s.place(x=0, y=0)

    # an extra "monitor" port placed 5 µm above the centre of the straight, facing up
    schematic.create_port(
        name="monitor",
        cross_section="WG_500",
        x=5_000,
        y=5_000,
        orientation=90,
    )

    schematic.add_port(name="left", port=s.ports["o1"])
    schematic.add_port(name="right", port=s.ports["o2"])
    return schematic


# %% [markdown]
# !!! note
#     `create_port` requires a registered cross-section. The example above assumes a
#     `WG_500` cross-section was registered on the PDK; in this notebook we don't
#     instantiate `fanout_port()` because the PDK has no cross-section table — it's
#     here for API illustration only. See the [PDK page](../pdk/creating_pdk.py) for
#     setting up cross-sections.

# %% [markdown]
# ## Part 2 — Pins
#
# A pin is a named bundle of ports. It carries a `pin_type` (`"DC"` by default) and
# free-form `info`. At the schematic level there are two ways to define one:
#
# | Stored as | Created with | Meaning |
# |-----------|--------------|---------|
# | `Pin` | `schematic.create_pin(name, ports=[...])` | Group existing top-level schematic ports |
# | `PinRef` | `schematic.add_pin(name, pin=inst.pins["..."])` | Forward an instance's pin to the top level |
#
# Pins are **structural only** for now — they're not part of nets, connections, or
# routes. They sit alongside ports on the schematic and on the resulting cell.

# %% [markdown]
# ### `create_pin` — explicit grouping
#
# Use this when the pin's member ports come from different instances or don't align
# with any single instance pin. The constituent port names must already exist in
# `schematic.ports` (typically via `add_port`).


# %%
@pdk.schematic_cell
def explicit_pin() -> kf.Schematic:
    schematic = kf.Schematic(kcl=pdk)

    s = schematic.create_inst(
        name="s", component="straight", settings={"width": 500, "length": 10_000}
    )
    s.place(x=0, y=0)

    schematic.add_port(name="left", port=s.ports["o1"])
    schematic.add_port(name="right", port=s.ports["o2"])

    schematic.create_pin(
        name="bus", ports=["left", "right"], pin_type="RF", info={"freq": 5}
    )

    return schematic


cell = explicit_pin()
for pin in cell.pins:
    print(
        f"pin {pin.name!r}:"
        f" ports={[p.name for p in pin.ports]}"
        f" type={pin.pin_type!r}"
        f" info={dict(pin.info)}"
    )

# %% [markdown]
# ### `add_pin` — forward an instance pin
#
# Use `add_pin` when an instance already exposes a pin you want at the top level.
# `inst.pins["name"]` produces a `PinRef`; pass it to `add_pin`.
#
# **Pre-condition:** every constituent port of the instance pin must be exposed as a
# top-level schematic port beforehand. The materialization step at `create_cell`
# time looks up each port via that exposure — if any port is missing you'll get a
# clear error.


# %%
@pdk.schematic_cell
def forwarded_pin() -> kf.Schematic:
    schematic = kf.Schematic(kcl=pdk)

    s = schematic.create_inst(
        name="s", component="straight", settings={"width": 500, "length": 10_000}
    )
    s.place(x=0, y=0)

    # both underlying ports of the instance's "dc" pin are needed at the top level
    schematic.add_port(name="left", port=s.ports["o1"])
    schematic.add_port(name="right", port=s.ports["o2"])

    # forward the pin — pin_type and info are inherited from the instance pin
    schematic.add_pin(name="dc", pin=s.pins["dc"])
    return schematic


cell = forwarded_pin()
for pin in cell.pins:
    print(f"pin {pin.name!r}: type={pin.pin_type!r} info={dict(pin.info)}")

# %% [markdown]
# ## Part 3 — YAML round-trip
#
# Schematic ports and pins serialize alongside instances and placements. The format
# accepts two shorthands:
#
# - Ports: `"<inst>,<port>"` (forwarded) or a `{x, y, ...}` dict (placeable)
# - Pins: `"<inst>,<pin>"` (forwarded) or a `{ports: [...], pin_type, info}` block

# %%
yaml_str = """
instances:
  s:
    component: straight
    settings: {width: 500, length: 10000}

placements:
  s: {x: 0, y: 0}

ports:
  left:  s,o1
  right: s,o2

pins:
  bus:
    ports: [left, right]
    pin_type: RF
  fwd: s,dc
"""

from ruamel.yaml import YAML

yaml = YAML(typ="safe")
schematic = kf.Schematic.from_pic_yml(yaml.load(yaml_str))

print("ports:", {n: type(p).__name__ for n, p in schematic.ports.items()})
print("pins:", {n: type(p).__name__ for n, p in schematic.pins.items()})
print("bus.ports:", schematic.pins["bus"].ports)
print("fwd:", schematic.pins["fwd"])

# %% [markdown]
# ## Pitfalls
#
# - **Schematic-port key ≠ original port name.** When you forward an instance port
#   with `add_port(name="left", port=s.ports["o1"])`, the cell's top-level port is
#   named `"left"`, not `"o1"`. The same naming applies to ports referenced from
#   pins.
# - **Forwarded pins need exposed underlying ports.** When you call
#   `add_pin(pin=inst.pins["x"])`, every constituent port of the instance pin must
#   already be a top-level schematic port. The materialization step at `create_cell`
#   time raises a clear error otherwise.
# - **Pins are top-level only.** They don't take part in nets, connections, or
#   routes. Connect ports the usual way (`inst.connect`, `add_route`); pins exist
#   purely to group ports for tooling that consumes them.
# - **Names are unique within their dict.** `add_port`/`create_port` share
#   `schematic.ports`; `add_pin`/`create_pin` share `schematic.pins`. Each raises on
#   duplicate names.
#
# ## Summary
#
# | Operation | API |
# |-----------|-----|
# | Forward an instance port to the top level | `schematic.add_port(name, port=inst.ports[...])` |
# | Create a placeable top-level port | `schematic.create_port(name, cross_section, x, y, orientation)` |
# | Reference an instance port | `inst.ports["o1"]` → `PortRef` |
# | Reference an array instance port | `inst.ports["o1", ia, ib]` → `PortArrayRef` |
# | Group existing top-level ports into a pin | `schematic.create_pin(name, ports=[...], pin_type, info)` |
# | Forward an instance pin to the top level | `schematic.add_pin(name, pin=inst.pins[...])` |
# | Reference an instance pin | `inst.pins["dc"]` → `PinRef` |
# | Inspect cell-level ports / pins | `cell.ports`, `cell.pins` |
