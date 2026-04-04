# Frequently Asked Questions

Common questions and "gotcha" moments collected from kfactory users.
For executable examples see [Best Practices](best_practices.py).

---

## Units & coordinates

### Why does my geometry look 1000× too big (or too small)?

kfactory uses two coordinate systems in parallel:

| System | Unit | Used by |
|--------|------|---------|
| DBU (database units) | nm (1 nm = 1 DBU at default 1 nm/DBU) | KLayout internals, `KCell`, `Port`, `kdb.Trans` |
| µm | micrometres | Human-readable APIs, `DKCell`, `DPort`, `kdb.DTrans` |

The two never mix automatically.  Always convert explicitly:

```python
width_nm = kf.kcl.to_dbu(0.5)   # 0.5 µm → 500 DBU
width_um = kf.kcl.to_um(500)    # 500 DBU → 0.5 µm
```

The integer `to_dbu` conversion **rounds** — widths that are not a multiple of 2 DBU
are silently rounded.  Design your grid in multiples of 2 DBU to avoid asymmetry.

---

### Which factory takes DBU and which takes µm?

| Factory | Width / radius units |
|---------|---------------------|
| `straight_dbu_factory` | **DBU** |
| `taper_factory` | **DBU** |
| `bend_euler_factory` | **µm** |
| `bend_circular_factory` | **µm** |
| `bend_s_euler_factory` | **µm** |
| `bezier_factory` (via `kf.cells.bezier`) | **µm** |

When in doubt, look at the function name: `_dbu_` → DBU, otherwise µm.

---

## Ports

### I get a `TypeError` about a missing keyword argument on `add_port`

`add_port` requires the `port=` keyword — passing a port positionally raises a
`TypeError`:

```python
# Wrong
c.add_port(instance.ports["o1"])

# Correct
c.add_port(port=instance.ports["o1"])
```

---

### How do I rename a port when exposing it from a sub-cell?

```python
c.add_port(port=instance.ports["o1"], name="in")
```

Do **not** use `port.copy("new_name")` — that creates a detached copy not linked
to the instance.

---

### What are the port angle integers?

KLayout integer angles: `0` = East (0°), `1` = North (90°), `2` = West (180°), `3` = South (270°).

A port's angle is the **outward** direction — the direction a wire *exits* at that port.

---

## Layers & KCLayout

### My layer indices are wrong when I mix PDK cells with global `kf.kcl` cells

Each `KCLayout` has its own layer-index table.  A port or shape created under `kf.kcl`
carries layer index 0 for `WG`; a different `KCLayout` may map `WG` to index 5.

**Fix**: always pass `kcl=pdk` when constructing `kf.Port` inside a PDK cell:

```python
c.add_port(port=kf.Port(
    name="o1",
    trans=kf.kdb.Trans(0, False, 0, 0),
    width=500,
    layer=pdk.find_layer(L.WG),
    kcl=pdk,                      # <-- critical
))
```

---

### `KCLayout` isn't seeing my layers even though I set `kcl.infos`

Pass the **class** (not an instance) to `KCLayout.__init__`:

```python
# Correct — pass the class
pdk = kf.KCLayout("my_pdk", infos=LAYER)

# Wrong — setting after construction does not fully propagate
pdk = kf.KCLayout("my_pdk")
pdk.infos = LAYER()   # ← incomplete
```

After construction `pdk.infos` holds the instance; the `infos=` constructor
argument triggers internal layer registration that the post-hoc assignment skips.

---

### Where do I import `LayerLevel`, `LayerStack`, `layerenum_from_dict`?

These are **not** re-exported from top-level `kf`.  Import them from the sub-module:

```python
from kfactory.layer import LayerLevel, LayerStack, layerenum_from_dict
```

---

## Caching & `@kf.cell`

### My `@kf.cell` function raises `TypeError: unhashable type`

All arguments passed to a `@kf.cell` function must be hashable (Python can cache
them as dict keys).  Common offenders:

| Type | Fix |
|------|-----|
| `list` | Use `tuple` |
| `dict` | Use a frozen dataclass or a named tuple |
| `LayerInfo` object | Use `LayerInfo` directly — it *is* hashable |
| `CrossSection` object | Pass the name string; look it up inside with `kcl.get_icross_section(name)` |

---

### Why does `@pdk.cell` work but `@kf.cell` raises `ValueError: must use same KCLayout`?

When a cell factory creates `KCell(kcl=pdk)` the decorator must match.
`@kf.cell` registers cells in `kf.kcl`; `@pdk.cell` registers them in `pdk`.
Mix-up causes a layout-ownership mismatch at registration time.

**Rule**: use `@pdk.cell` (or `kf.cell(kcl=pdk)`) whenever your factory body
creates cells under a custom `KCLayout`.

---

## Routing

### What is the difference between the nominal radius and the effective radius?

Euler (clothoid) bends are longer than a circular arc of the same nominal radius
because the curvature ramps up gradually.  Their physical footprint extends further
than the radius you passed to the factory.

Always use `kf.routing.optical.get_radius(bend_cell)` when you need the actual
footprint radius for routing calculations:

```python
bend90 = kf.factories.euler.bend_euler_factory(kcl=kf.kcl)(
    width=0.5, radius=10, layer=L.WG, angle=90,
)
r_eff = kf.routing.optical.get_radius(bend90)   # > 10 µm for euler bends
```

Circular bends return the nominal radius unchanged (`get_radius(bend)` == `radius`).

---

### Path-length matching loops collide — how do I fix it?

Path-length matching inserts S-loops into shorter routes.  Each loop needs room:

- Routes must be spaced ≥ 150 µm apart horizontally.
- Routes must already contain at least one bend (purely straight routes have no
  room for loop insertion).

Increase the horizontal pitch between ports, or add explicit waypoints to force
bends before the matching section.

---

### `route_bundle` shows a KLayout error dialog during headless builds

Collision detection calls `kdb.show_error()` which spawns a dialog in GUI mode.
Suppress it for CI / notebook execution:

```python
kf.routing.optical.route_bundle(
    c, start_ports, end_ports,
    bend90_cell=bend90,
    straight_factory=sf,
    on_collision=None,   # <-- suppress dialog
)
```

---

### `route_smart` raises a `ValueError` about `BasePort`

`route_smart` expects kfactory's internal `BasePort` (a Pydantic model), **not**
a `kf.Port`.  Use `route_manhattan` + `place_manhattan` directly for low-level
single-route control instead.

---

### All-angle bundle fails with "not enough space"

Each backbone segment between waypoints must be at least 2× the effective bend
radius.  If your waypoints are too close together the router cannot fit the entry
and exit bends.  Space backbone waypoints further apart.

---

## Enclosures

### My cladding doesn't follow the taper profile — it's rectangular

Use `apply_minkowski_y` which morphologically expands along the Y axis, following
non-rectangular outlines:

```python
enc = kf.LayerEnclosure(sections=[(L.WGCLAD, 2_000)])
enc.apply_minkowski_y(c)   # call after shapes are drawn
```

`apply_minkowski_tiled` (the default) works on the merged bounding region and
can produce rectangular results for tapered shapes.

---

### `LayerEnclosure` with `dsections=` raises a conversion error

`dsections=` uses µm values and needs a layout context to convert them to DBU.
Pass `kcl=` at construction time:

```python
enc = kf.LayerEnclosure(
    dsections=[(L.WGCLAD, 0, 2.0)],
    kcl=kf.kcl,          # <-- required for µm→DBU conversion
)
```

---

## Utilities

### `fill_tiled` doesn't appear to do anything

`fill_tiled` modifies the target cell **in-place** and returns `None`.  It must be
called while the cell is unlocked, i.e., **inside** the `@kf.cell` function body
(not after the decorator has finalised the cell).

---

### `packing.pack_kcells` ignores my `spacing` value

`spacing`, `max_width`, and `max_height` are all in **DBU**, not µm.  Convert first:

```python
kf.packing.pack_kcells(
    cells,
    spacing=kf.kcl.to_dbu(2),      # 2 µm → DBU
    max_width=kf.kcl.to_dbu(500),
)
```

---

### `inst.dmove((x, y))` works but `inst.dmove(kf.kdb.DVector(x, y))` raises `TypeError`

`dmove` unpacks its argument as a 2-tuple internally.  Pass a plain Python tuple
or a 2-element sequence, not a `kdb.DVector`:

```python
inst.dmove((dx, dy))              # correct
inst.dmove(kf.kdb.DVector(dx, dy))  # TypeError
```

---

## Schematics

### `create_inst` raises a JSON serialisation error

Settings passed to `create_inst` must be JSON-serialisable.  Do **not** pass
`LayerInfo` objects — use `int`, `float`, or `str` instead:

```python
# Wrong
sch.create_inst("wg", settings={"layer": L.WG})

# Correct
sch.create_inst("wg", settings={"layer": (1, 0)})
```

---

## Difftest / regression testing

### `difftest()` raises `AssertionError` on the first run

This is expected — on the first run there is no reference GDS file to compare
against.  The reference is written by that first run.  Re-run your test suite
a second time; it will pass once the reference exists.

Do **not** call `difftest()` in executable notebook pages — it will always fail
in a clean CI environment.  Show it as a code comment instead.

## See Also

| Topic | Where |
|-------|-------|
| Common pitfalls with code examples | [How-To: Best Practices](best_practices.py) |
| Common design patterns | [How-To: Patterns](patterns.py) |
| Contributing to kfactory | [How-To: Contributing](contributing.md) |
| DBU vs µm coordinate systems | [Core Concepts: DBU vs µm](../concepts/dbu_vs_um.py) |
