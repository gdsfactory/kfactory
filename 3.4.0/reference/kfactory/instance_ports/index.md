# instance\_ports

## DInstancePorts

Bases: `ProtoTInstancePorts[float]`

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
__init__(instance: DInstance) -> None
```

Creates the virtual ports object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `instance` | `DInstance` | The related instance | *required* |

### filter

```
filter(angle: int | None = None, orientation: float | None = None, layer: LayerEnum | int | None = None, port_type: str | None = None, regex: str | None = None) -> Sequence[DPort]
```

Filter ports by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `angle` | `int \| None` | Filter by angle. 0, 1, 2, 3. | `None` |
| `orientation` | `float \| None` | Filter by orientation in degrees. | `None` |
| `layer` | `LayerEnum \| int \| None` | Filter by layer. | `None` |
| `port_type` | `str \| None` | Filter by port type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

## InstancePorts

Bases: `ProtoTInstancePorts[int]`

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
__init__(instance: Instance) -> None
```

Creates the virtual ports object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `instance` | `Instance` | The related instance | *required* |

### filter

```
filter(angle: int | None = None, orientation: float | None = None, layer: LayerEnum | int | None = None, port_type: str | None = None, regex: str | None = None) -> Sequence[Port]
```

Filter ports by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `angle` | `int \| None` | Filter by angle. 0, 1, 2, 3. | `None` |
| `orientation` | `float \| None` | Filter by orientation in degrees. | `None` |
| `layer` | `LayerEnum \| int \| None` | Filter by layer. | `None` |
| `port_type` | `str \| None` | Filter by port type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

## ProtoTInstancePorts

Bases: `ProtoInstancePorts[T, ProtoTInstance[T]]`, `ABC`

Ports of an Instance.

These act as virtual ports as the centers needs to change if the instance changes etc.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `cell_ports` | `ProtoPorts[T]` | A pointer to the `KCell.ports` of the cell |
| `instance` | `ProtoTInstance[T]` | A pointer to the Instance related to this. This provides a way to dynamically calculate the ports. |

### \_\_contains\_\_

```
__contains__(port: str | ProtoPort[Any] | BasePort) -> bool
```

Check whether a port is in this port collection.

A string is matched against the port names. A port is matched with `BasePort.__eq__` against the instance's ports.

### \_\_getitem\_\_

```
__getitem__(key: int | str | tuple[int | str | None, int, int] | None) -> ProtoPort[T]
```

Returns port from instance.

The key can either be an integer, in which case the nth port is returned, or a string in which case the first port with a matching name is returned.

If the instance is an array, the key can also be a tuple in the form of `c.ports[key_name, i_a, i_b]`, where `i_a` is the index in the `instance.a` direction and `i_b` the `instance.b` direction.

E.g. `c.ports["a", 3, 5]`, accesses the ports of the instance which is 3 times in `a` direction (4th index in the array), and 5 times in `b` direction (5th index in the array).

### \_\_len\_\_

```
__len__() -> int
```

Return Port count.

### copy

```
copy(rename_function: Callable[[list[Port]], None] | None = None) -> Ports
```

Creates a copy in the form of Ports.

### each\_port

```
each_port() -> Iterator[ProtoPort[T]]
```

Create a copy of the ports to iterate through.

### filter

```
filter(angle: int | None = None, orientation: float | None = None, layer: LayerEnum | int | None = None, port_type: str | None = None, regex: str | None = None) -> Sequence[ProtoPort[T]]
```

Filter ports by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `angle` | `int \| None` | Filter by angle. 0, 1, 2, 3. | `None` |
| `orientation` | `float \| None` | Filter by orientation in degrees. | `None` |
| `layer` | `LayerEnum \| int \| None` | Filter by layer. | `None` |
| `port_type` | `str \| None` | Filter by port type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

## VInstancePorts

Bases: `ProtoInstancePorts[float, VInstance]`

Ports of an instance.

These act as virtual ports as the centers needs to change if the instance changes etc.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `cell_ports` | `DPorts` | A pointer to the `KCell.ports` of the cell |
| `instance` | `VInstance` | A pointer to the Instance related to this. This provides a way to dynamically calculate the ports. |

### \_\_contains\_\_

```
__contains__(port: str | ProtoPort[Any] | BasePort) -> bool
```

Check whether a port is in this port collection.

A string is matched against the port names. A port is matched with `BasePort.__eq__` against the instance's ports.

### \_\_init\_\_

```
__init__(instance: VInstance) -> None
```

Creates the virtual ports object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `instance` | `VInstance` | The related instance | *required* |

### \_\_iter\_\_

```
__iter__() -> Iterator[DPort]
```

Create a copy of the ports to iterate through.

### \_\_len\_\_

```
__len__() -> int
```

Return Port count.

### copy

```
copy() -> DPorts
```

Creates a copy in the form of Ports.

### filter

```
filter(angle: int | None = None, orientation: float | None = None, layer: LayerEnum | int | None = None, port_type: str | None = None, regex: str | None = None) -> list[DPort]
```

Filter ports by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `angle` | `int \| None` | Filter by angle. 0, 1, 2, 3. | `None` |
| `orientation` | `float \| None` | Filter by orientation in degrees. | `None` |
| `layer` | `LayerEnum \| int \| None` | Filter by layer. | `None` |
| `port_type` | `str \| None` | Filter by port type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |
