# DBU vs µm — coordinate systems

kfactory inherits two parallel coordinate systems from KLayout:

| System | Unit | Type | KLayout prefix |
| --- | --- | --- | --- |
| **DBU** — database units | 1 nm (by default) | `int` | no prefix / `I` |
| **µm** — micrometres | 1 µm | `float` | `D` |

Every geometry class exists in both flavours:

| DBU (integer) | µm (float) |
| --- | --- |
| `kdb.Box` | `kdb.DBox` |
| `kdb.Polygon` | `kdb.DPolygon` |
| `kdb.Point` | `kdb.DPoint` |
| `kdb.Vector` | `kdb.DVector` |
| `kdb.Trans` | `kdb.DTrans` |
| `kdb.Edge` | `kdb.DEdge` |

The relationship is fixed: **1 µm = 1 000 DBU** (because `kf.kcl.dbu = 0.001 µm`). This page shows how to use both, convert between them, and choose the right one.

```
import kfactory as kf


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    SLAB: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)


L = LAYER()
kf.kcl.infos = L
```

## The `dbu` constant

`kf.kcl.dbu` is the size of one DBU expressed in µm. The default is `0.001`, meaning **1 DBU = 0.001 µm = 1 nm**.

```
print(f"dbu = {kf.kcl.dbu} µm/DBU")
print(f"1 µm = {kf.kcl.to_dbu(1.0)} DBU")
print(f"1000 DBU = {kf.kcl.to_um(1000)} µm")
```

```
dbu = 0.001 µm/DBU
1 µm = 1000 DBU
1000 DBU = 1.0 µm
```

## Geometry objects

### `Box` vs `DBox`

```
# DBU: integer coordinates, 1 unit = 1 nm
box_dbu = kf.kdb.Box(2000, 1000)  # 2 µm × 1 µm
print(f"Box (DBU):  {box_dbu}")

# µm: float coordinates
box_um = kf.kdb.DBox(2.0, 1.0)  # same size
print(f"DBox (µm): {box_um}")
```

```
Box (DBU):  (-1000,-500;1000,500)
DBox (µm): (-1,-0.5;1,0.5)
```

Both represent the same physical area. KLayout centres boxes at the origin by default, so the corners are `(±half_width, ±half_height)`.

### Converting between DBU and µm

```
# DBU → µm
box_um_from_dbu = box_dbu.to_dtype(kf.kcl.dbu)
print(f"Box → DBox: {box_um_from_dbu}")

# µm → DBU
box_dbu_from_um = box_um.to_itype(kf.kcl.dbu)
print(f"DBox → Box: {box_dbu_from_um}")
```

```
Box → DBox: (-1,-0.5;1,0.5)
DBox → Box: (-1000,-500;1000,500)
```

### `Trans` vs `DTrans`

`Trans` / `DTrans` encode a rotation + optional mirror + translation. The displacement part uses DBU integers / µm floats respectively.

```
# DBU: displacement in integer DBU
t_dbu = kf.kdb.Trans(0, False, 5000, 0)  # 5 µm to the right
print(f"Trans (DBU):  {t_dbu}")

# µm: displacement in float µm
t_um = kf.kdb.DTrans(0, False, 5.0, 0.0)
print(f"DTrans (µm): {t_um}")

# Convert
print(f"Trans → DTrans: {t_dbu.to_dtype(kf.kcl.dbu)}")
print(f"DTrans → Trans: {t_um.to_itype(kf.kcl.dbu)}")
```

```
Trans (DBU):  r0 5000,0
DTrans (µm): r0 5,0
Trans → DTrans: r0 5,0
DTrans → Trans: r0 5000,0
```

## Cell bounding boxes

`KCell` exposes bounding boxes in both systems:

| Method | Returns |
| --- | --- |
| `cell.bbox()` | `kdb.Box` in DBU |
| `cell.dbbox()` | `kdb.DBox` in µm |

```
li = kf.kcl.find_layer(L.WG)

example = kf.KCell("example_bbox")
example.shapes(li).insert(kf.kdb.Box(4000, 2000))  # 4 µm × 2 µm

print(f"bbox  (DBU): {example.bbox()}")  # integer coords
print(f"dbbox (µm):  {example.dbbox()}")  # float coords
```

```
bbox  (DBU): (-2000,-1000;2000,1000)
dbbox (µm):  (-2,-1;2,1)
```

## Ports: `width` vs `dwidth`

Port width is stored internally in **DBU** (`int`). The `.dwidth` property converts on-the-fly to µm:

