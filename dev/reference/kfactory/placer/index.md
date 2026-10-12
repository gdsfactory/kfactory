# placer

Placer of bends/straights from a route.

## cells\_from\_yaml

```
cells_from_yaml(inp: Path, kcl: KCLayout = stdkcl, additional_classes: list[object] | None = None, verbose: bool = False) -> None
```

Recreate cells from a yaml file.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `inp` | `Path` | Input file path. | *required* |
| `kcl` | `KCLayout` | KCLayout to load the cells into. | `kcl` |
| `additional_classes` | `list[object] \| None` | Additional yaml classes that should be registered. This is used for example to enable loading additional yaml files etc. | `None` |
| `verbose` | `bool` | Print more verbose errors etc. | `False` |

## cells\_to\_yaml

```
cells_to_yaml(output: PathLike, cells: Sequence[ProtoTKCell[Any]] | ProtoTKCell[Any] | Sequence[TKCell] | TKCell) -> None
```

Convert cell(s) to a yaml representations.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `output` | `PathLike` | A stream or string of a path where to dump the yaml. Can also be set to sys.stdout | *required* |
| `cells` | `Sequence[ProtoTKCell[Any]] \| ProtoTKCell[Any] \| Sequence[TKCell] \| TKCell` | A single KCell or a list of them. | *required* |

Returns:

| Type | Description |
| --- | --- |
| `None` | yaml dump |

## exploded\_yaml

```
exploded_yaml(inp: PathLike[Any], library: KCLayout = stdkcl, additional_classes: list[object] | None = None, verbose: bool = False) -> Any
```

Expanded yaml.

Expand cross-references. Same syntax as `cells_from_yaml`

## get\_yaml\_obj

```
get_yaml_obj() -> YAML
```

New global yaml object.

## include\_from\_loader

```
include_from_loader(folder: Path, library: KCLayout, additional_classes: list[object] | None, verbose: bool) -> Any
```

Expand ruamel to support the `!include` keyword.

## register\_classes

```
register_classes(yaml: YAML, kcl: KCLayout = stdkcl, additional_classes: list[object] | None = None, verbose: bool = False) -> None
```

Register a new KCell class compatible with ruamel yaml.
