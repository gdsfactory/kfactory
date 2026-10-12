# layer

## LayerEnum

Bases: `int`, `Enum`

Class for having the layers stored and a mapping int \<-\> layer,datatype.

This Enum can also be treated as a tuple, i.e. it implements `__getitem__` and `__len__`.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `layer` | `int` | layer number |
| `datatype` | `int` | layer datatype |

### \_\_getitem\_\_

```
__getitem__(key: int) -> int
```

Retrieve layer number\[0\] / datatype\[1\] of a layer.

### \_\_init\_\_

```
__init__(layer: int, datatype: int) -> None
```

Just here to make sure klayout knows the layer name.

### \_\_iter\_\_

```
__iter__() -> Iterator[int]
```

Allow for loops to iterate over the LayerEnum.

### \_\_len\_\_

```
__len__() -> int
```

A layer has length 2, layer number and datatype.

### \_\_new\_\_

```
__new__(layer: int, datatype: int) -> Self
```

Create a new Enum.

Because it needs to act like an integer an enum is created and expanded.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `layer` | `int` | Layer number of the layer. | *required* |
| `datatype` | `int` | Datatype of the layer. | *required* |

### \_\_str\_\_

```
__str__() -> str
```

Return the name of the LayerEnum.

## LayerInfos

Bases: `BaseModel`

Class to store and serialize LayerInfos used in KCLayout.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kwargs` | `Any` | kdb.LayerInfo . if any extra field is not a kdb.LayerInfo, the validator will raise a ValidationError. | `{}` |

Config:

- `arbitrary_types_allowed`: `True`
- `extra`: `allow`

Validators:

- `_validate_layers`

### \_\_init\_\_

```
__init__(**kwargs: Any) -> None
```

Initialize the LayerInfos class.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kwargs` | `Any` | kdb.LayerInfo . if any extra field is not a kdb.LayerInfo, the validator will raise a ValidationError. | `{}` |

## LayerLevel

Bases: `BaseModel`

Level for 3D LayerStack.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `layer` | `tuple[int, int] \| LayerInfo` | (GDSII Layer number, GDSII datatype). | *required* |
| `thickness` | `float` | layer thickness in um. | *required* |
| `thickness_tolerance` | `float \| None` | layer thickness tolerance in um. | `None` |
| `zmin` | `float` | height position where material starts in um. | *required* |
| `material` | `str \| None` | material name. | `None` |
| `sidewall_angle` | `float` | in degrees with respect to normal. | `0.0` |
| `z_to_bias` | `tuple[int, ...] \| None` | parametrizes shrinking/expansion of the design GDS layer when extruding from zmin (0) to zmin + thickness (1). Defaults no buffering \[\[0, 1\], \[0, 0\]\]. | `None` |
| `info` | `Info \| None` | simulation\_info and other types of metadata. mesh\_order: lower mesh order (1) will have priority over higher mesh order (2) in the regions where materials overlap. refractive\_index: refractive\_index can be int, complex or function that depends on wavelength (um). type: grow, etch, implant, or background. mode: octagon, taper, round. https://gdsfactory.github.io/klayout\_pyxs/DocGrow.html into: etch into another layer. https://gdsfactory.github.io/klayout\_pyxs/DocGrow.html doping\_concentration: for implants. resistivity: for metals. bias: in um for the etch. | `None` |

Fields:

- `layer` (`tuple[int, int]`)
- `thickness` (`float`)
- `thickness_tolerance` (`float | None`)
- `zmin` (`float`)
- `material` (`str | None`)
- `sidewall_angle` (`float`)
- `z_to_bias` (`tuple[int, ...] | None`)
- `info` (`Info`)

## LayerStack

Bases: `BaseModel`

For simulation and 3D rendering.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `layers` | `LayerLevel` | dict of layer\_levels. | `{}` |

Fields:

- `layers` (`dict[str, LayerLevel]`)

### \_\_getitem\_\_

```
__getitem__(key: str) -> LayerLevel
```

Access layer stack elements.

### \_\_init\_\_

```
__init__(**layers: LayerLevel) -> None
```

Add LayerLevels automatically for subclassed LayerStacks.

### get\_layer\_to\_info

```
get_layer_to_info() -> dict[tuple[int, int], Info]
```

Returns layer tuple to info dict.

### get\_layer\_to\_material

```
get_layer_to_material() -> dict[tuple[int, int], str]
```

Returns layer tuple to material name.

### get\_layer\_to\_sidewall\_angle

```
get_layer_to_sidewall_angle() -> dict[tuple[int, int], float]
```

Returns layer tuple to material name.

### get\_layer\_to\_thickness

```
get_layer_to_thickness() -> dict[tuple[int, int], float]
```

Returns layer tuple to thickness (um).

### get\_layer\_to\_zmin

```
get_layer_to_zmin() -> dict[tuple[int, int], float]
```

Returns layer tuple to z min position (um).
