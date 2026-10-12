# instance\_pins

## DInstancePins

Bases: `ProtoTInstancePins[float]`

### \_\_getitem\_\_

```
__getitem__(key: int | str | tuple[int | str, int, int]) -> DPin
```

Returns pin from instance.

The key can either be an integer, in which case the nth pin is returned, or a string in which case the first pin with a matching name is returned.

If the instance is an array, the key can also be a tuple in the form of `c.pins[key_name, i_a, i_b]`, where `i_a` is the index in the `instance.a` direction and `i_b` the `instance.b` direction.

E.g. `c.pins["a", 3, 5]`, accesses the pins of the instance which is 3 times in `a` direction (4th index in the array), and 5 times in `b` direction (5th index in the array).

Raises:

| Type | Description |
| --- | --- |
| `IndexError` | If the pin is an array pin and the index is out of range. |
| `KeyError` | If the pin name does not exist. |

Returns:

| Type | Description |
| --- | --- |
| `ProtoPin[T]` | Pin from instance by name or name and array index. |

### \_\_init\_\_

```
__init__(instance: DInstance) -> None
```

Creates the virtual pins object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `instance` | `DInstance` | The related instance | *required* |

### filter

```
filter(pin_type: str | None = None, regex: str | None = None) -> list[DPin]
```

Filter pins by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `pin_type` | `str \| None` | Filter by pin type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

Returns: Filtered list of pins.

## InstancePins

Bases: `ProtoTInstancePins[int]`

### \_\_getitem\_\_

```
__getitem__(key: int | str | tuple[int | str, int, int]) -> Pin
```

Returns pin from instance.

The key can either be an integer, in which case the nth pin is returned, or a string in which case the first pin with a matching name is returned.

If the instance is an array, the key can also be a tuple in the form of `c.pins[key_name, i_a, i_b]`, where `i_a` is the index in the `instance.a` direction and `i_b` the `instance.b` direction.

E.g. `c.pins["a", 3, 5]`, accesses the pins of the instance which is 3 times in `a` direction (4th index in the array), and 5 times in `b` direction (5th index in the array).

Raises:

| Type | Description |
| --- | --- |
| `IndexError` | If the pin is an array pin and the index is out of range. |
| `KeyError` | If the pin name does not exist. |

Returns:

| Type | Description |
| --- | --- |
| `ProtoPin[T]` | Pin from instance by name or name and array index. |

### \_\_init\_\_

```
__init__(instance: Instance) -> None
```

Creates the virtual pins object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `instance` | `Instance` | The related instance | *required* |

### filter

```
filter(pin_type: str | None = None, regex: str | None = None) -> list[Pin]
```

Filter pins by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `pin_type` | `str \| None` | Filter by pin type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

Returns: Filtered list of pins.

## ProtoTInstancePins

Bases: `ProtoInstancePins[T, ProtoTInstance[T]]`, `ABC`

Pins of an Instance.

These act as virtual pins as the centers needs to change if the instance changes etc.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `cell_pins` | `ProtoPins[T]` | A pointer to the `KCell.pins` of the cell |
| `instance` | `ProtoTInstance[T]` | A pointer to the Instance related to this. This provides a way to dynamically calculate the pins. |

### \_\_contains\_\_

```
__contains__(pin: str | ProtoPin[Any]) -> bool
```

Check whether a pin is in this pin collection.

### \_\_getitem\_\_

```
__getitem__(key: int | str | tuple[int | str, int, int]) -> ProtoPin[T]
```

Returns pin from instance.

The key can either be an integer, in which case the nth pin is returned, or a string in which case the first pin with a matching name is returned.

If the instance is an array, the key can also be a tuple in the form of `c.pins[key_name, i_a, i_b]`, where `i_a` is the index in the `instance.a` direction and `i_b` the `instance.b` direction.

E.g. `c.pins["a", 3, 5]`, accesses the pins of the instance which is 3 times in `a` direction (4th index in the array), and 5 times in `b` direction (5th index in the array).

Raises:

| Type | Description |
| --- | --- |
| `IndexError` | If the pin is an array pin and the index is out of range. |
| `KeyError` | If the pin name does not exist. |

Returns:

| Type | Description |
| --- | --- |
| `ProtoPin[T]` | Pin from instance by name or name and array index. |

### \_\_len\_\_

```
__len__() -> int
```

Return Pin count.

### copy

```
copy(rename_function: Callable[[list[Pin]], None] | None = None) -> Pins
```

Creates a copy in the form of Pins.

### each\_pin

```
each_pin() -> Iterator[ProtoPin[T]]
```

Create a copy of the pins to iterate through.

### filter

```
filter(pin_type: str | None = None, regex: str | None = None) -> Sequence[ProtoPin[T]]
```

Filter pins by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `pin_type` | `str \| None` | Filter by pin type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

Returns: Filtered list of pins.

## VInstancePins

Bases: `ProtoInstancePins[float, VInstance]`

Pins of an instance.

These act as virtual pins as the centers needs to change if the instance changes etc.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `cell_pins` | `DPins` | A pointer to the `KCell.pins` of the cell |
| `instance` | `VInstance` | A pointer to the Instance related to this. This provides a way to dynamically calculate the pins. |

### \_\_contains\_\_

```
__contains__(pin: str | ProtoPin[Any]) -> bool
```

Check if a pin is in the instance.

### \_\_getitem\_\_

```
__getitem__(key: int | str) -> DPin
```

Get a pin by name.

### \_\_init\_\_

```
__init__(instance: VInstance) -> None
```

Creates the virtual pins object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `instance` | `VInstance` | The related instance | *required* |

### \_\_iter\_\_

```
__iter__() -> Iterator[DPin]
```

Create a copy of the pins to iterate through.

### \_\_len\_\_

```
__len__() -> int
```

Return Pin count.

### copy

```
copy() -> DPins
```

Creates a copy in the form of Pins.

### filter

```
filter(pin_type: str | None = None, regex: str | None = None) -> list[DPin]
```

Filter pins by name.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `pin_type` | `str \| None` | Filter by pin type. | `None` |
| `regex` | `str \| None` | Filter by regex of the name. | `None` |

Returns: Filtered list of pins.