```
p = kf.Port(
    name="o1",
    trans=kf.kdb.Trans(0, False, 2000, 0),
    width=500,  # 500 DBU = 0.5 µm
    layer=li,
    port_type="optical",
)
print(f"Port width  (DBU): {p.width}")  # 500
print(f"Port dwidth (µm):  {p.dwidth}")  # 0.5
```

```
Port width  (DBU): 500
Port dwidth (µm):  0.5
```

## Shapes: inserting DBU and µm geometry

`cell.shapes(layer_index).insert(...)` accepts both DBU and µm objects directly — KLayout converts `D`-prefixed shapes automatically using the layout's `dbu`.

```
mixed = kf.KCell("shapes_mixed")

# Insert a DBU box
mixed.shapes(li).insert(kf.kdb.Box(3000, 500))

# Insert a µm DPolygon — automatically converted
dpoly = kf.kdb.DPolygon(kf.kdb.DBox(1.0, 0.25))
mixed.shapes(li).insert(dpoly)

print(f"Shapes count: {mixed.shapes(li).size()}")
print(f"Total bbox (DBU): {mixed.bbox()}")
print(f"Total dbbox (µm): {mixed.dbbox()}")
```

```
Shapes count: 2
Total bbox (DBU): (-1500,-250;1500,250)
Total dbbox (µm): (-1.5,-0.25;1.5,0.25)
```

## Choosing the right system

**Use DBU (`int`)** when: - Writing internal cell logic — integer arithmetic avoids floating-point drift. - Defining port `width` and `trans` — the API stores these as integers. - Doing boolean operations (`Region`) — `Region` always works in DBU.

**Use µm (`float`)** when: - Accepting user-facing parameters in a factory function — `width=0.5` reads more naturally than `width=500`. - Reading back coordinates for display or export. - Constructing paths or references from physical dimensions.

A common idiom is to accept µm at the function boundary and convert immediately:

```
@kf.cell
def waveguide(width: float = 0.5, length: float = 10.0) -> kf.KCell:
    """Simple waveguide with µm parameters converted to DBU internally."""
    c = kf.KCell()
    w = kf.kcl.to_dbu(width)  # → int DBU
    ll = kf.kcl.to_dbu(length)  # → int DBU

    c.shapes(li).insert(kf.kdb.Box(ll, w))
    c.add_port(
        port=kf.Port(
            name="o1",
            trans=kf.kdb.Trans(2, False, -ll // 2, 0),
            width=w,
            layer=li,
            port_type="optical",
        )
    )
    c.add_port(
        port=kf.Port(
            name="o2",
            trans=kf.kdb.Trans(0, False, ll // 2, 0),
            width=w,
            layer=li,
            port_type="optical",
        )
    )
    return c


wg = waveguide(width=0.5, length=10.0)
print(f"bbox  (DBU): {wg.bbox()}")
print(f"dbbox (µm):  {wg.dbbox()}")
print(f"Port o1 dwidth: {wg.ports['o1'].dwidth} µm")
```

```
bbox  (DBU): (-5000,-250;5000,250)
dbbox (µm):  (-5,-0.25;5,0.25)
Port o1 dwidth: 0.5 µm
```

## Quick-reference table

| Task | DBU expression | µm expression |
| --- | --- | --- |
| Rectangle | `kdb.Box(w, h)` | `kdb.DBox(w, h)` |
| Point | `kdb.Point(x, y)` | `kdb.DPoint(x, y)` |
| Translation | `kdb.Trans(rot, mir, x, y)` | `kdb.DTrans(rot, mir, x, y)` |
| Cell bbox | `cell.bbox()` | `cell.dbbox()` |
| Port width | `port.width` | `port.dwidth` |
| Convert DBU→µm | `kf.kcl.to_um(n)` | — |
| Convert µm→DBU | `kf.kcl.to_dbu(x)` | — |
| Shape convert | `dshape.to_itype(kf.kcl.dbu)` | `shape.to_dtype(kf.kcl.dbu)` |

## See Also

| Topic | Where |
| --- | --- |
| KCell and DKCell side-by-side | [Core Concepts: KCell](<https://gdsfactory.github.io/kfactory/dev/concepts/kcell/index.md>) |
| Port width and position in DBU | [Core Concepts: Ports](<https://gdsfactory.github.io/kfactory/dev/concepts/ports/index.md>) |
| Factory functions and their unit conventions | [Components: Factory Functions](<https://gdsfactory.github.io/kfactory/dev/components/cells/factories/overview/index.md>) |
| FAQ — when to use DBU vs µm | [How-To: FAQ](<https://gdsfactory.github.io/kfactory/dev/howto/faq/index.md>) |
