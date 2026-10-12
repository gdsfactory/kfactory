# ports

## DCreatePort

Bases: `ABC`

Protocol for a create\_port functionality

### create\_port

```
create_port(*, trans: Trans, width: float, layer: int, name: str, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> DPort
```

```
create_port(*, dcplx_trans: DCplxTrans, width: float, layer: LayerEnum | int, name: str, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> DPort
```

```
create_port(*, width: float, layer: LayerEnum | int, center: tuple[float, float], orientation: float, name: str, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> DPort
```

```
create_port(*, trans: Trans, width: float, layer_info: LayerInfo, name: str, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> DPort
```

```
create_port(*, dcplx_trans: DCplxTrans, width: float, layer_info: LayerInfo, name: str, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> DPort
```

```
create_port(*, width: float, layer_info: LayerInfo, center: tuple[float, float], orientation: float, name: str, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> DPort
```

```
create_port(*, trans: Trans, cross_section: CrossSectionSpecDict | DCrossSectionSpecDict | CrossSection | DCrossSection | SymmetricalCrossSection | AsymmetricalCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection, name: str, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> DPort
```

```
create_port(*, dcplx_trans: DCplxTrans, cross_section: CrossSectionSpecDict | DCrossSectionSpecDict | CrossSection | DCrossSection | SymmetricalCrossSection | AsymmetricalCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection, name: str, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> DPort
```

```
create_port(*, name: str, width: float | None = None, layer: LayerEnum | int | None = None, layer_info: LayerInfo | None = None, port_type: str = 'optical', trans: Trans | None = None, dcplx_trans: DCplxTrans | None = None, center: tuple[float, float] | None = None, orientation: float | None = None, mirror_x: bool = False, cross_section: CrossSectionSpecDict | DCrossSectionSpecDict | CrossSection | DCrossSection | SymmetricalCrossSection | AsymmetricalCrossSection | DAsymmetricalCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection | None = None, info: dict[str, MetaData] | None = None) -> DPort
```

Create a port.

## DPorts

Bases: `ProtoPorts[float]`, `DCreatePort`

A collection of um ports.

It is not a traditional dictionary. Elements can be retrieved as in a traditional dictionary. But to keep tabs on names etc, the ports are stored as a list

### \_\_iter\_\_

```
__iter__() -> Iterator[DPort]
```

Iterator, that allows for loops etc to directly access the object.

### \_\_repr\_\_

```
__repr__() -> str
```

Representation of the Ports as strings.

### add\_port

```
add_port(*, port: ProtoPort[Any], name: str | None = None, keep_mirror: bool = False) -> DPort
```

