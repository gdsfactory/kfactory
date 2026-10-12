# pin

## DPin

Bases: `ProtoPin[float]`

### \_\_getitem\_\_

```
__getitem__(key: int | str | None) -> DPort
```

Get a port in the pin by index or name.

### copy

```
copy(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> DPin
```

Get a copy of a pin.

Transformation order which results in `copy.trans`: - Trans: `trans * pin.trans * post_trans` - DCplxTrans: `trans * pin.dcplx_trans * post_trans`

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `trans` | `Trans \| DCplxTrans` | an optional transformation applied to the pin to be copied. | `R0` |
| `post_trans` | `Trans \| DCplxTrans` | transformation to apply to the pin after copying. | `R0` |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `pin` | `DPin` | a copy of the pin |

## Pin

Bases: `ProtoPin[int]`

### \_\_getitem\_\_

```
__getitem__(key: int | str | None) -> Port
```

Get a port in the pin by index or name.

### copy

```
copy(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> Pin
```

Get a copy of a pin.

Transformation order which results in `copy.trans`: - Trans: `trans * pin.trans * post_trans` - DCplxTrans: `trans * pin.dcplx_trans * post_trans`

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `trans` | `Trans \| DCplxTrans` | an optional transformation applied to the pin to be copied. | `R0` |
| `post_trans` | `Trans \| DCplxTrans` | transformation to apply to the pin after copying. | `R0` |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `pin` | `Pin` | a copy of the pin |

## ProtoPin

Bases: `ABC`

Base class for kf.Pin, kf.DPin.

### base

```
base: BasePin
```

Get the BasePin associated with this Pin.

### info

```
info: Info
```

Additional info about the pin.

### kcl

```
kcl: KCLayout
```

KCLayout associated to the pin.

### name

```
name: str | None
```

Name of the pin.

### pin\_type

```
pin_type: str
```

Type of the pin.

### \_\_getitem\_\_

```
__getitem__(key: int | str | None) -> ProtoPort[T]
```

Get a port in the pin by index or name.

### \_\_repr\_\_

```
__repr__() -> str
```

String representation of pin.

### copy

```
copy(trans: Trans | DCplxTrans = kdb.Trans.R0, post_trans: Trans | DCplxTrans = kdb.Trans.R0) -> ProtoPin[T]
```

Copy the port with a transformation.

### to\_dtype

```
to_dtype() -> DPin
```

Convert the pin to a um pin.

### to\_itype

```
to_itype() -> Pin
```

Convert the pin to a dbu pin.

## filter\_regex

```
filter_regex(pins: Iterable[TPin], regex: str) -> filter[TPin]
```

Filter iterable/sequence of pins by port name.

## filter\_type

```
filter_type(pins: Iterable[TPin], pin_type: str) -> filter[TPin]
```

Filter iterable/sequence of pins by port\_type.
