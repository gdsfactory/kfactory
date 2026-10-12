# pins

## DPins

Bases: `ProtoPins[float]`

### \_\_getitem\_\_

```
__getitem__(key: int | str) -> DPin
```

Get a specific pin by name.

### \_\_iter\_\_

```
__iter__() -> Iterator[DPin]
```

Iterator, that allows for loops etc to directly access the object.

### create\_pin

```
create_pin(*, name: str, ports: Iterable[ProtoPort[Any]], pin_type: str = 'DC', info: dict[str, MetaData] | None = None) -> DPin
```

Add a pin to Pins.

### get\_all\_named

```
get_all_named() -> Mapping[str, DPin]
```

Get all pins in a dictionary with names as keys.

## Pins

Bases: `ProtoPins[int]`

### \_\_getitem\_\_

```
__getitem__(key: int | str | None) -> Pin
```

Get a specific pin by name.

### \_\_iter\_\_

```
__iter__() -> Iterator[Pin]
```

Iterator, that allows for loops etc to directly access the object.

### create\_pin

```
create_pin(*, name: str, ports: Iterable[ProtoPort[Any]], pin_type: str = 'DC', info: dict[str, MetaData] | None = None) -> Pin
```

Add a pin to Pins.

### get\_all\_named

```
get_all_named() -> Mapping[str, Pin]
```

Get all pins in a dictionary with names as keys.

### print

```
print(unit: Literal['dbu', 'um'] | None = None) -> None
```

Pretty print ports.

## ProtoPins

Bases: `Protocol`

### bases

```
bases: list[BasePin]
```

Get the bases.

### kcl

```
kcl: KCLayout
```

KCLayout associated to the pins.

### \_\_contains\_\_

```
__contains__(pin: str | ProtoPin[Any] | BasePin) -> bool
```

Check whether a pin is in this pin collection.

### \_\_getitem\_\_

```
__getitem__(key: int | str) -> ProtoPin[T]
```

Get a pin by index or name.

### \_\_iter\_\_

```
__iter__() -> Iterator[ProtoPin[T]]
```

Iterator over the Pins.

### \_\_len\_\_

```
__len__() -> int
```

Return Pin count.

### create\_pin

```
create_pin(*, name: str, ports: Iterable[ProtoPort[Any]], pin_type: str = 'DC', info: dict[str, MetaData] | None = None) -> ProtoPin[T]
```

Add a pin.

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

### get\_all\_named

```
get_all_named() -> Mapping[str, ProtoPin[T]]
```

Get all pins in a dictionary with names as keys.

This filters out Pins with `None` as name.

### to\_dtype

```
to_dtype() -> DPins
```

Convert to a DPins.

### to\_itype

```
to_itype() -> Pins
```

Convert to a Ports.
