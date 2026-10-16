# instance

## DInstance

Bases: `ProtoTInstance[float]`, `UMGeometricObject`

An Instance of a KCell.

An Instance is a reference to a KCell with a transformation.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `_instance` |  | The internal `kdb.Instance` reference |
| `ports` | `DInstancePorts` | Transformed ports of the KCell |
| `kcl` |  | Pointer to the layout object holding the instance |
| `d` |  | Helper that allows retrieval of instance information in um |

### cell

```
cell: DKCell
```

Parent KCell of the Instance.

### kcl

```
kcl = kcl
```

KCLayout object.

### parent\_cell

```
parent_cell: DKCell
```

Gets the cell this instance is contained in.

### pins

```
pins: DInstancePins
```

Gets the transformed ports of the KCell.

### ports

```
ports: DInstancePorts
```

Gets the transformed ports of the KCell.

### \_\_getitem\_\_

```
__getitem__(key: int | str | tuple[int | str | None, int, int] | None) -> DPort
```

Returns port from instance.

The key can either be an integer, in which case the nth port is returned, or a string in which case the first port with a matching name is returned.

If the instance is an array, the key can also be a tuple in the form of `c.ports[key_name, i_a, i_b]`, where `i_a` is the index in the `instance.a` direction and `i_b` the `instance.b` direction.

E.g. `c.ports["a", 3, 5]`, accesses the ports of the instance which is 3 times in `a` direction (4th index in the array), and 5 times in `b` direction (5th index in the array).

### \_\_init\_\_

```
__init__(kcl: KCLayout, instance: Instance) -> None
```

Create an instance from a KLayout Instance.

## Instance

Bases: `ProtoTInstance[int]`, `DBUGeometricObject`

An Instance of a KCell.

An Instance is a reference to a KCell with a transformation.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `_instance` |  | The internal `kdb.Instance` reference |
| `ports` | `InstancePorts` | Transformed ports of the KCell |
| `kcl` |  | Pointer to the layout object holding the instance |
| `d` |  | Helper that allows retrieval of instance information in um |

### cell

```
cell: KCell
```

Parent KCell of the Instance.

### kcl

```
kcl = kcl
```

KCLayout object.

### parent\_cell

```
parent_cell: KCell
```

Gets the cell this instance is contained in.

### pins

```
pins: InstancePins
```

Gets the transformed pins of the KCell.

### ports

```
ports: InstancePorts
```

Gets the transformed ports of the KCell.

### \_\_getitem\_\_

```
__getitem__(key: int | str | tuple[int | str | None, int, int] | None) -> Port
```

Returns port from instance.

The key can either be an integer, in which case the nth port is returned, or a string in which case the first port with a matching name is returned.

If the instance is an array, the key can also be a tuple in the form of `c.ports[key_name, i_a, i_b]`, where `i_a` is the index in the `instance.a` direction and `i_b` the `instance.b` direction.

E.g. `c.ports["a", 3, 5]`, accesses the ports of the instance which is 3 times in `a` direction (4th index in the array), and 5 times in `b` direction (5th index in the array).

### \_\_init\_\_

```
__init__(kcl: KCLayout, instance: Instance) -> None
```

Create an instance from a KLayout Instance.

### to\_yaml

```
to_yaml(representer: BaseRepresenter, node: Self) -> MappingNode
```

Convert the instance to a yaml representation.

## ProtoInstance

Bases: `GeometricObject[T]`

Base class for instances.

### cell\_name

```
cell_name: str | None
```

Name of the cell the instance refers to.

### kcl

```
kcl: KCLayout
```

KCLayout object.

### name

```
name: str | None
```

Name of the instance.

## ProtoTInstance

Bases: `ProtoInstance[T]`

### a

```
a: Vector
```

Returns the displacement vector for the 'a' axis.

### b

```
b: Vector
```

Returns the displacement vector for the 'b' axis.

### cell