Add a port object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port` | `ProtoPort[Any]` | The port to add | *required* |
| `name` | `str \| None` | Overwrite the name of the port | `None` |
| `keep_mirror` | `bool` | Keep the mirror flag from the original port if `True`, else set Port.trans.mirror (or the complex equivalent) to `False`. Ports with an asymmetric cross section always keep their mirror flag, as it determines which side of the port the cross section lies on. | `False` |

### copy

```
copy(rename_function: Callable[[Sequence[DPort]], None] | None = None) -> Self
```

Get a copy of each port.

### filter

```
filter(angle: Angle | None = None, orientation: float | None = None, layer: LayerEnum | int | None = None, layer_info: LayerInfo | None = None, port_type: str | None = None, regex: str | None = None) -> list[DPort]
```

Filter ports by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `angle` | `Angle \| None` | Filter by angle. 0, 1, 2, 3. | `None` |
| `orientation` | `float \| None` | Alias for angle. | `None` |
| `layer` | `LayerEnum \| int \| None` | Filter by layer. | `None` |
| `port_type` | `str \| None` | Filter by port type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

### get\_all\_named

```
get_all_named() -> Mapping[str, DPort]
```

Get all ports in a dictionary with names as keys.

## ICreatePort

Bases: `ABC`

Protocol for a create\_port functionality

### create\_port

```
create_port(*, name: str, trans: Trans, cross_section: CrossSectionSpecDict | DCrossSectionSpecDict | CrossSection | DCrossSection | SymmetricalCrossSection | AsymmetricalCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> Port
```

```
create_port(*, name: str, trans: Trans, width: int, layer: int, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> Port
```

```
create_port(*, name: str, dcplx_trans: DCplxTrans, width: int, layer: LayerEnum | int, port_type: str = 'optical') -> Port
```

```
create_port(*, name: str, width: int, layer: LayerEnum | int, center: tuple[int, int], angle: Angle, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> Port
```

```
create_port(*, name: str, trans: Trans, width: int, layer_info: LayerInfo, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> Port
```

```
create_port(*, name: str, width: int, layer_info: LayerInfo, center: tuple[int, int], angle: Angle, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> Port
```

```
create_port(*, name: str, layer_info: LayerInfo, trans: Trans, cross_section: CrossSectionSpecDict | DCrossSectionSpecDict | CrossSection | DCrossSection | SymmetricalCrossSection | AsymmetricalCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> Port
```

```
create_port(*, name: str, dcplx_trans: DCplxTrans, cross_section: CrossSectionSpecDict | DCrossSectionSpecDict | CrossSection | DCrossSection | SymmetricalCrossSection | AsymmetricalCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection, port_type: str = 'optical', info: dict[str, MetaData] | None = None) -> Port
```

```
create_port(*, name: str, width: int | None = None, layer: LayerEnum | int | None = None, layer_info: LayerInfo | None = None, port_type: str = 'optical', trans: Trans | None = None, dcplx_trans: DCplxTrans | None = None, center: tuple[int, int] | None = None, angle: Angle | None = None, mirror_x: bool = False, cross_section: CrossSectionSpecDict | DCrossSectionSpecDict | CrossSection | DCrossSection | SymmetricalCrossSection | AsymmetricalCrossSection | DAsymmetricalCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection | None = None, info: dict[str, MetaData] | None = None) -> Port
```

Create a port.

## Ports

Bases: `ProtoPorts[int]`, `ICreatePort`

A collection of dbu ports.

It is not a traditional dictionary. Elements can be retrieved as in a traditional dictionary. But to keep tabs on names etc, the ports are stored as a list

### \_\_iter\_\_

```
__iter__() -> Iterator[Port]
```

Iterator, that allows for loops etc to directly access the object.

### \_\_repr\_\_

```
__repr__() -> str
```

Representation of the Ports as strings.

### add\_port

```
add_port(*, port: ProtoPort[Any], name: str | None = None, keep_mirror: bool = False) -> Port
```

Add a port object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port` | `ProtoPort[Any]` | The port to add | *required* |
| `name` | `str \| None` | Overwrite the name of the port | `None` |
| `keep_mirror` | `bool` | Keep the mirror flag from the original port if `True`, else set Port.trans.mirror (or the complex equivalent) to `False`. Ports with an asymmetric cross section always keep their mirror flag, as it determines which side of the port the cross section lies on. | `False` |

### copy

```
copy(rename_function: Callable[[Sequence[Port]], None] | None = None) -> Self
```

Get a copy of each port.

### filter

```
filter(angle: Angle | None = None, orientation: float | None = None, layer: LayerEnum | int | None = None, layer_info: LayerInfo | None = None, port_type: str | None = None, regex: str | None = None) -> list[Port]
```

Filter ports.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `angle` | `Angle \| None` | Filter by angle. 0, 1, 2, 3. | `None` |
| `orientation` | `float \| None` | Filter by orientation in degrees. | `None` |
| `layer` | `LayerEnum \| int \| None` | Filter by layer. | `None` |
| `port_type` | `str \| None` | Filter by port type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

### get\_all\_named

```
get_all_named() -> Mapping[str, Port]
```

Get all ports in a dictionary with names as keys.

## ProtoPorts

Bases: `Protocol`

Base class for kf.Ports, kf.DPorts.

### bases

```
bases: list[BasePort]
```

Get the bases.

### kcl

```
kcl: KCLayout
```

Get the KCLayout.

### \_\_contains\_\_

```
__contains__(port: str | ProtoPort[Any] | BasePort) -> bool
```

Check whether a port is in this port collection.

A string is matched against the port names. A port is matched with `BasePort.__eq__` against the collection's ports.

### \_\_eq\_\_

```
__eq__(other: object) -> bool
```

Support for `ports1 == ports2` comparisons.

### \_\_hash\_\_

```
__hash__() -> int
```

Hash the ports.

### \_\_init\_\_

```
__init__(*, kcl: KCLayout) -> None
```

```
__init__(*, kcl: KCLayout, ports: Iterable[ProtoPort[Any]] | None = None) -> None
```

```
__init__(*, kcl: KCLayout, bases: list[BasePort] | None = None) -> None
```

```
__init__(*, kcl: KCLayout, bases: list[BasePort], name_cache: dict[str | None, BasePort] | None = None) -> None
```

```
__init__(*, kcl: KCLayout, ports: Iterable[ProtoPort[Any]] | None = None, bases: list[BasePort] | None = None, name_cache: dict[str | None, BasePort] | None = None) -> None
```

Initialize the Ports.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout instance. | *required* |
| `ports` | `Iterable[ProtoPort[Any]] \| None` | The ports to add. | `None` |
| `bases` | `list[BasePort] \| None` | The bases to add. | `None` |
| `name_cache` | `dict[str \| None, BasePort] \| None` | Optional shared name lookup cache. | `None` |

### \_\_iter\_\_

```
__iter__() -> Iterator[ProtoPort[T]]
```

Iterator over the Ports.

### \_\_len\_\_

```
__len__() -> int
```

Return Port count.

### add\_port

```
add_port(*, port: ProtoPort[Any], name: str | None = None, keep_mirror: bool = False) -> ProtoPort[T]
```

Add a port.

### add\_ports

```
add_ports(ports: Iterable[ProtoPort[Any]], prefix: str = '', keep_mirror: bool = False, suffix: str = '') -> None
```

Append a list of ports.

### clear

```
clear() -> None
```

Deletes all ports.

### copy

```
copy(rename_function: Callable[[Sequence[ProtoPort[T]]], None] | None = None) -> Self
```

Get a copy of each port.

### filter

```
filter(angle: Angle | None = None, orientation: float | None = None, layer: LayerEnum | int | None = None, layer_info: LayerInfo | None = None, port_type: str | None = None, regex: str | None = None) -> Sequence[ProtoPort[T]]
```

Filter ports.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `angle` | `Angle \| None` | Filter by angle. 0, 1, 2, 3. | `None` |
| `orientation` | `float \| None` | Filter by orientation in degrees. | `None` |
| `layer` | `LayerEnum \| int \| None` | Filter by layer. | `None` |
| `port_type` | `str \| None` | Filter by port type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

### get\_all\_named

```
get_all_named() -> Mapping[str, ProtoPort[T]]
```

Get all ports in a dictionary with names as keys.

This filters out Ports with `None` as name.

### pformat

```
pformat(unit: Literal['dbu', 'um'] | None = None) -> str
```

Pretty print ports.

### print

```
print(unit: Literal['dbu', 'um'] | None = None) -> None
```

Pretty print ports.

### to\_dtype

```
to_dtype() -> DPorts
```

Convert to a DPorts.

### to\_itype

```
to_itype() -> Ports
```

Convert to a Ports.
