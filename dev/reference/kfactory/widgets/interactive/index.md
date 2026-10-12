# interactive

Interactivate jupyter widget.

## LayoutWidget

### build\_selector

```
build_selector(max_height: float) -> Tab
```

Builds a widget for toggling layer displays.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `max_height` | `float` | Maximum height to set for the widget (likely the height of the pixel buffer). | *required* |

### load\_layout

```
load_layout(filepath: str, layer_properties: str | None) -> None
```

Loads a GDS layout.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `filepath` | `str` | path for the GDS layout. | *required* |
| `layer_properties` | `str \| None` | Optional path for the layer\_properties klayout file (lyp). | *required* |

## display\_kcell

```
display_kcell(kc: ProtoKCell[Any, Any], lyrdb: Path | str | None = None, display_type: Literal['image', 'widget'] | None = None) -> None
```

Display a KCell in a jupyter widget or an image.
