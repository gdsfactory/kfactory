# port

Utilities for Ports.

Mainly renaming functions

## BasePort

Bases: `BaseModel`

Class representing the base port.

This does not have any knowledge of units. Exactly one of `cross_section` (symmetric) or `asymmetric_cross_section` (asymmetric) must be set, mirroring the `trans` / `dcplx_trans` pattern.

Fields:

- `name` (`str`)
- `kcl` (`KCLayout`)
- `cross_section` (`SymmetricalCrossSection | None`)
- `asymmetric_cross_section` (`AsymmetricalCrossSection | None`)
- `trans` (`Trans | None`)
- `dcplx_trans` (`DCplxTrans | None`)
- `info` (`Info`)
- `port_type` (`str`)

Validators:

- `check_exclusivity`

### any\_cross\_section

```
any_cross_section: SymmetricalCrossSection | AsymmetricalCrossSection
```

The cross section regardless of kind (symmetric or asymmetric).

### \_\_copy\_\_

```
__copy__() -> BasePort
```

Copy the BasePort.

### \_\_eq\_\_

```
__eq__(other: object) -> bool
```

Check if two ports are equal.

Two ports are equal if they have the same placement, name, layout, cross section, port type and info.

Placement is compared as `trans` if both ports store one, and as `get_dcplx_trans()` otherwise.

To ask whether two ports are the same physical port regardless of name, use `is_coincident`.

### check\_exclusivity

```
check_exclusivity() -> Self
```

Check that exactly one trans and exactly one cross\_section is set.

### get\_dcplx\_trans

```
get_dcplx_trans() -> kdb.DCplxTrans
```

Get the complex transformation.

### get\_trans

```
get_trans() -> kdb.Trans
```

Get the transformation.

### is\_coincident

```
is_coincident(other: BasePort) -> bool
```

Whether both ports are the same physical port, ignoring name and info.

Compares the layout, port type, cross section and placement.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `other` | `BasePort` | The port to compare against. | *required* |

### is\_symmetric

```
is_symmetric() -> bool
```

Whether the port carries a symmetric cross section.

### ser\_model

```
ser_model() -> BasePortDict
```

Serialize the BasePort.

### transform

```
transform(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> Self
```

Transform self.

### transformed

```
transformed(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> BasePort
```

Get a transformed copy of the BasePort.

## BasePortDict

Bases: `TypedDict`

TypedDict for the BasePort.

## DIRECTION

Bases: `IntEnum`

Alias for KLayout direction to compass directions.

## DPort

Bases: `ProtoPort[float]`

A port is the photonics equivalent to a pin in electronics.

In addition to the location and layer that defines a pin, a port also contains an orientation and a width. This can be fully represented with a transformation, integer and layer\_index.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `name` | `str` | String to name the port. |
| `width` | `float` | The width of the port in dbu. |
| `trans` | `Trans` | Transformation in dbu. If the port can be represented in 90° intervals this is the safe way to do so. |
| `dcplx_trans` |  | Transformation in micrometer. The port will autoconvert between trans and dcplx\_trans on demand. |
| `port_type` | `str` | A string defining the type of the port |
| `layer` | `LayerEnum \| int` | Index of the layer or a LayerEnum that acts like an integer, but can contain layer number and datatype |
| `info` | `Info` | A dictionary with additional info. Not reflected in GDS. Copy will make a (shallow) copy of it. |
| `d` | `Info` | Access port info in micrometer basis such as width and center / angle. |
| `kcl` | `KCLayout` | Link to the layout this port resides in. |

### asymmetric\_cross\_section

```
asymmetric_cross_section: DAsymmetricCrossSection
```

Get the asymmetric cross section of the port.

Raises:

| Type | Description |
| --- | --- |
| `TypeError` | if the port carries a symmetric cross section. |

### center

```
center = center
```

Returns port center.

### cross\_section

```
cross_section: DCrossSection | DAsymmetricCrossSection
```

Get the cross section of the port, symmetric or asymmetric.

Returns the symmetric cross section if the port carries one, otherwise the asymmetric cross section. Use `symmetric_cross_section` or `asymmetric_cross_section` to require a specific kind.

### dcplx\_trans

```
dcplx_trans = dcplx_trans_
```

Complex transformation (um based).

If the internal transformation is simple, return a complex copy.

The setter will set a complex transformation and overwrite the internal transformation (set simple to `None` and the complex to the provided value.

### orientation

```
orientation = orientation
```

Returns orientation in degrees for gdsfactory compatibility.

In the range of `[0,360)`

### symmetric\_cross\_section

```
symmetric_cross_section: DCrossSection
```

Get the symmetric cross section of the port.

Raises:

| Type | Description |
| --- | --- |
| `TypeError` | if the port carries an asymmetric cross section. |

### width

```
width: float
```

Width of the port in um.

### x

```
x: float
```

X coordinate of the port in um.

### y

```
y: float
```

Y coordinate of the port in um.

### \_\_init\_\_

```
__init__(name: str, *, width: float, layer: LayerEnum | int, trans: Trans | str, kcl: KCLayout | None = None, port_type: str = 'optical', info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: float, layer: LayerEnum | int, dcplx_trans: DCplxTrans | str, kcl: KCLayout | None = None, port_type: str = 'optical', info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: float, layer: LayerEnum | int, port_type: str = 'optical', orientation: float, center: tuple[float, float] = (0, 0), mirror_x: bool = False, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: float, layer_info: LayerInfo, trans: Trans | str, kcl: KCLayout | None = None, port_type: str = 'optical', info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: float, layer_info: LayerInfo, dcplx_trans: DCplxTrans | str, kcl: KCLayout | None = None, port_type: str = 'optical', info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: float, layer_info: LayerInfo, port_type: str = 'optical', orientation: float, center: tuple[float, float] = (0, 0), mirror_x: bool = False, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, cross_section: AnyCrossSectionInput, port_type: str = 'optical', orientation: float, center: tuple[float, float], mirror_x: bool = False, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, cross_section: AnyCrossSectionInput, trans: Trans | str, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ..., port_type: str = 'optical') -> None
```

```
__init__(name: str, *, cross_section: AnyCrossSectionInput, dcplx_trans: DCplxTrans | str, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ..., port_type: str = 'optical') -> None
```

```
__init__(*, base: BasePort) -> None
```

```
__init__(*, port: ProtoPort[Any]) -> None
```

```
__init__(name: str | None = None, *, width: float | None = None, layer: int | None = None, layer_info: LayerInfo | None = None, port_type: str = 'optical', trans: Trans | str | None = None, dcplx_trans: DCplxTrans | str | None = None, orientation: float = 0, center: tuple[float, float] = (0, 0), mirror_x: bool = False, port: ProtoPort[Any] | None = None, kcl: KCLayout | None = None, info: dict[str, int | float | str] | None = None, cross_section: AnyCrossSectionInput | None = None, base: BasePort | None = None) -> None
```

Create a port from dbu or um based units.

### copy

```
copy(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> DPort
```

Get a copy of a port.

Transformation order which results in `copy.trans`: - Trans: `trans * port.trans * post_trans` - DCplxTrans: `trans * port.dcplx_trans * post_trans`

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `trans` | `Trans \| DCplxTrans` | an optional transformation applied to the port to be copied. | `R0` |
| `post_trans` | `Trans \| DCplxTrans` | transformation to apply to the port after copying. | `R0` |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `port` | `DPort` | a copy of the port |

### copy\_polar

```
copy_polar(d: float = 0, d_orth: float = 0, orientation: float = 180, mirror: bool = False) -> DPort
```

Get a polar copy of the port.

This will return a port which is transformed relatively to the original port's transformation (orientation, angle and position).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `d` | `float` | The distance to the old port | `0` |
| `d_orth` | `float` | Orthogonal distance (positive is positive y for a port which is facing angle=0°) | `0` |
| `orientation` | `float` | Relative angle to the original port, in degrees. | `180` |
| `mirror` | `bool` | Whether to mirror the port relative to the original port. | `False` |

## Port

Bases: `ProtoPort[int]`

A port is the photonics equivalent to a pin in electronics.

In addition to the location and layer that defines a pin, a port also contains an orientation and a width. This can be fully represented with a transformation, integer and layer\_index.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `name` | `str` | String to name the port. |
| `width` | `int` | The width of the port in dbu. |
| `trans` | `Trans` | Transformation in dbu. If the port can be represented in 90° intervals this is the safe way to do so. |
| `dcplx_trans` |  | Transformation in micrometer. The port will autoconvert between trans and dcplx\_trans on demand. |
| `port_type` | `str` | A string defining the type of the port |
| `layer` | `LayerEnum \| int` | Index of the layer or a LayerEnum that acts like an integer, but can contain layer number and datatype |
| `info` | `Info` | A dictionary with additional info. Not reflected in GDS. Copy will make a (shallow) copy of it. |
| `d` | `Info` | Access port info in micrometer basis such as width and center / angle. |
| `kcl` | `KCLayout` | Link to the layout this port resides in. |

### asymmetric\_cross\_section

```
asymmetric_cross_section: AsymmetricCrossSection
```

Get the asymmetric cross section of the port.

Raises:

| Type | Description |
| --- | --- |
| `TypeError` | if the port carries a symmetric cross section. |

### cross\_section

```
cross_section: CrossSection | AsymmetricCrossSection
```

Get the cross section of the port, symmetric or asymmetric.

Returns the symmetric cross section if the port carries one, otherwise the asymmetric cross section. Use `symmetric_cross_section` or `asymmetric_cross_section` to require a specific kind.

### dcplx\_trans

```
dcplx_trans = dcplx_trans_
```

Complex transformation (um based).

If the internal transformation is simple, return a complex copy.

The setter will set a complex transformation and overwrite the internal transformation (set simple to `None` and the complex to the provided value.

### symmetric\_cross\_section

```
symmetric_cross_section: CrossSection
```

Get the symmetric cross section of the port.

Raises:

| Type | Description |
| --- | --- |
| `TypeError` | if the port carries an asymmetric cross section. |

### width

```
width: int
```

Width of the port in um.

### x

```
x: int
```

X coordinate of the port in dbu.

### y

```
y: int
```

Y coordinate of the port in dbu.

### \_\_init\_\_

```
__init__(*, name: str, width: int, layer: LayerEnum | int, trans: Trans | str, kcl: KCLayout | None = None, port_type: str = 'optical', info: dict[str, int | float | str] = ...) -> None
```

```
__init__(*, name: str, width: int, layer: LayerEnum | int, dcplx_trans: DCplxTrans | str, kcl: KCLayout | None = None, port_type: str = 'optical', info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: int, layer: LayerEnum | int, port_type: str = 'optical', angle: int, center: tuple[int, int], mirror_x: bool = False, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: int, layer_info: LayerInfo, trans: Trans | str, kcl: KCLayout | None = None, port_type: str = 'optical', info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: int, layer_info: LayerInfo, dcplx_trans: DCplxTrans | str, kcl: KCLayout | None = None, port_type: str = 'optical', info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, width: int, layer_info: LayerInfo, port_type: str = 'optical', angle: int, center: tuple[int, int], mirror_x: bool = False, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, cross_section: AnyCrossSectionInput, port_type: str = 'optical', angle: int, center: tuple[int, int], mirror_x: bool = False, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ...) -> None
```

```
__init__(name: str, *, cross_section: AnyCrossSectionInput, trans: Trans | str, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ..., port_type: str = 'optical') -> None
```

```
__init__(name: str, *, cross_section: AnyCrossSectionInput, dcplx_trans: DCplxTrans | str, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ..., port_type: str = 'optical') -> None
```

```
__init__(*, base: BasePort) -> None
```

```
__init__(*, port: ProtoPort[Any]) -> None
```

```
__init__(name: str | None = None, *, width: int | None = None, layer: int | None = None, layer_info: LayerInfo | None = None, port_type: str = 'optical', trans: Trans | str | None = None, dcplx_trans: DCplxTrans | str | None = None, angle: int | None = None, center: tuple[int, int] | None = None, mirror_x: bool = False, port: ProtoPort[Any] | None = None, kcl: KCLayout | None = None, info: dict[str, int | float | str] | None = None, cross_section: AnyCrossSectionInput | None = None, base: BasePort | None = None) -> None
```

Create a port from dbu or um based units.

### copy

```
copy(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> Port
```

Get a copy of a port.

Transformation order which results in `copy.trans`: - Trans: `trans * port.trans * post_trans` - DCplxTrans: `trans * port.dcplx_trans * post_trans`

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `trans` | `Trans \| DCplxTrans` | an optional transformation applied to the port to be copied. | `R0` |
| `post_trans` | `Trans \| DCplxTrans` | transformation to apply to the port after copying. | `R0` |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `port` | `Port` | a copy of the port |

### copy\_polar

```
copy_polar(d: int = 0, d_orth: int = 0, angle: int = 2, mirror: bool = False) -> Port
```

Get a polar copy of the port.

This will return a port which is transformed relatively to the original port's transformation (orientation, angle and position).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `d` | `int` | The distance to the old port | `0` |
| `d_orth` | `int` | Orthogonal distance (positive is positive y for a port which is facing angle=0°) | `0` |
| `angle` | `int` | Relative angle to the original port (0=0°,1=90°,2=180°,3=270°). | `2` |
| `mirror` | `bool` | Whether to mirror the port relative to the original port. | `False` |

Returns:

| Type | Description |
| --- | --- |
| `Port` | Port copied relative to it's current position and angle/orientation. |

## PortCheck

Bases: `IntFlag`

Check for port equality.

This is used to check if two ports are equal.

## ProtoPort

Bases: `ABC`

Base class for kf.Port, kf.DPort.

### angle

```
angle: Angle
```

Angle of the transformation.

In the range of `[0,1,2,3]` which are increments in 90°.

### asymmetric\_cross\_section

```
asymmetric_cross_section: TAsymmetricCrossSection[T]
```

Get the asymmetric cross section of the port. Raises if symmetric.

### base

```
base: BasePort
```

Get the BasePort associated with this Port.

### center

```
center: tuple[T, T]
```

Returns port center.

### cross\_section

```
cross_section: TCrossSection[T] | TAsymmetricCrossSection[T]
```

Get the cross section of the port, symmetric or asymmetric.

Returns the symmetric cross section if the port carries one, otherwise the asymmetric cross section. Use `symmetric_cross_section` or `asymmetric_cross_section` to require a specific kind (raising if the port carries the other kind).

### dcenter

```
dcenter: tuple[float, float]
```

Coordinate of the port in um.

### dcplx\_trans

```
dcplx_trans: DCplxTrans
```

Complex transformation (um based).

If the internal transformation is simple, return a complex copy.

The setter will set a complex transformation and overwrite the internal transformation (set simple to `None` and the complex to the provided value.

### dwidth

```
dwidth: float
```

Width of the port in um.

### dx

```
dx: float
```

X coordinate of the port in um.

### dy

```
dy: float
```

Y coordinate of the port in um.

### icenter

```
icenter: tuple[int, int]
```

Coordinate of the port in dbu.

### info

```
info: Info
```

Additional info about the port.

### iwidth

```
iwidth: int
```

Width of the port in dbu.

### ix

```
ix: int
```

X coordinate of the port in dbu.

### iy

```
iy: int
```

Y coordinate of the port in dbu.

### kcl

```
kcl: KCLayout
```

KCLayout associated to the prot.

### layer

```
layer: LayerEnum | int
```

Get the layer index of the port.

This corresponds to the port's cross section's main layer converted to the index.

### layer\_info

```
layer_info: LayerInfo
```

Get the layer info of the port.

This corresponds to the port's cross section's main layer.

### mirror

```
mirror: bool
```

Returns `True`/`False` depending on the mirror flag on the transformation.

### name

```
name: str
```

Name of the port.

### orientation

```
orientation: float
```

Returns orientation in degrees for gdsfactory compatibility.

In the range of `[0,360)`

### port\_type

```
port_type: str
```

Type of the port.

Usually "optical" or "electrical".

### symmetric\_cross\_section

```
symmetric_cross_section: TCrossSection[T]
```

Get the symmetric cross section of the port. Raises if asymmetric.

### trans

```
trans: Trans
```

Simple Transformation of the Port.

If this is set with the setter, it will overwrite any transformation or dcplx transformation

### width

```
width: T
```

Width of the port.

### x

```
x: T
```

X coordinate of the port.

### y

```
y: T
```

Y coordinate of the port.

### \_\_eq\_\_

```
__eq__(other: object) -> bool
```

Support for `port1 == port2` comparisons.

### \_\_init\_\_

```
__init__(name: str, *, width: T | None = None, layer: int | None = None, layer_info: LayerInfo | None = None, port_type: str = 'optical', trans: Trans | str | None = None, dcplx_trans: DCplxTrans | str | None = None, angle: T | None = None, center: tuple[T, T] | None = None, mirror_x: bool = False, port: Port | None = None, kcl: KCLayout | None = None, info: dict[str, int | float | str] = ..., cross_section: TCrossSection[T] | None = None, base: BasePort | None = None) -> None
```

Initialise a ProtoPort.

### \_\_repr\_\_

```
__repr__() -> str
```

String representation of port.

### copy

```
copy(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> ProtoPort[T]
```

Copy the port with a transformation.

### is\_coincident

```
is_coincident(other: ProtoPort[Any] | BasePort) -> bool
```

Whether two ports denote one physical port, ignoring the name.

See `BasePort.is_coincident`.

### is\_symmetric

```
is_symmetric() -> bool
```

Whether the port carries a symmetric cross section.

### print

```
print(print_type: Literal['dbu', 'um'] | None = None) -> None
```

Print the port pretty.

### to\_dtype

```
to_dtype() -> DPort
```

Convert the port to a um port.

### to\_itype

```
to_itype() -> Port
```

Convert the port to a dbu port.

### transform

```
transform(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> Self
```

Get a transformed copy of the BasePort.

## autorename

```
autorename(c: KCell, f: Callable[..., None], *args: Any, **kwargs: Any) -> None
```

Rename a KCell with a renaming function.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | KCell to be renamed. | *required* |
| `f` | `Callable[..., None]` | Renaming function. | *required* |
| `args` | `Any` | Arguments for the renaming function. | `()` |
| `kwargs` | `Any` | Keyword arguments for the renaming function. | `{}` |

## create\_port\_error

```
create_port_error(p1: ProtoPort[Any], p2: ProtoPort[Any], c1: AnyTKCell, c2: AnyTKCell, db: ReportDatabase, db_cell: RdbCell, cat: RdbCategory, dbu: float, inst_name1: str | None = None, inst_name2: str | None = None) -> None
```

Create an error report for two ports.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `p1` | `ProtoPort[Any]` | First port. | *required* |
| `p2` | `ProtoPort[Any]` | Second port. | *required* |
| `c1` | `AnyTKCell` | Cell of the first port. | *required* |
| `c2` | `AnyTKCell` | Cell of the second port. | *required* |
| `db` | `ReportDatabase` | ReportDatabase to add the item to. | *required* |
| `db_cell` | `RdbCell` | RdbCell to add the item to. | *required* |
| `cat` | `RdbCategory` | RdbCategory to add the item to. | *required* |
| `dbu` | `float` | Database unit. | *required* |
| `inst_name1` | `str \| None` | Optional explicit instance name for first port's instance. | `None` |
| `inst_name2` | `str \| None` | Optional explicit instance name for second port's instance. | `None` |

## filter\_direction

```
filter_direction(ports: Iterable[TPort], direction: int) -> filter[TPort]
```

Filter iterable/sequence of ports by direction `DIRECTION`.

## filter\_layer

```
filter_layer(ports: Iterable[TPort], layer: LayerEnum | int) -> filter[TPort]
```

Filter iterable/sequence of ports by layer index / LayerEnum.

## filter\_layer\_info

```
filter_layer_info(ports: Iterable[TPort], layer_info: LayerInfo) -> filter[TPort]
```

Filter iterable/sequence of ports by kdb.LayerInfo.

## filter\_layer\_pt\_reg

```
filter_layer_pt_reg(ports: Iterable[TPort], layer: LayerEnum | int | None = None, layer_info: LayerInfo | None = None, port_type: str | None = None, regex: str | None = None) -> Iterable[TPort]
```

Filter ports by layer index, port type and name regex.

## filter\_orientation

```
filter_orientation(ports: Iterable[TPort], orientation: float) -> filter[TPort]
```

Filter iterable/sequence of ports by direction `DIRECTION`.

## filter\_port\_type

```
filter_port_type(ports: Iterable[TPort], port_type: str) -> filter[TPort]
```

Filter iterable/sequence of ports by port\_type.

## filter\_regex

```
filter_regex(ports: Iterable[TPort], regex: str) -> filter[TPort]
```

Filter iterable/sequence of ports by port name.

## port\_check

```
port_check(p1: ProtoPort[Any], p2: ProtoPort[Any], checks: PortCheck | int = PortCheck.all_opposite) -> None
```

Check if two ports are equal.

## port\_polygon

```
port_polygon(width: int) -> kdb.Polygon
```

Gets a polygon representation for a given port width.

## rename\_by\_direction

```
rename_by_direction(ports: Iterable[ProtoPort[Any]], layer: LayerEnum | int | None = None, layer_info: LayerInfo | None = None, port_type: str | None = None, regex: str | None = None, dir_names: tuple[str, str, str, str] = ('E', 'N', 'W', 'S'), prefix: str = '') -> None
```

Rename ports by angle of their transformation.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ports` | `Iterable[ProtoPort[Any]]` | list of ports to be renamed | *required* |
| `layer` | `LayerEnum \| int \| None` | A layer index to filter by | `None` |
| `port_type` | `str \| None` | port\_type string to filter by | `None` |
| `regex` | `str \| None` | Regex string to use to filter the ports to be renamed. | `None` |
| `dir_names` | `tuple[str, str, str, str]` | Prefixes for the directions (east, north, west, south). | `('E', 'N', 'W', 'S')` |
| `prefix` | `str` | Prefix to add before `dir_names` | `''` |

```
         N0  N1
         |___|_
    W1 -|      |- E1
        |      |
    W0 -|______|- E0
         |   |
        S0   S1
```

## rename\_clockwise

```
rename_clockwise(ports: Iterable[ProtoPort[Any]], layer: LayerEnum | int | None = None, layer_info: LayerInfo | None = None, port_type: str | None = None, regex: str | None = None, prefix: str = 'o', start: int = 1) -> None
```

Sort and return ports in the clockwise direction.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ports` | `Iterable[ProtoPort[Any]]` | List of ports to rename. | *required* |
| `layer` | `LayerEnum \| int \| None` | Layer index / LayerEnum of port layer. | `None` |
| `port_type` | `str \| None` | Port type to filter the ports by. | `None` |
| `regex` | `str \| None` | Regex string to filter the port names by. | `None` |
| `prefix` | `str` | Prefix to add to all ports. | `'o'` |
| `start` | `int` | Start index per orientation. | `1` |

```
         o3  o4
         |___|_
    o2 -|      |- o5
        |      |
    o1 -|______|- o6
         |   |
        o8  o7
```

## rename\_clockwise\_multi

```
rename_clockwise_multi(ports: Iterable[ProtoPort[Any]], layers: Iterable[LayerEnum | int] | None = None, regex: str | None = None, type_prefix_mapping: dict[str, str] | None = None, start: int = 1) -> None
```

Sort and return ports in the clockwise direction.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ports` | `Iterable[ProtoPort[Any]]` | List of ports to rename. | *required* |
| `layers` | `Iterable[LayerEnum \| int] \| None` | Layer indexes / LayerEnums of port layers to rename. | `None` |
| `type_prefix_mapping` | `dict[str, str] \| None` | Port type to prefix matching in a dictionary. | `None` |
| `regex` | `str \| None` | Regex string to filter the port names by. | `None` |
| `start` | `int` | Start index per orientation. | `1` |

```
         o3  o4
         |___|_
    o2 -|      |- o5
        |      |
    o1 -|______|- o6
         |   |
        o8  o7
```