```
cell: ProtoTKCell[T]
```

Parent KCell of the Instance.

### cell\_index

```
cell_index: int
```

Get the index of the cell this instance refers to.

### cell\_inst

```
cell_inst: CellInstArray
```

Gets the basic CellInstArray object associated with this instance.

### cell\_name

```
cell_name: str
```

Name of the cell the instance refers to.

### cplx\_trans

```
cplx_trans: ICplxTrans
```

Gets the complex transformation of the instance.

Or the first instance in the array.

### dcplx\_trans

```
dcplx_trans: DCplxTrans
```

Gets the complex transformation of the instance.

Or the first instance in the array.

### dtrans

```
dtrans: DTrans
```

Gets the complex transformation of the instance.

Or the first instance in the array.

### hash

```
hash: bytes
```

Hash the instance.

### info

```
info: Info
```

Metadata owned by the parent cell and keyed by an explicit name.

### na

```
na: int
```

Returns the displacement vector for the 'a' axis.

### name

```
name: str
```

Name of instance in GDS.

### nb

```
nb: int
```

Returns the number of instances in the 'b' axis.

### pins

```
pins: ProtoTInstancePins[T]
```

Ports of the instance.

### ports

```
ports: ProtoTInstancePorts[T]
```

Ports of the instance.

### prop\_id

```
prop_id: int
```

Gets the properties ID associated with the instance.

### purpose

```
purpose: str | None
```

Purpose value of instance in GDS.

### trans

```
trans: Trans
```

Gets the complex transformation of the instance.

Or the first instance in the array.

### \_\_getattr\_\_

```
__getattr__(name: str) -> Any
```

If we don't have an attribute, get it from the instance.

### \_\_repr\_\_

```
__repr__() -> str
```

Return a string representation of the instance.

### connect

```
connect(port: str | ProtoPort[Any] | None, other: ProtoPort[Any], *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, allow_cross_section_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> Self
```

```
connect(port: str | ProtoPort[Any] | None, other: ProtoTInstance[Any], other_port_name: str | int | tuple[int | str, int, int] | None, *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, allow_cross_section_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> Self
```

```
connect(port: str | ProtoPort[Any] | None, other: VInstance, other_port_name: str | int | None, *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, allow_cross_section_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> Self
```

```
connect(port: str | ProtoPort[Any] | None, other: ProtoInstance[Any] | ProtoPort[Any], other_port_name: str | int | tuple[int | str, int, int] | None = None, *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, allow_cross_section_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> Self
```

Align port with name `portname` to a port.

