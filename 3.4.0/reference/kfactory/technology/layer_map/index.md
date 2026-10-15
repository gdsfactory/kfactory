# layer\_map

Utilities to go lyp \<-\> yaml.

## LayerGroupModel

Bases: `BaseModel`

A group of layers.

Fields:

- `name` (`str`)
- `members` (`list[LayerPropertiesModel | LayerGroupModel]`)

## LayerPropertiesModel

Bases: `BaseModel`

A leaf node in the layer properties.

Fields:

- `name` (`str`)
- `layer` (`tuple[int, int]`)
- `frame_color` (`Color | None`)
- `fill_color` (`Color | None`)
- `dither_pattern` (`int`)
- `line_style` (`int`)
- `visible` (`bool`)
- `width` (`int`)
- `xfill` (`bool`)
- `layer_to_name` (`bool`)
- `transparent` (`bool`)
- `valid` (`bool`)

Validators:

- `color_to_frame_fill`
- `dither_to_index` → `dither_pattern`
- `line_to_index` → `line_style`

### color\_to\_frame\_fill

```
color_to_frame_fill(data: dict[str, Any]) -> dict[str, Any]
```

Convert a color string to a frame fill.

### dither\_to\_index

```
dither_to_index(v: str | int) -> int
```

Convert string to the index with the dict dither2index.

### dither\_to\_json

```
dither_to_json(value: int) -> str
```

Convert dither int to string key on json dump.

### line\_to\_index

```
line_to_index(v: str | int) -> int
```

Convert string to the index with the dict dither2index.

### line\_to\_json

```
line_to_json(value: int) -> str
```

Convert dither int to string key on json dump.

## LypModel

Bases: `BaseModel`

Model for the whole lyp.

Fields:

- `layers` (`list[LayerGroupModel | LayerPropertiesModel]`)

## group2lp

```
group2lp(lp: LayerGroupModel) -> lay.LayerPropertiesNode
```

Convert a group model to a LayerPropertiesNode.

## kl2group

```
kl2group(iterable: LayerPropertiesIterator) -> list[LayerGroupModel | LayerPropertiesModel]
```

Convert a full LayerPropertiesIterator to a pydantic representation.

## kl2lp

```
kl2lp(kl: LayerPropertiesNodeRef) -> LayerPropertiesModel
```

Convert a KLayout LayerPropertiesNodeRef to a pydantic representation.

## lp2kl

```
lp2kl(lp: LayerPropertiesModel) -> lay.LayerPropertiesNode
```

LayerPropertiesModel to KLayout LayerPropertiesNode.

## lyp\_to\_lyp\_model

```
lyp_to_lyp_model(inp: Path | str) -> LypModel
```

Convert a lyp file to a LypModel.

## lyp\_to\_yaml

```
lyp_to_yaml(inp: Path | str, out: Path | str) -> None
```

Convert a lyp file to a YAML ffile.

## yaml\_to\_lyp

```
yaml_to_lyp(inp: Path | str, out: Path | str) -> None
```

Convert a YAML file to a lyp file readable by KLayout.
