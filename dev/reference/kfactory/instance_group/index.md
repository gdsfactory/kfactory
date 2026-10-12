# instance\_group

## DInstanceGroup

Bases: `ProtoTInstanceGroup[float, DInstance]`, `UMGeometricObject`, `DCreatePort`

Group of DInstances.

The instance group can be treated similar to a single instance with regards to transformation functions and bounding boxes.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `insts` | `Sequence[TI] \| None` | List of the dinstances of the group. | `None` |

### ports

```
ports: DPorts
```

Ports of the instance.

## InstanceGroup

Bases: `ProtoTInstanceGroup[int, Instance]`, `DBUGeometricObject`, `ICreatePort`

Group of Instances.

The instance group can be treated similar to a single instance with regards to transformation functions and bounding boxes.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `insts` | `Sequence[TI] \| None` | List of the instances of the group. | `None` |

### ports

```
ports: Ports
```

Ports of the instance.

## ProtoInstanceGroup

Bases: `GeometricObject[T]`, `ABC`

### ports

```
ports: ProtoPorts[T]
```

Ports of the instance.

### \_\_init\_\_

```
__init__(insts: Sequence[TI] | None = None, ports: Sequence[ProtoPort[Any]] | None = None) -> None
```

Initialize the InstanceGroup.

### connect

```
connect(port: str | ProtoPort[Any] | None, other: ProtoPort[Any], *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> None
```

```
connect(port: str | ProtoPort[Any] | None, other: ProtoTInstance[Any], other_port_name: str | int | tuple[int | str, int, int] | None, *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> None
```

```
connect(port: str | ProtoPort[Any] | None, other: ProtoTInstance[Any] | ProtoPort[Any], other_port_name: str | int | tuple[int | str, int, int] | None = None, *, mirror: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, use_mirror: bool | None = None, use_angle: bool | None = None) -> None
```

Align port with name `portname` to a port.

Function to allow to transform this instance so that a port of this instance is connected (same center with 180° turn) to another instance.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port` | `str \| ProtoPort[Any] \| None` | The name of the port of this instance to be connected, or directly an instance port. Can be `None` because port names can be `None`. | *required* |
| `other` | `ProtoTInstance[Any] \| ProtoPort[Any]` | The other instance or a port. Skip `other_port_name` if it's a port. | *required* |
| `other_port_name` | `str \| int \| tuple[int \| str, int, int] \| None` | The name of the other port. Ignored if `other` is a port. | `None` |
| `mirror` | `bool` | Instead of applying klayout.db.Trans.R180 as a connection transformation, use klayout.db.Trans.M90, which effectively means this instance will be mirrored and connected. | `False` |
| `allow_width_mismatch` | `bool \| None` | Skip width check between the ports if set. | `None` |
| `allow_layer_mismatch` | `bool \| None` | Skip layer check between the ports if set. | `None` |
| `allow_type_mismatch` | `bool \| None` | Skip port\_type check between the ports if set. | `None` |
| `use_mirror` | `bool \| None` | If False mirror flag does not get applied from the connection. | `None` |
| `use_angle` | `bool \| None` | If False the angle does not get applied from the connection. | `None` |

### dbbox

```
dbbox(layer: int | None = None) -> kdb.DBox
```

Get the total bounding box or the bounding box of a layer in um.

### ibbox

```
ibbox(layer: int | None = None) -> kdb.Box
```

Get the total bounding box or the bounding box of a layer in dbu.

### transform

```
transform(trans: Trans | DTrans | ICplxTrans | DCplxTrans) -> None
```

Transform the instance group.

## VInstanceGroup

Bases: `ProtoInstanceGroup[float, VInstance]`, `UMGeometricObject`, `DCreatePort`

Group of DInstances.

The instance group can be treated similar to a single instance with regards to transformation functions and bounding boxes.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `insts` | `Sequence[TI] \| None` | List of the vinstances of the group. | `None` |

### ports

```
ports: DPorts
```

Ports of the instance.