Function to allow to transform this instance so that a port of this instance is connected (same center with 180° turn) to another instance.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port` | `str \| ProtoPort[Any] \| None` | The name of the port of this instance to be connected, or directly an instance port. Can be `None` because port names can be `None`. | *required* |
| `other` | `ProtoInstance[Any] \| ProtoPort[Any]` | The other instance or a port. Skip `other_port_name` if it's a port. | *required* |
| `other_port_name` | `str \| int \| tuple[int \| str, int, int] \| None` | The name of the other port. Ignored if `other` is a port. | `None` |
| `mirror` | `bool` | Instead of applying klayout.db.Trans.R180 as a connection transformation, use klayout.db.Trans.M90, which effectively means this instance will be mirrored and connected. | `False` |
| `allow_width_mismatch` | `bool \| None` | Skip width check between the ports if set. | `None` |
| `allow_layer_mismatch` | `bool \| None` | Skip layer check between the ports if set. | `None` |
| `allow_type_mismatch` | `bool \| None` | Skip port\_type check between the ports if set. | `None` |
| `allow_cross_section_mismatch` | `bool \| None` | Only compare the core offsets of asymmetric cross sections if set, instead of requiring identical cross sections. Asymmetric profiles must not be flipped against each other either way. These checks only apply to ports with the same width and layer. | `None` |
| `use_mirror` | `bool \| None` | If False mirror flag does not get applied from the connection. | `None` |
| `use_angle` | `bool \| None` | If False the angle does not get applied from the connection. | `None` |

### delete

```
delete() -> None
```

Delete the instance and its parent-owned metadata.

### flatten

```
flatten(levels: int | None = None) -> None
```

Flatten all or just certain instances.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `levels` | `int \| None` | If level \< \#hierarchy-levels -\> pull the sub instances to self, else pull the polygons. None will always flatten all levels. | `None` |

## VInstance

Bases: `ProtoInstance[float]`, `UMGeometricObject`

### a

```
a: DVector
```

Returns the displacement vector for the 'a' axis.

### b

```
b: DVector
```

Returns the displacement vector for the 'b' axis.

### cell\_name

```
cell_name: str | None
```

Name of the cell the instance refers to.

### kcl

```
kcl = cell.kcl
```

KCLayout object.

### name

```
name: str | None
```

Name of the instance.

### \_\_getitem\_\_

```
__getitem__(key: int | str | tuple[int | str | None, int, int] | None) -> DPort
```

Returns port from instance.

The key can either be an integer, in which case the nth port is returned, or a string in which case the first port with a matching name is returned.

If the instance is an array, the key can also be a tuple in the form of `c.ports[key_name, i_a, i_b]`, where `i_a` is the index in the `instance.a` direction and `i_b` the `instance.b` direction.

E.g. `c.ports["a", 3, 5]`, accesses the ports of the instance which is 3 times in `a` direction (4th index in the array), and 5 times in `b` direction (5th index in the array).

### \_\_repr\_\_

```
__repr__() -> str
```

Return a string representation of the instance.

### connect

```
connect(port: str | ProtoPort[Any] | None, other: ProtoPort[Any], *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, allow_cross_section_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> Self
```

```
connect(port: str | ProtoPort[Any] | None, other: ProtoTInstance[Any], other_port_name: str | int | tuple[int | str, int, int] | None, *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, allow_cross_section_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> Self
```

```
connect(port: str | ProtoPort[Any] | None, other: VInstance, other_port_name: str | int | None, *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, allow_cross_section_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> Self
```

```
connect(port: str | ProtoPort[Any] | None, other: ProtoInstance[Any] | ProtoPort[Any], other_port_name: str | int | tuple[int | str, int, int] | None = None, *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, allow_cross_section_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> Self
```

Align port with name `portname` to a port.

Function to allow to transform this instance so that a port of this instance is connected (same center with 180° turn) to another instance.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port` | `str \| ProtoPort[Any] \| None` | The name of the port of this instance to be connected, or directly an instance port. Can be `None` because port names can be `None`. | *required* |
| `other` | `ProtoInstance[Any] \| ProtoPort[Any]` | The other instance or a port. Skip `other_port_name` if it's a port. | *required* |
| `other_port_name` | `str \| int \| tuple[int \| str, int, int] \| None` | The name of the other port. Ignored if `other` is a port. | `None` |
| `mirror` | `bool` | Instead of applying klayout.db.Trans.R180 as a connection transformation, use klayout.db.Trans.M90, which effectively means this instance will be mirrored and connected. | `False` |
| `allow_width_mismatch` | `bool \| None` | Skip width check between the ports if set. | `None` |
| `allow_layer_mismatch` | `bool \| None` | Skip layer check between the ports if set. | `None` |
| `allow_type_mismatch` | `bool \| None` | Skip port\_type check between the ports if set. | `None` |
| `allow_cross_section_mismatch` | `bool \| None` | Only compare the core offsets of asymmetric cross sections if set, instead of requiring identical cross sections. Asymmetric profiles must not be flipped against each other either way. These checks only apply to ports with the same width and layer. | `None` |
| `use_mirror` | `bool \| None` | If False mirror flag does not get applied from the connection. | `None` |
| `use_angle` | `bool \| None` | If False the angle does not get applied from the connection. | `None` |
